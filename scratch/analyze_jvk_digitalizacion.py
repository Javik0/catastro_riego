# -*- coding: utf-8 -*-
import sqlite3

DATA_GPKG = r'C:\Users\HP\QField\cloud\porotog_levantamiento_offline\data.gpkg'
conn = sqlite3.connect(DATA_GPKG)
cursor = conn.cursor()

cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [t[0] for t in cursor.fetchall()]
fichas_table = next((t for t in tables if 'Fichas_Predios' in t and not any(x in t for x in ('rtree_','log_','gpkg_'))), None)
cultivos_table = next((t for t in tables if 'Cultivos_Agricolas' in t and not any(x in t for x in ('rtree_','log_','gpkg_'))), None)
animales_table = next((t for t in tables if 'Animales_Especies' in t and not any(x in t for x in ('rtree_','log_','gpkg_'))), None)

# Consultar las 103 fichas de jvk-digitalizacion del 23-Jul
cursor.execute(f"""
    SELECT id, clave_catastral, comunidad, estado_investigacion, origen_datos, area_riego, area_total, observaciones
    FROM "{fichas_table}"
    WHERE (completado_por = 'jvk-digitalizacion' OR creado_por = 'jvk-digitalizacion')
      AND (substr(fecha_completado, 1, 10) = '2026-07-23' OR substr(fecha_creacion, 1, 10) = '2026-07-23')
""")
fichas_jvk = cursor.fetchall()
print(f"Total fichas de jvk-digitalizacion el 23-Jul: {len(fichas_jvk)}")

f_ids = [f[0] for f in fichas_jvk]
f_ids_str = "','".join(f_ids)

# Verificar cuántas tienen cultivos
cursor.execute(f"""
    SELECT ficha_id, COUNT(*) 
    FROM "{cultivos_table}" 
    WHERE ficha_id IN ('{f_ids_str}')
    GROUP BY ficha_id
""")
cultivos_dict = dict(cursor.fetchall())

# Verificar cuántas tienen animales
cursor.execute(f"""
    SELECT ficha_id, COUNT(*) 
    FROM "{animales_table}" 
    WHERE ficha_id IN ('{f_ids_str}')
    GROUP BY ficha_id
""")
animales_dict = dict(cursor.fetchall())

print(f"\nCon cultivos registrados: {len(cultivos_dict)} / {len(fichas_jvk)}")
print(f"Con animales registrados: {len(animales_dict)} / {len(fichas_jvk)}")

# Clasificación de origen_datos y estado_investigacion
estados = {}
origenes = {}
for f in fichas_jvk:
    est = f[3]
    orig = f[4]
    estados[est] = estados.get(est, 0) + 1
    origenes[orig] = origenes.get(orig, 0) + 1

print(f"\nEstados de investigación: {estados}")
print(f"Orígenes de datos: {origenes}")

print("\nMuestra de las primeras 8 fichas de jvk-digitalizacion:")
for f in fichas_jvk[:8]:
    fid = f[0]
    n_cul = cultivos_dict.get(fid, 0)
    n_ani = animales_dict.get(fid, 0)
    print(f"  ID: {fid} | Clave: {f[1]} | Comunidad: {f[2]} | Estado: {f[3]} | Origen: {f[4]} | Cultivos: {n_cul} | Animales: {n_ani} | Obs: {f[7]}")

conn.close()
