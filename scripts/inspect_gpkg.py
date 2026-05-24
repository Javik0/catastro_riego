import sqlite3

# Inspeccionar data.gpkg - tablas hijas (Cultivos, Animales, Predios Adicionales)
gpkg_path = r'C:\Users\HP\QField\cloud\porotog_levantamiento_offline\data.gpkg'
conn = sqlite3.connect(gpkg_path)
cursor = conn.cursor()

# Listar TODAS las tablas (no solo gpkg_contents)
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
all_tables = cursor.fetchall()
print('=== TODAS las tablas en data.gpkg ===')
for t in all_tables:
    if not t[0].startswith('gpkg_') and not t[0].startswith('sqlite_') and not t[0].startswith('rtree_'):
        cursor.execute(f'SELECT COUNT(*) FROM "{t[0]}"')
        count = cursor.fetchone()[0]
        print(f'  {t[0]:60s} -> {count} registros')

# Tablas hijas probables
for table_name in [t[0] for t in all_tables]:
    if 'Cultivo' in table_name or 'Animal' in table_name or 'Predio' in table_name:
        if 'Fichas' not in table_name:
            print(f'\n--- Campos de {table_name} ---')
            cursor.execute(f'PRAGMA table_info("{table_name}")')
            for col in cursor.fetchall():
                print(f'  {col[1]:30s} {col[2]:15s}')
            
            cursor.execute(f'SELECT COUNT(*) FROM "{table_name}"')
            count = cursor.fetchone()[0]
            print(f'  >>> Total: {count}')
            
            if count > 0:
                cursor.execute(f'SELECT * FROM "{table_name}" LIMIT 2')
                sample = cursor.fetchall()
                cursor.execute(f'PRAGMA table_info("{table_name}")')
                col_names = [c[1] for c in cursor.fetchall()]
                for i, row in enumerate(sample):
                    print(f'\n  Ejemplo {i+1}:')
                    for name, val in zip(col_names, row):
                        if val is not None and str(val).strip():
                            print(f'    {name}: {val}')

conn.close()

print('\n\n=== CATASTRO RURAL ===')
catastro_path = r'C:\Users\HP\QField\cloud\porotog_levantamiento_offline\CATASTROACTUALIZADORURALCATASTRORURALACTUALIZADO.gpkg'
conn2 = sqlite3.connect(catastro_path)
cursor2 = conn2.cursor()
cursor2.execute('SELECT table_name, data_type FROM gpkg_contents')
for r in cursor2.fetchall():
    print(f'  Capa: {r[0]} ({r[1]})')
    cursor2.execute(f'PRAGMA table_info("{r[0]}")')
    for col in cursor2.fetchall():
        print(f'    {col[1]:30s} {col[2]}')
    cursor2.execute(f'SELECT COUNT(*) FROM "{r[0]}"')
    print(f'    >>> Total: {cursor2.fetchone()[0]}')
    
    # Sample
    cursor2.execute(f'SELECT * FROM "{r[0]}" LIMIT 1')
    sample = cursor2.fetchone()
    cursor2.execute(f'PRAGMA table_info("{r[0]}")')
    col_names = [c[1] for c in cursor2.fetchall()]
    if sample:
        print(f'\n    Ejemplo:')
        for name, val in zip(col_names, sample):
            if name == 'geom':
                print(f'      {name}: [GEOMETRY BLOB]')
            elif val is not None and str(val).strip():
                print(f'      {name}: {val}')

cursor2.execute('SELECT table_name, column_name, geometry_type_name, srs_id FROM gpkg_geometry_columns')
for g in cursor2.fetchall():
    print(f'  Geometría: {g[0]}.{g[1]} -> {g[2]} (SRS: {g[3]})')

conn2.close()

print('\n\n=== PARROQUIAS ===')
parr_path = r'C:\Users\HP\QField\cloud\porotog_levantamiento_offline\PARROQUIAS.gpkg'
conn3 = sqlite3.connect(parr_path)
cursor3 = conn3.cursor()
cursor3.execute('SELECT table_name FROM gpkg_contents')
for r in cursor3.fetchall():
    print(f'  Capa: {r[0]}')
    cursor3.execute(f'PRAGMA table_info("{r[0]}")')
    for col in cursor3.fetchall():
        print(f'    {col[1]:30s} {col[2]}')
    cursor3.execute(f'SELECT COUNT(*) FROM "{r[0]}"')
    print(f'    >>> Total: {cursor3.fetchone()[0]}')
    
    # All records (should be few parroquias)
    cursor3.execute(f'SELECT * FROM "{r[0]}"')
    all_rows = cursor3.fetchall()
    cursor3.execute(f'PRAGMA table_info("{r[0]}")')
    col_names = [c[1] for c in cursor3.fetchall()]
    for row in all_rows:
        vals = {name: val for name, val in zip(col_names, row) if val is not None and name != 'geom'}
        print(f'    {vals}')
conn3.close()

print('\n\n=== RAMALES ===')
ram_path = r'C:\Users\HP\QField\cloud\porotog_levantamiento_offline\RamalesGuanguiquiPorotog.gpkg'
conn4 = sqlite3.connect(ram_path)
cursor4 = conn4.cursor()
cursor4.execute('SELECT table_name FROM gpkg_contents')
for r in cursor4.fetchall():
    print(f'  Capa: {r[0]}')
    cursor4.execute(f'PRAGMA table_info("{r[0]}")')
    for col in cursor4.fetchall():
        print(f'    {col[1]:30s} {col[2]}')
    cursor4.execute(f'SELECT COUNT(*) FROM "{r[0]}"')
    print(f'    >>> Total: {cursor4.fetchone()[0]}')
conn4.close()
