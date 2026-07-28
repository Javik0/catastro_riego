# -*- coding: utf-8 -*-
"""
Investigación profunda sobre el problema de visualización de polígonos en ALPAKA.
Analizaremos:
1. Claves catastrales en fichas_predios.geojson vs catastro_geo.geojson vs CATASTROACTUALIZADORURALCATASTRORURALACTUALIZADO.gpkg
2. Geometría real de los polígonos en CATASTROACTUALIZADORURALCATASTRORURALACTUALIZADO.gpkg para las claves de ALPAKA.
3. Si los polígonos son macro-predios (madres) o micro-lotes fraccionados.
4. Cómo funciona MapPage.tsx para colorear polígonos (catastroData / catastro_geo.geojson vs todos los predios).
"""
import sqlite3
import json
import os

QFIELD_DIR = r'C:\Users\HP\QField\cloud\porotog_levantamiento_offline'
DATA_GPKG = os.path.join(QFIELD_DIR, 'data.gpkg')
CATASTRO_GPKG = os.path.join(QFIELD_DIR, 'CATASTROACTUALIZADORURALCATASTRORURALACTUALIZADO.gpkg')
GEOJSON_CATASTRO = r'C:\Users\HP\OneDrive\Escritorio\CAYAMBE CATASTRO RIEGO\padron-app\public\geo\catastro_geo.geojson'
GEOJSON_FICHAS = r'C:\Users\HP\OneDrive\Escritorio\CAYAMBE CATASTRO RIEGO\padron-app\public\geo\fichas_predios.geojson'

# 1. Cargar fichas de ALPAKA desde GeoJSON exportado
with open(GEOJSON_FICHAS, 'r', encoding='utf-8') as f:
    fichas_data = json.load(f)

fichas_alpaka = [
    feat for feat in fichas_data['features'] 
    if (feat['properties'].get('comunidad') == 'ALPAKA')
]

print(f"Total fichas en ALPAKA: {len(fichas_alpaka)}")

# Analizar claves catastrales únicas en ALPAKA
claves_alpaka = set()
for f in fichas_alpaka:
    c = f['properties'].get('cod_poligono') or f['properties'].get('clave_catastral')
    if c:
        claves_alpaka.add(str(c).strip())

print(f"Claves catastrales distintas en fichas ALPAKA: {len(claves_alpaka)}")
print(f"Muestra de claves distintas (hasta 15): {list(claves_alpaka)[:15]}")

# 2. Cargar catastro_geo.geojson (los polígonos exportados a la web)
with open(GEOJSON_CATASTRO, 'r', encoding='utf-8') as f:
    catastro_data = json.load(f)

polig_map = {}
for feat in catastro_data['features']:
    c = feat['properties'].get('clave_cata')
    if c:
        polig_map[str(c).strip()] = feat

poligonos_alpaka_exportados = [c for c in claves_alpaka if c in polig_map]
print(f"\nPolígonos de ALPAKA presentes en catastro_geo.geojson: {len(poligonos_alpaka_exportados)}")

# 3. Investigar cuántos polígonos DISTINTOS se están pintando en el mapa para las 490 fichas de ALPAKA
print(f"Relación Fichas -> Polígonos exportados:")
fichas_por_poligono = {}
for f in fichas_alpaka:
    c = str(f['properties'].get('cod_poligono') or f['properties'].get('clave_catastral') or '').strip()
    fichas_por_poligono[c] = fichas_por_poligono.get(c, 0) + 1

print(f"Distribución de fichas ALPAKA por polígono (clave_catastral):")
for clave, count in sorted(fichas_por_poligono.items(), key=lambda x: x[1], reverse=True)[:15]:
    print(f"  Clave {clave}: {count} fichas asignadas a esta misma clave")

# 4. Verificar qué pasa en CATASTROACTUALIZADORURALCATASTRORURALACTUALIZADO.gpkg con estas claves
conn_cat = sqlite3.connect(CATASTRO_GPKG)
cursor_cat = conn_cat.cursor()

cursor_cat.execute("SELECT clave_cata, area_predi FROM CATASTROACTUALIZADORURALCATASTRORURALACTUALIZADO WHERE clave_cata IN ({})".format(
    ','.join('?' for _ in list(claves_alpaka)[:20])
), list(list(claves_alpaka)[:20]))

print(f"\nMuestra de áreas de los polígonos catastrales en GPKG:")
for r in cursor_cat.fetchall():
    print(f"  Clave catastral: {r[0]} | Área predio en catastro: {r[1]} m²")

conn_cat.close()

