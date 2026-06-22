# -*- coding: utf-8 -*-
"""
Corregir áreas con riego inconsistentes físicas en el GeoPackage local.
Actualiza los registros donde area_riego > area_total o area_sin_riego < 0,
fijando area_riego = area_total y area_sin_riego = 0.0.

Uso:
  python scripts/corregir_gpkg_fisico.py
"""

import sqlite3
import os

QFIELD_DIR = r'C:\Users\HP\QField\cloud\porotog_levantamiento_offline'
DATA_GPKG  = os.path.join(QFIELD_DIR, 'data.gpkg')

def main():
    if not os.path.exists(DATA_GPKG):
        print(f"❌ No se encuentra el archivo de datos: {DATA_GPKG}")
        return

    print("════════════════════════════════════════════════════════════")
    # Realizar un backup de seguridad antes de modificar
    backup_path = DATA_GPKG + ".bak_correccion"
    try:
        import shutil
        shutil.copy2(DATA_GPKG, backup_path)
        print(f"💾 Respaldo de seguridad creado en: {backup_path}")
    except Exception as e:
        print(f"⚠️ No se pudo crear el respaldo de seguridad: {e}")

    conn = sqlite3.connect(DATA_GPKG)
    cursor = conn.cursor()

    # Encontrar la tabla dinámica de fichas
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    all_tables = [t[0] for t in cursor.fetchall()]
    fichas_table = next((t for t in all_tables if 'Fichas_Predios' in t and not any(x in t for x in ('rtree_','log_','gpkg_'))), None)

    if not fichas_table:
        print("❌ No se encontró la tabla de Fichas_Predios en el GeoPackage.")
        conn.close()
        return

    print(f"🔍 Buscando inconsistencias de área en la tabla: {fichas_table}")
    
    # Contar registros con error
    cursor.execute(f"""
        SELECT COUNT(*) FROM "{fichas_table}" 
        WHERE area_sin_riego < 0 OR area_riego > area_total
    """)
    inconsistent_count = cursor.fetchone()[0]
    
    if inconsistent_count == 0:
        print("✅ No se encontraron inconsistencias físicas. ¡La base de datos ya está limpia!")
        conn.close()
        return

    print(f"⚠️ Se encontraron {inconsistent_count} registros con errores de área.")

    # Ejecutar la corrección física
    try:
        cursor.execute(f"""
            UPDATE "{fichas_table}"
            SET area_riego = area_total,
                area_sin_riego = 0.0
            WHERE area_sin_riego < 0 OR area_riego > area_total
        """)
        conn.commit()
        print(f"🎉 Se corrigieron exitosamente {inconsistent_count} registros en la base de datos física.")
    except Exception as e:
        conn.rollback()
        print(f"❌ Error al ejecutar la corrección: {e}")

    conn.close()
    print("════════════════════════════════════════════════════════════")

if __name__ == "__main__":
    main()
