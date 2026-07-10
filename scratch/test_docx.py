import sqlite3

conn = sqlite3.connect(r'C:\Users\HP\QField\cloud\porotog_levantamiento_offline\data.gpkg')
cursor = conn.cursor()

# Buscar tablas de fichas
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'Fichas_Predios%'")
table = cursor.fetchone()[0]

# Buscar cualquier registro del Sector 3 cuya comunidad contenga "MONTESER" pero que no tenga la clave catastral de Monteserín Bajo
cursor.execute(f"""
    SELECT id, codigo_final, clave_catastral, creado_por, comunidad, propietario, nombres, apellidos 
    FROM "{table}" 
    WHERE sector_investigacion = 'Sector 3' 
      AND (comunidad LIKE '%MONTESER%' OR comunidad LIKE '%MONTESERR%')
      AND clave_catastral != '1702510040121'
""")
other_monteserin = cursor.fetchall()
print(f"Fichas del Sector 3 con comunidad 'MONTESER...' pero clave catastral diferente de '1702510040121': {len(other_monteserin)}")
for row in other_monteserin:
    print("  ", row)

# Buscar en toda la base de datos (cualquier sector)
cursor.execute(f"""
    SELECT id, codigo_final, clave_catastral, creado_por, comunidad, propietario, nombres, apellidos, sector_investigacion
    FROM "{table}" 
    WHERE (comunidad LIKE '%MONTESER%' OR comunidad LIKE '%MONTESERR%')
      AND clave_catastral != '1702510040121'
""")
other_monteserin_all = cursor.fetchall()
print(f"\nFichas de cualquier sector con comunidad 'MONTESER...' pero clave catastral diferente: {len(other_monteserin_all)}")
for row in other_monteserin_all:
    print("  ", row)

conn.close()
