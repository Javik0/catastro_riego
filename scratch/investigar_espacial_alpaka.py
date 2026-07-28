# -*- coding: utf-8 -*-
"""
Investigación espacial:
Verificar la ubicación GPS de las fichas de ALPAKA vs. la ubicación de los polígonos catastrales vinculados.
"""
import sqlite3
import json
import os
import struct

QFIELD_DIR = r'C:\Users\HP\QField\cloud\porotog_levantamiento_offline'
DATA_GPKG = os.path.join(QFIELD_DIR, 'data.gpkg')
CATASTRO_GPKG = os.path.join(QFIELD_DIR, 'CATASTROACTUALIZADORURALCATASTRORURALACTUALIZADO.gpkg')

GEOJSON_FICHAS = r'C:\Users\HP\OneDrive\Escritorio\CAYAMBE CATASTRO RIEGO\padron-app\public\geo\fichas_predios.geojson'
GEOJSON_CATASTRO = r'C:\Users\HP\OneDrive\Escritorio\CAYAMBE CATASTRO RIEGO\padron-app\public\geo\catastro_geo.geojson'

# 1. Cargar la ficha del popup del usuario: CHIMARRO QUISHPE ROSA CENAIDA (LOTE 26-39)
with open(GEOJSON_FICHAS, 'r', encoding='utf-8') as f:
    fichas_data = json.load(f)

fichas_alpaka = [
    feat for feat in fichas_data['features'] 
    if feat['properties'].get('comunidad') == 'ALPAKA'
]

sample_ficha = None
for f in fichas_alpaka:
    if 'ROSA CENAIDA' in (f['properties'].get('nombres') or '') or '26-39' in (f['properties'].get('codigo_final') or ''):
        sample_ficha = f
        break

if not sample_ficha:
    sample_ficha = fichas_alpaka[0]

props = sample_ficha['properties']
coords = sample_ficha['geometry']['coordinates'] # [lon, lat]

print("=" * 80)
print(" INVESTIGACIÓN ESPACIAL DE FICHA ALPAKA")
print("=" * 80)
print(f"Ficha: {props.get('nombres')} {props.get('apellidos')} | Código: {props.get('codigo_final')}")
print(f"Clave asignada: {props.get('clave_catastral')} | Coordenadas GPS (WGS84): {coords}")

# 2. Buscar en catastro_geo.geojson el polígono con esa clave catastral
with open(GEOJSON_CATASTRO, 'r', encoding='utf-8') as f:
    catastro_data = json.load(f)

clave_buscada = str(props.get('clave_catastral')).strip()
poligono_asociado = None
for feat in catastro_data['features']:
    if str(feat['properties'].get('clave_cata')).strip() == clave_buscada:
        poligono_asociado = feat
        break

if poligono_asociado:
    print(f"\nPolígono asociado encontrado en catastro_geo.geojson:")
    print(f"  FID: {poligono_asociado['properties'].get('fid')}")
    print(f"  Clave: {poligono_asociado['properties'].get('clave_cata')}")
    print(f"  Tipo Geometría: {poligono_asociado['geometry']['type']}")
    # Calcular centroide simple de este polígono
    ring = poligono_asociado['geometry']['coordinates'][0]
    if isinstance(ring[0][0], list): # MultiPolygon o Polygon con agujeros
        ring = ring[0]
    avg_lon = sum(pt[0] for pt in ring) / len(ring)
    avg_lat = sum(pt[1] for pt in ring) / len(ring)
    print(f"  Centroide del polígono (WGS84): [{avg_lon:.7f}, {avg_lat:.7f}]")
    
    # Calcular distancia entre el punto GPS de la ficha y el centroide de su polígono asignado
    d_lon = abs(coords[0] - avg_lon) * 111000 * 0.85 # aprox metros lon a lat 0
    d_lat = abs(coords[1] - avg_lat) * 111000
    dist_aprox_m = (d_lon**2 + d_lat**2)**0.5
    print(f"  📍 Distancia entre el punto GPS de la ficha y el polígono asignado: {dist_aprox_m:.1f} metros")
else:
    print(f"\n❌ NO se encontró polígono con clave {clave_buscada} en catastro_geo.geojson")

# 3. ¿Qué polígonos del catastro rural rodean geográficamente las coordenadas GPS de las fichas de ALPAKA?
# Haremos una búsqueda espacial simple de polígonos que contengan o estén cerca de [coords[0], coords[1]]
print(f"\nInvestigando polígonos del catastro rural CATASTROACTUALIZADORURAL en la posición real GPS del punto [{coords[0]}, {coords[1]}]...")

conn_cat = sqlite3.connect(CATASTRO_GPKG)
cursor_cat = conn_cat.cursor()
cursor_cat.execute("SELECT fid, clave_cata, area_predi, CATASTRO_U, CATASTRO_1, CATASTRO_2, CATASTRO_4 FROM CATASTROACTUALIZADORURALCATASTRORURALACTUALIZADO")
rows = cursor_cat.fetchall()
print(f"Total polígonos en el catastro municipal/rural: {len(rows)}")

conn_cat.close()
