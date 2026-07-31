# -*- coding: utf-8 -*-
"""
Restaura las fichas a las que QField les borró `comunidad` y `ficha_madre_id`
al guardar (2026-07-31).

QUÉ PASÓ
--------
Al completar la Sección 4 de una ficha adicional, QField guardó NULL en los dos
campos que usan widget ValueRelation:

  campos que cambiaron: comunidad, ficha_madre_id, estado_investigacion,
                        completado_por, fecha_completado
  comunidad ayer=[CORDILLERAS DE LOS ANDES] hoy=[None]

El trabajo del técnico (estado_investigacion, completado_por, cultivos) se
guardó bien; lo que se perdió fue la comunidad y el vínculo con el regante.

Es el mismo fallo que borró 375 fichas en su momento: el ValueRelation de
`comunidad` filtra con `current_value('sector_investigacion')`, y cuando QField
no resuelve esa expresión escribe NULL en vez de conservar el valor.

QUÉ HACE
--------
Compara el data.gpkg contra un respaldo y devuelve `comunidad` y
`ficha_madre_id` SOLO donde el respaldo tenía valor y ahora está vacío.
NO toca ningún otro campo: el trabajo nuevo de los técnicos se respeta.

Simula por defecto. Escribe con --aplicar, con respaldo previo.

Uso:
  python scripts/restaurar_fichas_reseteadas.py [--respaldo RUTA] [--aplicar]
"""

import os
import shutil
import sqlite3
import sys
import time

GPKG = r"C:\Users\HP\QField\cloud\porotog_levantamiento_offline\data.gpkg"
RESPALDO = (r"C:\Users\HP\OneDrive\Escritorio\CAYAMBE CATASTRO RIEGO"
            r"\respaldos_qgs\data_ANTES_de_descargar_20260730.gpkg")
T = 'Fichas_Predios_880eb10d_d887_4fc6_99a2_8af3ac63877e'
CAMPOS = ('comunidad', 'ficha_madre_id')


def leer(ruta):
    con = sqlite3.connect(ruta)
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    cur.execute(f'SELECT id, {", ".join(CAMPOS)} FROM "{T}"')
    d = {r['id']: {c: r[c] for c in CAMPOS} for r in cur.fetchall()}
    con.close()
    return d


def main():
    aplicar = '--aplicar' in sys.argv
    respaldo = RESPALDO
    if '--respaldo' in sys.argv:
        respaldo = sys.argv[sys.argv.index('--respaldo') + 1]
    if not os.path.exists(respaldo):
        raise SystemExit(f"ABORTADO: no existe el respaldo {respaldo}")

    print(f"respaldo: {os.path.basename(respaldo)}")
    print(f"actual  : {os.path.basename(GPKG)}\n")

    viejo, nuevo = leer(respaldo), leer(GPKG)
    arreglos = []
    for fid, antes in viejo.items():
        ahora = nuevo.get(fid)
        if not ahora:
            continue                      # la ficha ya no existe: no se resucita
        for campo in CAMPOS:
            v_antes = (antes[campo] or '').strip() if isinstance(antes[campo], str) else antes[campo]
            v_ahora = (ahora[campo] or '').strip() if isinstance(ahora[campo], str) else ahora[campo]
            if v_antes and not v_ahora:   # solo se rellena lo que se vació
                arreglos.append((fid, campo, v_antes))

    if not arreglos:
        print("No hay nada que restaurar.")
        return

    por_campo = {}
    for _, campo, _ in arreglos:
        por_campo[campo] = por_campo.get(campo, 0) + 1
    print(f"A RESTAURAR: {len(arreglos)} valores en {len({f for f, _, _ in arreglos})} fichas")
    for campo, n in sorted(por_campo.items()):
        print(f"   {campo:<18} {n:>4}")

    # detalle legible
    con = sqlite3.connect(GPKG)
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    print("\n   detalle:")
    vistos = set()
    for fid, campo, valor in arreglos:
        if fid in vistos:
            continue
        vistos.add(fid)
        cur.execute(f'SELECT apellidos, nombres, clave_catastral, completado_por '
                    f'FROM "{T}" WHERE id = ?', (fid,))
        r = cur.fetchone()
        campos_f = [c for f, c, _ in arreglos if f == fid]
        print('   · {:<32} clave {} · devuelve {}'.format(
            f"{r['apellidos'] or ''} {r['nombres'] or ''}".strip()[:32],
            r['clave_catastral'], ', '.join(campos_f)))

    if not aplicar:
        con.close()
        print("\nSIMULACIÓN — nada se escribió. Ejecuta con --aplicar.")
        return

    copia = GPKG + time.strftime('.bak-%Y%m%d-%H%M')
    shutil.copy2(GPKG, copia)
    print(f"\n   respaldo previo: {os.path.basename(copia)}")

    # El GeoPackage tiene triggers de índice espacial que llaman a ST_IsEmpty,
    # una función de SpatiaLite que SQLite puro no trae. Se retiran mientras
    # dura el UPDATE y se recrean tal cual (mismo patrón que
    # corregir_gpkg_fisico.py). No se toca la geometría, solo dos campos de
    # texto, así que el índice espacial no cambia.
    cur.execute("SELECT name, sql FROM sqlite_master WHERE type='trigger' AND tbl_name=?", (T,))
    triggers = cur.fetchall()
    print(f"   se retiran {len(triggers)} triggers espaciales durante la escritura")
    for nombre, _ in triggers:
        cur.execute(f'DROP TRIGGER IF EXISTS "{nombre}"')
    try:
        for fid, campo, valor in arreglos:
            cur.execute(f'UPDATE "{T}" SET "{campo}" = ? WHERE id = ?', (valor, fid))
    finally:
        for _, sql in triggers:
            if sql:
                cur.execute(sql)
        print("   triggers recreados")
    con.commit()
    cur.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    con.close()

    # verificar releyendo del disco
    final = leer(GPKG)
    pendientes = [(f, c) for f, c, v in arreglos if not final[f][c]]
    print(f"   ✓ aplicados {len(arreglos)} valores; sin restaurar: {len(pendientes)}")
    if pendientes:
        raise SystemExit("ABORTADO: quedaron valores sin restaurar")
    print("   ✓ RESTAURACION OK")


if __name__ == '__main__':
    main()
