# -*- coding: utf-8 -*-
"""
AUDITORIA ESPACIAL DE FICHAS -- Catastro de Riego Cayambe
Detecta discrepancias entre los atributos de comunidad/sector
y la ubicacion GPS real del punto levantado en QField.

Salida:
  - informe_discrepancias_espaciales.md
  - fichas_discrepantes.json

Uso:
  python padron-app/scripts/auditar_discrepancias_espaciales.py
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
PARROQUIAS_GPKG= os.path.join(QFIELD_DIR, 'PARROQUIAS.gpkg')

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(SCRIPT_DIR, '..', '..', '')  # Raíz del proyecto
OUTPUT_MD  = os.path.abspath(os.path.join(SCRIPT_DIR, '..', '..', 'informe_discrepancias_espaciales.md'))

# ─── Umbral de discrepancia ────────────────────────────────────────────────────
UMBRAL_KM = 1.5

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

# Mapeo inverso: comunidad normalizada → sector oficial
COM_A_SECTOR = {}
for sec, coms in COMUNIDADES_POR_SECTOR.items():
    for c in coms:
        COM_A_SECTOR[c] = sec

# Correcciones de nombres (mismas que en App.tsx y export_geojson.py)
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
    """Normaliza texto: mayúsculas, sin acentos, sin espacios extras."""
    if not texto:
        return ""
    texto = texto.upper().strip()
    texto = unicodedata.normalize('NFD', texto)
    texto = ''.join(c for c in texto if unicodedata.category(c) != 'Mn')
    import re
    texto = re.sub(r'\s+', ' ', texto)
    return texto


def aplicar_correcciones(com):
    """Aplica correcciones de nombre de comunidad (igual que App.tsx)."""
    com_norm = normalizar(com)
    for original, correcto in CORRECCIONES_COM.items():
        if normalizar(original) in com_norm:
            return correcto
    return com_norm


def parse_gpkg_header(blob):
    """Extrae (srid, offset_wkb) del header de un blob GeoPackage."""
    if not blob or blob[:2] != b'GP':
        return 0, 0
    flags = blob[3]
    envelope_type = (flags >> 1) & 0x07
    is_le = (flags & 0x01) == 1
    srid = struct.unpack('<i' if is_le else '>i', blob[4:8])[0]
    envelope_sizes = {0: 0, 1: 32, 2: 48, 3: 48, 4: 64}
    offset = 8 + envelope_sizes.get(envelope_type, 0)
    return srid, offset


def extraer_punto(blob):
    """Extrae coordenadas (x, y) de un blob GeoPackage Point. Retorna None si falla."""
    if not blob:
        return None
    try:
        srid, off = parse_gpkg_header(blob)
        wkb = blob[off:]
        bo = wkb[0]
        fmt = '<' if bo == 1 else '>'
        gtype = struct.unpack(f'{fmt}I', wkb[1:5])[0] & 0xFFFF
        if gtype != 1:  # Solo Point
            return None
        x, y = struct.unpack(f'{fmt}dd', wkb[5:21])
        if abs(x) < 0.001 and abs(y) < 0.001:
            return None  # Punto en el origen = sin GPS
        return (x, y)
    except Exception:
        return None


def extraer_multipolygon_centroid(blob):
    """Extrae el centroide aproximado de un blob GeoPackage Polygon/MultiPolygon."""
    if not blob:
        return None
    try:
        srid, off = parse_gpkg_header(blob)
        # Usar la envolvente (bounding box) para calcular centroide aproximado
        flags = blob[3]
        envelope_type = (flags >> 1) & 0x07
        is_le = (flags & 0x01) == 1
        if envelope_type >= 1:
            # La envolvente está en bytes 8..8+N: min_x, max_x, min_y, max_y
            fmt = '<' if is_le else '>'
            min_x, max_x, min_y, max_y = struct.unpack(f'{fmt}dddd', blob[8:40])
            cx = (min_x + max_x) / 2
            cy = (min_y + max_y) / 2
            return (cx, cy)
    except Exception:
        pass
    return None


def distancia_grados_km(lon1, lat1, lon2, lat2):
    """Calcula la distancia en km entre dos puntos en grados decimales (WGS84)."""
    R = 6371.0
    lat1_r = math.radians(lat1)
    lat2_r = math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1_r) * math.cos(lat2_r) * math.sin(dlon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def distancia_utm_km(x1, y1, x2, y2):
    """Calcula la distancia en km entre dos puntos en coordenadas UTM (metros)."""
    return math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2) / 1000.0


def mediana(valores):
    """Calcula la mediana de una lista de valores."""
    s = sorted(valores)
    n = len(s)
    if n == 0:
        return None
    mid = n // 2
    return s[mid] if n % 2 else (s[mid - 1] + s[mid]) / 2


# ─── Paso 1: Leer las fichas de data.gpkg ─────────────────────────────────────

def leer_fichas():
    """Lee todas las fichas de data.gpkg y retorna una lista de dicts."""
    print("📂 Leyendo fichas desde data.gpkg...")
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
    sin_gps = 0
    for fila in filas:
        d = dict(zip(columnas, fila))
        blob = d.get('geom')
        punto = extraer_punto(blob)
        d['_punto'] = punto  # (x, y) en WGS84 (lon, lat)
        if punto is None:
            sin_gps += 1
        # Aplicar correcciones de comunidad
        d['_com_corr'] = aplicar_correcciones(d.get('comunidad', '') or '')
        fichas.append(d)

    print(f"  ✓ {len(fichas)} fichas leídas ({sin_gps} sin GPS)")
    return fichas


# ─── Paso 2: Leer polígonos del catastro rural y urbano ───────────────────────

def leer_catastro():
    """Lee clave catastral, geometría (centroide bounding box) del catastro."""
    print("🗺  Leyendo polígonos catastrales...")
    catastro = {}  # clave_cata → (cx, cy) en UTM 17S

    if os.path.exists(CATASTRO_GPKG):
        conn = sqlite3.connect(CATASTRO_GPKG)
        cursor = conn.cursor()
        table = 'CATASTROACTUALIZADORURALCATASTRORURALACTUALIZADO'
        cursor.execute(f'SELECT clave_cata, geom FROM "{table}"')
        for clave, blob in cursor.fetchall():
            if clave and blob:
                centroide = extraer_multipolygon_centroid(blob)
                if centroide:
                    catastro[str(clave).strip()] = centroide
        conn.close()
        print(f"  ✓ {len(catastro)} predios rurales indexados")

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
                cursor.execute(f'SELECT "{clave_col}", "{geom_col}" FROM "{table}"')
                n = 0
                for clave, blob in cursor.fetchall():
                    if clave and blob:
                        centroide = extraer_multipolygon_centroid(blob)
                        if centroide:
                            catastro[str(clave).strip()] = centroide
                            n += 1
                print(f"  ✓ {n} predios urbanos indexados")
        conn.close()

    return catastro


# ─── Paso 3: Leer polígonos de parroquias ─────────────────────────────────────

def leer_parroquias():
    """Lee los polígonos de parroquias. Retorna lista de (nombre, centroide_utm)."""
    print("🏘  Leyendo parroquias...")
    parroquias = []

    if not os.path.exists(PARROQUIAS_GPKG):
        print("  ⚠ PARROQUIAS.gpkg no encontrado")
        return parroquias

    conn = sqlite3.connect(PARROQUIAS_GPKG)
    cursor = conn.cursor()
    cursor.execute('SELECT nombre, geom FROM "PARROQUIAS"')
    for nombre, blob in cursor.fetchall():
        if blob:
            c = extraer_multipolygon_centroid(blob)
            if c:
                parroquias.append({'nombre': normalizar(nombre or ''), 'centroide': c})
    conn.close()
    print(f"  ✓ {len(parroquias)} parroquias leídas")
    return parroquias


# ─── Paso 4: Construir centroides por comunidad (mediana de puntos GPS) ────────

def construir_centroides_comunidades(fichas):
    """Calcula el centroide (mediana X, mediana Y) por comunidad usando los puntos GPS."""
    por_comunidad = defaultdict(list)
    for f in fichas:
        p = f.get('_punto')
        com = f.get('_com_corr', '')
        if p and com:
            por_comunidad[com].append(p)

    centroides = {}
    for com, puntos in por_comunidad.items():
        xs = [p[0] for p in puntos]
        ys = [p[1] for p in puntos]
        cx = mediana(xs)
        cy = mediana(ys)
        if cx is not None and cy is not None:
            centroides[com] = (cx, cy, len(puntos))

    print(f"  ✓ {len(centroides)} comunidades con GPS ({sum(v[2] for v in centroides.values())} fichas con GPS)")
    return centroides


# ─── Paso 5: Detectar discrepancias ───────────────────────────────────────────

def detectar_discrepancias(fichas, centroides_com, catastro):
    """
    Para cada ficha analiza:
    1. Si el GPS cae lejos del centroide de su comunidad (> UMBRAL_KM).
    2. Si la clave catastral asigna un predio lejos del GPS (> UMBRAL_KM).
    3. Si el sector derivado de la comunidad no coincide con el sector registrado.
    Retorna lista de dicts con las discrepancias encontradas.
    """
    print(f"🔍 Detectando discrepancias (umbral: {UMBRAL_KM} km)...")
    discrepancias = []

    for f in fichas:
        punto = f.get('_punto')
        com = f.get('_com_corr', '')
        sec_registrado = normalizar(f.get('sector_investigacion', '') or '')
        clave = str(f.get('clave_catastral', '') or '').strip()
        parroquia_reg = normalizar(f.get('parroquia', '') or '')

        errores = []
        sugerencias = []

        # ── Error 1: GPS vs centroide de comunidad ─────────────────────────────
        if punto and com and com in centroides_com:
            cx, cy, _ = centroides_com[com]
            dist_km = distancia_grados_km(punto[0], punto[1], cx, cy)
            if dist_km > UMBRAL_KM:
                errores.append(
                    f"GPS alejado {dist_km:.2f} km del centroide de la comunidad **{com}** "
                    f"(centroide: {cx:.5f},{cy:.5f} | GPS: {punto[0]:.5f},{punto[1]:.5f})"
                )
                # Buscar comunidad más cercana al punto GPS para sugerir corrección
                mejor_com = None
                mejor_dist = float('inf')
                for otra_com, (ocx, ocy, _) in centroides_com.items():
                    if otra_com == com:
                        continue
                    d = distancia_grados_km(punto[0], punto[1], ocx, ocy)
                    if d < mejor_dist:
                        mejor_dist = d
                        mejor_com = otra_com

                if mejor_com and mejor_dist < UMBRAL_KM:
                    sector_sug = COM_A_SECTOR.get(normalizar(mejor_com), 'Desconocido')
                    sugerencias.append(
                        f"Posible comunidad correcta: **{mejor_com}** "
                        f"({mejor_dist:.2f} km) → Sector sugerido: **{sector_sug}**"
                    )
                elif mejor_com:
                    sugerencias.append(
                        f"Comunidad más cercana: **{mejor_com}** ({mejor_dist:.2f} km) — "
                        f"Verificar manualmente en QField"
                    )

        elif punto and not com:
            errores.append("Ficha con GPS pero **sin comunidad registrada**")
            # Sugerir la comunidad más cercana
            mejor_com = None
            mejor_dist = float('inf')
            for otra_com, (ocx, ocy, _) in centroides_com.items():
                d = distancia_grados_km(punto[0], punto[1], ocx, ocy)
                if d < mejor_dist:
                    mejor_dist = d
                    mejor_com = otra_com
            if mejor_com:
                sector_sug = COM_A_SECTOR.get(normalizar(mejor_com), 'Desconocido')
                sugerencias.append(
                    f"Comunidad más cercana geográficamente: **{mejor_com}** "
                    f"({mejor_dist:.2f} km) → Sector sugerido: **{sector_sug}**"
                )

        # ── Error 2: Clave catastral vs GPS ────────────────────────────────────
        if punto and clave and clave in catastro:
            cx_cat, cy_cat = catastro[clave]
            # El centroide del catastro está en UTM 17S, el GPS está en WGS84
            # Necesitamos convertir el GPS a UTM 17S para compararlos
            try:
                from pyproj import Transformer
                t = Transformer.from_crs("EPSG:4326", "EPSG:32717", always_xy=True)
                px_utm, py_utm = t.transform(punto[0], punto[1])
                dist_cat_km = distancia_utm_km(px_utm, py_utm, cx_cat, cy_cat)
                if dist_cat_km > UMBRAL_KM:
                    errores.append(
                        f"Clave catastral **{clave}** tiene su predio a {dist_cat_km:.2f} km del GPS del técnico "
                        f"(posible error de digitación de la clave)"
                    )
                    sugerencias.append(
                        f"Verificar la clave catastral en QField. El predio con clave {clave} "
                        f"está a {dist_cat_km:.2f} km del punto GPS levantado"
                    )
            except ImportError:
                pass  # pyproj no disponible, omitir este check

        # ── Error 3: Sector derivado vs sector registrado ──────────────────────
        if com:
            com_norm = normalizar(com)
            sector_derivado = COM_A_SECTOR.get(com_norm)
            if sector_derivado and sec_registrado and sec_registrado != normalizar(sector_derivado):
                errores.append(
                    f"Sector registrado en QField: **{sec_registrado or 'vacío'}** "
                    f"pero la comunidad **{com}** pertenece a **{sector_derivado}**"
                )
                sugerencias.append(
                    f"Corregir sector en QField de `{sec_registrado}` → `{sector_derivado}`"
                )

        if errores:
            discrepancias.append({
                'id': f.get('id', ''),
                'propietario': f"{f.get('apellidos', '')} {f.get('nombres', '')}".strip(),
                'cedula': f.get('cedula', ''),
                'clave_catastral': clave,
                'comunidad_bd': f.get('comunidad', ''),
                'comunidad_corr': com,
                'sector_bd': f.get('sector_investigacion', ''),
                'parroquia_bd': f.get('parroquia', ''),
                'gps': punto,
                'creado_por': f.get('creado_por', ''),
                'fecha_creacion': str(f.get('fecha_creacion', '')),
                'errores': errores,
                'sugerencias': sugerencias,
            })

    print(f"  ✓ {len(discrepancias)} fichas con discrepancias detectadas (de {len(fichas)} totales)")
    return discrepancias


# ─── Paso 6: Construir estadísticas por comunidad ─────────────────────────────

def estadisticas_por_comunidad(fichas, centroides_com, discrepancias):
    """Genera estadísticas globales por comunidad para el informe."""
    ids_discrepantes = {d['id'] for d in discrepancias}
    stats = defaultdict(lambda: {'total': 0, 'con_gps': 0, 'sin_gps': 0, 'discrepantes': 0,
                                  'area_riego_m2': 0.0, 'caudal_ls': 0.0})
    for f in fichas:
        com = f.get('_com_corr', '') or '(Sin comunidad)'
        stats[com]['total'] += 1
        if f.get('_punto'):
            stats[com]['con_gps'] += 1
        else:
            stats[com]['sin_gps'] += 1
        if f.get('id') in ids_discrepantes:
            stats[com]['discrepantes'] += 1
        stats[com]['area_riego_m2'] += f.get('area_riego', 0) or 0
        stats[com]['caudal_ls'] += f.get('caudal_valor', 0) or 0
    return stats


# ─── Paso 7: Generar el informe markdown ──────────────────────────────────────

def generar_informe(fichas, discrepancias, centroides_com, stats_com):
    """Escribe el informe de auditoría en markdown."""
    fecha = datetime.now().strftime('%d/%m/%Y %H:%M')
    total = len(fichas)
    total_disc = len(discrepancias)
    pct = (total_disc / total * 100) if total else 0

    # Agrupar discrepancias por tipo
    por_comunidad = defaultdict(list)
    for d in discrepancias:
        por_comunidad[d['comunidad_corr'] or '(Sin comunidad)'].append(d)

    lineas = [
        f"# Informe de Auditoría Espacial — Catastro de Riego Cayambe",
        f"",
        f"**Generado:** {fecha}  ",
        f"**Umbral de discrepancia:** {UMBRAL_KM} km  ",
        f"**Total fichas analizadas:** {total}  ",
        f"**Fichas con discrepancias:** {total_disc} ({pct:.1f}%)  ",
        f"",
        f"---",
        f"",
        f"## Resumen Global",
        f"",
        f"| Comunidad | Total Fichas | Con GPS | Sin GPS | Discrepantes | Área Riego (ha) | Caudal (l/s) |",
        f"|-----------|-------------|---------|---------|-------------|----------------|-------------|",
    ]

    for com, s in sorted(stats_com.items()):
        area_ha = s['area_riego_m2'] / 10000
        lineas.append(
            f"| {com} | {s['total']} | {s['con_gps']} | {s['sin_gps']} | "
            f"{s['discrepantes']} | {area_ha:.2f} | {s['caudal_ls']:.1f} |"
        )

    lineas += [
        f"",
        f"---",
        f"",
        f"## Resumen de Discrepancias por Comunidad",
        f"",
        f"> **Nota**: Los polígonos de comunidad y sector se generarán excluyendo los predios marcados como discrepantes.",
        f"> Corrija las fichas en QField antes de regenerar las capas GIS.",
        f"",
    ]

    for com, casos in sorted(por_comunidad.items()):
        sector_com = COM_A_SECTOR.get(normalizar(com), 'Desconocido')
        lineas += [
            f"### 📍 {com} ({len(casos)} discrepancias — {sector_com})",
            f"",
        ]
        for d in casos:
            gps_str = (f"{d['gps'][1]:.5f}°, {d['gps'][0]:.5f}°"
                       if d['gps'] else "Sin GPS")
            lineas += [
                f"#### Ficha: {d['propietario'] or '(Sin nombre)'} — Cédula: {d['cedula'] or 'N/A'}",
                f"- **ID QField:** `{d['id']}`",
                f"- **Clave Catastral:** `{d['clave_catastral'] or 'N/A'}`",
                f"- **Comunidad en BD:** `{d['comunidad_bd'] or 'vacía'}`",
                f"- **Sector en BD:** `{d['sector_bd'] or 'vacío'}`",
                f"- **Parroquia en BD:** `{d['parroquia_bd'] or 'vacía'}`",
                f"- **GPS (lat, lon):** `{gps_str}`",
                f"- **Técnico:** `{d['creado_por']}`  |  **Fecha:** `{d['fecha_creacion'][:10]}`",
                f"",
                f"**🔴 Errores detectados:**",
            ]
            for e in d['errores']:
                lineas.append(f"  - {e}")
            if d['sugerencias']:
                lineas.append(f"")
                lineas.append(f"**✅ Sugerencias de corrección:**")
                for s in d['sugerencias']:
                    lineas.append(f"  - {s}")
            lineas.append(f"")

    lineas += [
        f"---",
        f"",
        f"## Comunidades sin Discrepancias Detectadas",
        f"",
    ]

    comunidades_ok = sorted(set(f['_com_corr'] for f in fichas if f['_com_corr'])
                            - set(por_comunidad.keys()))
    for com in comunidades_ok:
        s = stats_com.get(com, {})
        lineas.append(f"- **{com}**: {s.get('total', 0)} fichas, {s.get('con_gps', 0)} con GPS ✅")

    lineas += [
        f"",
        f"---",
        f"",
        f"## Centroides por Comunidad (Mediana GPS)",
        f"",
        f"| Comunidad | Sector | Fichas GPS | Centroide Lon | Centroide Lat |",
        f"|-----------|--------|-----------|--------------|--------------|",
    ]

    for com, (cx, cy, n) in sorted(centroides_com.items()):
        sector_c = COM_A_SECTOR.get(normalizar(com), '—')
        lineas.append(f"| {com} | {sector_c} | {n} | {cx:.5f} | {cy:.5f} |")

    contenido = '\n'.join(lineas)
    with open(OUTPUT_MD, 'w', encoding='utf-8') as f:
        f.write(contenido)

    print(f"  💾 Informe guardado: {OUTPUT_MD}")


# ─── Paso 8: Exportar IDs discrepantes a JSON (para uso en el generador) ──────

def exportar_ids_discrepantes(discrepancias):
    """Exporta la lista de IDs de fichas discrepantes a un archivo JSON."""
    ids = [d['id'] for d in discrepancias]
    out = os.path.abspath(os.path.join(os.path.dirname(OUTPUT_MD), 'fichas_discrepantes.json'))
    with open(out, 'w', encoding='utf-8') as f:
        json.dump({'ids_excluir': ids, 'total': len(ids),
                   'generado': datetime.now().isoformat()}, f, ensure_ascii=False, indent=2)
    print(f"  💾 IDs discrepantes: {out}")
    return out


# ─── Main ──────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    print("=" * 60)
    print("  AUDITORIA ESPACIAL -- Catastro Riego Cayambe")
    print("=" * 60)
    print()

    fichas      = leer_fichas()
    catastro    = leer_catastro()
    _parroquias = leer_parroquias()

    print("\n📊 Calculando centroides por comunidad...")
    centroides  = construir_centroides_comunidades(fichas)

    discrepancias = detectar_discrepancias(fichas, centroides, catastro)

    print("\n📋 Generando estadísticas...")
    stats = estadisticas_por_comunidad(fichas, centroides, discrepancias)

    print("\n📝 Escribiendo informe...")
    generar_informe(fichas, discrepancias, centroides, stats)

    print("\n📤 Exportando IDs discrepantes...")
    exportar_ids_discrepantes(discrepancias)

    print("\n✅ ¡Auditoría completada!")
    print(f"   → Informe: {OUTPUT_MD}")
    print(f"   → Fichas con discrepancias: {len(discrepancias)}")
