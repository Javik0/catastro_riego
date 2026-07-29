# -*- coding: utf-8 -*-
"""
Clasifica los predios con area declarada > area catastral segun su ORIGEN:

  A) INYECTADO POR SCRIPT  fichas de ALPAKA creadas desde el Excel de
                           fraccionamiento (codigo_final 'LOTE x-y' o los 2
                           'S-C-P001' representativos). Si estan mal, es error
                           nuestro y se corrige con el area del poligono.
  B) AUTO-SECCION7         fichas hijas generadas automaticamente desde la
                           Seccion 7. Heredan el area que declaro la ficha madre.
  C) CAMPO                 levantadas por un tecnico en terreno. Aqui el dato
                           es lo que dijo el regante; se corrige con criterio,
                           no se inventa.

Solo MIDE y lista. No modifica nada.

Uso:  python -X utf8 padron-app/scratch/clasificar_areas_infladas.py
"""
import collections
import json
import os

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
GEO = os.path.join(BASE, 'public', 'geo')


def cargar(n):
    with open(os.path.join(GEO, n), encoding='utf-8') as f:
        return json.load(f)


def es_hija(p):
    return p.get('es_ficha_hija') in (1, True)


def origen(f):
    """De donde salio esta ficha."""
    com = str(f.get('comunidad') or '').upper().strip()
    cod = str(f.get('codigo_final') or '').upper().strip()
    creado = str(f.get('creado_por') or '').strip()
    if com == 'ALPAKA' and (cod.startswith('LOTE ') or cod == 'S-C-P001'):
        return 'A) inyectado ALPAKA'
    if creado == 'AUTO-SECCION7':
        return 'B) auto Seccion 7'
    return 'C) campo'


def main():
    fichas = [f['properties'] for f in cargar('fichas_predios.geojson')['features']]
    catastro = cargar('catastro_geo.geojson')['features']
    cultivos = cargar('cultivos.json')

    area_cat = {}
    for ft in catastro:
        p = ft.get('properties') or {}
        k = str(p.get('clave_cata') or '').strip()
        if k and p.get('area_predi'):
            area_cat[k] = float(p['area_predi'])

    cult_por_ficha = collections.defaultdict(list)
    for c in cultivos:
        cult_por_ficha[c.get('ficha_id')].append(c)

    # agrupar por clave (solo principales: las hijas se cuentan aparte)
    por_clave = collections.defaultdict(list)
    for f in fichas:
        k = str(f.get('clave_catastral') or f.get('cod_poligono') or '').strip()
        if k and not es_hija(f):
            por_clave[k].append(f)

    casos = []
    for k, fs in por_clave.items():
        ac = area_cat.get(k)
        if not ac or ac <= 0:
            continue
        suma = sum(f.get('area_total') or 0 for f in fs)
        if suma <= ac * 1.05:
            continue
        # cada ficha individual: excede ella sola el poligono?
        detalle = []
        for f in fs:
            at = f.get('area_total') or 0
            sup = sum(c.get('superficie_m2') or 0 for c in cult_por_ficha.get(f.get('id'), []))
            detalle.append({
                'ficha_id': f.get('id'), 'codigo': f.get('codigo_final'),
                'regante': ("{} {}".format(f.get('apellidos') or '', f.get('nombres') or '')).strip(),
                'cedula': f.get('cedula'), 'comunidad': f.get('comunidad'),
                'tecnico': f.get('creado_por'), 'origen': origen(f),
                'area_declarada': round(at, 2), 'area_catastral': round(ac, 2),
                'factor': round(at / ac, 2) if ac else 0,
                'sup_cultivos': round(sup, 2),
                'declara_exacto_el_poligono': abs(at - ac) < 1.0,
            })
        casos.append({'clave': k, 'comunidad': fs[0].get('comunidad'),
                      'n_fichas': len(fs), 'area_catastral': round(ac, 2),
                      'suma_declarada': round(suma, 2), 'factor': round(suma / ac, 2),
                      'fichas': detalle})

    print("=" * 78)
    print(" CLASIFICACION POR ORIGEN DE LOS PREDIOS CON AREA INFLADA")
    print("=" * 78)
    print("\nPredios afectados: {}".format(len(casos)))

    # clasificar cada predio por el origen de sus fichas
    tipo_predio = collections.Counter()
    por_origen = collections.Counter()
    for c in casos:
        origenes = {f['origen'] for f in c['fichas']}
        tipo_predio['+'.join(sorted(origenes))] += 1
        for f in c['fichas']:
            por_origen[f['origen']] += 1

    print("\n--- FICHAS INVOLUCRADAS, POR ORIGEN ---")
    for o, n in sorted(por_origen.items()):
        print("  {:<24} {:>5} fichas".format(o, n))

    print("\n--- PREDIOS SEGUN QUE ORIGENES MEZCLAN ---")
    for t, n in tipo_predio.most_common():
        print("  {:<40} {:>4} predios".format(t, n))

    # ── A) los inyectados: cuanto se desvian ──
    iny = [c for c in casos if any(f['origen'].startswith('A)') for f in c['fichas'])]
    print("\n" + "=" * 78)
    print(" A) INYECTADOS POR SCRIPT (ALPAKA) — error nuestro, corregible")
    print("=" * 78)
    print("  predios: {}".format(len(iny)))
    for c in iny:
        print("\n  clave {}  poligono {:,.0f} m2   declarado {:,.0f} m2  ({}x)".format(
            c['clave'], c['area_catastral'], c['suma_declarada'], c['factor']))
        for f in c['fichas']:
            print("     [{}] {:<12} {:<32} declara {:>12,.0f} m2  cultivos {:>12,.0f} m2".format(
                f['origen'][:1], f['codigo'] or '', (f['regante'] or '')[:32],
                f['area_declarada'], f['sup_cultivos']))

    # ── C) campo: el patron de "clave equivocada" ──
    print("\n" + "=" * 78)
    print(" C) CAMPO — fichas UNICAS que solas exceden el poligono")
    print("=" * 78)
    solitarias = []
    for c in casos:
        if c['n_fichas'] == 1:
            f = c['fichas'][0]
            if f['origen'].startswith('C'):
                solitarias.append((c, f))
    print("  predios con 1 sola ficha de campo que excede el poligono: {}".format(len(solitarias)))
    # agrupar por area declarada repetida: sintoma de clave mal asignada
    repes = collections.Counter(f['area_declarada'] for _, f in solitarias)
    print("\n  areas declaradas que se repiten en varios predios distintos")
    print("  (sintoma de que la clave catastral asignada no corresponde):")
    for area, n in repes.most_common(8):
        if n > 1:
            coms = {f['comunidad'] for _, f in solitarias if f['area_declarada'] == area}
            print("     {:>12,.0f} m2 declarados en {:>3} predios distintos   {}".format(
                area, n, ', '.join(sorted(c or '' for c in coms))[:50]))

    print("\n  por tecnico:")
    for t, n in collections.Counter(f['tecnico'] for _, f in solitarias).most_common():
        print("     {:<24} {:>4}".format(str(t), n))

    ruta = os.path.abspath(os.path.join(BASE, '..', 'logs_depuracion', 'areas_infladas_clasificadas.json'))
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    with open(ruta, 'w', encoding='utf-8') as f:
        json.dump({'resumen': {'predios': len(casos), 'por_origen': dict(por_origen),
                               'inyectados': len(iny), 'campo_solitarias': len(solitarias)},
                   'casos': casos}, f, ensure_ascii=False, indent=2)
    print("\n  detalle: {}".format(ruta))


if __name__ == '__main__':
    main()
