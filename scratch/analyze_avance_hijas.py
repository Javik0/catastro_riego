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
}

conn = sqlite3.connect(DATA_GPKG)
cursor = conn.cursor()

cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [t[0] for t in cursor.fetchall()]
fichas_table = next((t for t in tables if 'Fichas_Predios' in t and not any(x in t for x in ('rtree_','log_','gpkg_'))), None)
print(f"Tabla fichas: {fichas_table}")

cursor.execute(f'PRAGMA table_info("{fichas_table}")')
cols = [c[1] for c in cursor.fetchall()]

# 1. Avance general de fichas adicionales por estado
cursor.execute(f"""
    SELECT estado_investigacion, COUNT(*) 
    FROM "{fichas_table}"
    WHERE es_ficha_hija = 1 OR id LIKE 'H-%'
    GROUP BY estado_investigacion
""")
print("\n=== RESUMEN GLOBAL DE FICHAS ADICIONALES ===")
for r in cursor.fetchall():
    print(f"  {r[0] or 'Sin estado'}: {r[1]}")

# 2. Fichas adicionales completadas / investigadas por día y técnico
cursor.execute(f"""
    SELECT 
        COALESCE(completado_por, creado_por) as tec,
        substr(COALESCE(fecha_completado, fecha_creacion), 1, 10) as dia,
        estado_investigacion,
        COUNT(*) as total
    FROM "{fichas_table}"
    WHERE (es_ficha_hija = 1 OR id LIKE 'H-%')
      AND estado_investigacion IN ('completada', 'en_revision')
    GROUP BY tec, dia, estado_investigacion
    ORDER BY dia DESC, tec
""")
rows = cursor.fetchall()
print("\n=== FICHAS ADICIONALES INVESTIGADAS/COMPLETADAS POR DÍA Y TÉCNICO ===")
for r in rows:
    tec_nom = MAPEO_TECNICOS.get(r[0], r[0] or 'Sin Asignar')
    print(f"  Día: {r[1]} | Técnico: {tec_nom} ({r[0]}) | Estado: {r[2]} | Total: {r[3]}")

# 3. Avance diario total (fichas principales vs adicionales) por técnico
cursor.execute(f"""
    SELECT 
        COALESCE(completado_por, creado_por) as tec,
        substr(COALESCE(fecha_completado, fecha_creacion), 1, 10) as dia,
        CASE WHEN es_ficha_hija = 1 OR id LIKE 'H-%' THEN 'Ficha Adicional' ELSE 'Ficha Principal' END as tipo,
        COUNT(*) as total
    FROM "{fichas_table}"
    WHERE (fecha_creacion >= '2026-07-01' OR fecha_completado >= '2026-07-01')
    GROUP BY tec, dia, tipo
    ORDER BY dia DESC, tec, tipo
""")
print("\n=== RENDIMIENTO DIARIO RECIENTE (PRINCIPALES VS ADICIONALES) ===")
rows_rec = cursor.fetchall()
dias_dict = {}
for r in rows_rec:
    dia, tec, tipo, cnt = r[1], r[0], r[2], r[3]
    if dia not in dias_dict: dias_dict[dia] = {}
    tec_nom = MAPEO_TECNICOS.get(tec, tec or 'Sin Asignar')
    if tec_nom not in dias_dict[dia]: dias_dict[dia][tec_nom] = {'Principal': 0, 'Adicional': 0}
    if 'Adicional' in tipo:
        dias_dict[dia][tec_nom]['Adicional'] += cnt
    else:
        dias_dict[dia][tec_nom]['Principal'] += cnt

for dia in sorted(dias_dict.keys(), reverse=True)[:10]:
    print(f"\n--- FECHA: {dia} ---")
    for tec, counts in dias_dict[dia].items():
        total_dia = counts['Principal'] + counts['Adicional']
        print(f"  • {tec}: {counts['Principal']} principales + {counts['Adicional']} adicionales = {total_dia} fichas totales/día")

conn.close()
