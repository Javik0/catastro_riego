# -*- coding: utf-8 -*-
"""
Restaura el ficha_madre_id de las fichas adicionales que lo perdieron.

CAUSA: el desplegable de vinculacion (ValueRelation) que se agrego al formulario
usaba un filtro con current_value('comunidad'). QField no resuelve esa expresion:
mostraba el campo vacio y al guardar la ficha escribia NULL. Todas las hijas que
los tecnicos completaron con ese formulario perdieron el vinculo con su madre.

FUENTES DE RECUPERACION (verificadas sin discrepancias entre si):
  1) Predios_Adicionales.ficha_hija_generada_id -> ficha_id  (madre)
  2) respaldo data_gpkg_2026-07-28_1259_post-descarga.gpkg

MODO SEGURO: simula por defecto; escribe solo con --aplicar.
"""
import sqlite3
import sys

APLICAR = "--aplicar" in sys.argv
DB = r"C:\Users\HP\QField\cloud\porotog_levantamiento_offline\data.gpkg"
BK = r"C:\Users\HP\OneDrive\Escritorio\CAYAMBE CATASTRO RIEGO\respaldos\data_gpkg_2026-07-28_1259_post-descarga.gpkg"

con = sqlite3.connect(DB if APLICAR else "file:{}?mode=ro".format(DB), uri=not APLICAR)
cur = con.cursor()
cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
tabs = [t[0] for t in cur.fetchall()]


def T(kw, tt=None):
    tt = tt or tabs
    return next(t for t in tt if kw in t and not any(x in t for x in ('gpkg_', 'rtree_', 'log_')))


ft, pa = T('Fichas_Predios'), T('Predios_Adicionales')

# ids validos de madres (deben existir y ser principales)
cur.execute('SELECT id FROM "{}" WHERE COALESCE(es_ficha_hija,0) NOT IN (1)'.format(ft))
madres_validas = {r[0] for r in cur.fetchall()}

# fuente 1: Predios_Adicionales
cur.execute('SELECT ficha_hija_generada_id, ficha_id FROM "{}" '
            'WHERE ficha_hija_generada_id IS NOT NULL'.format(pa))
mapa_pa = {h: m for h, m in cur.fetchall() if h and m}

# fuente 2: respaldo del 28
con2 = sqlite3.connect("file:{}?mode=ro".format(BK), uri=True)
c2 = con2.cursor()
c2.execute("SELECT name FROM sqlite_master WHERE type='table'")
ft2 = T('Fichas_Predios', [t[0] for t in c2.fetchall()])
c2.execute('SELECT id, ficha_madre_id FROM "{}" WHERE es_ficha_hija IN (1) '
           'AND ficha_madre_id IS NOT NULL AND ficha_madre_id<>""'.format(ft2))
mapa_bk = dict(c2.fetchall())
con2.close()

cur.execute('SELECT id FROM "{}" WHERE es_ficha_hija IN (1) '
            'AND (ficha_madre_id IS NULL OR ficha_madre_id="")'.format(ft))
sin_madre = [r[0] for r in cur.fetchall()]

print("=" * 70)
print(" {} — RESTAURAR ficha_madre_id".format("APLICANDO" if APLICAR else "SIMULACION"))
print("=" * 70)
print("hijas sin madre:", len(sin_madre))

plan = []
sin_fuente = []
invalidas = []
for h in sin_madre:
    m = mapa_bk.get(h) or mapa_pa.get(h)
    if not m:
        sin_fuente.append(h)
    elif m not in madres_validas:
        invalidas.append((h, m))
    else:
        plan.append((m, h))

print("  restaurables con madre valida :", len(plan))
print("  sin fuente de recuperacion    :", len(sin_fuente))
print("  madre recuperada no valida    :", len(invalidas))

if not APLICAR:
    print("\nSIMULACION — nada escrito. Usar --aplicar.")
    con.close()
    sys.exit(0)

cur.execute("SELECT name, sql FROM sqlite_master WHERE type='trigger'")
trg = [(n, s) for n, s in cur.fetchall() if ft.lower() in (s or '').lower()]
for n, _ in trg:
    cur.execute('DROP TRIGGER IF EXISTS "{}"'.format(n))

cur.executemany('UPDATE "{}" SET ficha_madre_id=? WHERE id=?'.format(ft), plan)
print("\nrestauradas:", cur.rowcount if cur.rowcount >= 0 else len(plan))

for n, s in trg:
    try:
        cur.execute(s)
    except Exception as e:
        print("  [AVISO] trigger {}: {}".format(n, e))
con.commit()
cur.execute("PRAGMA wal_checkpoint(TRUNCATE)")
print("checkpoint:", cur.fetchone())

cur.execute('SELECT COUNT(*) FROM "{}" WHERE es_ficha_hija IN (1) '
            'AND (ficha_madre_id IS NULL OR ficha_madre_id="")'.format(ft))
print("hijas sin madre despues:", cur.fetchone()[0])
con.close()
print("LISTO.")
