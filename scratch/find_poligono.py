import sqlite3
import os

QFIELD_DIR = r'C:\Users\HP\QField\cloud\porotog_levantamiento_offline'
CATASTRO_GPKG = os.path.join(QFIELD_DIR, 'CATASTROACTUALIZADORURALCATASTRORURALACTUALIZADO.gpkg')

conn = sqlite3.connect(CATASTRO_GPKG)
cursor = conn.cursor()

# Listar tablas
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
all_tables = [t[0] for t in cursor.fetchall()]
print("Tablas en Catastro GPKG:", all_tables)

catastro_table = next((t for t in all_tables if 'CATASTRO' in t and not any(x in t for x in ('rtree_','log_','gpkg_'))), None)
print(f"Tabla de catastro identificada: {catastro_table}")

if catastro_table:
    # Buscar el poligono con clave catastral 1702510040121
    cursor.execute(f'PRAGMA table_info("{catastro_table}")')
    cols = [c[1] for c in cursor.fetchall()]
    print("Columnas:", cols)
    
    # Buscar clave catastral 1702510040121 (verificar que columna corresponde)
    clave_col = next((c for c in cols if 'clave' in c.lower() or 'codigo' in c.lower()), None)
    print(f"Columna de clave probable: {clave_col}")
    
    if clave_col:
        cursor.execute(f"""
            SELECT COUNT(*) FROM "{catastro_table}"
            WHERE "{clave_col}" = '1702510040121' OR "{clave_col}" LIKE '%1702510040121%'
        """)
        count = cursor.fetchone()[0]
        print(f"Poligonos encontrados con esa clave: {count}")
        
        if count > 0:
            cursor.execute(f"""
                SELECT "{clave_col}", geom FROM "{catastro_table}"
                WHERE "{clave_col}" = '1702510040121' OR "{clave_col}" LIKE '%1702510040121%'
            """)
            row = cursor.fetchone()
            print(f"Clave real: {row[0]}, Geom bytes len: {len(row[1]) if row[1] else 0}")
            
conn.close()
