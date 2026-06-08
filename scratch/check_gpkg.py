import sqlite3
import os

def main():
    gpkg_path = r'C:\Users\HP\QField\cloud\porotog_levantamiento_offline\data.gpkg'
    if not os.path.exists(gpkg_path):
        print(f"No se encontró el Geopackage en: {gpkg_path}")
        return
        
    conn = sqlite3.connect(gpkg_path)
    cursor = conn.cursor()
    
    # Encontrar el nombre de la tabla de fichas
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [t[0] for t in cursor.fetchall()]
    fichas_table = next((t for t in tables if 'Fichas_Predios' in t and not any(x in t for x in ('rtree_','log_','gpkg_'))), None)
    
    if not fichas_table:
        print("No se encontró la tabla de Fichas_Predios")
        conn.close()
        return
        
    target_id = "{d12d86e1-11d3-432c-a207-a7dd45deed7a}"
    cursor.execute(f"SELECT id, cedula, apellidos, nombres, clave_catastral, comunidad, sector_comunidad, parroquia, creado_por, fecha_creacion FROM \"{fichas_table}\" WHERE id = ?", (target_id,))
    row = cursor.fetchone()
    
    if row:
        print("--- REGISTRO EN LA BASE GPKG RAW ---")
        print(f"ID: {row[0]}")
        print(f"Cédula: {row[1]}")
        print(f"Nombre: {row[2]} {row[3]}")
        print(f"Clave: {row[4]}")
        print(f"Comunidad: {row[5]}")
        print(f"Sector Comunidad: {row[6]}")
        print(f"Parroquia: {row[7]}")
        print(f"Creado por: {row[8]}")
        print(f"Fecha Creación: {row[9]}")
        print("-------------------------------------")
    else:
        print(f"No se encontró el registro con ID {target_id} en la base GPKG.")
        
    conn.close()

if __name__ == "__main__":
    main()
