# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════╗
║  GENERADOR DE CAPAS GIS — Sectores y Comunidades             ║
║  Catastro de Riego Cayambe                                   ║
║                                                              ║
║  Genera dos capas disueltas a partir de los predios del       ║
║  catastro que tienen fichas investigadas asociadas:           ║
║    1. Capa de SECTORES DE INVESTIGACIÓN                       ║
║    2. Capa de COMUNIDADES                                     ║
║                                                              ║
║  Las fichas marcadas como discrepantes (fichas_discrepantes   ║
║  .json) se EXCLUYEN del dissolve pero quedan documentadas.   ║
║                                                              ║
║  Salida:                                                     ║
║    - Sectores_Comunidades.gpkg (SRC: EPSG:32717 - UTM 17S)  ║
║    - public/geo/sectores.geojson    (SRC: EPSG:4326)         ║
║    - public/geo/comunidades.geojson (SRC: EPSG:4326)         ║
║                                                              ║
║  Uso:                                                        ║
║    python padron-app/scripts/generar_capas_sectores_comunidades.py ║
╚══════════════════════════════════════════════════════════════╝
"""

import os
import sys
import json
import sqlite3
import struct
import math
import unicodedata
from collections import defaultdict
from datetime import datetime

# Forzar salida UTF-8 en Windows (evita UnicodeEncodeError en consola CP1252)
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf-8', buffering=1)
    sys.stderr = open(sys.stderr.fileno(), mode='w', encoding='utf-8', buffering=1)

# ─── Rutas ────────────────────────────────────────────────────────────────────
QFIELD_DIR     = r'C:\Users\HP\QField\cloud\porotog_levantamiento_offline'
DATA_GPKG      = os.path.join(QFIELD_DIR, 'data.gpkg')
CATASTRO_GPKG  = os.path.join(QFIELD_DIR, 'CATASTROACTUALIZADORURALCATASTRORURALACTUALIZADO.gpkg')
CATASTRO_URBAN = os.path.join(QFIELD_DIR, 'CATASTROURBANOUNIDO.gpkg')

SCRIPT_DIR  = os.path.dirname(os.path.abspath(__file__))
PROYECTO_DIR= os.path.abspath(os.path.join(SCRIPT_DIR, '..', '..'))
OUTPUT_GPKG = os.path.join(PROYECTO_DIR, 'Sectores_Comunidades.gpkg')
GEO_DIR     = os.path.join(SCRIPT_DIR, '..', 'public', 'geo')
DISC_JSON   = os.path.join(PROYECTO_DIR, 'fichas_discrepantes.json')

# ─── Mapeo oficial Comunidades → Sector de Investigación ──────────────────────
COMUNIDADES_POR_SECTOR = {
    'Sector 1': [
        "ASOCIACION 17 DE JUNIO", "ASOCIACION POROTOG", "AVELLANEDA",
        "CARRERA", "CHAMBITOLA", "COCHAPAMBA", "COMUNA IZACATA",
        "COMUNA POROTOG", "CORDILLERAS DE LOS ANDES", "IZACATA GRANDE",
        "JESUS GRAN PODER", "LA CANDELARIA", "LA LIBERTAD",
        "LARCACHACA", "LOMA GORDA", "LOS ANDES IZACATA",
        "MATIAS IMBAGO", "MILAGRO", "SAN ANTONIO", "SAN JACINTO",
        "SAN JOSE", "SANTA BARBARA"
    ],
    'Sector 2': [
        "ALPAKA", "ASOC. PITANA BAJO", "ASOC. SAN VICENTE ALTO",
        "ASOC. SAN VICENTE BAJO", "ASOCIACION ROSALIA", "ASOCIACION SAN PEDRO",
        "CUARTO LOTE", "PAMBAMARCA", "PITANA ALTO", "PROMEJ. PITANA BAJO",
        "PUCARA", "SANTA MARIANITA DE PINGULMI", "SANTA ROSA DE PACCHA",
        "SANTA ROSA DE PINGULMI"
    ],
    'Sector 3': [
        "ASOCIACION ROSALIA", "CANGAHUA PUNGO", "CHAUPIESTANCIA",
        "CHINCHINLOMA", "EL MANZANO", "HDA. GUANGUILQUI",
        "HDA. SAN FRANSISCO", "JUNTA SAN LUIS", "MONTESERIN BAJO",
        "MONTESERRIN ALTO", "OTONCITO", "PAMBAMARQUITO", "PUEBLO DE ASCAZUBI",
        "PUEBLO DE OTON", "SAN VICENTE DE GUAYLLABAMBA", "SR. COLOMA",
        "SR. HERNAN TIMPE"
    ]
}

COM_A_SECTOR = {}
for sec, coms in COMUNIDADES_POR_SECTOR.items():
    for c in coms:
        COM_A_SECTOR[c] = sec

CORRECCIONES_COM = {
    'LARCACOCHA': 'LARCACHACA',
    'LARCACOHA': 'LARCACHACA',
    'INSACATA': 'IZACATA',
    'CARRERA- ACEROLOMA': 'CARRERA',
    'CARRERA-ACEROLOMA': 'CARRERA',
    'CACHICUNGA': 'CARRERA',
    'PANBAMAQUITO': 'PAMBAMARQUITO',
    'PAMBAMAQUITO': 'PAMBAMARQUITO',
    'PANBAMARQUITO': 'PAMBAMARQUITO',
}


# ─── Utilidades ────────────────────────────────────────────────────────────────

def normalizar(texto):
    if not texto:
        return ""
    texto = texto.upper().strip()
    texto = unicodedata.normalize('NFD', texto)
    texto = ''.join(c for c in texto if unicodedata.category(c) != 'Mn')
    import re
    texto = re.sub(r'\s+', ' ', texto)
    return texto


def aplicar_correcciones(com):
    com_norm = normalizar(com)
    for original, correcto in CORRECCIONES_COM.items():
        if normalizar(original) in com_norm:
            return correcto
    return com_norm


# ─── Parseo de geometría GeoPackage (WKB) ─────────────────────────────────────

def parse_gpkg_header(blob):
    if not blob or blob[:2] != b'GP':
        return 0, 0
    flags = blob[3]
    envelope_type = (flags >> 1) & 0x07
    is_le = (flags & 0x01) == 1
    srid = struct.unpack('<i' if is_le else '>i', blob[4:8])[0]
    envelope_sizes = {0: 0, 1: 32, 2: 48, 3: 48, 4: 64}
    offset = 8 + envelope_sizes.get(envelope_type, 0)
    return srid, offset


def leer_anillo(wkb, off, fmt):
    n_pts = struct.unpack(f'{fmt}I', wkb[off:off + 4])[0]
    coords = []
    for i in range(n_pts):
        pos = off + 4 + i * 16
        x, y = struct.unpack(f'{fmt}dd', wkb[pos:pos + 16])
        coords.append([x, y])
    return coords, off + 4 + n_pts * 16


def wkb_a_geojson_geom(wkb, off=0):
    """Convierte un blob WKB (sin el header GeoPackage) a geometría GeoJSON dict.
    Devuelve None si no se puede parsear.
    NOTA: Las coordenadas quedan en el SRC original del GeoPackage (UTM 17S)."""
    try:
        bo = wkb[off]
        fmt = '<' if bo == 1 else '>'
        gtype = struct.unpack(f'{fmt}I', wkb[off + 1:off + 5])[0] & 0xFFFF

        if gtype == 3:  # Polygon
            n_rings = struct.unpack(f'{fmt}I', wkb[off + 5:off + 9])[0]
            rings = []
            cur = off + 9
            for _ in range(n_rings):
                ring, cur = leer_anillo(wkb, cur, fmt)
                rings.append(ring)
            return {'type': 'Polygon', 'coordinates': rings}, cur

        elif gtype == 6:  # MultiPolygon
            n_geoms = struct.unpack(f'{fmt}I', wkb[off + 5:off + 9])[0]
            polys = []
            cur = off + 9
            for _ in range(n_geoms):
                sub_bo = wkb[cur]
                sub_fmt = '<' if sub_bo == 1 else '>'
                sub_type = struct.unpack(f'{sub_fmt}I', wkb[cur + 1:cur + 5])[0] & 0xFFFF
                n_rings = struct.unpack(f'{sub_fmt}I', wkb[cur + 5:cur + 9])[0]
                rings = []
                cur2 = cur + 9
                for _ in range(n_rings):
                    ring, cur2 = leer_anillo(wkb, cur2, sub_fmt)
                    rings.append(ring)
                polys.append(rings)
                cur = cur2
            return {'type': 'MultiPolygon', 'coordinates': polys}, cur

    except Exception as e:
        pass
    return None, None


def blob_a_geojson_geom(blob):
    """Extrae geometría GeoJSON desde un blob GeoPackage. Coordenadas en SRC original."""
    if not blob:
        return None
    try:
        srid, off = parse_gpkg_header(blob)
        wkb = blob[off:]
        geom, _ = wkb_a_geojson_geom(wkb, 0)
        return geom
    except Exception:
        return None


# ─── Conversión UTM 17S → WGS84 ──────────────────────────────────────────────

try:
    from pyproj import Transformer
    _t_utm_wgs = Transformer.from_crs("EPSG:32717", "EPSG:4326", always_xy=True)
    HAS_PYPROJ = True
    print("✓ pyproj disponible — conversión UTM→WGS84 activa")
except ImportError:
    HAS_PYPROJ = False
    print("⚠ pyproj no disponible — instalar con: pip install pyproj")


def convertir_coordenada(x, y):
    """Convierte una coordenada (x, y) de UTM 17S a WGS84 (lon, lat)."""
    if HAS_PYPROJ:
        lon, lat = _t_utm_wgs.transform(x, y)
        return round(lon, 7), round(lat, 7)
    # Fallback: retornar como están (solo si el sistema fuera WGS84)
    return x, y


def convertir_coords_geom(geom):
    """Convierte todas las coordenadas de una geometría GeoJSON de UTM→WGS84 in-place."""
    if geom is None:
        return None

    def conv_ring(ring):
        return [list(convertir_coordenada(c[0], c[1])) for c in ring]

    if geom['type'] == 'Polygon':
        return {
            'type': 'Polygon',
            'coordinates': [conv_ring(ring) for ring in geom['coordinates']]
        }
    elif geom['type'] == 'MultiPolygon':
        return {
            'type': 'MultiPolygon',
            'coordinates': [[conv_ring(ring) for ring in poly] for poly in geom['coordinates']]
        }
    return geom


# ─── Dissolve simple de polígonos (sin Shapely) ───────────────────────────────

def flatten_polygon_to_rings(geom):
    """Extrae todos los anillos exteriores de un polígono o multipolígono."""
    if geom is None:
        return []
    if geom['type'] == 'Polygon':
        return [geom['coordinates'][0]] if geom['coordinates'] else []
    elif geom['type'] == 'MultiPolygon':
        rings = []
        for poly in geom['coordinates']:
            if poly:
                rings.append(poly[0])  # Solo anillo exterior
        return rings
    return []


def dissolve_geoms(geoms_utm):
    """
    Intentamos usar shapely si está disponible para un dissolve real.
    Si no, hacemos un MultiPolygon simple (unión de todos los polígonos).
    Los polígonos de entrada están en coordenadas UTM 17S.
    """
    if not geoms_utm:
        return None

    try:
        from shapely.geometry import shape, MultiPolygon
        from shapely.ops import unary_union

        shapes = []
        for g in geoms_utm:
            try:
                s = shape(g)
                if s.is_valid:
                    shapes.append(s)
                else:
                    shapes.append(s.buffer(0))  # Reparar geometría inválida
            except Exception:
                pass

        if not shapes:
            return None

        union = unary_union(shapes)
        import shapely.geometry
        result_geom = shapely.geometry.mapping(union)
        print(f"      --> Shapely dissolve: {result_geom['type']}")
        return dict(result_geom)

    except ImportError:
        # Sin Shapely: crear MultiPolygon con todos los polígonos
        all_polys = []
        for g in geoms_utm:
            if g is None:
                continue
            if g['type'] == 'Polygon':
                all_polys.append(g['coordinates'])
            elif g['type'] == 'MultiPolygon':
                all_polys.extend(g['coordinates'])
        if not all_polys:
            return None
        if len(all_polys) == 1:
            return {'type': 'Polygon', 'coordinates': all_polys[0]}
        return {'type': 'MultiPolygon', 'coordinates': all_polys}


# ─── Calcular área aproximada (anillo exterior en UTM — ya en metros) ─────────

def calcular_area_utm_m2(geom_utm):
    """Calcula el área total en m² de una geometría UTM (Polygon/MultiPolygon)
    usando la fórmula del polígono de Gauss-Shoelace."""

    def shoelace(ring):
        n = len(ring)
        if n < 3:
            return 0.0
        area = 0.0
        for i in range(n):
            j = (i + 1) % n
            area += ring[i][0] * ring[j][1]
            area -= ring[j][0] * ring[i][1]
        return abs(area) / 2.0

    if geom_utm is None:
        return 0.0
    total = 0.0
    if geom_utm['type'] == 'Polygon':
        if geom_utm['coordinates']:
            total += shoelace(geom_utm['coordinates'][0])
    elif geom_utm['type'] == 'MultiPolygon':
        for poly in geom_utm['coordinates']:
            if poly:
                total += shoelace(poly[0])
    return total


# ─── Leer fichas ──────────────────────────────────────────────────────────────

def leer_fichas():
    print("\n📂 Leyendo fichas desde data.gpkg...")
    conn = sqlite3.connect(DATA_GPKG)
    cursor = conn.cursor()

    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    todas = [t[0] for t in cursor.fetchall()]
    fichas_table = next(
        (t for t in todas if 'Fichas_Predios' in t and not any(x in t for x in ('rtree_', 'log_', 'gpkg_'))),
        None
    )
    if not fichas_table:
        print("  ❌ No se encontró la tabla Fichas_Predios")
        conn.close()
        return []

    cursor.execute(f'PRAGMA table_info("{fichas_table}")')
    columnas = [c[1] for c in cursor.fetchall()]

    cursor.execute(f'SELECT * FROM "{fichas_table}"')
    filas = cursor.fetchall()
    conn.close()

    fichas = []
    for fila in filas:
        d = dict(zip(columnas, fila))
        d['_com_corr'] = aplicar_correcciones(d.get('comunidad', '') or '')
        d['_sec_corr']  = COM_A_SECTOR.get(normalizar(d['_com_corr']), d.get('sector_investigacion', '') or '')
        fichas.append(d)

    print(f"  ✓ {len(fichas)} fichas cargadas")
    return fichas


def leer_ids_discrepantes():
    """Lee los IDs a excluir generados por el script de auditoría."""
    if os.path.exists(DISC_JSON):
        with open(DISC_JSON, 'r', encoding='utf-8') as f:
            data = json.load(f)
        ids = set(data.get('ids_excluir', []))
        print(f"  ✓ {len(ids)} fichas discrepantes cargadas (se excluirán del dissolve)")
        return ids
    else:
        print("  ⚠ fichas_discrepantes.json no encontrado — ejecuta primero el script de auditoría")
        print("    Continuando sin exclusiones...")
        return set()


# ─── Leer y agrupar predios catastrales ───────────────────────────────────────

def leer_catastro_para_fichas(fichas_validas):
    """
    Para cada ficha válida (no discrepante), intenta recuperar la geometría
    del predio catastral usando su clave catastral.
    Retorna un dict: clave_cata → geom_utm (GeoJSON dict en UTM 17S)
    """
    print("\n🗺  Leyendo geometrías catastrales...")
    claves_fichas = set()
    for f in fichas_validas:
        clave = str(f.get('clave_catastral', '') or '').strip()
        if clave:
            claves_fichas.add(clave)

    print(f"  Claves catastrales a buscar: {len(claves_fichas)}")

    geoms_por_clave = {}

    # Catastro Rural
    if os.path.exists(CATASTRO_GPKG):
        conn = sqlite3.connect(CATASTRO_GPKG)
        cursor = conn.cursor()
        table = 'CATASTROACTUALIZADORURALCATASTRORURALACTUALIZADO'
        if claves_fichas:
            ph = ','.join('?' * len(claves_fichas))
            cursor.execute(f'SELECT clave_cata, geom FROM "{table}" WHERE clave_cata IN ({ph})',
                           list(claves_fichas))
        else:
            cursor.execute(f'SELECT clave_cata, geom FROM "{table}"')
        for clave, blob in cursor.fetchall():
            if clave:
                geom = blob_a_geojson_geom(blob)
                if geom:
                    geoms_por_clave[str(clave).strip()] = geom
        conn.close()
        print(f"  ✓ {len(geoms_por_clave)} geometrías rurales encontradas")

    n_urban_prev = len(geoms_por_clave)
    # Catastro Urbano
    if os.path.exists(CATASTRO_URBAN):
        conn = sqlite3.connect(CATASTRO_URBAN)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' LIMIT 1")
        row = cursor.fetchone()
        if row:
            table = row[0]
            cursor.execute(f'PRAGMA table_info("{table}")')
            cols = [c[1] for c in cursor.fetchall()]
            clave_col = next((c for c in cols if 'pre_codigo' in c or 'clave' in c.lower()), None)
            geom_col  = next((c for c in cols if c.lower() in ('geom', 'geometry', 'shape')), None)
            if clave_col and geom_col:
                if claves_fichas:
                    ph = ','.join('?' * len(claves_fichas))
                    cursor.execute(f'SELECT "{clave_col}", "{geom_col}" FROM "{table}" WHERE "{clave_col}" IN ({ph})',
                                   list(claves_fichas))
                else:
                    cursor.execute(f'SELECT "{clave_col}", "{geom_col}" FROM "{table}"')
                for clave, blob in cursor.fetchall():
                    if clave and str(clave).strip() not in geoms_por_clave:
                        geom = blob_a_geojson_geom(blob)
                        if geom:
                            geoms_por_clave[str(clave).strip()] = geom
        conn.close()
        n_urban_found = len(geoms_por_clave) - n_urban_prev
        print(f"  ✓ {n_urban_found} geometrías urbanas adicionales encontradas")

    return geoms_por_clave


# ─── Agrupar fichas por comunidad y sector ────────────────────────────────────

def agrupar_fichas(fichas, ids_excluir):
    """
    Retorna:
        por_comunidad: { comunidad_corr: [fichas_validas, ...] }
        por_sector:    { sector_corr:    [fichas_validas, ...] }
    """
    por_comunidad = defaultdict(list)
    por_sector    = defaultdict(list)
    excluidas = 0

    for f in fichas:
        if f.get('id') in ids_excluir:
            excluidas += 1
            continue
        com = f.get('_com_corr', '')
        sec = f.get('_sec_corr', '')
        if com:
            por_comunidad[com].append(f)
        if sec:
            por_sector[sec].append(f)

    print(f"  ✓ {excluidas} fichas excluidas por discrepancia")
    print(f"  ✓ {len(por_comunidad)} comunidades activas")
    print(f"  ✓ {len(por_sector)} sectores activos")
    return dict(por_comunidad), dict(por_sector)


# ─── Generar GeoJSON de capa ──────────────────────────────────────────────────

def generar_capa(agrupacion, geoms_por_clave, fichas_totales_por_grupo,
                 nombre_campo, nombre_capa, ids_excluir):
    """
    Genera una capa GeoJSON disolviendo los predios catastrales de cada grupo.
    Retorna un dict GeoJSON FeatureCollection en WGS84.
    """
    print(f"\n🔧 Generando capa {nombre_capa}...")

    # Precalcular estadísticas de TODAS las fichas (incluyendo discrepantes) para metadatos
    # Pero la geometría solo usa las NO discrepantes
    stats_totales = defaultdict(lambda: {'fichas': 0, 'fichas_validas': 0, 'fichas_excluidas': 0,
                                          'area_riego_m2': 0.0, 'caudal_ls': 0.0,
                                          'sin_clave': 0, 'con_clave': 0, 'con_geom': 0})

    for grupo, fichas_lista in agrupacion.items():
        s = stats_totales[grupo]
        s['fichas_validas'] = len(fichas_lista)
        for f in fichas_lista:
            s['area_riego_m2'] += f.get('area_riego', 0) or 0
            s['caudal_ls']     += f.get('caudal_valor', 0) or 0
            clave = str(f.get('clave_catastral', '') or '').strip()
            if clave:
                s['con_clave'] += 1
            else:
                s['sin_clave'] += 1

    # Incluir fichas excluidas en el conteo total (para metadatos informativos)
    for grupo, total in fichas_totales_por_grupo.items():
        s = stats_totales[grupo]
        s['fichas'] = total

    features = []
    sin_geom = 0

    for grupo, fichas_lista in sorted(agrupacion.items()):
        # Recopilar geometrías de predios válidos de este grupo
        geoms_utm = []
        for f in fichas_lista:
            clave = str(f.get('clave_catastral', '') or '').strip()
            if clave and clave in geoms_por_clave:
                geoms_utm.append(geoms_por_clave[clave])
                stats_totales[grupo]['con_geom'] += 1

        if not geoms_utm:
            print(f"  ⚠ {grupo}: sin geometrías disponibles ({len(fichas_lista)} fichas, pero ninguna con predio en catastro)")
            sin_geom += 1
            continue

        print(f"  → {grupo}: {len(geoms_utm)} predios para dissolve ({len(fichas_lista)} fichas válidas)...")

        # Dissolve en UTM 17S
        geom_utm  = dissolve_geoms(geoms_utm)
        if not geom_utm:
            sin_geom += 1
            continue

        # Calcular área real en UTM
        area_m2   = calcular_area_utm_m2(geom_utm)
        area_ha   = round(area_m2 / 10000, 4)

        # Convertir a WGS84 para el GeoJSON web
        geom_wgs  = convertir_coords_geom(geom_utm)

        # Metadatos del feature
        s = stats_totales[grupo]
        sector_del_grupo = COM_A_SECTOR.get(normalizar(grupo), grupo)  # Para capa comunidades
        if nombre_campo == 'sector':
            sector_del_grupo = grupo  # Para capa sectores

        props = {
            nombre_campo:        grupo,
            'sector':            COM_A_SECTOR.get(normalizar(grupo), grupo) if nombre_campo == 'comunidad' else grupo,
            'total_fichas':      s['fichas'] if s['fichas'] > 0 else s['fichas_validas'],
            'fichas_validas':    s['fichas_validas'],
            'fichas_excluidas':  s.get('fichas_excluidas', 0),
            'predios_catastro':  s['con_geom'],
            'area_riego_m2':     round(s['area_riego_m2'], 2),
            'area_riego_ha':     round(s['area_riego_m2'] / 10000, 4),
            'caudal_total_ls':   round(s['caudal_ls'], 2),
            'area_dissolve_m2':  round(area_m2, 2),
            'area_dissolve_ha':  area_ha,
        }

        features.append({
            'type':       'Feature',
            'properties': props,
            'geometry':   geom_wgs,
        })

    fc = {'type': 'FeatureCollection', 'features': features}
    print(f"  ✓ {len(features)} polígonos generados ({sin_geom} grupos sin geometría)")
    return fc


# ─── Guardar GeoJSON ──────────────────────────────────────────────────────────

def guardar_geojson(fc, nombre_archivo, descripcion):
    ruta = os.path.join(GEO_DIR, nombre_archivo)
    with open(ruta, 'w', encoding='utf-8') as f:
        json.dump(fc, f, ensure_ascii=False, indent=None, separators=(',', ':'))
    tam = os.path.getsize(ruta)
    print(f"  💾 {descripcion}: {ruta} ({tam / 1024:.1f} KB)")
    return ruta


# ─── Guardar GeoPackage UTM 17S (para QGIS) ───────────────────────────────────

def guardar_gpkg_utm(fc_sectores_wgs, fc_comunidades_wgs):
    """
    Guarda las capas en un GeoPackage con geometrías en UTM 17S (EPSG:32717).
    Requiere pyproj para reconvertir WGS84→UTM.
    Si no hay pyproj, exporta las capas WGS84 en GeoJSON y advierte.
    """
    print(f"\n📦 Guardando GeoPackage QGIS ({OUTPUT_GPKG})...")

    if not HAS_PYPROJ:
        print("  ⚠ pyproj no disponible. El GeoPackage no se puede generar en UTM 17S.")
        print("    Para generarlo, instala pyproj: pip install pyproj")
        return

    try:
        import sqlite3

        # Eliminar archivo anterior si existe
        if os.path.exists(OUTPUT_GPKG):
            os.remove(OUTPUT_GPKG)

        conn = sqlite3.connect(OUTPUT_GPKG)
        cursor = conn.cursor()

        # Crear estructura mínima de GeoPackage
        cursor.executescript("""
            PRAGMA application_id = 1196444487;
            PRAGMA user_version = 10201;

            CREATE TABLE gpkg_spatial_ref_sys (
                srs_name TEXT NOT NULL,
                srs_id INTEGER NOT NULL PRIMARY KEY,
                organization TEXT NOT NULL,
                organization_coordsys_id INTEGER NOT NULL,
                definition TEXT NOT NULL,
                description TEXT
            );

            CREATE TABLE gpkg_contents (
                table_name TEXT NOT NULL PRIMARY KEY,
                data_type TEXT NOT NULL,
                identifier TEXT,
                description TEXT DEFAULT '',
                last_change DATETIME NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
                min_x REAL, min_y REAL, max_x REAL, max_y REAL,
                srs_id INTEGER,
                CONSTRAINT fk_gc_r_srs_id FOREIGN KEY (srs_id) REFERENCES gpkg_spatial_ref_sys(srs_id)
            );

            CREATE TABLE gpkg_geometry_columns (
                table_name TEXT NOT NULL,
                column_name TEXT NOT NULL,
                geometry_type_name TEXT NOT NULL,
                srs_id INTEGER NOT NULL,
                z TINYINT NOT NULL,
                m TINYINT NOT NULL,
                CONSTRAINT pk_geom_cols PRIMARY KEY (table_name, column_name)
            );
        """)

        # Insertar SRS: WGS84 (4326) y UTM 17S (32717)
        cursor.execute("""
            INSERT INTO gpkg_spatial_ref_sys VALUES
            ('WGS 84', 4326, 'EPSG', 4326,
             'GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563]],PRIMEM["Greenwich",0],UNIT["degree",0.0174532925199433,AUTHORITY["EPSG","9122"]],AUTHORITY["EPSG","4326"]]',
             'World Geodetic System 1984')
        """)
        cursor.execute("""
            INSERT INTO gpkg_spatial_ref_sys VALUES
            ('WGS 84 / UTM zone 17S', 32717, 'EPSG', 32717,
             'PROJCS["WGS 84 / UTM zone 17S",GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563]],PRIMEM["Greenwich",0],UNIT["degree",0.0174532925199433]],PROJECTION["Transverse_Mercator"],PARAMETER["latitude_of_origin",0],PARAMETER["central_meridian",-81],PARAMETER["scale_factor",0.9996],PARAMETER["false_easting",500000],PARAMETER["false_northing",10000000],UNIT["metre",1],AUTHORITY["EPSG","32717"]]',
             'UTM Zone 17S')
        """)

        # ── Función para crear una capa en el GeoPackage ────────────────────
        def crear_tabla_capa(nombre_tabla, fc_wgs, campos_extra, descripcion):
            from pyproj import Transformer
            t_wgs_utm = Transformer.from_crs("EPSG:4326", "EPSG:32717", always_xy=True)

            cursor.execute(f"""
                CREATE TABLE "{nombre_tabla}" (
                    fid INTEGER PRIMARY KEY AUTOINCREMENT,
                    geom MULTIPOLYGON,
                    {', '.join(f'"{k}" TEXT' for k in campos_extra)}
                )
            """)

            # Insertar en gpkg_geometry_columns
            cursor.execute("""
                INSERT INTO gpkg_geometry_columns VALUES (?, 'geom', 'MULTIPOLYGON', 32717, 0, 0)
            """, (nombre_tabla,))

            # Función para reconvertir coordenadas WGS84→UTM y empaquetar en WKB
            def coord_a_utm(lon, lat):
                return t_wgs_utm.transform(lon, lat)

            def ring_wgs_a_utm(ring):
                return [list(coord_a_utm(c[0], c[1])) for c in ring]

            def geom_wgs_a_wkb_utm(geom_wgs):
                """Convierte geometría GeoJSON WGS84 → WKB UTM 17S."""
                if geom_wgs is None:
                    return None

                polys = []
                if geom_wgs['type'] == 'Polygon':
                    polys = [geom_wgs['coordinates']]
                elif geom_wgs['type'] == 'MultiPolygon':
                    polys = geom_wgs['coordinates']
                else:
                    return None

                # Construir WKB MultiPolygon en little-endian
                import struct as st

                def encode_ring(ring_utm):
                    n = len(ring_utm)
                    data = st.pack('<I', n)
                    for pt in ring_utm:
                        data += st.pack('<dd', pt[0], pt[1])
                    return data

                def encode_polygon(poly_coords):
                    rings_utm = [ring_wgs_a_utm(r) for r in poly_coords]
                    data = st.pack('<bII', 1, 3, len(rings_utm))  # bo=1 (LE), type=3 (Polygon)
                    for r in rings_utm:
                        data += encode_ring(r)
                    return data

                # WKB MultiPolygon
                n_polys = len(polys)
                wkb = st.pack('<bII', 1, 6, n_polys)  # bo=1 (LE), type=6 (MultiPolygon)
                for poly in polys:
                    wkb += encode_polygon(poly)

                # GeoPackage header (GP + version + flags + srid)
                flags = 0x01  # little-endian, sin envelope
                header = b'GP' + st.pack('<B', 0) + st.pack('<B', flags) + st.pack('<i', 32717)
                return header + wkb

            min_x, min_y, max_x, max_y = float('inf'), float('inf'), float('-inf'), float('-inf')

            for feature in fc_wgs['features']:
                geom_wgs = feature.get('geometry')
                props    = feature.get('properties', {})

                blob = geom_wgs_a_wkb_utm(geom_wgs) if geom_wgs else None

                vals_extra = [str(props.get(k, '')) for k in campos_extra]
                placeholders = ', '.join(['?'] * (len(campos_extra) + 1))
                cursor.execute(
                    f'INSERT INTO "{nombre_tabla}" (geom, {", ".join(f"{chr(34)}{k}{chr(34)}" for k in campos_extra)}) VALUES ({placeholders})',
                    [blob] + vals_extra
                )

            cursor.execute(f"""
                INSERT INTO gpkg_contents (table_name, data_type, identifier, description, srs_id)
                VALUES (?, 'features', ?, ?, 32717)
            """, (nombre_tabla, nombre_tabla, descripcion))

        # ── Capa Sectores ─────────────────────────────────────────────────────
        campos_sec = ['sector', 'total_fichas', 'fichas_validas', 'fichas_excluidas',
                      'predios_catastro', 'area_riego_m2', 'area_riego_ha',
                      'caudal_total_ls', 'area_dissolve_m2', 'area_dissolve_ha']
        crear_tabla_capa('Sectores_Investigacion', fc_sectores_wgs, campos_sec,
                         'Sectores de investigación del Sistema de Riego Guanguilqui-Porotog')

        # ── Capa Comunidades ──────────────────────────────────────────────────
        campos_com = ['comunidad', 'sector', 'total_fichas', 'fichas_validas', 'fichas_excluidas',
                      'predios_catastro', 'area_riego_m2', 'area_riego_ha',
                      'caudal_total_ls', 'area_dissolve_m2', 'area_dissolve_ha']
        crear_tabla_capa('Comunidades', fc_comunidades_wgs, campos_com,
                         'Comunidades del Sistema de Riego Guanguilqui-Porotog')

        conn.commit()
        conn.close()

        tam = os.path.getsize(OUTPUT_GPKG)
        print(f"  ✓ GeoPackage guardado: {OUTPUT_GPKG} ({tam / 1024 / 1024:.2f} MB)")
        print(f"    SRC: EPSG:32717 (WGS 84 / UTM zone 17S)")
        print(f"    Capas: Sectores_Investigacion | Comunidades")

    except Exception as e:
        print(f"  ❌ Error generando GeoPackage: {e}")
        import traceback
        traceback.print_exc()


# ─── Main ──────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    print("=" * 60)
    print("  GENERADOR CAPAS GIS -- Sectores y Comunidades")
    print("  Catastro Riego Cayambe")
    print("=" * 60)
    print()


    # 1. Cargar datos
    fichas = leer_fichas()
    ids_excluir = leer_ids_discrepantes()

    # 2. Agrupar fichas válidas
    print("\n📊 Agrupando fichas por comunidad y sector...")
    por_com, por_sec = agrupar_fichas(fichas, ids_excluir)

    # Calcular totales por grupo (incluyendo discrepantes para metadatos)
    totales_com = defaultdict(int)
    totales_sec = defaultdict(int)
    for f in fichas:
        com = f.get('_com_corr', '')
        sec = f.get('_sec_corr', '')
        if com: totales_com[com] += 1
        if sec: totales_sec[sec] += 1

    # 3. Obtener geometrías catastrales para fichas válidas
    fichas_validas = [f for f in fichas if f.get('id') not in ids_excluir]
    geoms_por_clave = leer_catastro_para_fichas(fichas_validas)

    # 4. Generar capas
    fc_comunidades = generar_capa(por_com, geoms_por_clave, dict(totales_com),
                                   'comunidad', 'Comunidades', ids_excluir)
    fc_sectores    = generar_capa(por_sec, geoms_por_clave, dict(totales_sec),
                                   'sector', 'Sectores', ids_excluir)

    # 5. Guardar GeoJSON para la web (WGS84)
    print("\n💾 Guardando archivos GeoJSON...")
    guardar_geojson(fc_comunidades, 'comunidades.geojson', 'Capa Comunidades (WGS84)')
    guardar_geojson(fc_sectores,    'sectores.geojson',    'Capa Sectores (WGS84)')

    # 6. Guardar GeoPackage para QGIS (UTM 17S)
    guardar_gpkg_utm(fc_sectores, fc_comunidades)

    # 7. Resumen
    print("\n" + "="*60)
    print("✅ ¡PROCESO COMPLETADO!")
    print(f"   → {len(fc_comunidades['features'])} polígonos de Comunidades")
    print(f"   → {len(fc_sectores['features'])} polígonos de Sectores")
    print(f"   → GeoJSON: public/geo/comunidades.geojson")
    print(f"   → GeoJSON: public/geo/sectores.geojson")
    print(f"   → GeoPackage QGIS: {OUTPUT_GPKG}")
    print("="*60)
