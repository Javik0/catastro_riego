import sqlite3
import os
import shutil

# Rutas de archivos
QFIELD_DIR = r'C:\Users\HP\QField\cloud\porotog_levantamiento_offline'
DATA_GPKG = os.path.join(QFIELD_DIR, 'data.gpkg')
BACKUP_GPKG = os.path.join(QFIELD_DIR, 'data_backup_cleanup.gpkg')

def cleanup_database():
    if not os.path.exists(DATA_GPKG):
        print(f"Error: No se encontro el archivo del Geopackage en: {DATA_GPKG}")
        return

    # 1. Crear copia de seguridad preventiva
    print(f"Creando copia de seguridad en: {BACKUP_GPKG}...")
    try:
        shutil.copy2(DATA_GPKG, BACKUP_GPKG)
        print("Copia de seguridad creada con exito.")
    except Exception as e:
        print(f"Error al crear la copia de seguridad: {e}")
        return

    # 2. Conectar a la base de datos GPKG (SQLite)
    conn = sqlite3.connect(DATA_GPKG)
    cursor = conn.cursor()

    try:
        # Encontrar el nombre real de la tabla de fichas
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [t[0] for t in cursor.fetchall()]
        fichas_table = next((t for t in tables if 'Fichas_Predios' in t and not any(x in t for x in ('rtree_','log_','gpkg_'))), None)

        if not fichas_table:
            print("Error: No se pudo identificar la tabla de Fichas_Predios en el Geopackage.")
            conn.close()
            return

        print(f"Tabla identificada para depuracion: '{fichas_table}'")

        # ── REGLA 1: Domingo 24 de Mayo (18 registros de Asoc. 17 de Junio -> San José) ──
        cursor.execute(f"""
            UPDATE "{fichas_table}"
            SET comunidad = 'SAN JOSÉ'
            WHERE (comunidad = 'ASOCIACIÓN 17 DE JUNIO' OR comunidad = 'ASOCIACION 17 DE JUNIO')
              AND date(fecha_creacion) = '2026-05-24'
        """)
        regla1_count = cursor.rowcount

        # ── REGLA 2: Lunes 25 de Mayo Mañana (MILAGRO: 08:00 AM a 03:00 PM UTC) ──
        cursor.execute(f"""
            UPDATE "{fichas_table}"
            SET comunidad = 'MILAGRO'
            WHERE date(fecha_creacion) = '2026-05-25'
              AND time(fecha_creacion) >= '08:00:00'
              AND time(fecha_creacion) < '15:00:00'
        """)
        regla2_count = cursor.rowcount

        # ── REGLA 3: Lunes 25 de Mayo Tarde (ASOCIACIÓN 17 DE JUNIO: 03:00 PM en adelante UTC) ──
        # La mayoría ya dice Asoc. 17 de Junio, pero aseguramos consistencia
        cursor.execute(f"""
            UPDATE "{fichas_table}"
            SET comunidad = 'ASOCIACIÓN 17 DE JUNIO'
            WHERE date(fecha_creacion) = '2026-05-25'
              AND time(fecha_creacion) >= '15:00:00'
        """)
        regla3_count = cursor.rowcount

        # ── REGLA 4: Viernes 22 de Mayo (Registros vacíos -> LA LIBERTAD) ──
        cursor.execute(f"""
            UPDATE "{fichas_table}"
            SET comunidad = 'LA LIBERTAD'
            WHERE (comunidad IS NULL OR comunidad = '' OR comunidad = 'None' OR comunidad = 'none')
              AND date(fecha_creacion) = '2026-05-22'
        """)
        regla4_count = cursor.rowcount

        # ── REGLA 5: Martes 26 de Mayo (Registros vacíos -> CHAMBITOLA) ──
        cursor.execute(f"""
            UPDATE "{fichas_table}"
            SET comunidad = 'CHAMBITOLA'
            WHERE (comunidad IS NULL OR comunidad = '' OR comunidad = 'None' OR comunidad = 'none')
              AND date(fecha_creacion) = '2026-05-26'
        """)
        regla5_count = cursor.rowcount

        # Guardar cambios permanentemente en la base de datos
        conn.commit()

        print("\n=== REPORTE DE DEPURACION EN GEOPACKAGE (data.gpkg) ===")
        print(f"1. Domingo 24 de Mayo (Asoc. 17 de Junio -> SAN JOSE):  {regla1_count} registros actualizados.")
        print(f"2. Lunes 25 de Mayo Manana (-> MILAGRO):                  {regla2_count} registros actualizados.")
        print(f"3. Lunes 25 de Mayo Tarde (-> ASOCIACION 17 DE JUNIO):    {regla3_count} registros actualizados.")
        print(f"4. Viernes 22 de Mayo vacios (-> LA LIBERTAD):            {regla4_count} registros actualizados.")
        print(f"5. Martes 26 de Mayo vacios (-> CHAMBITOLA):             {regla5_count} registros actualizados.")
        print("========================================================\n")
        print("¡Base de datos del Geopackage depurada exitosamente!")

    except Exception as e:
        conn.rollback()
        print(f"Error al ejecutar la depuracion en la base de datos: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    cleanup_database()
