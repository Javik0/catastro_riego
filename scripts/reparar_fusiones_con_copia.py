# -*- coding: utf-8 -*-
"""
Repara las fusiones donde se sumó dos veces el mismo dato.

Qué pasó
--------
Al consolidar los cultivos repetidos dentro de una ficha (15-ago-2026,
`depurar_cultivos_y_animales.py`) se trataron dos casos:

    todos los valores iguales   -> copia: se deja uno
    valores distintos           -> el mismo cultivo en varias zonas: se suman

Faltaba el caso de en medio, que el cliente detectó al revisar: una ficha con
**«papas 500» + «PAPAS 500» + «papas 200»**. Hay una copia *dentro* de un grupo
que además tiene otro valor. Como los valores no eran todos iguales, se sumaron
los tres y salió 1.200 donde el regante siembra 700.

Son 7 fichas y 14.698,17 m² sumados de más. En animales no ocurrió.

Cómo se repara
--------------
El registro fusionado ya no conserva los valores originales, así que se leen del
respaldo anterior a la depuración, se recalcula la suma **de los valores
distintos** y se corrige el registro que quedó vivo. Si el valor ya es correcto,
no se toca.

La lógica de `depurar_cultivos_y_animales.py` quedó arreglada para que no vuelva
a ocurrir: ahora suma valores únicos.

Uso
---
    "C:\\OSGeo4W\\bin\\python-qgis.bat" -X utf8 scripts/reparar_fusiones_con_copia.py
    "C:\\OSGeo4W\\bin\\python-qgis.bat" -X utf8 scripts/reparar_fusiones_con_copia.py --aplicar

Sin `--aplicar` no escribe nada (regla 7).
"""
import argparse
import os
import sqlite3
import sys
import time
import unicodedata
from collections import defaultdict

GPKG = os.path.join(os.path.expanduser('~'), 'QField', 'cloud',
                    'porotog_levantamiento_offline', 'data.gpkg')
RAIZ_RESPALDOS = (r"C:\Users\HP\OneDrive\Escritorio\CAYAMBE CATASTRO RIEGO"
                  r"\respaldos_qgs")
# Estado inmediatamente anterior a la consolidación de repetidos.
RESPALDO = os.path.join(RAIZ_RESPALDOS, '2026-08-15',
                        'data.gpkg.0036-antes-depurar-cultivos.bak')

CULT = 'Cultivos_Agricolas_ebc9efb2_1fb3_459f_9538_6ecb946d1632'
ANIM = 'Animales_Especies_74c54436_56a5_45e4_aa36_20830a4c33f5'


def norm(s):
    s = unicodedata.normalize('NFKD', str(s or '').strip().upper())
    return ' '.join(''.join(c for c in s if not unicodedata.combining(c)).split())


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


def valores_originales(tabla, col_tipo, col_val):
    """(ficha, tipo) -> lista de valores tal como estaban antes de fusionar."""
    con = sqlite3.connect('file:{}?mode=ro'.format(RESPALDO.replace('\\', '/')), uri=True)
    cur = con.cursor()
    cur.execute('SELECT ficha_id, {}, COALESCE({},0) FROM "{}"'
                .format(col_tipo, col_val, tabla))
    grupos = defaultdict(list)
    for fid, tipo, val in cur.fetchall():
        grupos[(fid, norm(tipo))].append(round(float(val), 2))
    con.close()
    return grupos


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--aplicar', action='store_true',
                    help='escribe en el data.gpkg (sin esto solo simula)')
    args = ap.parse_args()

    print('=' * 78)
    print(' FUSIONES QUE SUMARON DOS VECES EL MISMO DATO' +
          ('  [APLICAR]' if args.aplicar else '  [SIMULACION - no escribe nada]'))
    print('=' * 78)

    if not os.path.exists(RESPALDO):
        print('ERROR: falta el respaldo de referencia:\n  {}'.format(RESPALDO))
        return 1

    total = 0
    plan = []
    for tabla, col_id, col_tipo, col_val, etiqueta, unidad in (
            (CULT, 'id_cultivo', 'tipo_cultivo', 'superficie_m2', 'CULTIVOS', 'm²'),
            (ANIM, 'id_animal', 'especie', 'cantidad', 'ANIMALES', 'cabezas')):
        grupos = valores_originales(tabla, col_tipo, col_val)
        con = sqlite3.connect(GPKG)
        cur = con.cursor()
        cur.execute('SELECT {}, ficha_id, {}, COALESCE({},0), '
                    '(SELECT TRIM(COALESCE(apellidos,\'\')||\' \'||COALESCE(nombres,\'\')) '
                    ' FROM Fichas_Predios_880eb10d_d887_4fc6_99a2_8af3ac63877e f '
                    ' WHERE f.id = t.ficha_id) '
                    'FROM "{}" t'.format(col_id, col_tipo, col_val, tabla))
        vivos = cur.fetchall()
        con.close()

        casos = []
        for id_r, fid, tipo, val, quien in vivos:
            vals = grupos.get((fid, norm(tipo)))
            if not vals or len(vals) < 2:
                continue
            unicos = []
            for v in vals:
                if v not in unicos:
                    unicos.append(v)
            if len(unicos) == len(vals):        # no había copia dentro del grupo
                continue
            correcto = round(sum(unicos), 2)
            actual = round(float(val), 2)
            if abs(actual - correcto) < 0.01:
                continue
            casos.append((id_r, tipo, quien, vals, actual, correcto))

        print('\n  {}: {} registro(s) por corregir'.format(etiqueta, len(casos)))
        for id_r, tipo, quien, vals, actual, correcto in sorted(
                casos, key=lambda c: -(c[4] - c[5])):
            print('     {:<20} {:<28} {} -> {:,.2f} {}  (era {:,.2f})'
                  .format(tipo[:20], (quien or '')[:28], vals, correcto, unidad, actual))
            total += actual - correcto
            plan.append((tabla, col_id, col_val, id_r, correcto))

    print('\n  se retiran en total: {:,.2f} m² ({:.2f} ha)'.format(total, total / 10000))

    if not args.aplicar or not plan:
        print('\n  ' + '-' * 74)
        print('  SIMULACION: no se escribió nada. Para aplicarlo:  --aplicar'
              if not args.aplicar else '  Nada que reparar.')
        print('  ' + '-' * 74)
        return 0

    print('\n  respaldando antes de tocar nada...')
    print('     {}'.format(respaldo_sqlite(GPKG, 'antes-reparar-fusiones')))

    con = sqlite3.connect(GPKG)
    cur = con.cursor()
    for tabla, col_id, col_val, id_r, correcto in plan:
        cur.execute('UPDATE "{}" SET {} = ? WHERE {} = ?'.format(tabla, col_val, col_id),
                    (correcto, id_r))
    con.commit()
    cur.execute('PRAGMA wal_checkpoint(TRUNCATE)')
    con.close()
    print('     {} registro(s) corregidos'.format(len(plan)))

    con = sqlite3.connect(GPKG)
    cur = con.cursor()
    cur.execute('SELECT COUNT(*), SUM(COALESCE(superficie_m2,0)) FROM "{}"'.format(CULT))
    n, s = cur.fetchone()
    con.close()
    print('\n  VERIFICADO releyendo del disco')
    print('     cultivos: {:,} registros · {:,.2f} ha'.format(n, s / 10000))
    print('\n  Falta regenerar: export -> gpkg cliente -> informes -> build -> deploy.')
    print('=' * 78)
    return 0


if __name__ == '__main__':
    sys.exit(main())
