import sqlite3, json

GPKG = r'C:\Users\HP\QField\cloud\porotog_levantamiento_offline\data.gpkg'
conn = sqlite3.connect(GPKG)
cur = conn.cursor()

cur.execute("SELECT table_name FROM gpkg_contents WHERE data_type='features'")
tables = [t[0] for t in cur.fetchall()]
fichas_table = [t for t in tables if 'Fichas' in t or 'fichas' in t][0]

cur.execute(f'PRAGMA table_info("{fichas_table}")')
cols = [c[1] for c in cur.fetchall()]

relevant = [c for c in cols if any(k in c.lower() for k in ['sector', 'comunidad', 'comuna', 'parroquia'])]
print(f"Tabla: {fichas_table}")
print(f"Campos relevantes: {json.dumps(relevant, indent=2, ensure_ascii=False)}")

for col in relevant:
    cur.execute(f'SELECT DISTINCT "{col}" FROM "{fichas_table}" WHERE "{col}" IS NOT NULL ORDER BY "{col}"')
    vals = [r[0] for r in cur.fetchall()]
    print(f"\n{col} ({len(vals)} valores): {vals[:25]}")

conn.close()
