import sqlite3

GPKG = r'C:\Users\HP\QField\cloud\porotog_levantamiento_offline\data.gpkg'
conn = sqlite3.connect(GPKG)
cur = conn.cursor()

cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
all_tables = [t[0] for t in cur.fetchall()]
fichas_table = next(t for t in all_tables if 'Fichas_Predios' in t and not any(x in t for x in ('rtree_','log_','gpkg_')))

cur.execute(f'PRAGMA table_info("{fichas_table}")')
cols = cur.fetchall()
for col in cols:
    print(f"Columna: {col[1]} ({col[2]})")

conn.close()
