# -*- coding: utf-8 -*-
"""
Una ficha de Juan Miguel Acero Farinango quedó con la comunidad equivocada.

El hallazgo
-----------
De sus 8 fichas, 7 dicen `comunidad = COCHAPAMBA`. Solo la del predio
`1702521730011` dice `SANTA BÁRBARA`. Armando lo confirmó por WhatsApp el
19-ago-2026: "no es de Santa Bárbara, es de la Comuna Cochapamba... no
pertenece, es solo de la familia".

Ese "Santa Bárbara" no sale de la ficha original del técnico: es la etiqueta
que el catastro municipal (GADM) le puso al predio ("LA COMPAÑIA LOTE 2 -
SANTA BARBARA"), un nombre de finca familiar, no una comunidad oficial. El
buscador del mapa web lee esa etiqueta directo del catastro crudo, NO de esta
ficha — corregir aquí no cambia lo que el buscador muestra al escribir esa
clave catastral. Es una decisión aparte, sin resolver.

Qué corrige
-----------
Un solo campo, en una sola ficha: `comunidad` de `SANTA BÁRBARA` a
`COCHAPAMBA`. No toca área, riego, cultivos ni animales — el error era de
comunidad, no de superficie.

Efecto en las cifras publicadas
--------------------------------
El predio no tiene más fichas encima (dueño único), así que su superficie
catastral completa (8,87 ha) se mueve entera de Santa Bárbara a Cochapamba
en `superficie_por_comunidad.json`. El total del sistema no cambia: es un
traspaso entre comunidades, no una superficie nueva ni perdida.

Uso
---
    python -X utf8 scripts/corregir_ficha_acero_cochapamba.py
    python -X utf8 scripts/corregir_ficha_acero_cochapamba.py --aplicar

Sin `--aplicar` no escribe nada (regla 7). Con `--aplicar` respalda antes, con
la API de backup de SQLite y fuera de la carpeta de QFieldCloud (regla 5).

Antes de correrlo con --aplicar
--------------------------------
1. Que nadie esté sincronizando desde una tablet.
2. Después hay que regenerar todo: export → capas → web → informes → gpkg
   cliente → build → deploy, y volver a publicar.
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

FICHA_ID = '{93fd3e92-4ee3-47f2-ac74-d7837f8f2389}'
CLAVE_ESPERADA = '1702521730011'
COMUNIDAD_VIEJA = 'SANTA BÁRBARA'
COMUNIDAD_NUEVA = 'COCHAPAMBA'

OBSERVACION = ('PREDIO CORREGIDO EN OFICINA: la comunidad decia SANTA BARBARA, '
               'etiqueta del catastro municipal (nombre de finca familiar, no '
               'comunidad oficial). El titular pertenece a la Comuna Cochapamba, '
               'igual que sus otras 7 fichas. Confirmado por Armando, 19-ago-2026.')


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


def tabla_fichas(cur):
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    todas = [t[0] for t in cur.fetchall()]
    return next((t for t in todas if 'Fichas_Predios' in t
                 and not any(x in t for x in ('rtree_', 'log_', 'gpkg_'))), None)


def main():
    ap = argparse.ArgumentParser(description='Corrige la comunidad de la ficha de Acero Farinango')
    ap.add_argument('--aplicar', action='store_true',
                    help='escribe en el data.gpkg (sin esto solo simula)')
    args = ap.parse_args()

    print('=' * 74)
    print(' FICHA ACERO FARINANGO — comunidad Santa Barbara -> Cochapamba' +
          ('  [APLICAR]' if args.aplicar else '  [SIMULACION - no escribe nada]'))
    print('=' * 74)

    if not os.path.exists(GPKG):
        print('ERROR: no se encuentra {}'.format(GPKG))
        return 1

    con = sqlite3.connect(GPKG)
    cur = con.cursor()
    t_fichas = tabla_fichas(cur)
    if not t_fichas:
        print('ERROR: no se encontro la tabla de fichas')
        return 1

    cur.execute('SELECT id, codigo_final, apellidos, nombres, cedula, clave_catastral, '
                'comunidad, area_total, observaciones FROM "{}" WHERE id = ?'
                .format(t_fichas), (FICHA_ID,))
    row = cur.fetchone()
    if not row:
        print('ERROR: no existe la ficha {} en el gpkg'.format(FICHA_ID))
        con.close()
        return 1

    _id, cod, ape, nom, ced, clave, comunidad, area, obs = row
    print('\n  FICHA')
    print('     {}  {} {}  · cedula {}'.format(cod, ape, nom, ced))
    print('     clave      {}'.format(clave))
    print('     area       {} m²'.format('{:,.2f}'.format(area or 0)))
    print('     comunidad  {}  ->  {}'.format(comunidad, COMUNIDAD_NUEVA))

    if str(clave or '').strip() != CLAVE_ESPERADA:
        print('\n  ATENCION: la clave catastral no es la esperada ({}). No se toca nada.'
              .format(CLAVE_ESPERADA))
        con.close()
        return 2
    if str(comunidad or '').strip().upper() == COMUNIDAD_NUEVA:
        print('\n  La ficha YA dice {}. No hay nada que hacer.'.format(COMUNIDAD_NUEVA))
        con.close()
        return 0
    if str(comunidad or '').strip().upper() != COMUNIDAD_VIEJA:
        print('\n  ATENCION: la comunidad actual es "{}", no "{}". No se toca nada '
              '— revisar a mano.'.format(comunidad, COMUNIDAD_VIEJA))
        con.close()
        return 2

    # cuántas fichas más tiene el mismo predio (para saber si el area catastral
    # completa se mueve de comunidad, o solo una parte)
    cur.execute('SELECT COUNT(*) FROM "{}" WHERE clave_catastral = ?'
                .format(t_fichas), (clave,))
    n_en_predio = cur.fetchone()[0]
    print('\n  Fichas sobre este mismo predio: {}'.format(n_en_predio))
    if n_en_predio == 1:
        print('     -> es la unica: los {} ha catastrales completos pasan de'
              ' Santa Barbara a Cochapamba'.format('{:,.2f}'.format((area or 0) / 10000)))

    if not args.aplicar:
        print('\n  ' + '-' * 70)
        print('  SIMULACION: no se escribio nada. Para aplicarlo:  --aplicar')
        print('  ' + '-' * 70)
        con.close()
        return 0

    con.close()

    print('\n  respaldando antes de tocar nada...')
    destino = respaldo_sqlite(GPKG, 'antes-acero-cochapamba')
    print('     {}'.format(destino))

    con = sqlite3.connect(GPKG)
    cur = con.cursor()
    cur.execute("SELECT name, sql FROM sqlite_master WHERE type='trigger' AND tbl_name=?",
                (t_fichas,))
    triggers = cur.fetchall()
    for nombre, _ in triggers:
        cur.execute('DROP TRIGGER IF EXISTS "{}"'.format(nombre))
    try:
        cur.execute('UPDATE "{}" SET comunidad = ?, observaciones = ? WHERE id = ?'
                    .format(t_fichas), (COMUNIDAD_NUEVA, OBSERVACION, FICHA_ID))
        n_upd = cur.rowcount
    finally:
        for _, sql in triggers:
            if sql:
                cur.execute(sql)

    con.commit()
    cur.execute('PRAGMA wal_checkpoint(TRUNCATE)')
    con.close()
    print('     fichas actualizadas: {} · triggers recreados: {}'.format(n_upd, len(triggers)))

    con = sqlite3.connect(GPKG)
    cur = con.cursor()
    cur.execute('SELECT comunidad FROM "{}" WHERE id = ?'.format(t_fichas), (FICHA_ID,))
    v = cur.fetchone()[0]
    con.close()

    print('\n  VERIFICADO releyendo del disco')
    print('     comunidad -> {}'.format(v))
    print('\n  Falta regenerar: export -> capas -> web -> informes -> gpkg cliente -> build -> deploy.')
    print('=' * 74)
    return 0


if __name__ == '__main__':
    sys.exit(main())
