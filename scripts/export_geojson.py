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
import re

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

# ─── Variables y Funciones para Unificación en Caliente ───
FICHA_REDIRECT_MAP = {}
VIRTUAL_PREDIOS_ADICIONALES = []

def normalizar_texto(texto):
    if not texto:
        return ""
    texto = texto.upper().strip()
    replacements = (
        ("Á", "A"), ("É", "E"), ("Í", "I"), ("Ó", "O"), ("Ú", "U"),
        ("Ñ", "N"), ("Ü", "U")
    )
    for a, b in replacements:
        texto = texto.replace(a, b)
    texto = re.sub(r'\s+', ' ', texto)
    return texto

def preparar_unificacion():
    global FICHA_REDIRECT_MAP, VIRTUAL_PREDIOS_ADICIONALES
    FICHA_REDIRECT_MAP = {}
    VIRTUAL_PREDIOS_ADICIONALES = []

    print("\n🔍 Analizando duplicados para unificación virtual en la exportación...")
    conn = sqlite3.connect(DATA_GPKG)
    cursor = conn.cursor()
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    all_tables = [t[0] for t in cursor.fetchall()]
    fichas_table = next((t for t in all_tables if 'Fichas_Predios' in t and not any(x in t for x in ('rtree_','log_','gpkg_'))), None)
    
    if not fichas_table:
        print("  ❌ No se encontró la tabla de Fichas_Predios")
        conn.close()
        return

    cursor.execute(f'''
        SELECT id, cedula, apellidos, nombres, area_total, area_riego, area_sin_riego, creado_por, fecha_creacion, clave_catastral, observaciones
        FROM "{fichas_table}"
    ''')
    fichas_raw = cursor.fetchall()
    conn.close()

    fichas = []
    for f in fichas_raw:
        fid, ced, ape, nom, area, ar, asr, creador, fecha, clave, obs = f
        ced_norm = (ced or "").strip()
        es_ced_valida = len(ced_norm) == 10 and ced_norm.isdigit()
        
        ape_norm = normalizar_texto(ape)
        nom_norm = normalizar_texto(nom)
        nombre_completo = f"{ape_norm} {nom_norm}".strip()
        
        fichas.append({
            'id': fid,
            'cedula': ced_norm,
            'es_ced_valida': es_ced_valida,
            'apellidos': (ape or "").strip(),
            'nombres': (nom or "").strip(),
            'nombre_completo_normalizado': nombre_completo,
            'area_total': area or 0.0,
            'area_riego': ar or 0.0,
            'area_sin_riego': asr or 0.0,
            'creado_por': (creador or "").strip(),
            'fecha_creacion': fecha,
            'clave_catastral': clave,
            'observaciones': obs or ""
        })

    regantes_por_cedula = {}
    fichas_sin_cedula_valida = []

    for f in fichas:
        if f['es_ced_valida']:
            ced = f['cedula']
            if ced not in regantes_por_cedula:
                regantes_por_cedula[ced] = []
            regantes_por_cedula[ced].append(f)
        else:
            fichas_sin_cedula_valida.append(f)

    regantes_por_nombre = {}
    for f in fichas_sin_cedula_valida:
        name = f['nombre_completo_normalizado']
        if not name:
            name = "SIN_NOMBRE_REGISTRADO"
        if name not in regantes_por_nombre:
            regantes_por_nombre[name] = []
        regantes_por_nombre[name].append(f)

    duplicados_cedula = {ced: lista for ced, lista in regantes_por_cedula.items() if len(lista) > 1}
    duplicados_nombre = {name: lista for name, lista in regantes_por_nombre.items() if len(lista) > 1 and name != "SIN_NOMBRE_REGISTRADO"}

    for ced, lista in duplicados_cedula.items():
        lista_ordenada = sorted(lista, key=lambda x: x['area_total'], reverse=True)
        ficha_madre = lista_ordenada[0]
        fichas_secundarias = lista_ordenada[1:]
        
        for fs in fichas_secundarias:
            FICHA_REDIRECT_MAP[fs['id']] = ficha_madre['id']
            tecnico_nombre = MAPEO_TECNICOS.get(fs['creado_por'], fs['creado_por'])
            obs_unificacion = f"Unificación automática. Ficha original: {fs['id']}. Técnico: {tecnico_nombre} en {fs['fecha_creacion']}."
            if fs['observaciones']:
                obs_unificacion += f" Obs. Orig: {fs['observaciones']}"
                
            VIRTUAL_PREDIOS_ADICIONALES.append({
                'id_adicional': fs['id'],
                'ficha_id': ficha_madre['id'],
                'clave_catastral_otro': fs['clave_catastral'],
                'area_total_otro': fs['area_total'],
                'area_riego_otro': fs['area_riego'],
                'area_sin_riego_otro': fs['area_sin_riego'],
                'area_lote_asignado_otro': fs['area_total'],
                'tiene_observaciones': 1,
                'observaciones_otro': obs_unificacion
            })

    for name, lista in duplicados_nombre.items():
        lista_ordenada = sorted(lista, key=lambda x: x['area_total'], reverse=True)
        ficha_madre = lista_ordenada[0]
        fichas_secundarias = lista_ordenada[1:]
        
        for fs in fichas_secundarias:
            FICHA_REDIRECT_MAP[fs['id']] = ficha_madre['id']
            tecnico_nombre = MAPEO_TECNICOS.get(fs['creado_por'], fs['creado_por'])
            obs_unificacion = f"Unificación automática (coincidencia de Nombre). Ficha original: {fs['id']}. Técnico: {tecnico_nombre} en {fs['fecha_creacion']}."
            if fs['observaciones']:
                obs_unificacion += f" Obs. Orig: {fs['observaciones']}"
                
            VIRTUAL_PREDIOS_ADICIONALES.append({
                'id_adicional': fs['id'],
                'ficha_id': ficha_madre['id'],
                'clave_catastral_otro': fs['clave_catastral'],
                'area_total_otro': fs['area_total'],
                'area_riego_otro': fs['area_riego'],
                'area_sin_riego_otro': fs['area_sin_riego'],
                'area_lote_asignado_otro': fs['area_total'],
                'tiene_observaciones': 1,
                'observaciones_otro': obs_unificacion
            })

    print(f"  ✓ {len(FICHA_REDIRECT_MAP)} fichas duplicadas secundarias redirigidas a sus fichas madre.")
    print(f"  ✓ {len(VIRTUAL_PREDIOS_ADICIONALES)} predios adicionales virtuales creados.")

# ══════════════════════════════════════════════════════════════
# Parseo de geometría GeoPackage (WKB + GPKG header)
# ══════════════════════════════════════════════════════════════

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

    # Mapeo automático: derivar 'comunidad' del 'sector_comunidad' para fichas antiguas
    # Diccionario de variantes ortográficas → comunidad oficial
    # Ordenado de más específico a más general para evitar falsos positivos
    VARIANTES_COMUNIDAD = [
        # LARCACOCHA (escrito como Larcachaca, Larcacocha, La Arcacha, etc.)
        ("LARCACHACA", "LARCACOCHA"),
        ("LARCACACHA", "LARCACOCHA"),
        ("LARCACOCHA", "LARCACOCHA"),
        ("LARCACHA", "LARCACOCHA"),
        ("LA ARCACHA", "LARCACOCHA"),
        ("ALCACHACA", "LARCACOCHA"),
        ("HUASIPUNGO", "LARCACOCHA"),
        ("GUASIPUNGO", "LARCACOCHA"),
        ("GUALIMBURO", "LARCACOCHA"),
        ("PARCELA", "LARCACOCHA"),
        ("MORAS", "LARCACOCHA"),
        ("PÁRAMO", "LARCACOCHA"),
        # LA LIBERTAD
        ("LIBERAD", "LA LIBERTAD"),
        ("LIBERTAD", "LA LIBERTAD"),
        ("CENTRAL LIBERTAD", "LA LIBERTAD"),
        # SAN ANTONIO
        ("SAN ANTONIO", "SAN ANTONIO"),
        ("SAM ANTONIO", "SAN ANTONIO"),
        ("PAILLACO", "SAN ANTONIO"),
        ("PAYLLACHO", "SAN ANTONIO"),
        ("PAILLACHO", "SAN ANTONIO"),
        # SAN JOSÉ (variantes con sectores internos)
        ("SAN JOSÉ", "SAN JOSÉ"),
        ("SAN JOSE", "SAN JOSÉ"),
        ("SAN  PEDRO", "SAN JOSÉ"),
        ("SAN PEDRO", "SAN JOSÉ"),
        ("YACUTIGRANA", "SAN JOSÉ"),
        ("PORTADAS", "SAN JOSÉ"),
        ("NINARUMI", "SAN JOSÉ"),
        ("NINA RUMI", "SAN JOSÉ"),
        ("INARUMI", "SAN JOSÉ"),
        ("ÑAVIPOGYO", "SAN JOSÉ"),
        ("ÑAVIPUYO", "SAN JOSÉ"),
        ("ÑAWIPUKYU", "SAN JOSÉ"),
        ("GUALIMPURO", "SAN JOSÉ"),
        ("LOS ANDES", "SAN JOSÉ"),
        # MILAGRO
        ("MILAGRO", "MILAGRO"),
        # ASOCIACIÓN 17 DE JUNIO
        ("ASOSIACION 17", "ASOCIACIÓN 17 DE JUNIO"),
        ("ASOCIACIÓN 17", "ASOCIACIÓN 17 DE JUNIO"),
        ("ASOCIACION 17", "ASOCIACIÓN 17 DE JUNIO"),
        ("17 DE JUNIO", "ASOCIACIÓN 17 DE JUNIO"),
        ("17 DE JULIO", "ASOCIACIÓN 17 DE JUNIO"),
        # AVELLANEDA
        ("AVELLANEDA", "AVELLANEDA"),
        # CHAMBITOLA
        ("CHAMBITOLA", "CHAMBITOLA"),
        ("CHAMITOLA", "CHAMBITOLA"),
        ("CAMBITOLA", "CHAMBITOLA"),
        ("CHIMBATOLA", "CHAMBITOLA"),
        # LA CANDELARIA
        ("CANDELARIA", "LA CANDELARIA"),
        # CARRERA
        ("CARRERA", "CARRERA"),
        ("CARERRA", "CARRERA"),
        ("ACERO LOMA", "CARRERA"),
        # MATÍAS IMBAGO
        ("MATÍAS IMBAGO", "MATÍAS IMBAGO"),
        ("MATIAS IMBAGO", "MATÍAS IMBAGO"),
        # COCHAPAMBA
        ("COCHAPAMBA", "COCHAPAMBA"),
        # JESÚS GRAN PODER
        ("GRAN PODER", "JESÚS GRAN PODER"),
        # SANTA BÁRBARA
        ("SANTA BÁRBARA", "SANTA BÁRBARA"),
        ("SANTA BARBARA", "SANTA BÁRBARA"),
        # ASOCIACIÓN POROTOG
        ("ASOCIACIÓN POROTOG", "ASOCIACIÓN POROTOG"),
        ("ASOCIACION POROTOG", "ASOCIACIÓN POROTOG"),
        # COMUNA POROTOG
        ("COMUNA POROTOG", "COMUNA POROTOG"),
        # CORDILLERAS DE LOS ANDES
        ("CORDILLERAS", "CORDILLERAS DE LOS ANDES"),
        # COMUNA INSACATA
        ("COMUNA INSACATA", "COMUNA INSACATA"),
        ("IZACATA", "COMUNA INSACATA"),
        ("INSACATA", "COMUNA INSACATA"),
        # INSACATA GRANDE
        ("INSACATA GRANDE", "INSACATA GRANDE"),
        # LOS ANDES INSACATA
        ("LOS ANDES INSACATA", "LOS ANDES INSACATA"),
        # LOMA GORDA
        ("LOMA GORDA", "LOMA GORDA"),
        # SAN JACINTO
        ("SAN JACINTO", "SAN JACINTO"),
        # Otros sectores genéricos → intentar mapear
        ("CRUZ LOMA", "SAN JOSÉ"),
        ("CRUZLOMA", "SAN JOSÉ"),
        ("TOTORA", "SAN JOSÉ"),
        ("TOTORAS", "SAN JOSÉ"),
        ("MULAPOTERO", "SAN JOSÉ"),
        ("MULA POTRERO", "SAN JOSÉ"),
        ("BANDURRIA", "SAN JOSÉ"),
        ("BANDURIA", "SAN JOSÉ"),
        ("BARROLOMA", "SAN JOSÉ"),
        ("PLAYA", "SAN JOSÉ"),
        ("CALDERA", "SAN JOSÉ"),
        ("POCARALOMA", "SAN JOSÉ"),
        ("CENTRAL", "SAN JOSÉ"),
        ("CÓNDOR LOMA", "SAN JOSÉ"),
        ("PUKARA", "SAN JOSÉ"),
        ("SOPALO LOMA", "LA CANDELARIA"),
        ("GUANGUILQUI", "LARCACOCHA"),
        ("CANGAHUA", "LARCACOCHA"),
    ]
    # Ordenar variantes de mayor a menor longitud para priorizar las más específicas
    VARIANTES_COMUNIDAD.sort(key=lambda x: len(x[0]), reverse=True)

    def derivar_comunidad(sector_comunidad_valor):
        sc = (sector_comunidad_valor or '').upper().strip()
        if not sc:
            return None
        for variante, comunidad_oficial in VARIANTES_COMUNIDAD:
            if variante in sc:
                return comunidad_oficial
        return None

    features = []
    for row in rows:
        props, geom_blob = {}, None
        for i, col in enumerate(columns):
            if col == 'geom': geom_blob = row[i]
            elif col == 'fid_1': continue
            elif row[i] is not None: props[col] = row[i]

        # Filtro de unificación virtual: omitir fichas secundarias duplicadas
        if props.get('id') in FICHA_REDIRECT_MAP:
            continue

        # Si 'comunidad' no existe o está vacío, derivar del 'sector_comunidad'
        if not props.get('comunidad'):
            com_derivada = derivar_comunidad(props.get('sector_comunidad'))
            if com_derivada:
                props['comunidad'] = com_derivada

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
    print("\n📋 Exportando tablas hijas con unificación virtual...")
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
            if item:
                # Unificación virtual: reasociar ficha_id a la Ficha Madre
                f_id = item.get('ficha_id')
                if f_id in FICHA_REDIRECT_MAP:
                    item['ficha_id'] = FICHA_REDIRECT_MAP[f_id]
                data.append(item)
        
        # Si estamos exportando predios adicionales, inyectar los predios unificados virtuales
        if output_name == 'predios_adicionales':
            data.extend(VIRTUAL_PREDIOS_ADICIONALES)
            
        path = os.path.join(OUTPUT_DIR, f'{output_name}.json')
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"  ✓ {len(data)} {output_name} (incluyendo unificados virtuales: {output_name == 'predios_adicionales'})")
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


MAPEO_TECNICOS = {
    'u0_a314': 'Melany Jara',
    'u0_a319': 'Melany Jara',
    'jvk-editor': 'Melany Jara',
    'u0_a504': 'Adriana Cuascota',
    'jvk-editor6': 'Adriana Cuascota',
    'u0_a279': 'Huguito Ipial',
    'jvk-editor2': 'Huguito Ipial',
    'u0_a70': 'Pablo Barrionuevo',
    'jvk-editor5': 'Pablo Barrionuevo',
    'u0_a330': 'Mayra Benavides',
    'mayralisseth201': 'Mayra Benavides',
    'u0_a362': 'Martha Simbaña',
    'u0_a335': 'Martha Simbaña',
    'jvk-editor4': 'Martha Simbaña',
    'u0_a2': 'JVK-DIGITALIZACION',
    'jvk-digitalizacion': 'JVK-DIGITALIZACION',
    'u0_a302': 'Dylan Chavez',
    'jvk-editor3': 'Dylan Chavez',
    'u0_a200': 'Melanie2',
}

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
            nombre_tec = MAPEO_TECNICOS.get(t.strip(), t.strip())
            tecnicos.add(nombre_tec)
            
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

    preparar_unificacion()
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
