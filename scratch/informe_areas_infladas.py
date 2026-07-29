# -*- coding: utf-8 -*-
"""
INFORME: predios donde la suma de areas declaradas excede el poligono catastral.

Origen del problema: cuando varias fichas comparten la misma clave catastral
(tipico en terrenos comunales que el catastro nunca subdividio), es frecuente que
cada regante declare la extension del terreno COMPLETO en lugar de su parcela.
Al sumar, el area declarada del predio se multiplica.

Es el mismo patron que ya se corrigio en ALPAKA (donde cada lote declaraba el
area del fraccionamiento entero), pero aqui aparece en cientos de predios.

Este script SOLO MIDE. No modifica nada. Sirve para decidir con numeros.

Uso:  python -X utf8 padron-app/scratch/informe_areas_infladas.py
"""
import collections
import json
import os

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
GEO = os.path.join(BASE, 'public', 'geo')


def cargar(nombre):
    with open(os.path.join(GEO, nombre), encoding='utf-8') as f:
        return json.load(f)


def main():
    fichas = [f['properties'] for f in cargar('fichas_predios.geojson')['features']]
    catastro = cargar('catastro_geo.geojson')['features']
    cultivos = cargar('cultivos.json')

    # area catastral por clave
    area_cat = {}
    for ft in catastro:
        p = ft.get('properties') or {}
        k = str(p.get('clave_cata') or '').strip()
        if k and p.get('area_predi'):
            area_cat[k] = float(p['area_predi'])

    def es_hija(p):
        return p.get('es_ficha_hija') in (1, True)

    # agrupar fichas PRINCIPALES por clave
    por_clave = collections.defaultdict(list)
    for f in fichas:
        if es_hija(f):
            continue
        k = str(f.get('clave_catastral') or f.get('cod_poligono') or '').strip()
        if k:
            por_clave[k].append(f)

    cult_por_ficha = collections.defaultdict(list)
    for c in cultivos:
        cult_por_ficha[c.get('ficha_id')].append(c)

    print("=" * 78)
    print(" AREAS DECLARADAS QUE EXCEDEN EL POLIGONO CATASTRAL")
    print("=" * 78)

    casos = []
    for k, fs in por_clave.items():
        ac = area_cat.get(k)
        if not ac or ac <= 0:
            continue
        suma = sum(f.get('area_total') or 0 for f in fs)
        if suma <= ac * 1.05:          # 5% de tolerancia por redondeos
            continue
        # cuantas fichas declaran EXACTAMENTE el area del poligono
        iguales = sum(1 for f in fs if f.get('area_total') and abs(f['area_total'] - ac) < 1.0)
        sup_cult = sum(c.get('superficie_m2') or 0
                       for f in fs for c in cult_por_ficha.get(f.get('id'), []))
        casos.append({
            'clave': k, 'comunidad': (fs[0].get('comunidad') or ''), 'n': len(fs),
            'area_cat': ac, 'suma': suma, 'factor': suma / ac,
            'iguales': iguales, 'sup_cult': sup_cult,
        })

    casos.sort(key=lambda c: -c['factor'])

    tot_cat = sum(c['area_cat'] for c in casos)
    tot_dec = sum(c['suma'] for c in casos)
    print("\nPredios afectados: {}".format(len(casos)))
    print("  area catastral de esos predios : {:>14,.0f} m2  ({:,.1f} ha)".format(tot_cat, tot_cat / 10000))
    print("  area declarada sumada          : {:>14,.0f} m2  ({:,.1f} ha)".format(tot_dec, tot_dec / 10000))
    print("  exceso                         : {:>14,.0f} m2  ({:,.1f} ha)  -> {:.1f}x".format(
        tot_dec - tot_cat, (tot_dec - tot_cat) / 10000, tot_dec / tot_cat if tot_cat else 0))

    # cuantos casos son "todos declaran el poligono completo"
    clonados = [c for c in casos if c['iguales'] >= 2]
    print("\n  de esos, con 2 o mas fichas declarando EXACTAMENTE el area del poligono: {}".format(
        len(clonados)))
    print("  (ese es el patron claro de 'cada uno declaro el terreno completo')")

    print("\n--- POR RANGO DE EXAGERACION ---")
    rangos = [(1.05, 1.5, '1.05x a 1.5x'), (1.5, 3, '1.5x a 3x'),
              (3, 6, '3x a 6x'), (6, 11, '6x a 11x'), (11, 1e9, 'mas de 11x')]
    for lo, hi, etq in rangos:
        sub = [c for c in casos if lo <= c['factor'] < hi]
        if sub:
            print("  {:<16} {:>4} predios   exceso {:>12,.1f} ha".format(
                etq, len(sub), sum(c['suma'] - c['area_cat'] for c in sub) / 10000))

    print("\n--- LOS 15 CASOS MAS GRAVES ---")
    print("  {:<15} {:<22} {:>3} {:>12} {:>13} {:>7} {:>6}".format(
        'clave', 'comunidad', 'fic', 'catastro m2', 'declarado m2', 'factor', 'clon'))
    for c in casos[:15]:
        print("  {:<15} {:<22} {:>3} {:>12,.0f} {:>13,.0f} {:>6.1f}x {:>6}".format(
            c['clave'], c['comunidad'][:22], c['n'], c['area_cat'], c['suma'],
            c['factor'], c['iguales']))

    print("\n--- IMPACTO EN SUPERFICIE SEMBRADA ---")
    imposibles = [c for c in casos if c['sup_cult'] > c['area_cat'] * 1.05]
    print("  predios donde los cultivos declarados NO CABEN en el poligono: {}".format(
        len(imposibles)))
    if imposibles:
        exceso = sum(c['sup_cult'] - c['area_cat'] for c in imposibles)
        print("  superficie sembrada que excede el terreno: {:,.1f} ha".format(exceso / 10000))
        print("\n  los 8 peores:")
        for c in sorted(imposibles, key=lambda x: -(x['sup_cult'] / x['area_cat']))[:8]:
            print("     {} {:<20} poligono {:>10,.0f} m2  sembrado {:>12,.0f} m2  ({:.1f}x)".format(
                c['clave'], c['comunidad'][:20], c['area_cat'], c['sup_cult'],
                c['sup_cult'] / c['area_cat']))

    print("\n--- POR COMUNIDAD ---")
    porcom = collections.Counter(c['comunidad'] for c in casos)
    for com, n in porcom.most_common(10):
        print("  {:<34} {:>4} predios".format(com or '(sin comunidad)', n))

    # guardar el detalle para revisarlo en Excel
    ruta = os.path.join(BASE, '..', 'logs_depuracion', 'areas_infladas.json')
    ruta = os.path.abspath(ruta)
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    with open(ruta, 'w', encoding='utf-8') as f:
        json.dump({
            'resumen': {
                'predios_afectados': len(casos),
                'area_catastral_ha': round(tot_cat / 10000, 2),
                'area_declarada_ha': round(tot_dec / 10000, 2),
                'exceso_ha': round((tot_dec - tot_cat) / 10000, 2),
                'con_fichas_clonando_el_poligono': len(clonados),
                'cultivos_que_no_caben': len(imposibles),
            },
            'detalle': casos,
        }, f, ensure_ascii=False, indent=2)
    print("\n  detalle guardado en: {}".format(ruta))


if __name__ == '__main__':
    main()
