import sqlite3

conn = sqlite3.connect(r'C:\Users\HP\QField\cloud\porotog_levantamiento_offline\data.gpkg')
cursor = conn.cursor()

# Buscar tablas de fichas
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'Fichas_Predios%'")
tables = cursor.fetchall()

if tables:
    fichas_table = tables[0][0]
    cursor.execute(f"SELECT COUNT(*) FROM \"{fichas_table}\"")
    print("Fichas en el data.gpkg local actual:", cursor.fetchone()[0])
    
    # Contar cuántas fichas tienen clave de Monteserín Bajo
    cursor.execute(f"SELECT COUNT(*) FROM \"{fichas_table}\" WHERE clave_catastral = '1702510040121'")
    print("Fichas de Monteserín Bajo (1702510040121) actuales:", cursor.fetchone()[0])
conn.close()
