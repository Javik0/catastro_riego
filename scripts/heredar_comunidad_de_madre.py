# -*- coding: utf-8 -*-
"""
Devuelve la comunidad a las fichas adicionales que la perdieron.

POR QUÉ FALTA
-------------
El desplegable de `comunidad` filtra con `current_value('sector_investigacion')`.
Cuando QField no logra resolver esa expresión al guardar, en vez de conservar el
valor escribe NULL. Pasa en ~30% de las fichas adicionales al completarse, y el
acumulado son 553 fichas.

POR QUÉ SE PUEDE DEDUCIR
------------------------
Una ficha adicional es OTRO PREDIO DEL MISMO REGANTE. La ficha madre sí tiene su
comunidad, así que la hija hereda la de su madre: no se está inventando un dato,
se está recuperando el que se perdió.

Solo se rellena donde la ficha está VACÍA y su madre TIENE comunidad. Nunca se
sobrescribe una comunidad existente.

Simula por defecto. Escribe con --aplicar, con respaldo previo.
"""

import os
import shutil
import sqlite3
import sys
import time
from collections import Counter

GPKG = r"C:\Users\HP\QField\cloud\porotog_levantamiento_offline\data.gpkg"
T = 'Fichas_Predios_880eb10d_d887_4fc6_99a2_8af3ac63877e'


def main():
    aplicar = '--aplicar' in sys.argv
    con = sqlite3.connect(GPKG)
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    cur.execute(f'SELECT id, comunidad, ficha_madre_id, es_ficha_hija, '
                f'apellidos, nombres, clave_catastral FROM "{T}"')
    filas = {r['id']: dict(r) for r in cur.fetchall()}

    def vacia(v):
        return not (v or '').strip()

    arreglos, sin_madre, madre_vacia = [], [], []
    for fid, f in filas.items():
        if not vacia(f['comunidad']):
            continue
        if f['es_ficha_hija'] not in (1, True):
            continue
        madre = filas.get(f['ficha_madre_id']) if f['ficha_madre_id'] else None
        if not madre:
            sin_madre.append(f)
        elif vacia(madre['comunidad']):
            madre_vacia.append(f)
        else:
            arreglos.append((fid, madre['comunidad'].strip(), f, madre))

    cur.execute(f'SELECT COUNT(*) FROM "{T}" WHERE comunidad IS NULL OR trim(comunidad)=""')
    total_vacias = cur.fetchone()[0]

    print(f"fichas sin comunidad en total          : {total_vacias}")
    print(f"  · adicionales que heredan de su madre: {len(arreglos)}")
    print(f"  · adicionales cuya madre tampoco tiene: {len(madre_vacia)}")
    print(f"  · adicionales sin ficha madre         : {len(sin_madre)}")
    print(f"  · fichas principales (no se tocan)    : "
          f"{total_vacias - len(arreglos) - len(madre_vacia) - len(sin_madre)}")

    if arreglos:
        print("\ncomunidades que se recuperan:")
        for com, n in Counter(c for _, c, _, _ in arreglos).most_common(10):
            print(f"   {com:<34} {n:>4}")
        print("\nmuestra:")
        for _, com, f, madre in arreglos[:4]:
            print('   {:<30} clave {} → {}'.format(
                f"{f['apellidos'] or ''} {f['nombres'] or ''}".strip()[:30],
                f['clave_catastral'], com))
            print('      (de su madre: {})'.format(
                f"{madre['apellidos'] or ''} {madre['nombres'] or ''}".strip()[:44]))

    if not aplicar:
        con.close()
        print("\nSIMULACIÓN — nada se escribió. Ejecuta con --aplicar.")
        return
    if not arreglos:
        con.close()
        return

    copia = GPKG + time.strftime('.bak-%Y%m%d-%H%M')
    shutil.copy2(GPKG, copia)
    print(f"\n   respaldo previo: {os.path.basename(copia)}")

    # Los triggers del índice espacial usan ST_IsEmpty, que SQLite puro no trae.
    cur.execute("SELECT name, sql FROM sqlite_master WHERE type='trigger' AND tbl_name=?", (T,))
    triggers = cur.fetchall()
    for nombre, _ in triggers:
        cur.execute(f'DROP TRIGGER IF EXISTS "{nombre}"')
    try:
        for fid, com, _, _ in arreglos:
            cur.execute(f'UPDATE "{T}" SET comunidad = ? WHERE id = ?', (com, fid))
    finally:
        for _, sql in triggers:
            if sql:
                cur.execute(sql)
    con.commit()
    cur.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    con.close()

    # verificar releyendo del disco
    c2 = sqlite3.connect(GPKG)
    k = c2.cursor()
    k.execute(f'SELECT COUNT(*) FROM "{T}" WHERE comunidad IS NULL OR trim(comunidad)=""')
    quedan = k.fetchone()[0]
    k.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='trigger' AND tbl_name=?", (T,))
    n_trig = k.fetchone()[0]
    c2.close()
    print(f"   ✓ {len(arreglos)} comunidades recuperadas")
    print(f"   ✓ quedan {quedan} fichas sin comunidad (antes {total_vacias})")
    print(f"   ✓ {n_trig} triggers recreados")


if __name__ == '__main__':
    main()
