# -*- coding: utf-8 -*-
"""
Marca como 'completada' las fichas adicionales que YA tienen Seccion 4 cargada
(cultivos o animales) pero quedaron en otro estado y por eso se seguian pintando
blancas en QField/QGIS.

Causa: el default del proyecto solo actuaba desde 'pendiente_produccion', asi que
las fichas en 'en_revision' nunca se marcaban por mas que el tecnico las llenara.
El proyecto ya quedo corregido (corregir_proyecto_qgis.py); esto arregla los
registros que ya estaban atrapados.

MODO SEGURO: por defecto solo simula. Para escribir hay que pasar --aplicar.
"""
import sqlite3
import sys
import collections

APLICAR = "--aplicar" in sys.argv
DB = r"C:\Users\HP\QField\cloud\porotog_levantamiento_offline\data.gpkg"

con = sqlite3.connect(DB if APLICAR else "file:{}?mode=ro".format(DB), uri=not APLICAR)
cur = con.cursor()
cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
tabs = [t[0] for t in cur.fetchall()]


def T(kw):
    return next(t for t in tabs if kw in t and not any(x in t for x in ('gpkg_', 'rtree_', 'log_')))


ft, ct, at = T('Fichas_Predios'), T('Cultivos_Agricolas'), T('Animales_Especies')

cur.execute('SELECT DISTINCT ficha_id FROM "{}"'.format(ct))
cc = set(r[0] for r in cur.fetchall())
cur.execute('SELECT DISTINCT ficha_id FROM "{}"'.format(at))
ca = set(r[0] for r in cur.fetchall())

cur.execute('SELECT id, codigo_final, apellidos, comunidad, estado_investigacion, completado_por '
            'FROM "{}" WHERE es_ficha_hija IN (1)'.format(ft))
hijas = cur.fetchall()
objetivo = [h for h in hijas if (h[0] in cc or h[0] in ca) and (h[4] or '') != 'completada']

print("=" * 70)
print(" {} — FICHAS ADICIONALES ATRAPADAS EN BLANCO".format(
    "APLICANDO" if APLICAR else "SIMULACION"))
print("=" * 70)
print("\nFichas adicionales:", len(hijas))
print("Con Seccion 4 cargada pero NO marcadas 'completada':", len(objetivo))
print("\n  estado actual:")
for k, v in collections.Counter(h[4] for h in objetivo).most_common():
    print("     {:<26} {}".format(repr(k), v))
print("\n  por comunidad:")
for k, v in collections.Counter(h[3] for h in objetivo).most_common(6):
    print("     {:<34} {}".format(str(k), v))
print("\n  ejemplos:")
for h in objetivo[:5]:
    print("     {} | {} | {}".format(h[1], (h[2] or '')[:30], h[3] or ''))

if not APLICAR:
    print("\nSIMULACION — no se escribio. Ejecutar con --aplicar para grabar.")
    con.close()
    sys.exit(0)

cur.execute("SELECT name, sql FROM sqlite_master WHERE type='trigger'")
trg = [(n, s) for n, s in cur.fetchall() if ft.lower() in (s or '').lower()]
for n, _ in trg:
    cur.execute('DROP TRIGGER IF EXISTS "{}"'.format(n))

for h in objetivo:
    cur.execute('UPDATE "{}" SET estado_investigacion=? WHERE id=?'.format(ft),
                ('completada', h[0]))
con.commit()

for n, s in trg:
    try:
        cur.execute(s)
    except Exception as e:
        print("  [AVISO] trigger {} no restaurado: {}".format(n, e))
con.commit()
cur.execute("PRAGMA wal_checkpoint(TRUNCATE)")
print("\n  checkpoint:", cur.fetchone())

cur.execute('SELECT COUNT(*) FROM "{}" WHERE es_ficha_hija IN (1) '
            'AND estado_investigacion=?'.format(ft), ('completada',))
print("  fichas adicionales completadas ahora:", cur.fetchone()[0])
con.close()
print("\nLISTO — {} fichas dejaron de pintarse blancas.".format(len(objetivo)))
