import sqlite3
import os
import json

QFIELD_DIR = r'C:\Users\HP\QField\cloud\porotog_levantamiento_offline'
DATA_GPKG  = os.path.join(QFIELD_DIR, 'data.gpkg')

conn = sqlite3.connect(DATA_GPKG)
cursor = conn.cursor()

# Encontrar tabla de Fichas
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
all_tables = [t[0] for t in cursor.fetchall()]
fichas_table = next((t for t in all_tables if 'Fichas_Predios' in t and not any(x in t for x in ('rtree_','log_','gpkg_'))), None)

print(f"Tabla de fichas: {fichas_table}")

if fichas_table:
    # Buscar registros con clave catastral 1702510040121
    cursor.execute(f'PRAGMA table_info("{fichas_table}")')
    cols = [c[1] for c in cursor.fetchall()]
    print("Columnas de la tabla:", cols)

    cursor.execute(f"""
        SELECT * FROM "{fichas_table}"
        WHERE clave_catastral = '1702510040121' OR clave_catastral LIKE '%1702510040121%'
    """)
    rows = cursor.fetchall()
    print(f"\nFichas encontradas: {len(rows)}")
    
    for row in rows:
        record = dict(zip(cols, row))
        # Quitar geom de la impresion por ser binario largo
        if "geom" in record:
            record["geom"] = str(record["geom"][:30]) + "... (bytes)"
        print(json.dumps(record, indent=2, ensure_ascii=False))

conn.close()
