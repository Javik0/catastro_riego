# -*- coding: utf-8 -*-
"""
Exportar capas base de GeoPackage a GeoJSON para el Dashboard
Convierte todas las capas de UTM 17S (EPSG:32717) a WGS84 (EPSG:4326).

Capas exportadas:
  - fichas_predios.geojson      → Puntos GPS de fichas investigadas
  - catastro_geo.geojson        → Polígonos del catastro (con fichas asociadas)
  - ramales_riego.geojson       → Líneas de canales de riego
  - parroquias.geojson          → Polígonos de parroquias

Uso:
  python scripts/export_geojson.py

Requisitos opcionales (para conversión de coordenadas de polígonos):
  pip install pyproj
"""

import sqlite3
import json
import struct
import os
import math

# ── Directorios ───────────────────────────────────────────────
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), '..', 'public', 'geo')
os.makedirs(OUTPUT_DIR, exist_ok=True)

QFIELD_DIR = r'C:\Users\HP\QField\cloud\porotog_levantamiento_offline'
DATA_GPKG      = os.path.join(QFIELD_DIR, 'data.gpkg')
CATASTRO_GPKG  = os.path.join(QFIELD_DIR, 'CATASTROACTUALIZADORURALCATASTRORURALACTUALIZADO.gpkg')
PARROQUIAS_GPKG = os.path.join(QFIELD_DIR, 'PARROQUIAS.gpkg')
RAMALES_GPKG   = os.path.join(QFIELD_DIR, 'RamalesGuanguiquiPorotog.gpkg')

# ─── Verificar pyproj ─────────────────────────────────────────
try:
    from pyproj import Transformer
    _transformer = Transformer.from_crs("EPSG:32717", "EPSG:4326", always_xy=True)
    HAS_PYPROJ = True
    print("✓ pyproj disponible — conversión de coordenadas activa")
except ImportError:
    HAS_PYPROJ = False
    print("⚠ pyproj no instalado. Instalar con: pip install pyproj")
    print("  Los polígonos UTM no se convertirán correctamente sin pyproj.")

# ══════════════════════════════════════════════════════════════
# Parseo de geometría GeoPackage (WKB + GPKG header)
# ══════════════════════════════════════════════════════════════

def parse_gpkg_header(blob):
    """Retorna (srid, offset_a_wkb) desde el header del blob GPKG."""
    if not blob or blob[:2] != b'GP':
        return 0, 0
    flags = blob[3]
    envelope_type = (flags >> 1) & 0x07
    is_le = (flags & 0x01) == 1
    srid = struct.unpack('<i' if is_le else '>i', blob[4:8])[0]
    envelope_sizes = {0: 0, 1: 32, 2: 48, 3: 48, 4: 64}
    offset = 8 + envelope_sizes.get(envelope_type, 0)
    return srid, offset

def utm_to_wgs84(x, y):
    """Convierte UTM 17S → WGS84 (lon, lat)."""
    if HAS_PYPROJ:
        lon, lat = _transformer.transform(x, y)
        return round(lon, 7), round(lat, 7)
    # Fallback aproximado (solo si no hay pyproj)
    return round(x, 2), round(y, 2)

def read_wkb_point(wkb, off=0):
    bo = wkb[off]
    fmt = '<' if bo == 1 else '>'
    gtype = struct.unpack(f'{fmt}I', wkb[off+1:off+5])[0]
    x, y = struct.unpack(f'{fmt}dd', wkb[off+5:off+21])
    lon, lat = utm_to_wgs84(x, y)
    return [lon, lat]

def read_wkb_linestring(wkb, off=0):
    bo = wkb[off]
    fmt = '<' if bo == 1 else '>'
    gtype = struct.unpack(f'{fmt}I', wkb[off+1:off+5])[0]
    n_pts = struct.unpack(f'{fmt}I', wkb[off+5:off+9])[0]
    coords = []
    for i in range(n_pts):
        pos = off + 9 + i * 16
        x, y = struct.unpack(f'{fmt}dd', wkb[pos:pos+16])
        lon, lat = utm_to_wgs84(x, y)
        coords.append([lon, lat])
    return coords

def read_wkb_ring(wkb, off, fmt):
    """Lee un anillo de polígono y retorna (coordenadas, nuevo_offset)."""
    n_pts = struct.unpack(f'{fmt}I', wkb[off:off+4])[0]
    coords = []
    for i in range(n_pts):
        pos = off + 4 + i * 16
        x, y = struct.unpack(f'{fmt}dd', wkb[pos:pos+16])
        lon, lat = utm_to_wgs84(x, y)
        coords.append([lon, lat])
    return coords, off + 4 + n_pts * 16

def read_wkb_polygon(wkb, off=0):
    bo = wkb[off]
    fmt = '<' if bo == 1 else '>'
    gtype = struct.unpack(f'{fmt}I', wkb[off+1:off+5])[0]
    n_rings = struct.unpack(f'{fmt}I', wkb[off+5:off+9])[0]
    rings = []
    cur = off + 9
    for _ in range(n_rings):
        ring, cur = read_wkb_ring(wkb, cur, fmt)
        rings.append(ring)
    return rings

def read_wkb_multilinestring(wkb, off=0):
    bo = wkb[off]
    fmt = '<' if bo == 1 else '>'
    n_geoms = struct.unpack(f'{fmt}I', wkb[off+5:off+9])[0]
    lines = []
    cur = off + 9
    for _ in range(n_geoms):
        # cada geometría tiene su propio header WKB (1+4 bytes)
        sub_bo = wkb[cur]
        sub_fmt = '<' if sub_bo == 1 else '>'
        sub_type = struct.unpack(f'{sub_fmt}I', wkb[cur+1:cur+5])[0]
        n_pts = struct.unpack(f'{sub_fmt}I', wkb[cur+5:cur+9])[0]
        coords = []
        for i in range(n_pts):
            pos = cur + 9 + i * 16
            x, y = struct.unpack(f'{sub_fmt}dd', wkb[pos:pos+16])
            lon, lat = utm_to_wgs84(x, y)
            coords.append([lon, lat])
        lines.append(coords)
        cur = cur + 9 + n_pts * 16
    return lines

def parse_geometry(blob):
    """Parsea un blob GPKG y retorna un objeto GeoJSON geometry o None."""
    if not blob:
        return None
    try:
        srid, off = parse_gpkg_header(blob)
        wkb = blob[off:]
        bo = wkb[0]
        fmt = '<' if bo == 1 else '>'
        gtype = struct.unpack(f'{fmt}I', wkb[1:5])[0]
        gtype_base = gtype & 0xFFFF  # ignorar flags Z/M

        if gtype_base == 1:   # Point
            return {"type": "Point", "coordinates": read_wkb_point(wkb, 0)}
        elif gtype_base == 2: # LineString
            return {"type": "LineString", "coordinates": read_wkb_linestring(wkb, 0)}
        elif gtype_base == 3: # Polygon
            return {"type": "Polygon", "coordinates": read_wkb_polygon(wkb, 0)}
        elif gtype_base == 5: # MultiLineString
            return {"type": "MultiLineString", "coordinates": read_wkb_multilinestring(wkb, 0)}
        elif gtype_base == 6: # MultiPolygon
            bo = wkb[0]; fmt = '<' if bo == 1 else '>'
            n_geoms = struct.unpack(f'{fmt}I', wkb[5:9])[0]
            polys = []
            cur = 9
            for _ in range(n_geoms):
                rings = read_wkb_polygon(wkb, cur)
                polys.append(rings)
                # Calcular cuántos bytes ocupa este polígono
                sub_bo = wkb[cur]; sub_fmt = '<' if sub_bo == 1 else '>'
                n_rings = struct.unpack(f'{sub_fmt}I', wkb[cur+5:cur+9])[0]
                cur += 9
                for _ in range(n_rings):
                    n_pts = struct.unpack(f'{sub_fmt}I', wkb[cur:cur+4])[0]
                    cur += 4 + n_pts * 16
            return {"type": "MultiPolygon", "coordinates": polys}
        else:
            return None
    except Exception as e:
        return None

# ══════════════════════════════════════════════════════════════
# 1. Fichas Predios (puntos GPS — ya en WGS84)
# ══════════════════════════════════════════════════════════════

def export_fichas():
    print("\n📍 Exportando Fichas_Predios (puntos GPS)...")
    conn = sqlite3.connect(DATA_GPKG)
    cursor = conn.cursor()

    cursor.execute("SELECT table_name FROM gpkg_contents WHERE data_type='features'")
    fichas_table = next((t[0] for t in cursor.fetchall() if 'Fichas' in t[0] or 'fichas' in t[0]), None)
    if not fichas_table:
        print("  ❌ No se encontró tabla de fichas"); conn.close(); return []

    cursor.execute(f'PRAGMA table_info("{fichas_table}")')
    columns = [col[1] for col in cursor.fetchall()]
    cursor.execute(f'SELECT * FROM "{fichas_table}"')
    rows = cursor.fetchall()

    features = []
    for row in rows:
        props, geom_blob = {}, None
        for i, col in enumerate(columns):
            if col == 'geom': geom_blob = row[i]
            elif col == 'fid_1': continue
            elif row[i] is not None: props[col] = row[i]
        if geom_blob:
            try:
                srid, off = parse_gpkg_header(geom_blob)
                # Fichas ya están en WGS84 (GPS) — NO convertir de UTM
                wkb = geom_blob[off:]
                bo = wkb[0]
                fmt = '<' if bo == 1 else '>'
                x, y = struct.unpack(f'{fmt}dd', wkb[5:21])
                coords = [round(x, 7), round(y, 7)]
                features.append({'type':'Feature','properties':props,'geometry':{'type':'Point','coordinates':coords}})
            except: pass

    _save(features, 'fichas_predios.geojson')
    print(f"  ✓ {len(features)} fichas exportadas")
    conn.close()
    return features

# ══════════════════════════════════════════════════════════════
# 2. Catastro — polígonos con geometría real
# ══════════════════════════════════════════════════════════════

def export_catastro(fichas_features):
    print("\n🗺  Exportando Catastro (polígonos)...")
    claves = set()
    if fichas_features:
        for f in fichas_features:
            c = f['properties'].get('cod_poligono') or f['properties'].get('clave_catastral')
            if c: claves.add(c)
    print(f"  Claves con fichas: {len(claves)}")

    conn = sqlite3.connect(CATASTRO_GPKG)
    cursor = conn.cursor()
    table = 'CATASTROACTUALIZADORURALCATASTRORURALACTUALIZADO'

    cursor.execute(f'PRAGMA table_info("{table}")')
    cols = [c[1] for c in cursor.fetchall()]
    geom_col = next((c for c in cols if c.lower() in ('geom','geometry','shape')), None)
    if not geom_col:
        print("  ❌ No se encontró columna de geometría"); conn.close(); return

    if claves:
        placeholders = ','.join('?' * len(claves))
        cursor.execute(
            f'SELECT fid, clave_cata, area_predi, CATASTRO_U, CATASTRO_1, CATASTRO_2, CATASTRO_4, "{geom_col}" '
            f'FROM "{table}" WHERE clave_cata IN ({placeholders})',
            list(claves)
        )
    else:
        cursor.execute(
            f'SELECT fid, clave_cata, area_predi, CATASTRO_U, CATASTRO_1, CATASTRO_2, CATASTRO_4, "{geom_col}" '
            f'FROM "{table}" LIMIT 600'
        )
    rows = cursor.fetchall()
    features = []
    ok, skip = 0, 0
    for row in rows:
        fid, clave, area, ape, nom, ced, com, blob = row
        geom = parse_geometry(blob)
        if geom:
            ok += 1
        else:
            skip += 1
        features.append({'type':'Feature','properties':{
            'fid': fid, 'clave_cata': clave, 'area_predi': area,
            'apellidos': ape, 'nombres': nom, 'cedula': ced, 'comunidad': com
        },'geometry': geom})

    _save(features, 'catastro_geo.geojson')
    print(f"  ✓ {ok} polígonos con geometría, {skip} sin geometría → catastro_geo.geojson")
    conn.close()


# ══════════════════════════════════════════════════════════════
# 2b. Índice de búsqueda del Catastro (TODOS los 24K+ predios)
# ══════════════════════════════════════════════════════════════

def _calc_centroid(geom):
    """Calcula el centroide aproximado de un GeoJSON geometry."""
    coords_list = []

    def _extract_coords(obj):
        if isinstance(obj, list):
            if len(obj) >= 2 and isinstance(obj[0], (int, float)):
                coords_list.append(obj[:2])
            else:
                for item in obj:
                    _extract_coords(item)

    if geom and geom.get('coordinates'):
        _extract_coords(geom['coordinates'])

    if not coords_list:
        return None, None

    avg_lng = sum(c[0] for c in coords_list) / len(coords_list)
    avg_lat = sum(c[1] for c in coords_list) / len(coords_list)
    return round(avg_lat, 6), round(avg_lng, 6)


def export_catastro_busqueda():
    """Exporta TODOS los predios catastrales como índice de búsqueda ligero (sin geometría, solo centroide)."""
    print("\n🔍 Exportando índice de búsqueda catastral (TODOS los predios)...")
    conn = sqlite3.connect(CATASTRO_GPKG)
    cursor = conn.cursor()
    table = 'CATASTROACTUALIZADORURALCATASTRORURALACTUALIZADO'

    cursor.execute(f'PRAGMA table_info("{table}")')
    cols = [c[1] for c in cursor.fetchall()]
    geom_col = next((c for c in cols if c.lower() in ('geom','geometry','shape')), None)
    if not geom_col:
        print("  ❌ No se encontró columna de geometría"); conn.close(); return

    cursor.execute(
        f'SELECT fid, clave_cata, area_predi, CATASTRO_U, CATASTRO_1, CATASTRO_2, CATASTRO_4, "{geom_col}" '
        f'FROM "{table}"'
    )
    rows = cursor.fetchall()
    registros = []
    ok, skip = 0, 0
    for row in rows:
        fid, clave, area, ape, nom, ced, com, blob = row
        geom = parse_geometry(blob)
        lat, lng = _calc_centroid(geom)
        if lat is not None:
            ok += 1
        else:
            skip += 1
        registros.append({
            'fid': fid,
            'clave_cata': clave or '',
            'area_predi': round(area, 2) if area else 0,
            'apellidos': ape or '',
            'nombres': nom or '',
            'cedula': ced or '',
            'comunidad': com or '',
            'lat': lat,
            'lng': lng,
        })

    path = os.path.join(OUTPUT_DIR, 'catastro_busqueda.json')
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(registros, f, ensure_ascii=False)
    size_kb = os.path.getsize(path) / 1024
    print(f"  💾 catastro_busqueda.json ({size_kb:.0f} KB)")
    print(f"  ✓ {ok} predios con centroide, {skip} sin coordenadas → catastro_busqueda.json")
    conn.close()


# ══════════════════════════════════════════════════════════════
# 2c. Geometrías de polígonos catastrales (para visualizar en búsqueda)
# ══════════════════════════════════════════════════════════════

def _round_coords(obj, decimals=5):
    """Redondea recursivamente todas las coordenadas en un GeoJSON geometry."""
    if isinstance(obj, list):
        if len(obj) >= 2 and isinstance(obj[0], (int, float)):
            return [round(obj[0], decimals), round(obj[1], decimals)]
        return [_round_coords(item, decimals) for item in obj]
    return obj


def export_catastro_poligonos():
    """Exporta TODOS los polígonos catastrales indexados por fid (solo geometría, sin propiedades).
    Archivo: catastro_poligonos.json = { "fid": { "type": "...", "coordinates": [...] }, ... }
    Coordenadas redondeadas a 5 decimales (~1.1m precisión) para reducir tamaño.
    """
    print("\n🗺️  Exportando polígonos catastrales (TODOS, para búsqueda visual)...")
    conn = sqlite3.connect(CATASTRO_GPKG)
    cursor = conn.cursor()
    table = 'CATASTROACTUALIZADORURALCATASTRORURALACTUALIZADO'

    cursor.execute(f'PRAGMA table_info("{table}")')
    cols = [c[1] for c in cursor.fetchall()]
    geom_col = next((c for c in cols if c.lower() in ('geom','geometry','shape')), None)
    if not geom_col:
        print("  ❌ No se encontró columna de geometría"); conn.close(); return

    cursor.execute(f'SELECT fid, "{geom_col}" FROM "{table}"')
    rows = cursor.fetchall()
    poligonos = {}
    ok, skip = 0, 0
    for row in rows:
        fid, blob = row
        geom = parse_geometry(blob)
        if geom and geom.get('coordinates'):
            geom['coordinates'] = _round_coords(geom['coordinates'])
            poligonos[str(fid)] = geom
            ok += 1
        else:
            skip += 1

    path = os.path.join(OUTPUT_DIR, 'catastro_poligonos.json')
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(poligonos, f, ensure_ascii=False)
    size_kb = os.path.getsize(path) / 1024
    size_mb = size_kb / 1024
    print(f"  💾 catastro_poligonos.json ({size_mb:.1f} MB)")
    print(f"  ✓ {ok} polígonos exportados, {skip} sin geometría")
    print(f"  ℹ  Firebase Hosting sirve gzip (~{size_mb*0.15:.1f} MB transferido)")
    conn.close()

# ══════════════════════════════════════════════════════════════
# 3. Ramales de Riego (líneas)
# ══════════════════════════════════════════════════════════════

def export_ramales():
    print("\n💧 Exportando Ramales de Riego (canales)...")
    if not os.path.exists(RAMALES_GPKG):
        print(f"  ❌ No se encontró: {RAMALES_GPKG}"); return

    conn = sqlite3.connect(RAMALES_GPKG)
    cursor = conn.cursor()

    cursor.execute("SELECT table_name FROM gpkg_contents WHERE data_type='features'")
    tables = [t[0] for t in cursor.fetchall()]
    if not tables:
        print("  ❌ No hay capas de features"); conn.close(); return
    table = tables[0]
    print(f"  Tabla: {table}")

    cursor.execute(f'PRAGMA table_info("{table}")')
    cols = [c[1] for c in cursor.fetchall()]
    geom_col = next((c for c in cols if c.lower() in ('geom','geometry','shape')), None)
    prop_cols = [c for c in cols if c != geom_col and c not in ('fid','fid_1')]
    if not geom_col:
        print("  ❌ No se encontró columna de geometría"); conn.close(); return

    col_list = ', '.join([f'"{c}"' for c in prop_cols] + [f'"{geom_col}"'])
    cursor.execute(f'SELECT {col_list} FROM "{table}"')
    rows = cursor.fetchall()

    features = []
    ok, skip = 0, 0
    for row in rows:
        props = {prop_cols[i]: row[i] for i in range(len(prop_cols)) if row[i] is not None}
        blob = row[-1]
        geom = parse_geometry(blob)
        if geom: ok += 1
        else: skip += 1
        features.append({'type':'Feature','properties':props,'geometry':geom})

    _save(features, 'ramales_riego.geojson')
    print(f"  ✓ {ok} ramales con geometría, {skip} sin geometría → ramales_riego.geojson")
    conn.close()

# ══════════════════════════════════════════════════════════════
# 4. Tablas hijas (Cultivos, Animales, Predios Adicionales)
# ══════════════════════════════════════════════════════════════

def export_tablas_hijas():
    print("\n📋 Exportando tablas hijas...")
    conn = sqlite3.connect(DATA_GPKG)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    all_tables = [t[0] for t in cursor.fetchall()]

    for keyword, output_name in [('Cultivo','cultivos'), ('Animal','animales'), ('Predios_Adicionales','predios_adicionales')]:
        matched = [t for t in all_tables if keyword in t and not any(x in t for x in ('gpkg_','rtree_','log_'))]
        if not matched: print(f"  ⚠ No se encontró tabla para '{keyword}'"); continue
        table = matched[0]
        cursor.execute(f'PRAGMA table_info("{table}")')
        all_cols = [c[1] for c in cursor.fetchall()]
        cursor.execute(f'SELECT * FROM "{table}"')
        data = []
        for row in cursor.fetchall():
            item = {all_cols[i]: row[i] for i in range(len(all_cols)) if all_cols[i] not in ('geom','fid_1') and row[i] is not None}
            if item: data.append(item)
        path = os.path.join(OUTPUT_DIR, f'{output_name}.json')
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"  ✓ {len(data)} {output_name}")
    conn.close()

# ══════════════════════════════════════════════════════════════
# Utilidad
# ══════════════════════════════════════════════════════════════

def _save(features, filename):
    path = os.path.join(OUTPUT_DIR, filename)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump({'type':'FeatureCollection','features':features}, f, ensure_ascii=False)
    size_kb = os.path.getsize(path) / 1024
    print(f"  💾 {filename} ({size_kb:.0f} KB)")


def export_stats(fichas):
    print("\n📊 Generando estadísticas para el Login...")
    claves = set()
    tecnicos = set()
    for f in fichas:
        c = f['properties'].get('cod_poligono') or f['properties'].get('clave_catastral')
        if c:
            claves.add(c)
        t = f['properties'].get('creado_por')
        if t:
            tecnicos.add(t)
            
    stats = {
        "fichas": len(fichas),
        "predios": len(claves),
        "tecnicos": len(tecnicos) if len(tecnicos) > 0 else 9
    }
    
    path = os.path.join(OUTPUT_DIR, 'stats.json')
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)
    print(f"  ✓ {stats['fichas']} fichas, {stats['predios']} predios, {stats['tecnicos']} técnicos → stats.json")

# ══════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════

if __name__ == '__main__':
    print("═" * 60)
    print("  EXPORTACIÓN GEOGRÁFICA → Dashboard Riego Porotog")
    print("═" * 60)

    if not os.path.exists(DATA_GPKG):
        print(f"\n❌ ERROR: No se encontró {DATA_GPKG}")
        print("  Asegúrate de que QFieldCloud esté sincronizado y la ruta sea correcta.")
        exit(1)

    fichas = export_fichas()
    export_catastro(fichas)
    export_catastro_busqueda()
    export_catastro_poligonos()
    export_ramales()
    export_tablas_hijas()
    export_stats(fichas)

    print("\n" + "═" * 60)
    print("  ✅ EXPORTACIÓN COMPLETADA")
    print(f"  📁 Archivos en: {os.path.abspath(OUTPUT_DIR)}")
    print("═" * 60)
    print("\n⚡ Siguiente paso: sube los cambios a GitHub:")
    print("   git add public/geo/; git commit -m 'data: sync desde QFieldCloud'; git push")
