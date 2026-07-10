# -*- coding: utf-8 -*-
"""
Extraer las estadísticas específicas que Armando necesita para la reunión.
"""
import sqlite3
import json
import os

DATA_GPKG = r'C:\Users\HP\QField\cloud\porotog_levantamiento_offline\data.gpkg'

conn = sqlite3.connect(DATA_GPKG)
cursor = conn.cursor()

# Buscar tabla de fichas
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'Fichas_Predios%'")
tables = [t[0] for t in cursor.fetchall() if not any(x in t[0] for x in ('rtree_','log_','gpkg_'))]
fichas_table = tables[0]
print(f"Tabla de fichas: {fichas_table}")

# Obtener columnas disponibles
cursor.execute(f'PRAGMA table_info("{fichas_table}")')
cols = [c[1] for c in cursor.fetchall()]
print(f"\nColumnas disponibles ({len(cols)}):")
for c in sorted(cols):
    print(f"  - {c}")

# 1. Hectáreas por sector (área total)
print("\n" + "="*60)
print("1. HECTÁREAS POR SECTOR (suma de area_total)")
print("="*60)
cursor.execute(f"""
    SELECT sector_investigacion, 
           COUNT(*) as fichas,
           SUM(CAST(area_total AS REAL)) as total_m2,
           ROUND(SUM(CAST(area_total AS REAL)) / 10000.0, 2) as total_ha
    FROM "{fichas_table}" 
    GROUP BY sector_investigacion
    ORDER BY sector_investigacion
""")
for row in cursor.fetchall():
    print(f"  {row[0]}: {row[1]} fichas, {row[2]:.2f} m², {row[3]:.2f} ha")

# 2. Predios catastrados (claves catastrales únicas)
print("\n" + "="*60)
print("2. PREDIOS CATASTRADOS (claves catastrales únicas por sector)")
print("="*60)
cursor.execute(f"""
    SELECT sector_investigacion, COUNT(DISTINCT clave_catastral) as predios_unicos
    FROM "{fichas_table}" 
    GROUP BY sector_investigacion
    ORDER BY sector_investigacion
""")
for row in cursor.fetchall():
    print(f"  {row[0]}: {row[1]} predios únicos")

# 3. Predios adicionales por sector
print("\n" + "="*60)
print("3. PREDIOS ADICIONALES (Sección 7)")
print("="*60)
# Buscar tabla de predios adicionales
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
all_tables = [t[0] for t in cursor.fetchall()]
pred_table = next((t for t in all_tables if 'Otros_Predios' in t or 'Predios_Adicionales' in t or 'predios_adicionales' in t.lower()), None)
if pred_table:
    print(f"  Tabla: {pred_table}")
    cursor.execute(f'PRAGMA table_info("{pred_table}")')
    pred_cols = [c[1] for c in cursor.fetchall()]
    print(f"  Columnas: {pred_cols}")

# Cargar predios adicionales del JSON ya exportado
pred_json = r'C:\Users\HP\OneDrive\Escritorio\CAYAMBE CATASTRO RIEGO\padron-app\public\geo\predios_adicionales.json'
if os.path.exists(pred_json):
    with open(pred_json, 'r', encoding='utf-8') as f:
        pred_data = json.load(f)
    print(f"  Total predios adicionales exportados: {len(pred_data)}")

# 4. ¿Conoce el proyecto Porotog? (campo conoce_presa)
print("\n" + "="*60)
print("4. CONOCE EL PROYECTO POROTOG (conoce_presa)")
print("="*60)
cursor.execute(f"""
    SELECT sector_investigacion, conoce_presa, COUNT(*) as total
    FROM "{fichas_table}" 
    GROUP BY sector_investigacion, conoce_presa
    ORDER BY sector_investigacion, conoce_presa
""")
for row in cursor.fetchall():
    print(f"  {row[0]} | {row[1]}: {row[2]}")

# Porcentaje global
cursor.execute(f"""
    SELECT conoce_presa, COUNT(*) as total,
           ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM "{fichas_table}"), 1) as pct
    FROM "{fichas_table}" 
    GROUP BY conoce_presa
    ORDER BY total DESC
""")
print("\n  Porcentaje global:")
for row in cursor.fetchall():
    print(f"    {row[0]}: {row[1]} ({row[2]}%)")

# 5. Longitud del canal principal
print("\n" + "="*60)
print("5. LONGITUD DEL CANAL PRINCIPAL (km_canal)")
print("="*60)
cursor.execute(f"""
    SELECT sector_investigacion, 
           AVG(CAST(km_canal AS REAL)) as prom_km,
           MIN(CAST(km_canal AS REAL)) as min_km,
           MAX(CAST(km_canal AS REAL)) as max_km,
           COUNT(CASE WHEN km_canal IS NOT NULL AND km_canal != '' AND km_canal != '0' THEN 1 END) as con_dato
    FROM "{fichas_table}" 
    GROUP BY sector_investigacion
    ORDER BY sector_investigacion
""")
for row in cursor.fetchall():
    print(f"  {row[0]}: Prom={row[1]:.2f} km, Min={row[2]:.2f}, Max={row[3]:.2f}, Con dato={row[4]}")

# 6. Conoce a la presidente de Guanguilqui Porotog (nom_presidente)
print("\n" + "="*60)
print("6. CONOCE PRESIDENTE GUANGUILQUI POROTOG (nom_presidente)")
print("="*60)
cursor.execute(f"""
    SELECT sector_investigacion, 
           COUNT(CASE WHEN nom_presidente IS NOT NULL AND nom_presidente != '' THEN 1 END) as conoce,
           COUNT(CASE WHEN nom_presidente IS NULL OR nom_presidente = '' THEN 1 END) as no_conoce,
           COUNT(*) as total
    FROM "{fichas_table}" 
    GROUP BY sector_investigacion
    ORDER BY sector_investigacion
""")
for row in cursor.fetchall():
    pct = round(row[1] * 100.0 / row[3], 1) if row[3] > 0 else 0
    print(f"  {row[0]}: Conoce={row[1]} ({pct}%), No conoce={row[2]}, Total={row[3]}")

# 7. Población, familias, servicios
print("\n" + "="*60)
print("7. POBLACIÓN Y FAMILIAS (hijos_hombres, hijos_mujeres)")
print("="*60)
cursor.execute(f"""
    SELECT sector_investigacion,
           COUNT(*) as familias,
           SUM(CAST(hijos_hombres AS INTEGER) + CAST(hijos_mujeres AS INTEGER)) as total_hijos,
           AVG(CAST(hijos_hombres AS INTEGER) + CAST(hijos_mujeres AS INTEGER)) as prom_hijos,
           SUM(CAST(hijos_hombres AS INTEGER)) as hijos_h,
           SUM(CAST(hijos_mujeres AS INTEGER)) as hijos_m
    FROM "{fichas_table}" 
    GROUP BY sector_investigacion
    ORDER BY sector_investigacion
""")
for row in cursor.fetchall():
    print(f"  {row[0]}: Familias={row[1]}, Total hijos={row[2]}, Prom={row[3]:.1f}, H={row[4]}, M={row[5]}")

# 8. Servicios (agua_consumo, energia_electrica)
print("\n" + "="*60)
print("8. SERVICIOS BÁSICOS (agua_consumo, energia_electrica)")
print("="*60)
cursor.execute(f"""
    SELECT sector_investigacion, agua_consumo, COUNT(*) as total
    FROM "{fichas_table}" 
    GROUP BY sector_investigacion, agua_consumo
    ORDER BY sector_investigacion, total DESC
""")
print("  Agua de consumo:")
for row in cursor.fetchall():
    print(f"    {row[0]} | {row[1]}: {row[2]}")

cursor.execute(f"""
    SELECT sector_investigacion, energia_electrica, COUNT(*) as total
    FROM "{fichas_table}" 
    GROUP BY sector_investigacion, energia_electrica
    ORDER BY sector_investigacion, total DESC
""")
print("\n  Energía eléctrica:")
for row in cursor.fetchall():
    print(f"    {row[0]} | {row[1]}: {row[2]}")

# 9. Material de construcción
print("\n" + "="*60)
print("9. MATERIAL DE CONSTRUCCIÓN")
print("="*60)
cursor.execute(f"""
    SELECT sector_investigacion, material_construccion, COUNT(*) as total
    FROM "{fichas_table}" 
    GROUP BY sector_investigacion, material_construccion
    ORDER BY sector_investigacion, total DESC
""")
for row in cursor.fetchall():
    print(f"  {row[0]} | {row[1]}: {row[2]}")

# 10. Nivel de instrucción
print("\n" + "="*60)
print("10. NIVEL DE INSTRUCCIÓN")
print("="*60)
cursor.execute(f"""
    SELECT sector_investigacion, nivel_instruccion, COUNT(*) as total
    FROM "{fichas_table}" 
    GROUP BY sector_investigacion, nivel_instruccion
    ORDER BY sector_investigacion, total DESC
""")
for row in cursor.fetchall():
    print(f"  {row[0]} | {row[1]}: {row[2]}")

# 11. Área con riego vs sin riego por sector
print("\n" + "="*60)
print("11. ÁREA CON RIEGO VS SIN RIEGO POR SECTOR")
print("="*60)
cursor.execute(f"""
    SELECT sector_investigacion,
           ROUND(SUM(CAST(area_riego AS REAL)) / 10000.0, 2) as ha_riego,
           ROUND(SUM(CAST(area_sin_riego AS REAL)) / 10000.0, 2) as ha_sin_riego,
           ROUND(SUM(CAST(area_total AS REAL)) / 10000.0, 2) as ha_total
    FROM "{fichas_table}" 
    GROUP BY sector_investigacion
    ORDER BY sector_investigacion
""")
for row in cursor.fetchall():
    print(f"  {row[0]}: Riego={row[1]} ha, Sin riego={row[2]} ha, Total={row[3]} ha")

# 12. Tenencia del predio
print("\n" + "="*60)
print("12. TENENCIA DEL PREDIO")
print("="*60)
cursor.execute(f"""
    SELECT sector_investigacion, tenencia_predio, COUNT(*) as total
    FROM "{fichas_table}" 
    GROUP BY sector_investigacion, tenencia_predio
    ORDER BY sector_investigacion, total DESC
""")
for row in cursor.fetchall():
    print(f"  {row[0]} | {row[1]}: {row[2]}")

conn.close()
print("\n✓ Extracción de estadísticas completada.")
