# -*- coding: utf-8 -*-
"""
La ficha de Virgilio Umaquinga Andrango quedó con la clave catastral de un
predio que no es el que describe.

El hallazgo
-----------
Apareció al investigar por qué el mapa contaba 5.995 predios investigados y el
Dashboard 5.987 (19-ago-2026). La causa general fue que `export_catastro()`
usaba `cod_poligono` antes que `clave_catastral` para dibujar los polígonos —
ver `corregir_prioridad_clave_export_catastro` en export_geojson.py. Al revisar
las 10 fichas donde las dos claves no coinciden, esta es la única con un
predio real detrás y no un simple dato vacío:

    declara area_total       13.933,15 m²
    clave_catastral (1702521020109)   1.423,23 m²  — SU predio, pero no este
    cod_poligono    (1702520530049)  13.933,15 m²  — coincide EXACTO

Las dos claves están registradas al mismo nombre y cédula (1710909969): tiene
dos predios catastrados, y la ficha describe el grande. La propia ficha ya
trae una observación que apunta al descuadre («Clave: 1702521020109 Área
Total: 1423.23 m²») — quedó anotado pero nunca corregido.

Qué corrige
-----------
Un solo campo: `clave_catastral` pasa de 1702521020109 a 1702520530049 (el
valor que ya tenía en `cod_poligono`, sin tocar ese campo). No cambia área,
riego, cultivos ni animales.

Uso
---
    python -X utf8 scripts/corregir_ficha_umaquinga_clave.py
    python -X utf8 scripts/corregir_ficha_umaquinga_clave.py --aplicar

Sin `--aplicar` no escribe nada (regla 7). Con `--aplicar` respalda antes.
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

FICHA_ID = '{650047a2-7c0a-478f-b1b2-b24580dfc1b4}'
CLAVE_VIEJA = '1702521020109'
CLAVE_NUEVA = '1702520530049'

OBSERVACION = ('PREDIO CORREGIDO EN OFICINA: la clave catastral apuntaba a otro '
               'predio del mismo titular (1.423,23 m², no coincide con lo '
               'declarado). Se corrigio a 1702520530049, que coincide exacto '
               'con el area_total declarada (13.933,15 m²) y ya estaba en '
               'cod_poligono. Detectado el 19-ago-2026.')


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
    ap = argparse.ArgumentParser(description='Corrige la clave catastral de la ficha de Umaquinga Andrango')
    ap.add_argument('--aplicar', action='store_true',
                    help='escribe en el data.gpkg (sin esto solo simula)')
    args = ap.parse_args()

    print('=' * 74)
    print(' FICHA UMAQUINGA ANDRANGO — clave catastral corregida' +
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
                'cod_poligono, area_total, observaciones FROM "{}" WHERE id = ?'
                .format(t_fichas), (FICHA_ID,))
    row = cur.fetchone()
    if not row:
        print('ERROR: no existe la ficha {} en el gpkg'.format(FICHA_ID))
        con.close()
        return 1

    _id, cod, ape, nom, ced, clave, cod_pol, area, obs = row
    print('\n  FICHA')
    print('     {}  {} {}  · cedula {}'.format(cod, ape, nom, ced))
    print('     area declarada  {} m²'.format('{:,.2f}'.format(area or 0)))
    print('     clave_catastral {}  ->  {}'.format(clave, CLAVE_NUEVA))
    print('     cod_poligono    {}  (sin cambio)'.format(cod_pol))

    if str(clave or '').strip() == CLAVE_NUEVA:
        print('\n  La ficha YA tiene la clave correcta. No hay nada que hacer.')
        con.close()
        return 0
    if str(clave or '').strip() != CLAVE_VIEJA:
        print('\n  ATENCION: la clave actual es "{}", no "{}". No se toca nada '
              '— revisar a mano.'.format(clave, CLAVE_VIEJA))
        con.close()
        return 2
    if str(cod_pol or '').strip() != CLAVE_NUEVA:
        print('\n  ATENCION: cod_poligono no es "{}". No se toca nada — revisar a mano.'
              .format(CLAVE_NUEVA))
        con.close()
        return 2

    if not args.aplicar:
        print('\n  ' + '-' * 70)
        print('  SIMULACION: no se escribio nada. Para aplicarlo:  --aplicar')
        print('  ' + '-' * 70)
        con.close()
        return 0

    con.close()

    print('\n  respaldando antes de tocar nada...')
    destino = respaldo_sqlite(GPKG, 'antes-umaquinga-clave')
    print('     {}'.format(destino))

    con = sqlite3.connect(GPKG)
    cur = con.cursor()
    cur.execute("SELECT name, sql FROM sqlite_master WHERE type='trigger' AND tbl_name=?",
                (t_fichas,))
    triggers = cur.fetchall()
    for nombre, _ in triggers:
        cur.execute('DROP TRIGGER IF EXISTS "{}"'.format(nombre))
    try:
        cur.execute('UPDATE "{}" SET clave_catastral = ?, observaciones = ? WHERE id = ?'
                    .format(t_fichas), (CLAVE_NUEVA, OBSERVACION, FICHA_ID))
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
    cur.execute('SELECT clave_catastral FROM "{}" WHERE id = ?'.format(t_fichas), (FICHA_ID,))
    v = cur.fetchone()[0]
    con.close()

    print('\n  VERIFICADO releyendo del disco')
    print('     clave_catastral -> {}'.format(v))
    print('\n  Falta regenerar: export -> capas -> web -> informes -> gpkg cliente -> build -> deploy.')
    print('=' * 74)
    return 0


if __name__ == '__main__':
    sys.exit(main())
