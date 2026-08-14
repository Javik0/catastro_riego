# -*- coding: utf-8 -*-
"""
Cultivos digitados con el punto decimal corrido.

El hallazgo
-----------
Al medir qué fichas siembran más superficie de la que su predio mide, aparecen
152 casos y 261,26 ha de exceso. Casi todos necesitan criterio —puede ser
terreno arrendado fuera del predio, que es una práctica real—, pero uno no:

    CHIMARRO LANCHIMBA SILVIA BEATRIZ · clave 1702520680109
        predio               8.767,33 m²   (riego 7.000 + sin riego 1.767,33)
        pasto no mejorado  876.733,00 m²   ← el área del predio sin el punto

Es el área del propio predio multiplicada por cien exacto: el técnico digitó
`876733` en vez de `8767.33`. No hay nada que interpretar, es aritmética.

Qué corrige
-----------
Solo los registros de cultivo cuya superficie es **cien veces el área del predio
de su ficha**, dentro del 1 %. Ese cuadre es la prueba de que se trata del punto
decimal y no de una superficie declarada de más: si fuera terreno arrendado no
coincidiría con el área del predio hasta la segunda cifra.

Se divide entre cien. El resultado —el predio entero sembrado— es lo que la
ficha venía diciendo desde el principio.

Qué NO corrige
--------------
Las otras 151 fichas que declaran más cultivo que predio. Van de ×1,1 a ×36 sin
patrón aritmético, y decidir ahí es del cliente o de campo, no de un script.
Se listan al final de la ejecución para tenerlas a la vista.

Uso
---
    "C:\\OSGeo4W\\bin\\python-qgis.bat" -X utf8 scripts/corregir_cultivo_punto_decimal.py
    "C:\\OSGeo4W\\bin\\python-qgis.bat" -X utf8 scripts/corregir_cultivo_punto_decimal.py --aplicar

Sin `--aplicar` no escribe nada (regla 7). Con `--aplicar` respalda antes, con la
API de backup de SQLite y fuera de la carpeta de QFieldCloud (regla 5).

Después hay que regenerar: export → gpkg del cliente → informes → build → deploy.
"""
import argparse
import os
import sqlite3
import sys
import time

GPKG = os.path.join(os.path.expanduser('~'), 'QField', 'cloud',
                    'porotog_levantamiento_offline', 'data.gpkg')
RAIZ_RESPALDOS = (r"C:\Users\HP\OneDrive\Escritorio\CAYAMBE CATASTRO RIEGO"
                  r"\respaldos_qgs")

FACTOR = 100.0
MARGEN = 0.01        # 1 %: el cuadre tiene que ser exacto, no parecido
UMBRAL_LISTADO = 1.10   # a partir de aquí se lista como «siembra de más»


def m2(v):
    return '{:,.2f}'.format(v or 0).replace(',', 'X').replace('.', ',').replace('X', '.')


def respaldo_sqlite(origen, etiqueta):
    carpeta = os.path.join(RAIZ_RESPALDOS, time.strftime('%Y-%m-%d'))
    os.makedirs(carpeta, exist_ok=True)
    destino = os.path.join(carpeta, '{}.{}-{}.bak'.format(
        os.path.basename(origen), time.strftime('%H%M'), etiqueta))
    src = sqlite3.connect(origen)
    dst = sqlite3.connect(destino)
    with dst:
        src.backup(dst)
    dst.close()
    src.close()
    return destino


def tablas(cur):
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    todas = [t[0] for t in cur.fetchall()]

    def buscar(clave):
        return next((t for t in todas if clave in t
                     and not any(x in t for x in ('rtree_', 'log_', 'gpkg_'))), None)
    return buscar('Fichas_Predios'), buscar('Cultivos_Agricolas')


def main():
    ap = argparse.ArgumentParser(description='Corrige cultivos con el punto decimal corrido')
    ap.add_argument('--aplicar', action='store_true',
                    help='escribe en el data.gpkg (sin esto solo simula)')
    args = ap.parse_args()

    print('=' * 78)
    print(' CULTIVOS CON EL PUNTO DECIMAL CORRIDO' +
          ('  [APLICAR]' if args.aplicar else '  [SIMULACION - no escribe nada]'))
    print('=' * 78)

    con = sqlite3.connect(GPKG)
    cur = con.cursor()
    t_fichas, t_cult = tablas(cur)

    cur.execute('SELECT c.id_cultivo, c.ficha_id, c.tipo_cultivo, c.superficie_m2, '
                'f.area_total, f.clave_catastral, f.apellidos, f.nombres, f.comunidad, '
                'f.creado_por '
                'FROM "{}" c JOIN "{}" f ON f.id = c.ficha_id '
                'WHERE COALESCE(f.area_total,0) > 0 AND COALESCE(c.superficie_m2,0) > 0'
                .format(t_cult, t_fichas))
    filas = cur.fetchall()

    corregibles, otros = [], {}
    for id_c, fid, tipo, sup, area, clave, ape, nom, com, tec in filas:
        factor = sup / area
        if abs(factor - FACTOR) <= FACTOR * MARGEN:
            corregibles.append((id_c, tipo, sup, area, clave, ape, nom, com, tec))
        # el desborde se mide por ficha, no por registro suelto
        otros.setdefault(fid, {'sup': 0.0, 'area': area, 'clave': clave,
                               'quien': '{} {}'.format(ape or '', nom or '').strip(),
                               'com': com, 'tec': tec})
        otros[fid]['sup'] += sup

    print('\n  registros que son el area del predio x{:,.0f} (±{:.0%}): {}'
          .format(FACTOR, MARGEN, len(corregibles)))
    for id_c, tipo, sup, area, clave, ape, nom, com, tec in corregibles:
        print('     {} · {} {}'.format(clave, ape or '', nom or ''))
        print('        comunidad {} · levantada por {}'.format(com, tec))
        print('        {:<22} {:>16} m²  ->  {:>14} m²'
              .format(tipo or '—', m2(sup), m2(sup / FACTOR)))
        print('        area del predio        {:>14} m²'.format(m2(area)))

    if not corregibles:
        print('     ninguno: no hay nada que corregir')

    total = sum(f[3] for f in filas)
    baja = sum(c[2] - c[2] / FACTOR for c in corregibles)
    print('\n  EFECTO EN EL PADRON')
    print('     superficie cultivada  {:>14} ha  ->  {:>14} ha'
          .format(m2(total / 10000), m2((total - baja) / 10000)))

    desbordadas = [v for v in otros.values() if v['sup'] / v['area'] > UMBRAL_LISTADO]
    exceso = sum(v['sup'] - v['area'] for v in desbordadas)
    print('\n  LO QUE ESTE SCRIPT NO TOCA')
    print('     fichas que siembran mas de lo que su predio mide: {}'.format(len(desbordadas)))
    print('     superficie sembrada de mas: {} ha'.format(m2(exceso / 10000)))
    print('     (puede ser terreno arrendado fuera del predio: decision del cliente)')
    peores = sorted(desbordadas, key=lambda v: -(v['sup'] / v['area']))[:8]
    for v in peores:
        print('        {:<15} {:<32} x{:>5.1f}   predio {:>12} m²'
              .format(v['clave'] or '—', v['quien'][:32], v['sup'] / v['area'], m2(v['area'])))

    if not args.aplicar or not corregibles:
        print('\n  ' + '-' * 74)
        print('  SIMULACION: no se escribio nada. Para aplicarlo:  --aplicar'
              if not args.aplicar else '  Nada que aplicar.')
        print('  ' + '-' * 74)
        con.close()
        return 0
    con.close()

    print('\n  respaldando antes de tocar nada...')
    destino = respaldo_sqlite(GPKG, 'antes-punto-decimal')
    print('     {}'.format(destino))

    con = sqlite3.connect(GPKG)
    cur = con.cursor()
    tocados = 0
    for id_c, _, sup, _, _, _, _, _, _ in corregibles:
        cur.execute('UPDATE "{}" SET superficie_m2 = ? WHERE id_cultivo = ?'
                    .format(t_cult), (round(sup / FACTOR, 2), id_c))
        tocados += cur.rowcount
    con.commit()
    cur.execute('PRAGMA wal_checkpoint(TRUNCATE)')
    con.close()
    print('     {} registro(s) de cultivo corregidos'.format(tocados))

    # ── verificación releyendo del disco ──
    con = sqlite3.connect(GPKG)
    cur = con.cursor()
    for id_c, tipo, _, area, clave, _, _, _, _ in corregibles:
        cur.execute('SELECT superficie_m2 FROM "{}" WHERE id_cultivo = ?'.format(t_cult),
                    (id_c,))
        v = cur.fetchone()[0]
        print('     VERIFICADO {} · {} -> {} m²  (predio {} m²)'
              .format(clave, tipo, m2(v), m2(area)))
    cur.execute('SELECT SUM(COALESCE(superficie_m2,0)) FROM "{}"'.format(t_cult))
    print('     superficie cultivada del padron: {} ha'.format(m2(cur.fetchone()[0] / 10000)))
    con.close()
    print('\n  Falta regenerar: export -> gpkg cliente -> informes -> build -> deploy.')
    print('=' * 78)
    return 0


if __name__ == '__main__':
    sys.exit(main())
