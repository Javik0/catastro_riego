# -*- coding: utf-8 -*-
"""
Verificación de cobertura de polígonos de ALPAKA en catastro_geo.geojson.
"""
import json
import os

GEOJSON_CATASTRO = r'C:\Users\HP\OneDrive\Escritorio\CAYAMBE CATASTRO RIEGO\padron-app\public\geo\catastro_geo.geojson'
GEOJSON_FICHAS = r'C:\Users\HP\OneDrive\Escritorio\CAYAMBE CATASTRO RIEGO\padron-app\public\geo\fichas_predios.geojson'

with open(GEOJSON_FICHAS, 'r', encoding='utf-8') as f:
    fichas_data = json.load(f)

with open(GEOJSON_CATASTRO, 'r', encoding='utf-8') as f:
    catastro_data = json.load(f)

fichas_alpaka = [f for f in fichas_data['features'] if f['properties'].get('comunidad') == 'ALPAKA']
print(f"Total fichas ALPAKA en fichas_predios.geojson: {len(fichas_alpaka)}")

# Claves de fichas ALPAKA
claves_fichas_alpaka = set(str(f['properties'].get('clave_catastral')).strip() for f in fichas_alpaka if f['properties'].get('clave_catastral'))

# Polígonos en catastro_geo.geojson
polig_catastro = {str(f['properties'].get('clave_cata')).strip(): f for f in catastro_data['features'] if f['properties'].get('clave_cata')}

coincidentes = set(claves_fichas_alpaka) & set(polig_catastro.keys())
faltantes = set(claves_fichas_alpaka) - set(polig_catastro.keys())

print(f"Claves de ALPAKA en fichas_predios: {len(claves_fichas_alpaka)}")
print(f"Polígonos coincidente presentes en catastro_geo.geojson: {len(coincidentes)}")
print(f"Claves de ALPAKA sin polígono en catastro_geo.geojson: {len(faltantes)}")

# Coordenadas BBOX de las fichas de ALPAKA vs polígonos
lons_f = [f['geometry']['coordinates'][0] for f in fichas_alpaka if f['geometry']]
lats_f = [f['geometry']['coordinates'][1] for f in fichas_alpaka if f['geometry']]

print(f"\nRango de coordenadas GPS de las fichas de ALPAKA:")
print(f"  Longitud: [{min(lons_f):.6f}, {max(lons_f):.6f}]")
print(f"  Latitud:  [{min(lats_f):.6f}, {max(lats_f):.6f}]")

# Revisar los polígonos de esas claves coincidentes
polig_alpaka_features = [polig_catastro[c] for c in coincidentes]
print(f"\nTotal features de polígonos de ALPAKA en catastro_geo.geojson: {len(polig_alpaka_features)}")

