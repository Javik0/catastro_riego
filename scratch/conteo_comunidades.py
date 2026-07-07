import sqlite3

conn = sqlite3.connect(r'C:\Users\HP\QField\cloud\porotog_levantamiento_offline\data.gpkg')
cursor = conn.cursor()

# Buscar tablas de fichas
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'Fichas_Predios%'")
tables = cursor.fetchall()
print("Tablas encontradas:", tables)

if tables:
    fichas_table = tables[0][0]
    cursor.execute(f"""
        SELECT COALESCE(NULLIF(sector_investigacion, ''), 'None') as sec, COUNT(DISTINCT TRIM(comunidad))
        FROM "{fichas_table}"
        WHERE comunidad IS NOT NULL AND comunidad != ''
        GROUP BY sec
    """)
    print("Comunidades por sector (con fichas):", cursor.fetchall())
    
    # Listar comunidades por sector
    cursor.execute(f"""
        SELECT COALESCE(NULLIF(sector_investigacion, ''), 'None') as sec, TRIM(comunidad) as com, COUNT(*) as cnt
        FROM "{fichas_table}"
        WHERE com IS NOT NULL AND com != ''
        GROUP BY sec, com
        ORDER BY sec, com
    """)
    comunidades = cursor.fetchall()
    
    sectors = {'Sector 1': [], 'Sector 2': [], 'Sector 3': []}
    for sec, com, cnt in comunidades:
        sec_name = 'Sector 1' if sec == 'None' else sec
        if sec_name in sectors:
            sectors[sec_name].append((com, cnt))
            
    for sec, coms in sectors.items():
        print(f"\n{sec} - Total comunidades: {len(coms)}")
        for com, cnt in coms:
            print(f"  {com}: {cnt} fichas")
conn.close()
