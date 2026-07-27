# -*- coding: utf-8 -*-
import sqlite3

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

cursor.execute(f"""
    SELECT 
        substr(COALESCE(fecha_completado, fecha_creacion), 1, 10) as dia,
        COALESCE(completado_por, creado_por) as tec,
        COUNT(CASE WHEN (es_ficha_hija = 1 OR id LIKE 'H-%') THEN 1 END) as adicionales_completadas,
        COUNT(CASE WHEN (es_ficha_hija IS NULL OR es_ficha_hija = 0) AND NOT (id LIKE 'H-%') THEN 1 END) as principales
    FROM "{fichas_table}"
    WHERE (fecha_completado >= '2026-07-20' OR fecha_creacion >= '2026-07-20')
      AND (estado_investigacion = 'completada' OR es_ficha_hija = 1)
    GROUP BY dia, tec
    ORDER BY dia DESC, adicionales_completadas DESC
""")

rows = cursor.fetchall()
print("=== HISTORIAL DE TRABAJO DIARIO (DESDE 20 JULIO 2026) ===")
dias = {}
for r in rows:
    dia, tec_id, adic, princ = r[0], r[1], r[2], r[3]
    tec_nom = MAPEO_TECNICOS.get(tec_id, tec_id or 'Sin Asignar')
    if dia not in dias: dias[dia] = []
    dias[dia].append({'tec': tec_nom, 'user': tec_id, 'adic': adic, 'princ': princ})

for dia, lista in dias.items():
    tot_adic = sum(x['adic'] for x in lista)
    tot_princ = sum(x['princ'] for x in lista)
    print(f"\n📅 FECHA: {dia} | Total Adicionales: {tot_adic} | Total Principales: {tot_princ}")
    for item in lista:
        if item['adic'] > 0 or item['princ'] > 0:
            print(f"   • {item['tec']} (`{item['user']}`): {item['adic']} adicionales completadas | {item['princ']} principales")

conn.close()
