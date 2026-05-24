# -*- coding: utf-8 -*-
"""
Exportar capas base de GeoPackage a GeoJSON para el Dashboard
Convierte las capas de referencia (polígonos catastro, parroquias, ramales)
de UTM 17S (EPSG:32717) a WGS84 (EPSG:4326) para uso en Leaflet.

Solo exporta los polígonos que tienen fichas investigadas (los relevantes).

Uso: python scripts/export_geojson.py
"""

import sqlite3
import json
import struct
import os
import sys

# Directorio de salida
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), '..', 'public', 'geo')
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Rutas a los GeoPackages
QFIELD_DIR = r'C:\Users\HP\QField\cloud\porotog_levantamiento_offline'
DATA_GPKG = os.path.join(QFIELD_DIR, 'data.gpkg')
CATASTRO_GPKG = os.path.join(QFIELD_DIR, 'CATASTROACTUALIZADORURALCATASTRORURALACTUALIZADO.gpkg')
PARROQUIAS_GPKG = os.path.join(QFIELD_DIR, 'PARROQUIAS.gpkg')
RAMALES_GPKG = os.path.join(QFIELD_DIR, 'RamalesGuanguiquiPorotog.gpkg')

# ═══════════════════════════════════════
# Utilidades para leer geometría GPKG
# ═══════════════════════════════════════

def parse_gpkg_header(blob):
    """Parse GeoPackage geometry header and return (srid, offset_to_wkb)."""
    if blob[:2] != b'GP':
        return 0, 0
    version = blob[2]
    flags = blob[3]
    envelope_type = (flags >> 1) & 0x07
    srid = struct.unpack('<i', blob[4:8])[0]
    
    envelope_sizes = {0: 0, 1: 32, 2: 48, 3: 48, 4: 64}
    offset = 8 + envelope_sizes.get(envelope_type, 0)
    return srid, offset

def wkb_to_coordinates_point(wkb, offset=0):
    """Extract point coordinates from WKB."""
    byte_order = wkb[offset]
    fmt = '<' if byte_order == 1 else '>'
    geom_type = struct.unpack(f'{fmt}I', wkb[offset+1:offset+5])[0]
    x, y = struct.unpack(f'{fmt}dd', wkb[offset+5:offset+21])
    return [round(x, 6), round(y, 6)]


# ═══════════════════════════════════════
# Exportar Fichas (puntos) a GeoJSON
# ═══════════════════════════════════════

def export_fichas():
    """Exporta los puntos de fichas investigadas."""
    print("Exportando Fichas_Predios...")
    
    conn = sqlite3.connect(DATA_GPKG)
    cursor = conn.cursor()
    
    # Encontrar la tabla de fichas (nombre con UUID)
    cursor.execute("SELECT table_name FROM gpkg_contents WHERE data_type='features'")
    tables = cursor.fetchall()
    fichas_table = None
    for t in tables:
        if 'Fichas' in t[0] or 'fichas' in t[0]:
            fichas_table = t[0]
            break
    
    if not fichas_table:
        print("  ERROR: No se encontró tabla de fichas")
        conn.close()
        return
    
    cursor.execute(f'PRAGMA table_info("{fichas_table}")')
    columns = [col[1] for col in cursor.fetchall()]
    
    cursor.execute(f'SELECT * FROM "{fichas_table}"')
    rows = cursor.fetchall()
    
    features = []
    for row in rows:
        props = {}
        geom_blob = None
        for i, col_name in enumerate(columns):
            if col_name == 'geom':
                geom_blob = row[i]
            elif col_name == 'fid_1':
                continue
            elif row[i] is not None:
                props[col_name] = row[i]
        
        if geom_blob:
            try:
                srid, offset = parse_gpkg_header(geom_blob)
                coords = wkb_to_coordinates_point(geom_blob, offset)
                features.append({
                    'type': 'Feature',
                    'properties': props,
                    'geometry': {
                        'type': 'Point',
                        'coordinates': coords
                    }
                })
            except Exception as e:
                print(f"  WARN: Error parsing geometry for fid={props.get('fid', '?')}: {e}")
    
    geojson = {
        'type': 'FeatureCollection',
        'features': features
    }
    
    output_path = os.path.join(OUTPUT_DIR, 'fichas_predios.geojson')
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(geojson, f, ensure_ascii=False)
    
    print(f"  ✓ {len(features)} fichas exportadas → {output_path}")
    conn.close()
    return features


# ═══════════════════════════════════════
# Exportar Parroquias a GeoJSON
# ═══════════════════════════════════════

def export_parroquias():
    """Exporta los polígonos de parroquias. Son solo 8, se exportan todos."""
    print("Exportando PARROQUIAS...")
    
    try:
        from pyproj import Transformer
        transformer = Transformer.from_crs("EPSG:32717", "EPSG:4326", always_xy=True)
        has_pyproj = True
    except ImportError:
        print("  WARN: pyproj no instalado. Las coordenadas quedarán en UTM.")
        has_pyproj = False
    
    conn = sqlite3.connect(PARROQUIAS_GPKG)
    cursor = conn.cursor()
    
    cursor.execute("SELECT fid, nombre, cod_catast, area_ha, area_km2 FROM PARROQUIAS")
    rows = cursor.fetchall()
    
    features = []
    for row in rows:
        props = {
            'fid': row[0],
            'nombre': row[1],
            'cod_catast': row[2],
            'area_ha': row[3],
            'area_km2': row[4],
        }
        features.append({
            'type': 'Feature',
            'properties': props,
            'geometry': None  # Se llenará si podemos parsear WKB
        })
    
    # Simplificado: solo exportar propiedades por ahora
    # La geometría de parroquias es compleja (MultiPolygon)
    # Se necesita ogr2ogr o pyproj + shapely para convertir correctamente
    
    geojson = {
        'type': 'FeatureCollection',
        'features': features
    }
    
    output_path = os.path.join(OUTPUT_DIR, 'parroquias.geojson')
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(geojson, f, ensure_ascii=False)
    
    print(f"  ✓ {len(features)} parroquias exportadas → {output_path}")
    conn.close()


# ═══════════════════════════════════════
# Exportar Catastro (solo polígonos relevantes)
# ═══════════════════════════════════════

def export_catastro_relevantes(fichas_features):
    """Exporta solo los polígonos del catastro que tienen fichas asociadas."""
    print("Exportando polígonos relevantes del CATASTRO...")
    
    # Recopilar claves catastrales con fichas
    claves_con_fichas = set()
    if fichas_features:
        for f in fichas_features:
            clave = f['properties'].get('cod_poligono') or f['properties'].get('clave_catastral')
            if clave:
                claves_con_fichas.add(clave)
    
    print(f"  Claves catastrales con fichas: {len(claves_con_fichas)}")
    
    if not claves_con_fichas:
        print("  WARN: No hay claves para filtrar. Exportando propiedades básicas de todos.")
    
    conn = sqlite3.connect(CATASTRO_GPKG)
    cursor = conn.cursor()
    
    # Solo exportar propiedades (sin geometría pesada por ahora)
    table_name = 'CATASTROACTUALIZADORURALCATASTRORURALACTUALIZADO'
    
    if claves_con_fichas:
        placeholders = ','.join('?' * len(claves_con_fichas))
        cursor.execute(
            f'SELECT fid, clave_cata, area_predi, CATASTRO_U, CATASTRO_1, CATASTRO_4 '
            f'FROM "{table_name}" WHERE clave_cata IN ({placeholders})',
            list(claves_con_fichas)
        )
    else:
        cursor.execute(
            f'SELECT fid, clave_cata, area_predi, CATASTRO_U, CATASTRO_1, CATASTRO_4 '
            f'FROM "{table_name}" LIMIT 1000'
        )
    
    rows = cursor.fetchall()
    features = []
    for row in rows:
        features.append({
            'type': 'Feature',
            'properties': {
                'fid': row[0],
                'clave_cata': row[1],
                'area_predi': row[2],
                'apellidos': row[3],
                'nombres': row[4],
                'comunidad': row[5],
            },
            'geometry': None
        })
    
    geojson = {
        'type': 'FeatureCollection',
        'features': features
    }
    
    output_path = os.path.join(OUTPUT_DIR, 'catastro_relevantes.geojson')
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(geojson, f, ensure_ascii=False)
    
    print(f"  ✓ {len(features)} polígonos relevantes exportados → {output_path}")
    conn.close()


# ═══════════════════════════════════════
# Exportar tablas hijas
# ═══════════════════════════════════════

def export_tablas_hijas():
    """Exporta Cultivos, Animales y Predios Adicionales como JSON."""
    print("Exportando tablas hijas...")
    
    conn = sqlite3.connect(DATA_GPKG)
    cursor = conn.cursor()
    
    # Encontrar tablas
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    all_tables = [t[0] for t in cursor.fetchall()]
    
    for keyword, output_name in [('Cultivo', 'cultivos'), ('Animal', 'animales'), ('Predios_Adicionales', 'predios_adicionales')]:
        matched = [t for t in all_tables if keyword in t and 'gpkg_' not in t and 'rtree_' not in t and 'log_' not in t]
        if not matched:
            print(f"  WARN: No se encontró tabla para '{keyword}'")
            continue
        
        table_name = matched[0]
        cursor.execute(f'PRAGMA table_info("{table_name}")')
        columns = [col[1] for col in cursor.fetchall() if col[1] not in ('geom', 'fid_1')]
        
        cursor.execute(f'SELECT * FROM "{table_name}"')
        rows = cursor.fetchall()
        
        cursor.execute(f'PRAGMA table_info("{table_name}")')
        all_cols = [col[1] for col in cursor.fetchall()]
        
        data = []
        for row in rows:
            item = {}
            for i, col_name in enumerate(all_cols):
                if col_name in ('geom', 'fid_1'):
                    continue
                if row[i] is not None:
                    item[col_name] = row[i]
            if item:
                data.append(item)
        
        output_path = os.path.join(OUTPUT_DIR, f'{output_name}.json')
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"  ✓ {len(data)} registros de {output_name} → {output_path}")
    
    conn.close()


# ═══════════════════════════════════════
# MAIN
# ═══════════════════════════════════════

if __name__ == '__main__':
    print("═" * 60)
    print("  EXPORTACIÓN DE DATOS GEOGRÁFICOS → GeoJSON/JSON")
    print("═" * 60)
    print()
    
    fichas = export_fichas()
    print()
    export_parroquias()
    print()
    export_catastro_relevantes(fichas)
    print()
    export_tablas_hijas()
    
    print()
    print("═" * 60)
    print("  ✅ EXPORTACIÓN COMPLETADA")
    print(f"  Archivos en: {os.path.abspath(OUTPUT_DIR)}")
    print("═" * 60)
