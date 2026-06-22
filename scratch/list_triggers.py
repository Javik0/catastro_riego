import sqlite3
import os

QFIELD_DIR = r'C:\Users\HP\QField\cloud\porotog_levantamiento_offline'
DATA_GPKG  = os.path.join(QFIELD_DIR, 'data.gpkg')

conn = sqlite3.connect(DATA_GPKG)
cursor = conn.cursor()

# Buscar tabla de fichas
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
all_tables = [t[0] for t in cursor.fetchall()]
fichas_table = next((t for t in all_tables if 'Fichas_Predios' in t and not any(x in t for x in ('rtree_','log_','gpkg_'))), None)

print(f"Tabla encontrada: {fichas_table}")

if fichas_table:
    # Listar triggers asociados
    cursor.execute("SELECT name, sql FROM sqlite_master WHERE type='trigger' AND tbl_name=?", (fichas_table,))
    triggers = cursor.fetchall()
    print(f"Triggers encontrados: {len(triggers)}")
    for t_name, t_sql in triggers:
        print(f"\n--- TRIGGER: {t_name} ---")
        print(t_sql)

conn.close()
