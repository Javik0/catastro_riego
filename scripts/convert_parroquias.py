"""
Convierte el shapefile de PARROQUIAS a GeoJSON con geometrías incluidas.
El shapefile original tiene proyección UTM 17S (EPSG:32717), por lo que
se reprojecta a WGS84 (EPSG:4326) para uso en Leaflet.
"""
import shapefile
import json
import os
from pyproj import Transformer

# Rutas
SHP_PATH = os.path.join(
    os.path.dirname(__file__), '..', '..', 'INFORMACION BASE', 'PARROQUIAS.shp'
)
OUT_PATH = os.path.join(
    os.path.dirname(__file__), '..', 'public', 'geo', 'parroquias.geojson'
)

# Leer el archivo .prj para diagnosticar la proyección
prj_path = SHP_PATH.replace('.shp', '.prj')
if os.path.exists(prj_path):
    with open(prj_path, 'r') as f:
        prj_text = f.read()
    print(f"Proyección del shapefile:\n{prj_text}\n")

# Crear transformador de coordenadas
# Detectar si es UTM 17S basándose en el .prj
transformer = Transformer.from_crs("EPSG:32717", "EPSG:4326", always_xy=True)

# Leer shapefile
sf = shapefile.Reader(SHP_PATH)
fields = [f[0] for f in sf.fields[1:]]  # Omitir DeletionFlag

print(f"Campos: {fields}")
print(f"Total registros: {len(sf.shapeRecords())}")

features = []
for sr in sf.shapeRecords():
    # Obtener atributos
    props = dict(zip(fields, sr.record))
    # Convertir tipos no-JSON (Decimal, etc.)
    for k, v in props.items():
        if hasattr(v, '__float__'):
            props[k] = float(v)
        elif hasattr(v, '__int__'):
            props[k] = int(v)
    
    geom = sr.shape.__geo_interface__
    
    # Reproyectar coordenadas de UTM 17S a WGS84
    if geom['type'] == 'Polygon':
        new_coords = []
        for ring in geom['coordinates']:
            new_ring = []
            for x, y in ring:
                lng, lat = transformer.transform(x, y)
                new_ring.append([round(lng, 6), round(lat, 6)])
            new_coords.append(new_ring)
        geom['coordinates'] = new_coords
    elif geom['type'] == 'MultiPolygon':
        new_coords = []
        for polygon in geom['coordinates']:
            new_polygon = []
            for ring in polygon:
                new_ring = []
                for x, y in ring:
                    lng, lat = transformer.transform(x, y)
                    new_ring.append([round(lng, 6), round(lat, 6)])
                new_polygon.append(new_ring)
            new_coords.append(new_polygon)
        geom['coordinates'] = new_coords
    
    feature = {
        "type": "Feature",
        "properties": {
            "fid": props.get("FID") or props.get("fid") or props.get("OBJECTID"),
            "nombre": props.get("PARROQUIA") or props.get("nombre") or props.get("NOMBRE") or props.get("NOM_PAR") or props.get("DPA_DESPAR"),
            "cod_catast": props.get("CODIGO") or props.get("cod_catast") or props.get("DPA_PARROQ"),
        },
        "geometry": geom
    }
    features.append(feature)
    
    nombre = feature['properties']['nombre'] or 'SIN NOMBRE'
    tipo = geom['type'] if geom else 'NULL'
    n_coords = sum(len(r) for r in geom['coordinates']) if geom and 'coordinates' in geom else 0
    print(f"  - {nombre}: {tipo} ({n_coords} vértices)")

geojson = {
    "type": "FeatureCollection",
    "features": features
}

os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
with open(OUT_PATH, 'w', encoding='utf-8') as f:
    json.dump(geojson, f, ensure_ascii=False)

print(f"\n✅ GeoJSON generado: {OUT_PATH}")
print(f"   {len(features)} parroquias con geometrías")
print(f"   Tamaño: {os.path.getsize(OUT_PATH) / 1024:.1f} KB")
