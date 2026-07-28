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

# Consultar fichas adicionales de jvk-editor6
cursor.execute(f"""
    SELECT id, clave_catastral, comunidad, creado_por, completado_por, fecha_creacion, fecha_completado, estado_investigacion, origen_datos, observaciones
    FROM "{fichas_table}"
    WHERE (creado_por = 'jvk-editor6' OR completado_por = 'jvk-editor6')
      AND (es_ficha_hija = 1 OR id LIKE 'H-%')
""")
fichas_editor6 = cursor.fetchall()
print(f"Total fichas adicionales de jvk-editor6: {len(fichas_editor6)}")

origenes = {}
estados = {}
fechas_crea = {}
fechas_comp = {}
comunidades = {}

for f in fichas_editor6:
    orig = f[8] or 'Sin Origen'
    est = f[7] or 'Sin Estado'
    f_c = str(f[5])[:16] if f[5] else 'Sin Fecha'
    f_m = str(f[6])[:16] if f[6] else 'Sin Fecha'
    com = f[2] or 'Sin Comunidad'
    
    origenes[orig] = origenes.get(orig, 0) + 1
    estados[est] = estados.get(est, 0) + 1
    fechas_crea[f_c] = fechas_crea.get(f_c, 0) + 1
    fechas_comp[f_m] = fechas_comp.get(f_m, 0) + 1
    comunidades[com] = comunidades.get(com, 0) + 1

print(f"\nOrígenes de datos: {origenes}")
print(f"Estados de investigación: {estados}")
print(f"Comunidades: {comunidades}")

print("\nTop timestamps de creación:")
for k, v in sorted(fechas_crea.items(), key=lambda x: x[1], reverse=True)[:10]:
    print(f"  {k}: {v} fichas")

print("\nTop timestamps de completado:")
for k, v in sorted(fechas_comp.items(), key=lambda x: x[1], reverse=True)[:10]:
    print(f"  {k}: {v} fichas")

# Comprobar si tienen cultivos o animales
f_ids = [f[0] for f in fichas_editor6]
f_ids_str = "','".join(f_ids)

cursor.execute(f"""
    SELECT ficha_id, COUNT(*) 
    FROM "{cultivos_table}" 
    WHERE ficha_id IN ('{f_ids_str}')
    GROUP BY ficha_id
""")
cultivos_dict = dict(cursor.fetchall())

cursor.execute(f"""
    SELECT ficha_id, COUNT(*) 
    FROM "{animales_table}" 
    WHERE ficha_id IN ('{f_ids_str}')
    GROUP BY ficha_id
""")
animales_dict = dict(cursor.fetchall())

print(f"\nFichas con cultivos en tabla Cultivos_Agricolas: {len(cultivos_dict)} / {len(fichas_editor6)}")
print(f"Fichas con animales en tabla Animales_Especies: {len(animales_dict)} / {len(fichas_editor6)}")

print("\nMuestra detallada de 8 fichas de jvk-editor6:")
for f in fichas_editor6[:8]:
    fid = f[0]
    nc = cultivos_dict.get(fid, 0)
    na = animales_dict.get(fid, 0)
    print(f"  ID: {fid} | Clave: {f[1]} | Com: {f[2]} | Creado: {f[3]} | Comp: {f[4]} | FCrea: {f[5]} | FComp: {f[6]} | Orig: {f[8]} | Cul: {nc} | Ani: {na} | Obs: {f[9]}")

conn.close()
