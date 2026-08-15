# -*- coding: utf-8 -*-
"""
Cuánta superficie tiene el sistema, medida de las cuatro maneras que importan.

Por qué hace falta una fuente única
-----------------------------------
La superficie del padrón se puede medir de dos formas y **las dos son ciertas**:

* **Declarada** — lo que cada regante dijo que tiene. Es el dato social: lo que
  la gente considera suyo. Suma 9.872,77 ha.
* **Catastral** — la suma de los polígonos del GADM, contando cada predio una
  sola vez. Es el dato territorial: lo que hay en el suelo. Suma 8.092,45 ha.

La diferencia —1.780 ha, un 22 %— no es un error de nadie: en los predios de
herederos, cada uno declara el predio familiar completo, y al sumar fichas ese
terreno se cuenta tantas veces como titulares tenga. Con 435 predios en esa
situación, sumar fichas infla y sumar polígonos no.

La decisión del proyecto (14-ago-2026) fue **no repartir a mano lo que nadie
midió**: la superficie del sistema se mide por polígonos únicos, y lo declarado
se conserva intacto porque es material de análisis para el sociólogo. Este
script publica ambas para que ningún informe tenga que recalcularlas por su
cuenta —que es como se pierden los datos en silencio (regla 4).

Las cuatro cifras
-----------------
    superficie_declarada_ha   suma de `area_total` de las fichas
    superficie_catastral_ha   suma de los polígonos distintos del GADM
    riego_declarado_ha        suma de `area_riego` de las fichas
    riego_ajustado_ha         el riego declarado recortado a lo que cabe en el
                              polígono, en proporción a lo que declaró cada uno

Sobre el riego ajustado: cuando las fichas de un predio declaran más superficie
que la que el predio mide, su riego se reduce en la misma proporción. No inventa
reparto —respeta el peso de lo que cada regante declaró— y evita que el riego
herede la duplicación. Son 457 predios y 1.179,88 ha de recorte.

Salida
------
public/geo/superficie_por_comunidad.json
"""
import json
import os
import sys
from collections import defaultdict
from datetime import datetime

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from comunidades_canon import canonica, nombre_publico          # noqa: E402
from generar_capas_sectores_comunidades import COMUNIDADES_POR_SECTOR   # noqa: E402

GEO = os.path.join(BASE, 'public', 'geo')
FICHAS = os.path.join(GEO, 'fichas_predios.geojson')
CATASTRO = os.path.join(GEO, 'catastro_geo.geojson')
SALIDA = os.path.join(GEO, 'superficie_por_comunidad.json')

# comunidad canónica -> sector, con el mapeo oficial del proyecto
SECTOR_DE = {}
for _sec, _coms in COMUNIDADES_POR_SECTOR.items():
    for _c in _coms:
        SECTOR_DE.setdefault(canonica(_c), _sec)


def ha(m2):
    return round((m2 or 0) / 10000.0, 2)


def main():
    print('=' * 74)
    print(' SUPERFICIE POR COMUNIDAD — declarada y catastral')
    print('=' * 74)

    with open(FICHAS, encoding='utf-8') as f:
        fichas = [x['properties'] for x in json.load(f)['features']]
    catastro = {}
    with open(CATASTRO, encoding='utf-8') as f:
        for x in json.load(f)['features']:
            p = x['properties']
            catastro[str(p.get('clave_cata') or '').strip()] = float(p.get('area_predi') or 0)
    print('\n  fichas: {:,} · catastro: {:,} predios'.format(len(fichas), len(catastro)))

    # ── fichas agrupadas por predio, para saber dónde se duplica ──
    por_predio = defaultdict(list)
    sin_poligono = []
    for p in fichas:
        clave = str(p.get('clave_catastral') or '').strip()
        if clave and clave in catastro:
            por_predio[clave].append(p)
        else:
            sin_poligono.append(p)

    # factor de recorte del riego: cuánto de lo declarado cabe en el predio
    factor = {}
    for clave, fs in por_predio.items():
        dec = sum(float(x.get('area_total') or 0) for x in fs)
        factor[clave] = min(1.0, catastro[clave] / dec) if dec > 0 else 1.0

    # ── el predio pertenece a la comunidad de la mayoría de sus fichas ──
    # Un predio no se parte entre comunidades: se le asigna entera a la que más
    # fichas tiene sobre él. Con empate manda la primera por orden alfabético,
    # para que el resultado no dependa del orden de lectura del archivo.
    dueno = {}
    for clave, fs in por_predio.items():
        votos = defaultdict(int)
        for x in fs:
            votos[canonica(x.get('comunidad') or '')] += 1
        dueno[clave] = sorted(votos.items(), key=lambda v: (-v[1], v[0]))[0][0]

    # Cómo se escribe cada comunidad de cara al lector.
    #
    # Se agrupa por el nombre canónico —que va sin tildes, para poder comparar—
    # pero publicarlo así dejaría «SAN JOSE» y «JESUS GRAN PODER» en documentos
    # que leen los propios comuneros. Se recupera la forma con la que la
    # escribieron los técnicos, prefiriendo la acentuada cuando existe.
    escrituras = defaultdict(lambda: defaultdict(int))
    for p in fichas:
        bruto = ' '.join(str(p.get('comunidad') or '').split())
        if bruto:
            escrituras[canonica(bruto)][bruto] += 1

    def como_se_escribe(com):
        formas = escrituras.get(com)
        if not formas:
            return nombre_publico(com)
        con_tilde = {k: v for k, v in formas.items() if canonica(k) != k.upper()}
        elegidas = con_tilde or formas
        return nombre_publico(max(elegidas.items(), key=lambda x: x[1])[0])

    filas = defaultdict(lambda: {
        'fichas': 0, 'regantes': 0, 'adicionales': 0, 'predios': 0,
        'declarada': 0.0, 'catastral': 0.0, 'riego_dec': 0.0, 'riego_aj': 0.0,
        'sin_riego': 0.0,
    })
    for p in fichas:
        com = canonica(p.get('comunidad') or '')
        r = filas[com]
        r['fichas'] += 1
        if p.get('es_ficha_hija') in (True, 1, '1'):
            r['adicionales'] += 1
        else:
            r['regantes'] += 1
        r['declarada'] += float(p.get('area_total') or 0)
        r['sin_riego'] += float(p.get('area_sin_riego') or 0)
        rie = float(p.get('area_riego') or 0)
        r['riego_dec'] += rie
        clave = str(p.get('clave_catastral') or '').strip()
        r['riego_aj'] += rie * factor.get(clave, 1.0)
    for clave, com in dueno.items():
        filas[com]['predios'] += 1
        filas[com]['catastral'] += catastro[clave]

    comunidades = []
    for com, r in sorted(filas.items(), key=lambda x: -x[1]['catastral']):
        comunidades.append({
            'comunidad': como_se_escribe(com),
            'sector': SECTOR_DE.get(com, 'Sin asignar'),
            'fichas': r['fichas'], 'regantes': r['regantes'],
            'predios_adicionales': r['adicionales'],
            'predios_catastrales': r['predios'],
            'superficie_catastral_ha': ha(r['catastral']),
            'superficie_declarada_ha': ha(r['declarada']),
            'riego_declarado_ha': ha(r['riego_dec']),
            'riego_ajustado_ha': ha(r['riego_aj']),
            'sin_riego_declarado_ha': ha(r['sin_riego']),
        })

    por_sector = defaultdict(lambda: defaultdict(float))
    for c in comunidades:
        s = por_sector[c['sector']]
        for k in ('fichas', 'regantes', 'predios_catastrales'):
            s[k] += c[k]
        for k in ('superficie_catastral_ha', 'superficie_declarada_ha',
                  'riego_declarado_ha', 'riego_ajustado_ha'):
            s[k] += c[k]

    total = {
        'fichas': len(fichas),
        'regantes': sum(c['regantes'] for c in comunidades),
        'predios_catastrales': len(por_predio),
        'superficie_catastral_ha': ha(sum(catastro[k] for k in por_predio)),
        'superficie_declarada_ha': ha(sum(float(p.get('area_total') or 0) for p in fichas)),
        'riego_declarado_ha': ha(sum(float(p.get('area_riego') or 0) for p in fichas)),
        'riego_ajustado_ha': ha(sum(c['riego_ajustado_ha'] for c in comunidades) * 10000),
        'fichas_sin_poligono': len(sin_poligono),
        'predios_compartidos': sum(1 for v in por_predio.values() if len(v) > 1),
    }

    # Los predios donde lo declarado no cabe en el polígono, con cuánto hay que
    # recortar. Lo publica para que cualquier análisis por titular —quién tiene
    # cuánta tierra— pueda usar el mismo criterio que la superficie del sistema
    # en vez de inventarse otro (regla 4).
    recortes = {c: round(v, 6) for c, v in factor.items() if v < 0.999}

    salida = {
        'generado': datetime.now().strftime('%Y-%m-%d %H:%M'),
        'nota': ('La superficie del sistema se mide sumando POLIGONOS CATASTRALES '
                 'DISTINTOS (superficie_catastral_ha). Lo declarado por cada regante '
                 'se conserva aparte (superficie_declarada_ha) porque es dato de '
                 'analisis, no un error: en predios de herederos cada titular declara '
                 'el predio completo. NO sume fichas para obtener la superficie.'),
        'total': total,
        'sectores': {k: {kk: (round(vv, 2) if isinstance(vv, float) else int(vv))
                         for kk, vv in v.items()}
                     for k, v in sorted(por_sector.items())},
        'comunidades': comunidades,
        'factor_por_predio': recortes,
    }
    with open(SALIDA, 'w', encoding='utf-8') as f:
        json.dump(salida, f, ensure_ascii=False, indent=1)

    print('\n  TOTAL DEL SISTEMA')
    print('     predios catastrales distintos {:>12,}'.format(total['predios_catastrales']))
    print('     superficie catastral          {:>12,.2f} ha'.format(total['superficie_catastral_ha']))
    print('     superficie declarada          {:>12,.2f} ha'.format(total['superficie_declarada_ha']))
    print('     riego declarado               {:>12,.2f} ha'.format(total['riego_declarado_ha']))
    print('     riego ajustado al poligono    {:>12,.2f} ha'.format(total['riego_ajustado_ha']))
    print('     predios con varias fichas     {:>12,}'.format(total['predios_compartidos']))
    if total['fichas_sin_poligono']:
        print('     fichas sin poligono           {:>12,}  (no suman superficie catastral)'
              .format(total['fichas_sin_poligono']))

    print('\n  POR SECTOR')
    print('     {:<14} {:>7} {:>9} {:>13} {:>13} {:>12}'
          .format('sector', 'fichas', 'regantes', 'catastral ha', 'declarada ha', 'riego aj.'))
    for s, v in sorted(por_sector.items()):
        print('     {:<14} {:>7,} {:>9,} {:>13,.2f} {:>13,.2f} {:>12,.2f}'
              .format(s, int(v['fichas']), int(v['regantes']),
                      v['superficie_catastral_ha'], v['superficie_declarada_ha'],
                      v['riego_ajustado_ha']))

    print('\n  archivo: {}  ({:,.0f} KB)'
          .format(os.path.basename(SALIDA), os.path.getsize(SALIDA) / 1024))
    print('=' * 74)
    return 0


if __name__ == '__main__':
    sys.exit(main())
