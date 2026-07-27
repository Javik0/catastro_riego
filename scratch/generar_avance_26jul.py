# -*- coding: utf-8 -*-
import sqlite3
import json

DATA_GPKG = r'C:\Users\HP\QField\cloud\porotog_levantamiento_offline\data.gpkg'
MAPEO_TECNICOS = {
    'u0_a314': 'Melany Jara',
    'u0_a319': 'Melany Jara',
    'jvk-editor': 'Melany Jara',
    'u0_a504': 'Adriana Cuascota',
    'jvk-editor6': 'Adriana Cuascota',
    'u0_a279': 'Huguito Ipial',
    'jvk-editor2': 'Huguito Ipial',
    'u0_a70': 'Pablo Barrionuevo',
    'jvk-editor5': 'Pablo Barrionuevo',
    'u0_a330': 'Mayra Benavides',
    'mayralisseth201': 'Mayra Benavides',
    'u0_a362': 'Martha Simbaña',
    'u0_a335': 'Martha Simbaña',
    'jvk-editor4': 'Martha Simbaña',
    'u0_a2': 'JVK Digitalización (Script)',
    'jvk-digitalizacion': 'JVK Digitalización (Script)',
    'u0_a302': 'Dylan Chavez',
    'jvk-editor3': 'Dylan Chavez',
    'jvk-corp': 'JVK Corp'
}

conn = sqlite3.connect(DATA_GPKG)
cursor = conn.cursor()

cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [t[0] for t in cursor.fetchall()]
fichas_table = next((t for t in tables if 'Fichas_Predios' in t and not any(x in t for x in ('rtree_','log_','gpkg_'))), None)

# Rendimiento del 26 de Julio de 2026 (Ayer)
cursor.execute(f"""
    SELECT 
        COALESCE(completado_por, creado_por) as tec,
        estado_investigacion,
        COUNT(*) as total
    FROM "{fichas_table}"
    WHERE (es_ficha_hija = 1 OR id LIKE 'H-%')
      AND (substr(fecha_completado, 1, 10) = '2026-07-26' OR substr(fecha_creacion, 1, 10) = '2026-07-26')
    GROUP BY tec, estado_investigacion
    ORDER BY total DESC
""")
yer_rows = cursor.fetchall()
print("=== TRABAJO EN FICHAS ADICIONALES EL 26 DE JULIO ===")
for r in yer_rows:
    tec_nom = MAPEO_TECNICOS.get(r[0], r[0] or 'Sin Asignar')
    print(f"  Técnico: {tec_nom} ({r[0]}) | Estado: {r[1]} | Total: {r[2]}")

# Fichas principales del 26-Jul
cursor.execute(f"""
    SELECT 
        COALESCE(completado_por, creado_por) as tec,
        COUNT(*) as total
    FROM "{fichas_table}"
    WHERE (es_ficha_hija IS NULL OR es_ficha_hija = 0)
      AND NOT (id LIKE 'H-%')
      AND (substr(fecha_completado, 1, 10) = '2026-07-26' OR substr(fecha_creacion, 1, 10) = '2026-07-26')
    GROUP BY tec
    ORDER BY total DESC
""")
yer_princ = cursor.fetchall()
print("\n=== FICHAS PRINCIPALES DEL 26 DE JULIO ===")
for r in yer_princ:
    tec_nom = MAPEO_TECNICOS.get(r[0], r[0] or 'Sin Asignar')
    print(f"  Técnico: {tec_nom} ({r[0]}) | Principales: {r[1]}")

conn.close()
