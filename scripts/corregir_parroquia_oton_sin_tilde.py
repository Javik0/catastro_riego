# -*- coding: utf-8 -*-
"""
4 fichas tienen `parroquia = "OTON"` sin tilde, mientras las otras 633 de la
misma parroquia dicen "OTÓN". No es una parroquia distinta: es el mismo dato
escrito sin acento.

El hallazgo
-----------
Apareció el 19-ago-2026 al revisar el gráfico "Fichas por Parroquia" del
Dashboard, que las mostraba como una barra aparte. El desplegable "Parroquia"
de la web está fijo en el código (`PARROQUIAS` en `constants.ts`) con la forma
acentuada, y el filtro compara con igualdad exacta
(`f.parroquia !== filtros.parroquia` en App.tsx): las 4 fichas quedan
invisibles para cualquiera que filtre por Otón, en cualquier pantalla.

En los informes de Python el efecto es menor porque `generar_capitulo_perfil.py`
y la tabla "Resumen Ejecutivo" de `generate_technical_report.py` ya normalizan
el texto antes de agrupar. El único punto sin normalizar es el gráfico
"Comunidades por Parroquia" del Informe Técnico, que saca una barra fantasma
casi vacía — verificado que no pierde ninguna comunidad: Chaupiestancia y
Otoncito, las dos de estas 4 fichas, ya están bien contadas en Otón por sus
demás fichas.

Qué corrige
-----------
Un solo campo, en las 4 fichas: `parroquia` de "OTON" a "OTÓN". No toca nada
más — el resto del dato de estas fichas está bien.

Uso
---
    python -X utf8 scripts/corregir_parroquia_oton_sin_tilde.py
    python -X utf8 scripts/corregir_parroquia_oton_sin_tilde.py --aplicar

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

PARROQUIA_VIEJA = 'OTON'
PARROQUIA_NUEVA = 'OTÓN'


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
    ap = argparse.ArgumentParser(description='Corrige "OTON" sin tilde a "OTÓN" en parroquia')
    ap.add_argument('--aplicar', action='store_true',
                    help='escribe en el data.gpkg (sin esto solo simula)')
    args = ap.parse_args()

    print('=' * 74)
    print(' PARROQUIA "OTON" SIN TILDE -> "OTÓN"' +
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

    cur.execute('SELECT id, codigo_final, apellidos, nombres, cedula, comunidad FROM "{}" '
                'WHERE parroquia = ?'.format(t_fichas), (PARROQUIA_VIEJA,))
    filas = cur.fetchall()
    print('\n  FICHAS CON "{}" (se cambian a "{}"): {}'.format(
        PARROQUIA_VIEJA, PARROQUIA_NUEVA, len(filas)))
    for _id, cod, ape, nom, ced, com in filas:
        print('     {}  {} {}  · cedula {} · comunidad {}'.format(cod, ape, nom, ced, com))

    if not filas:
        print('\n  No hay fichas con "{}". No hay nada que hacer.'.format(PARROQUIA_VIEJA))
        con.close()
        return 0

    if not args.aplicar:
        print('\n  ' + '-' * 70)
        print('  SIMULACION: no se escribio nada. Para aplicarlo:  --aplicar')
        print('  ' + '-' * 70)
        con.close()
        return 0

    con.close()

    print('\n  respaldando antes de tocar nada...')
    destino = respaldo_sqlite(GPKG, 'antes-parroquia-oton')
    print('     {}'.format(destino))

    con = sqlite3.connect(GPKG)
    cur = con.cursor()
    cur.execute("SELECT name, sql FROM sqlite_master WHERE type='trigger' AND tbl_name=?",
                (t_fichas,))
    triggers = cur.fetchall()
    for nombre, _ in triggers:
        cur.execute('DROP TRIGGER IF EXISTS "{}"'.format(nombre))
    try:
        cur.execute('UPDATE "{}" SET parroquia = ? WHERE parroquia = ?'
                    .format(t_fichas), (PARROQUIA_NUEVA, PARROQUIA_VIEJA))
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
    cur.execute('SELECT COUNT(*) FROM "{}" WHERE parroquia = ?'.format(t_fichas), (PARROQUIA_VIEJA,))
    quedan = cur.fetchone()[0]
    cur.execute('SELECT COUNT(*) FROM "{}" WHERE parroquia = ?'.format(t_fichas), (PARROQUIA_NUEVA,))
    ahora = cur.fetchone()[0]
    con.close()

    print('\n  VERIFICADO releyendo del disco')
    print('     fichas con "{}" restantes: {}  (debe ser 0)'.format(PARROQUIA_VIEJA, quedan))
    print('     fichas con "{}" ahora: {}'.format(PARROQUIA_NUEVA, ahora))
    print('\n  Falta regenerar: export -> capas -> web -> informes -> gpkg cliente -> build -> deploy.')
    print('=' * 74)
    return 0


if __name__ == '__main__':
    sys.exit(main())
