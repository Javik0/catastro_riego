# -*- coding: utf-8 -*-
"""
Corregir áreas con riego inconsistentes físicas en el GeoPackage local.
Actualiza los registros donde area_riego > area_total o area_sin_riego < 0,
fijando area_riego = area_total y area_sin_riego = 0.0.

Limpia temporalmente los triggers espaciales que requieren funciones de SpatiaLite
para evitar el error "no such function: ST_IsEmpty", ejecutando la corrección
e inmediatamente recreando los triggers originales.
"""

import sqlite3
import os
import shutil

QFIELD_DIR = r'C:\Users\HP\QField\cloud\porotog_levantamiento_offline'
DATA_GPKG  = os.path.join(QFIELD_DIR, 'data.gpkg')

def main():
    if not os.path.exists(DATA_GPKG):
        print(f"[ERROR] No se encuentra el archivo de datos: {DATA_GPKG}")
        return

    print("=" * 60)
    print(" DEPURACION FISICA DE AREAS -> GeoPackage QField")
    print("=" * 60)

    # Realizar un backup de seguridad antes de modificar
    backup_path = DATA_GPKG + ".bak_correccion"
    try:
        shutil.copy2(DATA_GPKG, backup_path)
        print(f"[BACKUP] Respaldo creado en: {backup_path}")
    except Exception as e:
        print(f"[WARN] No se pudo crear el respaldo de seguridad: {e}")

    conn = sqlite3.connect(DATA_GPKG)
    cursor = conn.cursor()

    try:
        # 1. Encontrar la tabla dinámica de fichas
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        all_tables = [t[0] for t in cursor.fetchall()]
        fichas_table = next((t for t in all_tables if 'Fichas_Predios' in t and not any(x in t for x in ('rtree_','log_','gpkg_'))), None)

        if not fichas_table:
            print("[ERROR] No se encontro la tabla de Fichas_Predios.")
            conn.close()
            return

        print(f"[INFO] Analizando tabla: {fichas_table}")
        
        # 2. Contar registros con error de areas
        cursor.execute(f"""
            SELECT COUNT(*) FROM "{fichas_table}" 
            WHERE area_sin_riego < 0 OR area_riego > area_total
        """)
        inconsistent_count = cursor.fetchone()[0]
        
        if inconsistent_count == 0:
            print("[OK] No se encontraron inconsistencias físicas. Base de datos limpia.")
            conn.close()
            return

        print(f"[WARN] Registros con errores de area detectados: {inconsistent_count}")

        # 3. Guardar triggers asociados a la tabla
        cursor.execute("SELECT name, sql FROM sqlite_master WHERE type='trigger' AND tbl_name=?", (fichas_table,))
        triggers_info = cursor.fetchall()
        print(f"[INFO] Respaldando {len(triggers_info)} triggers de la tabla...")

        # 4. Eliminar triggers temporalmente
        for t_name, _ in triggers_info:
            cursor.execute(f'DROP TRIGGER IF EXISTS "{t_name}"')
        print("[INFO] Triggers eliminados temporalmente.")

        # 5. Ejecutar la actualización física de las areas
        cursor.execute(f"""
            UPDATE "{fichas_table}"
            SET area_riego = area_total,
                area_sin_riego = 0.0
            WHERE area_sin_riego < 0 OR area_riego > area_total
        """)
        print(f"[SUCCESS] Se actualizaron {inconsistent_count} registros fisicamente.")

        # 6. Recrear los triggers originales
        print("[INFO] Recreando triggers originales...")
        for _, t_sql in triggers_info:
            cursor.execute(t_sql)
        print("[OK] Triggers recreados exitosamente.")

        # Consolidar transaccion
        conn.commit()
        print(f"[OK] Transaccion confirmada. GeoPackage depurado exitosamente.")

    except Exception as e:
        conn.rollback()
        print(f"[ERROR] Ocurrio un fallo durante la correccion: {e}")
        print("[INFO] Se realizo un rollback de la base de datos.")
    
    finally:
        conn.close()
        print("=" * 60)

if __name__ == "__main__":
    main()
