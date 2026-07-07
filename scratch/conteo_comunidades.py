import sqlite3

conn = sqlite3.connect(r'C:\Users\HP\QField\cloud\porotog_levantamiento_offline\data.gpkg')
cursor = conn.cursor()

# Buscar tablas de cultivos
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%cultivos%'")
tables = cursor.fetchall()
print("Tablas encontradas:", tables)

if tables:
    cultivos_table = tables[0][0]
    cursor.execute(f"PRAGMA table_info(\"{cultivos_table}\")")
    print("Columnas de cultivos:", cursor.fetchall())
conn.close()
