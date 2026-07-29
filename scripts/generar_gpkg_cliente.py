# -*- coding: utf-8 -*-
"""
Genera el GeoPackage de entrega para el CONTRATANTE (Consorcio Cayambe SPT).

Qué produce
-----------
padron-app/public/descargas/padron_riego_porotog.gpkg  con estas capas:

  predios_investigados  polígonos de los predios con ficha, simbología por estado
                        (tomate = con ficha principal, azul = adicional investigado,
                        celeste = adicional pendiente de Sección 4)
  catastro_completo     los 24.452 predios del catastro rural, como contexto
  fichas                una fila por ficha, enlazada al predio por clave catastral
  cultivos              Sección 4 agrícola, enlazada a la ficha
  animales              Sección 4 pecuaria, enlazada a la ficha
  canales_riego         red de conducción
  comunidades           límites por comunidad
  sectores              sectores de investigación

Decisiones de diseño
--------------------
* Se entrega en EPSG:32717 (UTM 17S), no en grados: es el sistema del catastro
  y permite que QGIS calcule áreas y distancias en metros sin configurar nada.
* Un predio = una fila, aunque tenga varias fichas. El detalle se consulta por
  la relación 1:N que trae el proyecto .qgz, así no hay polígonos superpuestos.
* Las fotografías van como URL a Firebase Storage, no empaquetadas.
* NO se incluye ninguna expresión del proyecto de campo (aggregate, ValueRelation,
  defaults calculados): el entregable es un visor de solo lectura.

Uso:
  python -X utf8 padron-app/scripts/generar_gpkg_cliente.py
"""
import json
import os
import sqlite3
import struct
import sys
from datetime import datetime, timezone

from pyproj import Transformer

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
GEO = os.path.join(BASE, 'public', 'geo')
# El GeoPackage se arma en una carpeta de trabajo, NO en public/: allí solo debe
# quedar el .zip final, para no publicar 40 MB duplicados en cada despliegue.
OUT_DIR = os.path.join(BASE, 'build_entrega')
GPKG = os.path.join(OUT_DIR, 'padron_riego_porotog.gpkg')

SRS_ID = 32717
BUCKET = 'invs-riego-comunitario.firebasestorage.app'

# Nombre real del técnico a partir del usuario de QField (mismo mapeo que el resto
# del proyecto). En el entregable se muestra el nombre, no el usuario interno.
TECNICOS = {
    'u0_a314': 'Melany Jara', 'u0_a319': 'Melany Jara', 'jvk-editor': 'Melany Jara',
    'u0_a504': 'Adriana Cuascota', 'jvk-editor6': 'Adriana Cuascota',
    'u0_a279': 'Huguito Ipial', 'jvk-editor2': 'Huguito Ipial',
    'u0_a70': 'Pablo Barrionuevo', 'jvk-editor5': 'Pablo Barrionuevo',
    'u0_a330': 'Mayra Benavides', 'mayralisseth201': 'Mayra Benavides',
    'u0_a362': 'Martha Simbaña', 'u0_a335': 'Martha Simbaña', 'jvk-editor4': 'Martha Simbaña',
    'u0_a2': 'JVK-DIGITALIZACION', 'jvk-digitalizacion': 'JVK-DIGITALIZACION',
    'u0_a302': 'Dylan Chavez', 'jvk-editor3': 'Dylan Chavez',
    'u0_a200': 'Melanie2', 'jvk-corp': 'Melany Recalde',
    'AUTO-SECCION7': 'Generada desde la Sección 7',
}

_tr = Transformer.from_crs("EPSG:4326", "EPSG:32717", always_xy=True)


# ══════════════════════════════════════════════════════════════
# Escritura de geometrías GeoPackage (header GPKG + WKB)
# ══════════════════════════════════════════════════════════════

def _rings_utm(coords, depth):
    """Reproyecta recursivamente una lista de coordenadas a UTM 17S."""
    if depth == 0:
        x, y = _tr.transform(coords[0], coords[1])
        return [x, y]
    return [_rings_utm(c, depth - 1) for c in coords]


def _wkb_polygon(rings):
    out = struct.pack('<BII', 1, 3, len(rings))
    for r in rings:
        out += struct.pack('<I', len(r))
        for p in r:
            out += struct.pack('<dd', p[0], p[1])
    return out


def _wkb_multipolygon(polys):
    out = struct.pack('<BII', 1, 6, len(polys))
    for rings in polys:
        out += _wkb_polygon(rings)
    return out


def _wkb_linestring(pts):
    out = struct.pack('<BII', 1, 2, len(pts))
    for p in pts:
        out += struct.pack('<dd', p[0], p[1])
    return out


def _wkb_multilinestring(lines):
    out = struct.pack('<BII', 1, 5, len(lines))
    for pts in lines:
        out += _wkb_linestring(pts)
    return out


def _bbox(coords, acc):
    if coords and isinstance(coords[0], (int, float)):
        acc[0] = min(acc[0], coords[0]); acc[1] = max(acc[1], coords[0])
        acc[2] = min(acc[2], coords[1]); acc[3] = max(acc[3], coords[1])
        return
    for c in coords:
        _bbox(c, acc)


def gpkg_blob(geom):
    """GeoJSON geometry (WGS84) -> blob GeoPackage en UTM 17S. None si no aplica."""
    if not geom:
        return None
    t = geom.get('type')
    c = geom.get('coordinates')
    if not c:
        return None
    try:
        if t == 'Polygon':
            u = _rings_utm(c, 2)
            wkb = _wkb_multipolygon([u])          # se normaliza a MultiPolygon
        elif t == 'MultiPolygon':
            u = _rings_utm(c, 3)
            wkb = _wkb_multipolygon(u)
        elif t == 'LineString':
            u = _rings_utm(c, 1)
            wkb = _wkb_multilinestring([u])
        elif t == 'MultiLineString':
            u = _rings_utm(c, 2)
            wkb = _wkb_multilinestring(u)
        else:
            return None
    except Exception:
        return None

    acc = [1e18, -1e18, 1e18, -1e18]
    _bbox(u, acc)
    # flags: bit0 little endian + envelope XY (indicador 1)
    header = b'GP' + struct.pack('<BBi', 0, 0x03, SRS_ID)
    header += struct.pack('<dddd', acc[0], acc[1], acc[2], acc[3])
    return header + wkb


# ══════════════════════════════════════════════════════════════
# Estructura mínima del GeoPackage
# ══════════════════════════════════════════════════════════════

def crear_gpkg(path):
    if os.path.exists(path):
        os.remove(path)
    con = sqlite3.connect(path)
    cur = con.cursor()
    cur.execute("PRAGMA application_id = 1196444487")   # 'GPKG'
    cur.execute("PRAGMA user_version = 10300")          # 1.3.0

    cur.executescript("""
    CREATE TABLE gpkg_spatial_ref_sys (
      srs_name TEXT NOT NULL, srs_id INTEGER PRIMARY KEY,
      organization TEXT NOT NULL, organization_coordsys_id INTEGER NOT NULL,
      definition TEXT NOT NULL, description TEXT);
    CREATE TABLE gpkg_contents (
      table_name TEXT PRIMARY KEY, data_type TEXT NOT NULL, identifier TEXT UNIQUE,
      description TEXT DEFAULT '', last_change DATETIME NOT NULL
        DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
      min_x DOUBLE, min_y DOUBLE, max_x DOUBLE, max_y DOUBLE, srs_id INTEGER,
      CONSTRAINT fk_gc_r_srs_id FOREIGN KEY (srs_id)
        REFERENCES gpkg_spatial_ref_sys(srs_id));
    CREATE TABLE gpkg_geometry_columns (
      table_name TEXT NOT NULL, column_name TEXT NOT NULL, geometry_type_name TEXT NOT NULL,
      srs_id INTEGER NOT NULL, z TINYINT NOT NULL, m TINYINT NOT NULL,
      CONSTRAINT pk_geom_cols PRIMARY KEY (table_name, column_name));
    """)

    wgs84 = ('GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563]],'
             'PRIMEM["Greenwich",0],UNIT["degree",0.0174532925199433],AUTHORITY["EPSG","4326"]]')
    utm17s = ('PROJCS["WGS 84 / UTM zone 17S",GEOGCS["WGS 84",DATUM["WGS_1984",'
              'SPHEROID["WGS 84",6378137,298.257223563,AUTHORITY["EPSG","7030"]],'
              'AUTHORITY["EPSG","6326"]],PRIMEM["Greenwich",0],UNIT["degree",0.0174532925199433],'
              'AUTHORITY["EPSG","4326"]],PROJECTION["Transverse_Mercator"],'
              'PARAMETER["latitude_of_origin",0],PARAMETER["central_meridian",-81],'
              'PARAMETER["scale_factor",0.9996],PARAMETER["false_easting",500000],'
              'PARAMETER["false_northing",10000000],UNIT["metre",1],AUTHORITY["EPSG","32717"]]')
    cur.executemany("INSERT INTO gpkg_spatial_ref_sys VALUES (?,?,?,?,?,?)", [
        ('Undefined cartesian SRS', -1, 'NONE', -1, 'undefined', ''),
        ('Undefined geographic SRS', 0, 'NONE', 0, 'undefined', ''),
        ('WGS 84', 4326, 'EPSG', 4326, wgs84, ''),
        ('WGS 84 / UTM zone 17S', 32717, 'EPSG', 32717, utm17s, 'Sistema del catastro'),
    ])

    # Tabla de estilos de QGIS: es lo que hace que la capa se pinte sola
    cur.executescript("""
    CREATE TABLE layer_styles (
      id INTEGER PRIMARY KEY AUTOINCREMENT, f_table_catalog TEXT, f_table_schema TEXT,
      f_table_name TEXT, f_geometry_column TEXT, styleName TEXT, styleQML TEXT,
      styleSLD TEXT, useAsDefault BOOLEAN, description TEXT, owner TEXT,
      ui TEXT, update_time DATETIME DEFAULT CURRENT_TIMESTAMP);
    """)
    con.commit()
    return con


def registrar_capa(cur, tabla, tipo_geom, titulo, descripcion, bbox):
    if tipo_geom:
        cur.execute("INSERT INTO gpkg_contents "
                    "(table_name,data_type,identifier,description,min_x,min_y,max_x,max_y,srs_id) "
                    "VALUES (?,?,?,?,?,?,?,?,?)",
                    (tabla, 'features', titulo, descripcion,
                     bbox[0], bbox[2], bbox[1], bbox[3], SRS_ID))
        cur.execute("INSERT INTO gpkg_geometry_columns VALUES (?,?,?,?,0,0)",
                    (tabla, 'geom', tipo_geom, SRS_ID))
    else:
        cur.execute("INSERT INTO gpkg_contents "
                    "(table_name,data_type,identifier,description,srs_id) VALUES (?,?,?,?,?)",
                    (tabla, 'attributes', titulo, descripcion, SRS_ID))


def cargar(nombre):
    with open(os.path.join(GEO, nombre), encoding='utf-8') as f:
        return json.load(f)


def txt(v):
    if v is None:
        return None
    s = str(v).strip()
    return None if s in ('', 'None', 'null') else s


def num(v):
    try:
        return round(float(v), 2)
    except (TypeError, ValueError):
        return None


# ══════════════════════════════════════════════════════════════
# Estilos QGIS (QML) — simbología y formulario de solo lectura
# ══════════════════════════════════════════════════════════════

def _simbolo_relleno(nombre, relleno, borde, ancho='0.4'):
    return """<symbol alpha="1" clip_to_extent="1" force_rhr="0" name="{n}" type="fill">
      <layer class="SimpleFill" enabled="1" pass="0">
        <Option type="Map">
          <Option name="color" type="QString" value="{r}"/>
          <Option name="outline_color" type="QString" value="{b}"/>
          <Option name="outline_width" type="QString" value="{w}"/>
          <Option name="outline_style" type="QString" value="solid"/>
          <Option name="style" type="QString" value="solid"/>
        </Option>
      </layer>
    </symbol>""".format(n=nombre, r=relleno, b=borde, w=ancho)


def _simbolo_linea(nombre, color, ancho='0.6'):
    return """<symbol alpha="1" clip_to_extent="1" force_rhr="0" name="{n}" type="line">
      <layer class="SimpleLine" enabled="1" pass="0">
        <Option type="Map">
          <Option name="line_color" type="QString" value="{c}"/>
          <Option name="line_width" type="QString" value="{w}"/>
          <Option name="line_style" type="QString" value="solid"/>
        </Option>
      </layer>
    </symbol>""".format(n=nombre, c=color, w=ancho)


def _bloque_solo_lectura(campos):
    """Deja todos los campos no editables: el entregable es un visor."""
    ed = "\n".join('    <field editable="0" name="{}"/>'.format(c) for c in campos)
    al = "\n".join('    <field labelOnTop="0" name="{}"/>'.format(c) for c in campos)
    return ("  <editable>\n{}\n  </editable>\n"
            "  <labelOnTop>\n{}\n  </labelOnTop>\n"
            "  <editorlayout>generatedlayout</editorlayout>\n"
            "  <readOnly>1</readOnly>\n").format(ed, al)


def qml_predios(campos):
    reglas = [
        ("\"estado_predio\" = 'Investigado'", 'Predio investigado (ficha principal)', '0'),
        ("\"estado_predio\" = 'Adicional investigado'", 'Predio adicional — investigado', '1'),
        ("\"estado_predio\" = 'Adicional pendiente'", 'Predio adicional — pendiente Sección 4', '2'),
        ("ELSE", 'Otro', '3'),
    ]
    r = "\n".join(
        '        <rule filter="{f}" key="{{r{i}}}" label="{l}" symbol="{s}"/>'.format(
            f=f.replace('"', '&quot;'), i=i, l=l, s=s)
        for i, (f, l, s) in enumerate(reglas))
    simbolos = "\n".join([
        _simbolo_relleno('0', '249,115,22,90,rgb:0.976,0.451,0.086,0.353', '234,88,12,255,rgb:0.918,0.345,0.047,1'),
        _simbolo_relleno('1', '59,130,246,90,rgb:0.231,0.510,0.965,0.353', '37,99,235,255,rgb:0.145,0.388,0.922,1'),
        _simbolo_relleno('2', '125,211,252,110,rgb:0.490,0.827,0.988,0.431', '14,165,233,255,rgb:0.055,0.647,0.914,1'),
        _simbolo_relleno('3', '148,163,184,60,rgb:0.580,0.639,0.722,0.235', '100,116,139,255,rgb:0.392,0.455,0.545,1'),
    ])
    return """<!DOCTYPE qgis>
<qgis version="3.36.0" styleCategories="Symbology|Fields|Forms|MapTips">
  <renderer-v2 type="RuleRenderer" symbollevels="0" forceraster="0" enableorderby="0">
    <rules key="{{predios}}">
{reglas}
    </rules>
    <symbols>
{simbolos}
    </symbols>
  </renderer-v2>
  <mapTip>[% "propietarios" %]&lt;br&gt;Clave: [% "clave_catastral" %]&lt;br&gt;[% "estado_predio" %]</mapTip>
{ro}</qgis>""".format(reglas=r, simbolos=simbolos, ro=_bloque_solo_lectura(campos))


def qml_simple(campos, simbolo, maptip=''):
    mt = '<mapTip>{}</mapTip>'.format(maptip) if maptip else ''
    return """<!DOCTYPE qgis>
<qgis version="3.36.0" styleCategories="Symbology|Fields|Forms|MapTips">
  <renderer-v2 type="singleSymbol" symbollevels="0" forceraster="0" enableorderby="0">
    <symbols>
{s}
    </symbols>
  </renderer-v2>
  {mt}
{ro}</qgis>""".format(s=simbolo, mt=mt, ro=_bloque_solo_lectura(campos))


def guardar_estilo(cur, tabla, campos, qml, geom_col='geom'):
    cur.execute("INSERT INTO layer_styles (f_table_catalog,f_table_schema,f_table_name,"
                "f_geometry_column,styleName,styleQML,useAsDefault,description,owner) "
                "VALUES ('','',?,?,?,?,1,?,'Consorcio Cayambe SPT')",
                (tabla, geom_col, tabla, qml, 'Estilo de entrega'))


# ══════════════════════════════════════════════════════════════
# Construcción
# ══════════════════════════════════════════════════════════════

def crear_tabla(cur, nombre, columnas, con_geom=True, tipo_geom='MULTIPOLYGON'):
    cols = ["fid INTEGER PRIMARY KEY AUTOINCREMENT"]
    if con_geom:
        cols.append("geom {}".format(tipo_geom))
    cols += ["{} {}".format(c, t) for c, t in columnas]
    cur.execute("CREATE TABLE {} ({})".format(nombre, ", ".join(cols)))


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    print("=" * 74)
    print(" GEOPACKAGE PARA EL CONTRATANTE — Consorcio Cayambe SPT")
    print("=" * 74)

    print("\n[1/6] Leyendo datos publicados...")
    fichas = [f['properties'] for f in cargar('fichas_predios.geojson')['features']]
    catastro = cargar('catastro_geo.geojson')['features']
    cultivos = cargar('cultivos.json')
    animales = cargar('animales.json')

    # Hay registros de Sección 4 que quedaron de fichas ya eliminadas en campo:
    # apuntan a un ficha_id que no existe. En el entregable no se pueden consultar
    # y distorsionarían los totales, así que se excluyen.
    _ids = {f.get('id') for f in [x['properties'] for x in
                                  cargar('fichas_predios.geojson')['features']]}
    _c0, _a0 = len(cultivos), len(animales)
    cultivos = [c for c in cultivos if c.get('ficha_id') in _ids]
    animales = [a for a in animales if a.get('ficha_id') in _ids]
    if _c0 - len(cultivos) or _a0 - len(animales):
        print("      [excluidos por no tener ficha] cultivos {} | animales {}".format(
            _c0 - len(cultivos), _a0 - len(animales)))
    poligonos = cargar('catastro_poligonos.json')
    busqueda = {str(r['fid']): r for r in cargar('catastro_busqueda.json')}
    print("      fichas {:,} | predios con ficha {:,} | catastro completo {:,}".format(
        len(fichas), len(catastro), len(poligonos)))
    print("      cultivos {:,} | animales {:,}".format(len(cultivos), len(animales)))

    # ── estado de cada predio ──
    print("\n[2/6] Clasificando predios...")
    por_clave = {}
    for f in fichas:
        k = txt(f.get('clave_catastral')) or txt(f.get('cod_poligono'))
        if k:
            por_clave.setdefault(k, []).append(f)

    def es_hija(p):
        return p.get('es_ficha_hija') in (1, True)

    def pendiente(p):
        return es_hija(p) and (p.get('estado_investigacion') or 'pendiente_produccion') != 'completada'

    def estado_de(fs):
        if any(not es_hija(p) for p in fs):
            return 'Investigado'
        return 'Adicional pendiente' if any(pendiente(p) for p in fs) else 'Adicional investigado'

    con = crear_gpkg(GPKG)
    cur = con.cursor()

    # ── capa 1: predios investigados ──
    print("\n[3/6] Capa de predios investigados...")
    cols_predios = [
        ('clave_catastral', 'TEXT'), ('estado_predio', 'TEXT'), ('comunidad', 'TEXT'),
        ('sector_riego', 'TEXT'), ('parroquia', 'TEXT'), ('propietarios', 'TEXT'),
        ('propietario_catastro', 'TEXT'), ('area_catastro_m2', 'REAL'),
        ('total_fichas', 'INTEGER'), ('fichas_principales', 'INTEGER'),
        ('fichas_adicionales', 'INTEGER'), ('adicionales_pendientes', 'INTEGER'),
        ('area_declarada_m2', 'REAL'), ('area_riego_m2', 'REAL'), ('caudal_ls', 'REAL'),
        ('cultivos_predio', 'TEXT'), ('animales_predio', 'TEXT'),
    ]
    crear_tabla(cur, 'predios_investigados', cols_predios)

    cult_por_ficha, anim_por_ficha = {}, {}
    for c in cultivos:
        cult_por_ficha.setdefault(c.get('ficha_id'), []).append(c)
    for a in animales:
        anim_por_ficha.setdefault(a.get('ficha_id'), []).append(a)

    bbox = [1e18, -1e18, 1e18, -1e18]
    n = 0
    for feat in catastro:
        blob = gpkg_blob(feat.get('geometry'))
        if not blob:
            continue
        p = feat.get('properties') or {}
        k = txt(p.get('clave_cata'))
        fs = por_clave.get(k, [])
        ppal = [x for x in fs if not es_hija(x)]
        adic = [x for x in fs if es_hija(x)]
        cs, ans = [], []
        for x in fs:
            for c in cult_por_ficha.get(x.get('id'), []):
                t = txt(c.get('tipo_cultivo_otro')) or txt(c.get('tipo_cultivo'))
                if t:
                    cs.append(t)
            for a in anim_por_ficha.get(x.get('id'), []):
                t = txt(a.get('especie_otro')) or txt(a.get('especie'))
                if t:
                    ans.append(t)
        vals = (blob, k, estado_de(fs) if fs else 'Sin ficha',
                txt(fs[0].get('comunidad')) if fs else None,
                txt(fs[0].get('sector')) if fs else None,
                txt(fs[0].get('parroquia')) if fs else None,
                ' / '.join(sorted({("{} {}".format(x.get('apellidos') or '', x.get('nombres') or '')).strip()
                                   for x in fs if (x.get('apellidos') or x.get('nombres'))})) or None,
                ("{} {}".format(p.get('apellidos') or '', p.get('nombres') or '')).strip() or None,
                num(p.get('area_predi')),
                len(fs), len(ppal), len(adic), sum(1 for x in adic if pendiente(x)),
                num(sum(x.get('area_total') or 0 for x in fs)),
                num(sum(x.get('area_riego') or 0 for x in fs)),
                num(sum(x.get('caudal_valor') or 0 for x in fs)),
                ', '.join(sorted(set(cs))) or None, ', '.join(sorted(set(ans))) or None)
        cur.execute("INSERT INTO predios_investigados (geom,{}) VALUES ({})".format(
            ",".join(c for c, _ in cols_predios), ",".join('?' * (len(cols_predios) + 1))), vals)
        e = struct.unpack('<dddd', blob[8:40])
        bbox[0] = min(bbox[0], e[0]); bbox[1] = max(bbox[1], e[1])
        bbox[2] = min(bbox[2], e[2]); bbox[3] = max(bbox[3], e[3])
        n += 1
    registrar_capa(cur, 'predios_investigados', 'MULTIPOLYGON',
                   'Predios investigados',
                   'Predios con ficha de empadronamiento. El color indica el estado.', bbox)
    guardar_estilo(cur, 'predios_investigados', [c for c, _ in cols_predios],
                   qml_predios([c for c, _ in cols_predios]))
    print("      {:,} predios".format(n))
    con.commit()

    # ── capa 2: catastro completo (universo de la investigación) ──
    print("\n[4/6] Capa del catastro completo...")
    cols_cat = [('clave_catastral', 'TEXT'), ('propietario', 'TEXT'), ('cedula', 'TEXT'),
                ('comunidad', 'TEXT'), ('area_predi_m2', 'REAL'), ('tiene_ficha', 'TEXT')]
    crear_tabla(cur, 'catastro_completo', cols_cat)
    bb2 = [1e18, -1e18, 1e18, -1e18]
    n2 = 0
    for fid, geom in poligonos.items():
        blob = gpkg_blob(geom)
        if not blob:
            continue
        r = busqueda.get(str(fid), {})
        k = txt(r.get('clave_cata'))
        cur.execute("INSERT INTO catastro_completo (geom,{}) VALUES ({})".format(
            ",".join(c for c, _ in cols_cat), ",".join('?' * (len(cols_cat) + 1))),
            (blob, k,
             ("{} {}".format(r.get('apellidos') or '', r.get('nombres') or '')).strip() or None,
             txt(r.get('cedula')), txt(r.get('comunidad')), num(r.get('area_predi')),
             'Sí' if k in por_clave else 'No'))
        e = struct.unpack('<dddd', blob[8:40])
        bb2[0] = min(bb2[0], e[0]); bb2[1] = max(bb2[1], e[1])
        bb2[2] = min(bb2[2], e[2]); bb2[3] = max(bb2[3], e[3])
        n2 += 1
    registrar_capa(cur, 'catastro_completo', 'MULTIPOLYGON', 'Catastro rural completo',
                   'Universo catastral de referencia. Muestra el alcance de la investigación.', bb2)
    guardar_estilo(cur, 'catastro_completo', [c for c, _ in cols_cat],
                   qml_simple([c for c, _ in cols_cat],
                              _simbolo_relleno('0', '226,232,240,25,rgb:0.886,0.910,0.941,0.098',
                                               '148,163,184,180,rgb:0.580,0.639,0.722,0.706', '0.2'),
                              'Clave: [% "clave_catastral" %]&lt;br&gt;[% "propietario" %]'))
    print("      {:,} predios de contexto".format(n2))
    con.commit()

    # ── tablas de atributos: fichas, cultivos, animales ──
    print("\n[5/6] Tablas de fichas, cultivos y animales...")
    CAMPOS_FICHA = [
        ('ficha_id', 'TEXT'), ('clave_catastral', 'TEXT'), ('codigo_predio', 'TEXT'),
        ('tipo_ficha', 'TEXT'), ('estado_investigacion', 'TEXT'), ('regante_principal', 'TEXT'),
        ('apellidos', 'TEXT'), ('nombres', 'TEXT'), ('cedula', 'TEXT'),
        ('telefono_celular', 'TEXT'), ('telefono_casa', 'TEXT'),
        ('parroquia', 'TEXT'), ('comunidad', 'TEXT'), ('sector', 'TEXT'),
        ('sector_comunidad', 'TEXT'), ('tenencia_predio', 'TEXT'), ('nivel_instruccion', 'TEXT'),
        ('area_total_m2', 'REAL'), ('area_riego_m2', 'REAL'), ('area_sin_riego_m2', 'REAL'),
        ('canal', 'TEXT'), ('caudal_ls', 'REAL'), ('caudal_tipo', 'TEXT'),
        ('frecuencia_riego', 'TEXT'), ('dias_riego', 'REAL'), ('horas_turno', 'REAL'),
        ('metodo_gravedad_pct', 'REAL'), ('metodo_aspersion_pct', 'REAL'), ('metodo_goteo_pct', 'REAL'),
        ('valor_tarifa', 'REAL'), ('tipo_tarifa', 'TEXT'), ('tiene_reservorio', 'TEXT'),
        ('agua_consumo', 'TEXT'), ('energia_electrica', 'TEXT'), ('material_construccion', 'TEXT'),
        ('cota_msnm', 'REAL'), ('org_riego', 'TEXT'), ('actividad_productiva', 'TEXT'),
        ('observaciones', 'TEXT'), ('investigado_por', 'TEXT'), ('fecha_registro', 'TEXT'),
        ('foto_url', 'TEXT'),
    ]
    crear_tabla(cur, 'fichas', CAMPOS_FICHA, con_geom=False)

    por_id = {f.get('id'): f for f in fichas}

    def nombre_regante(f):
        return ("{} {}".format(f.get('apellidos') or '', f.get('nombres') or '')).strip() or None

    def foto_url(f):
        nom = txt(f.get('foto_predio'))
        if not nom:
            return None
        base = nom.replace('\\', '/').split('/')[-1]
        return ("https://firebasestorage.googleapis.com/v0/b/{}/o/fotos_predios%2F{}?alt=media"
                .format(BUCKET, base.replace(' ', '%20')))

    ins_f = "INSERT INTO fichas ({}) VALUES ({})".format(
        ",".join(c for c, _ in CAMPOS_FICHA), ",".join('?' * len(CAMPOS_FICHA)))
    for f in fichas:
        hija = es_hija(f)
        madre = por_id.get(f.get('ficha_madre_id')) if hija else None
        cur.execute(ins_f, (
            txt(f.get('id')), txt(f.get('clave_catastral')) or txt(f.get('cod_poligono')),
            txt(f.get('codigo_final')),
            'Ficha adicional' if hija else 'Ficha principal',
            ('Pendiente Sección 4' if pendiente(f) else 'Investigada') if hija else 'Investigada',
            nombre_regante(madre) if madre else None,
            txt(f.get('apellidos')), txt(f.get('nombres')), txt(f.get('cedula')),
            txt(f.get('telefono_celular')), txt(f.get('telefono_casa')),
            txt(f.get('parroquia')), txt(f.get('comunidad')), txt(f.get('sector')),
            txt(f.get('sector_comunidad')), txt(f.get('tenencia_predio')), txt(f.get('nivel_instruccion')),
            num(f.get('area_total')), num(f.get('area_riego')), num(f.get('area_sin_riego')),
            txt(f.get('canal')), num(f.get('caudal_valor')), txt(f.get('caudal_tipo')),
            txt(f.get('frecuencia_riego')), num(f.get('dias_riego')), num(f.get('horas_turno')),
            num(f.get('metodo_gravedad_pct')), num(f.get('metodo_aspersion_pct')), num(f.get('metodo_goteo_pct')),
            num(f.get('valor_tarifa')), txt(f.get('tipo_tarifa')), txt(f.get('tiene_reservorio')),
            txt(f.get('agua_consumo')), txt(f.get('energia_electrica')), txt(f.get('material_construccion')),
            num(f.get('cota_msnm')), txt(f.get('org_riego')), txt(f.get('actividad_productiva')),
            txt(f.get('observaciones')), TECNICOS.get(txt(f.get('creado_por')), txt(f.get('creado_por'))),
            txt(f.get('fecha_creacion')), foto_url(f)))
    registrar_capa(cur, 'fichas', None, 'Fichas de empadronamiento',
                   'Una fila por ficha. Se enlaza al predio por la clave catastral.', None)
    guardar_estilo(cur, 'fichas', [c for c, _ in CAMPOS_FICHA],
                   qml_simple([c for c, _ in CAMPOS_FICHA], ''), geom_col='')

    CAMPOS_CULT = [('ficha_id', 'TEXT'), ('cultivo', 'TEXT'), ('superficie_m2', 'REAL'),
                   ('es_principal', 'TEXT'), ('destino', 'TEXT')]
    crear_tabla(cur, 'cultivos', CAMPOS_CULT, con_geom=False)
    for c in cultivos:
        destinos = [n for n, k in (('Autoconsumo', 'es_autoconsumo'), ('Mercado', 'es_mercado'),
                                   ('Agroindustria', 'es_agroindustria'), ('Exportación', 'es_exportacion'))
                    if c.get(k) in (1, True)]
        cur.execute("INSERT INTO cultivos (ficha_id,cultivo,superficie_m2,es_principal,destino) "
                    "VALUES (?,?,?,?,?)",
                    (txt(c.get('ficha_id')), txt(c.get('tipo_cultivo_otro')) or txt(c.get('tipo_cultivo')),
                     num(c.get('superficie_m2')), 'Sí' if c.get('es_principal') in (1, True) else 'No',
                     ', '.join(destinos) or None))
    registrar_capa(cur, 'cultivos', None, 'Cultivos (Sección 4)',
                   'Cultivos declarados en cada ficha.', None)
    guardar_estilo(cur, 'cultivos', [c for c, _ in CAMPOS_CULT],
                   qml_simple([c for c, _ in CAMPOS_CULT], ''), geom_col='')

    CAMPOS_ANIM = [('ficha_id', 'TEXT'), ('especie', 'TEXT'), ('cantidad', 'INTEGER'),
                   ('destino', 'TEXT')]
    crear_tabla(cur, 'animales', CAMPOS_ANIM, con_geom=False)
    for a in animales:
        destinos = [n for n, k in (('Autoconsumo', 'es_autoconsumo'), ('Mercado', 'es_mercado'),
                                   ('Agroindustria', 'es_agroindustria'), ('Exportación', 'es_exportacion'))
                    if a.get(k) in (1, True)]
        cur.execute("INSERT INTO animales (ficha_id,especie,cantidad,destino) VALUES (?,?,?,?)",
                    (txt(a.get('ficha_id')), txt(a.get('especie_otro')) or txt(a.get('especie')),
                     a.get('cantidad'), ', '.join(destinos) or None))
    registrar_capa(cur, 'animales', None, 'Especies pecuarias (Sección 4)',
                   'Animales declarados en cada ficha.', None)
    guardar_estilo(cur, 'animales', [c for c, _ in CAMPOS_ANIM],
                   qml_simple([c for c, _ in CAMPOS_ANIM], ''), geom_col='')
    print("      fichas {:,} | cultivos {:,} | animales {:,}".format(
        len(fichas), len(cultivos), len(animales)))
    con.commit()

    # ── capas de contexto ──
    print("\n[6/6] Capas de contexto...")
    def capa_geojson(archivo, tabla, columnas, titulo, desc, qml_fn, tipo='MULTIPOLYGON'):
        try:
            feats = cargar(archivo)['features']
        except Exception as e:
            print("      [aviso] {} no disponible: {}".format(archivo, e))
            return
        crear_tabla(cur, tabla, columnas, tipo_geom=tipo)
        bb = [1e18, -1e18, 1e18, -1e18]
        m = 0
        ins = "INSERT INTO {} (geom,{}) VALUES ({})".format(
            tabla, ",".join(c for c, _ in columnas), ",".join('?' * (len(columnas) + 1)))
        for ft in feats:
            blob = gpkg_blob(ft.get('geometry'))
            if not blob:
                continue
            p = ft.get('properties') or {}
            cur.execute(ins, (blob,) + tuple(
                num(p.get(c)) if t == 'REAL' else txt(p.get(c)) for c, t in columnas))
            e = struct.unpack('<dddd', blob[8:40])
            bb[0] = min(bb[0], e[0]); bb[1] = max(bb[1], e[1])
            bb[2] = min(bb[2], e[2]); bb[3] = max(bb[3], e[3])
            m += 1
        if m == 0:
            return
        registrar_capa(cur, tabla, tipo, titulo, desc, bb)
        guardar_estilo(cur, tabla, [c for c, _ in columnas], qml_fn([c for c, _ in columnas]))
        print("      {}: {:,}".format(titulo, m))

    capa_geojson('comunidades.geojson', 'comunidades',
                 [('comunidad', 'TEXT'), ('sector', 'TEXT'), ('total_fichas', 'TEXT'),
                  ('predios_catastro', 'TEXT'), ('area_dissolve_ha', 'REAL'),
                  ('area_riego_ha', 'REAL'), ('caudal_total_ls', 'REAL')],
                 'Comunidades', 'Límite aproximado por comunidad, generado de los predios investigados.',
                 lambda cs: qml_simple(cs, _simbolo_relleno(
                     '0', '236,72,153,20,rgb:0.925,0.282,0.600,0.078',
                     '236,72,153,200,rgb:0.925,0.282,0.600,0.784', '0.5'),
                     '[% "comunidad" %]'))

    capa_geojson('sectores.geojson', 'sectores',
                 [('sector', 'TEXT'), ('total_fichas', 'TEXT'), ('predios_catastro', 'TEXT'),
                  ('area_dissolve_ha', 'REAL'), ('area_riego_ha', 'REAL'), ('caudal_total_ls', 'REAL')],
                 'Sectores de investigación', 'Agrupación de comunidades por sector.',
                 lambda cs: qml_simple(cs, _simbolo_relleno(
                     '0', '139,92,246,18,rgb:0.545,0.361,0.965,0.071',
                     '139,92,246,220,rgb:0.545,0.361,0.965,0.863', '0.7'),
                     '[% "sector" %]'))

    capa_geojson('ramales_riego.geojson', 'canales_riego',
                 [('nombre', 'TEXT')], 'Canales de riego',
                 'Red de conducción del sistema Guanguilquí–Porotog.',
                 lambda cs: qml_simple(cs, _simbolo_linea('0', '56,189,248,255,rgb:0.220,0.741,0.973,1', '0.8'),
                                       '[% "nombre" %]'),
                 tipo='MULTILINESTRING')

    con.commit()
    cur.execute("VACUUM")
    con.close()

    mb = os.path.getsize(GPKG) / (1024 * 1024)
    print("\n" + "=" * 74)
    print(" LISTO: {}".format(GPKG))
    print(" Tamaño: {:.1f} MB   |   generado {}".format(
        mb, datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')))
    print("=" * 74)


if __name__ == '__main__':
    main()
