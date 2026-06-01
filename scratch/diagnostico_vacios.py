import sqlite3
import os

GPKG = r'C:\Users\HP\QField\cloud\porotog_levantamiento_offline\data.gpkg'
conn = sqlite3.connect(GPKG)
cur = conn.cursor()

cur.execute("SELECT table_name FROM gpkg_contents WHERE data_type='features'")
tables = [t[0] for t in cur.fetchall()]
fichas_table = [t for t in tables if 'Fichas' in t or 'fichas' in t][0]

cur.execute(f'PRAGMA table_info("{fichas_table}")')
cols = [c[1] for c in cur.fetchall()]

cur.execute(f'SELECT * FROM "{fichas_table}"')
rows = cur.fetchall()

total = len(rows)
print(f"Total de registros: {total}")

fields_to_check = [
    'parroquia', 'sector', 'comunidad', 'sector_comunidad',
    'metodo_aspersion_pct', 'metodo_gravedad_pct', 'metodo_goteo_pct',
    'caudal_valor', 'caudal_tipo', 'frecuencia_riego'
]

for col in fields_to_check:
    if col in cols:
        idx = cols.index(col)
        vacios = sum(1 for r in rows if r[idx] is None or str(r[idx]).strip() == '' or (col.endswith('_pct') and r[idx] == 0))
        print(f"Campo '{col}' vacío o 0: {vacios} ({vacios/total*100:.1f}%)")

print("\nEjemplos de registros con comunidad vacía:")
com_idx = cols.index('comunidad')
sec_idx = cols.index('sector_comunidad')
tec_idx = cols.index('creado_por')
fecha_idx = cols.index('fecha_creacion')
prop_idx = cols.index('apellidos') if 'apellidos' in cols else 0

for r in rows:
    if r[com_idx] is None or str(r[com_idx]).strip() == '':
        print(f"Fecha: {r[fecha_idx]} | Técnico: {r[tec_idx]} | Sector Com.: {r[sec_idx]} | Prop: {r[prop_idx]}")

conn.close()
