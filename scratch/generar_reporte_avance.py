# -*- coding: utf-8 -*-
import sqlite3
import os
import json

DATA_GPKG = r'C:\Users\HP\QField\cloud\porotog_levantamiento_offline\data.gpkg'
MAPEO_TECNICOS = {
    "u0_a2": "Ing. Lenyn Pérez",
    "u0_a279": "Ing. Pamela Yugsi",
    "u0_a302": "Ing. Santiago Simbaña",
    "u0_a314": "Ing. Edwin Yugsi",
    "u0_a330": "Ing. Geovanny Yugsi",
    "u0_a331": "Ing. Mauricio Quishpe",
    "u0_a332": "Ing. Cristian Oña",
    "u0_a335": "Ing. Freddy Calderón",
    "u0_a336": "Ing. Edison Paspuel",
    "jvk-editor": "Técnico Editor 1",
    "jvk-editor2": "Técnico Editor 2",
    "jvk-editor3": "Técnico Editor 3",
    "jvk-editor4": "Técnico Editor 4",
    "jvk-editor5": "Técnico Editor 5",
    "jvk-editor6": "Técnico Editor 6",
    "jvk-corp": "Técnico Corp",
    "jvk-digitalizacion": "Equipo Digitalización",
    "mayralisseth201": "Técnica Mayra Lisseth"
}

conn = sqlite3.connect(DATA_GPKG)
cursor = conn.cursor()

cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [t[0] for t in cursor.fetchall()]
fichas_table = next((t for t in tables if 'Fichas_Predios' in t and not any(x in t for x in ('rtree_','log_','gpkg_'))), None)

# Obtener desglose por sector de las fichas adicionales
cursor.execute(f"""
    SELECT COALESCE(sector_investigacion, 'Sin Sector') as sec,
           estado_investigacion,
           COUNT(*) as total
    FROM "{fichas_table}"
    WHERE es_ficha_hija = 1 OR id LIKE 'H-%'
    GROUP BY sec, estado_investigacion
""")
sectores_breakdown = cursor.fetchall()

# Obtener detalle exacto del 23 de Julio de 2026 (Ayer)
cursor.execute(f"""
    SELECT 
        COALESCE(completado_por, creado_por) as tec,
        estado_investigacion,
        COUNT(*) as total
    FROM "{fichas_table}"
    WHERE (es_ficha_hija = 1 OR id LIKE 'H-%')
      AND (substr(fecha_completado, 1, 10) = '2026-07-23' OR substr(fecha_creacion, 1, 10) = '2026-07-23')
    GROUP BY tec, estado_investigacion
    ORDER BY total DESC
""")
ayer_detail = cursor.fetchall()

# Obtener detalle del 22 de Julio de 2026 (Anteayer)
cursor.execute(f"""
    SELECT 
        COALESCE(completado_por, creado_por) as tec,
        estado_investigacion,
        COUNT(*) as total
    FROM "{fichas_table}"
    WHERE (es_ficha_hija = 1 OR id LIKE 'H-%')
      AND (substr(fecha_completado, 1, 10) = '2026-07-22' OR substr(fecha_creacion, 1, 10) = '2026-07-22')
    GROUP BY tec, estado_investigacion
    ORDER BY total DESC
""")
anteayer_detail = cursor.fetchall()

# Acumulado total completado por usuario
cursor.execute(f"""
    SELECT 
        COALESCE(completado_por, creado_por) as tec,
        COUNT(*) as total
    FROM "{fichas_table}"
    WHERE (es_ficha_hija = 1 OR id LIKE 'H-%')
      AND estado_investigacion = 'completada'
    GROUP BY tec
    ORDER BY total DESC
""")
acumulado_detail = cursor.fetchall()

print("✓ Datos extraídos correctamente")
conn.close()
