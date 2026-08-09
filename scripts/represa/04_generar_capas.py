# -*- coding: utf-8 -*-
"""
Capas georreferenciadas de la represa de Porotog, para la web y para QGIS.

Qué hace
--------
Toma la geometría extraída del plano 1000 (en coordenadas de página) y le aplica
la transformación calculada en `03_georreferenciar.py` (RMS 0,216 m, escala
1:1.998 contra 1:2.000 declarado). El resultado son capas en UTM 17S que se
exportan a GeoJSON en WGS84 para el visor web.

Tres decisiones que conviene entender
-------------------------------------
1. **El límite de proyecto NO se dibuja desde el PDF, se construye desde la
   tabla de coordenadas del consorcio.** Es el dato oficial, con precisión de
   milímetros; el trazo del PDF es una línea gruesa (40 trapecios) cuyo eje hay
   que estimar. Se usa la tabla, con el vértice 23 corregido según lo deducido
   en el paso 3 — y ese cambio queda anotado en las propiedades de la capa.

2. **Cada polígono se identifica por el rótulo que cae dentro de él.** El plano
   trae 8 polígonos rojos en la misma capa CAD (`C3D-Volumen`) sin nada que los
   distinga; los textos «BANCO DE MATERIALES 1», «LIMITE DE PROYECTO», etc. sí
   están georreferenciados, así que se le pone a cada polígono el nombre del
   rótulo que contiene. Lo que no contiene ningún rótulo queda como «sin
   identificar» en lugar de inventarle un nombre.

3. **Se valida contra las curvas de nivel de 5 m** (`curvas_5m_zona.gpkg`, de
   otra fuente y ya georreferenciada). Las curvas «mayores» del levantamiento
   son las de cota múltiplo de 5, así que tienen que caer encima de las
   regionales. Es la única comprobación que no depende de los datos del propio
   plano: si esto cuadra, la georreferenciación es correcta de verdad.

Salida
------
padron-app/public/geo/represa/*.geojson   (WGS84, para el visor)
CARTOGRAFIA REPRESA/procesado/represa_utm.gpkg   (UTM 17S, para QGIS)
"""
import json
import math
import os
import sys

from osgeo import ogr, osr

ogr.UseExceptions()
osr.UseExceptions()

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
RAIZ = os.path.abspath(os.path.join(BASE, '..'))
PROCESADO = os.path.join(RAIZ, 'CARTOGRAFIA REPRESA', 'procesado')
GPKG_PLANO = os.path.join(PROCESADO, 'plano_1000.gpkg')
GEORREF = os.path.join(PROCESADO, 'georref_1000.json')
CURVAS_5M = os.path.join(PROCESADO, 'curvas_5m_zona.gpkg')
GPKG_SALIDA = os.path.join(PROCESADO, 'represa_utm.gpkg')
WEB = os.path.join(BASE, 'public', 'geo', 'represa')

# Capa CAD del plano  ->  (capa de salida, simplificacion en metros)
# Lo que no está aquí no se publica: rótulo, tablas, logos, cuadrícula, textos.
MAPEO = {
    'ACAD-TOP-BASE PRESA POROTOG-Model|TOP-AREA PROTEGIDA CAYAMBE COCA':
        ('area_protegida', 0.5),
    'ACAD-TOP-BASE PRESA POROTOG-Model|TOP-RIO': ('hidrografia', 0.3),
    'ACAD-TOP-BASE PRESA POROTOG-Model|TOP-CANAL': ('hidrografia', 0.3),
    'ACAD-TOP-BASE PRESA POROTOG-Model|TOP-PANTANO': ('hidrografia', 0.3),
    'ACAD-TOP-BASE PRESA POROTOG-Model|TOP-CAMINO': ('vialidad', 0.3),
    'ACAD-TOP-BASE PRESA POROTOG-Model|TOP-DERECHO DE PASO TUBERIA':
        ('tuberia', 0.3),
    'ACAD-TOP-BASE PRESA POROTOG-Model|TOP-TUBERIA 3P': ('tuberia', 0.3),
    'ACAD-TOP-BASE PRESA POROTOG-Model|C3D-Superficie_ConMay': ('curvas_5m', 0.4),
    'ACAD-TOP-BASE PRESA POROTOG-Model|C3D-Superficie_ConMen': ('curvas_1m', 0.4),
    'ACAD-TOP-BASE PRESA POROTOG-Model|TOP-GPS': ('control_gnss', 0.0),
    'TOP-GNSS': ('control_gnss', 0.0),
    'TOP-GPS': ('control_gnss', 0.0),
    '01-01-CAPTACION$0$CA-0.05': ('obras', 0.1),
    '01-01-CAPTACION$0$CA-0.05a': ('obras', 0.1),
    '01-01-CAPTACION$0$CA-0.05b': ('obras', 0.1),
    '01-01-CAPTACION$0$CH-0.10a': ('obras', 0.1),
    '01-01-CAPTACION$0$0.05a': ('obras', 0.1),
    '03-01-TANQUE$0$CH-0.05': ('obras', 0.1),
    '03-01-TANQUE$0$CH-0.10a': ('obras', 0.1),
    '03-01-TANQUE$0$CA-Hatch': ('obras', 0.1),
    '04-01-CANAL$0$CH-0.10a': ('obras', 0.1),
    '04-01-CANAL$0$CA-Hatch': ('obras', 0.1),
    '05-01-VERTEDERO$0$CA-0.05': ('obras', 0.1),
    '05-01-VERTEDERO$0$CA-Hatch': ('obras', 0.1),
    'C3D-Eje Horizontal': ('ejes', 0.2),
    'C3D-Volumen': ('limite_dibujado', 0.1),
}

# La capa `C3D-Eje Horizontal` mezcla dos cosas distintas bajo el mismo nombre:
# en magenta está el sombreado de los BANCOS DE MATERIALES y en negro los ejes
# de replanteo. Se separan por color, que es lo único que las distingue.
COLOR_BANCOS = '#FF00FF'

# Rótulos que nombran obras puntuales; se publican como capa de puntos porque
# es lo que hace legible el mapa (el dibujo por sí solo no dice qué es cada cosa)
ROTULOS_OBRA = [
    'Captación', 'Inicio Túnel', 'Fin Túnel', 'Tanque Disipador', 'Canal',
    'Rápida', 'Disipador', 'Vertedero de Excesos', 'EJE DE PRESA',
    'BANCO DE MATERIALES 1', 'BANCO DE MATERIALES 2', 'BANCO DE MATERIALES 3',
    'LIMITE DE PROYECTO', 'RÍO POROTOG', 'PANTANO', 'CANAL',
]

# Rótulos del plano que sirven para nombrar los polígonos rojos
ROTULOS = ['LIMITE DE PROYECTO', 'BANCO DE MATERIALES 1', 'BANCO DE MATERIALES 2',
           'BANCO DE MATERIALES 3', 'EJE DE PRESA', 'LIMITE DE AREA PROTEGIDA',
           'PARQUE NACIONAL CAYAMBE COCA']

# Tabla del consorcio con el vértice 23 CORREGIDO (ver 03_georreferenciar.py)
from importlib import util as _util                                    # noqa: E402
_spec = _util.spec_from_file_location(
    'geo3', os.path.join(os.path.dirname(__file__), '03_georreferenciar.py'))
_g3 = _util.module_from_spec(_spec)
_spec.loader.exec_module(_g3)
TABLA = dict(_g3.TABLA)


def cargar_transformacion():
    """
    Devuelve los parámetros del ajuste y, de paso, corrige en TABLA el vértice
    23 con la coordenada deducida del dibujo. La tabla del consorcio lo sitúa a
    2,5 km de donde está: publicar el límite con ese valor daría un polígono
    cruzado consigo mismo y 300.000 m² de menos.
    """
    with open(GEORREF, encoding='utf-8') as f:
        g = json.load(f)
    d = g.get('vertice_23_deducido')
    if d:
        TABLA[g['vertice_erroneo_en_tabla']] = (d['norte'], d['este'])
    else:
        print("  AVISO: no hay coordenada deducida para el vertice 23; se usa la")
        print("         tabla tal cual y el limite saldra mal. Revisa el paso 3.")
    p = g['parametros']
    return (p['a'], p['b'], p['tx'], p['ty']), g


def a_utm(par, x, y):
    a, b, tx, ty = par
    return (a * x - b * y + tx, b * x + a * y + ty)


def partes(geo):
    """
    Devuelve las líneas de una geometría, sea MULTILINESTRING o LINESTRING.

    Hace falta porque SimplifyPreserveTopology colapsa un multi de una sola
    parte a LINESTRING, y sobre un LINESTRING GetGeometryCount() vale 0: sin
    esto, todo lo simplificado se recorre en vacío y desaparece en silencio.
    """
    if geo is None or geo.IsEmpty():
        return []
    if geo.GetGeometryName() == 'LINESTRING':
        return [geo]
    return [geo.GetGeometryRef(i) for i in range(geo.GetGeometryCount())]


def transformar_geom(geo, par):
    """Copia la geometría llevando cada vértice de página a UTM."""
    salida = ogr.Geometry(ogr.wkbMultiLineString)
    for ln in partes(geo):
        nueva = ogr.Geometry(ogr.wkbLineString)
        for j in range(ln.GetPointCount()):
            x, y, *_ = ln.GetPoint(j)
            nueva.AddPoint_2D(*a_utm(par, x, y))
        salida.AddGeometry(nueva)
    return salida


def leer_rotulos(par):
    """Textos del plano ya en UTM: {texto: (E, N)} y lista completa."""
    ds = ogr.Open(GPKG_PLANO, 0)
    capa = ds.GetLayerByName('textos')
    todos = []
    for ft in capa:
        t = (ft.GetField('texto') or '').strip()
        g = ft.GetGeometryRef()
        if not t or (abs(g.GetX()) < 1e-6 and abs(g.GetY()) < 1e-6):
            continue
        todos.append((t, a_utm(par, g.GetX(), g.GetY())))
    ds = None
    return todos


def poligono_limite():
    """Límite de proyecto desde la tabla oficial, con el 23 corregido."""
    anillo = ogr.Geometry(ogr.wkbLinearRing)
    for o in sorted(TABLA):
        N, E = TABLA[o]
        anillo.AddPoint_2D(E, N)
    anillo.CloseRings()
    poli = ogr.Geometry(ogr.wkbPolygon)
    poli.AddGeometry(anillo)
    return poli


def validar_contra_curvas_5m(capas_utm):
    """
    Comprobación independiente: las curvas «mayores» del levantamiento (cota
    múltiplo de 5) tienen que caer sobre las curvas de 5 m regionales.
    """
    print("\n  [validacion independiente] curvas del plano vs curvas de 5 m")
    if not os.path.exists(CURVAS_5M):
        print("      falta {}; se omite.".format(os.path.basename(CURVAS_5M)))
        return None
    mayores = capas_utm.get('curvas_5m') or []
    if not mayores:
        print("      el plano no aporto curvas mayores; se omite.")
        return None

    ds = ogr.Open(CURVAS_5M, 0)
    capa = ds.GetLayer(0)
    ref = ogr.Geometry(ogr.wkbMultiLineString)
    for ft in capa:
        g = ft.GetGeometryRef()
        for i in range(g.GetGeometryCount()):
            ref.AddGeometry(g.GetGeometryRef(i).Clone())

    distancias = []
    for geo, _ in mayores:
        for ln in partes(geo):
            n = ln.GetPointCount()
            if n < 2:
                continue
            for j in range(0, n, max(1, n // 6)):       # muestreo
                x, y, *_ = ln.GetPoint(j)
                p = ogr.Geometry(ogr.wkbPoint)
                p.AddPoint_2D(x, y)
                distancias.append(p.Distance(ref))
    ds = None

    if not distancias:
        print("      sin puntos que comparar; se omite.")
        return None

    distancias.sort()
    n = len(distancias)
    mediana = distancias[n // 2]
    p90 = distancias[int(n * 0.9)]
    print("      puntos comparados : {:,}".format(n))
    print("      distancia mediana : {:.1f} m".format(mediana))
    print("      percentil 90      : {:.1f} m".format(p90))
    if mediana < 25:
        print("      -> las dos cartografias coinciden en el terreno: la")
        print("         georreferenciacion cae donde debe. (No dan cero porque")
        print("         son fuentes distintas: levantamiento propio a 1 m contra")
        print("         cartografia regional a 5 m.)")
    else:
        print("      -> ATENCION: se separan demasiado. Revisar antes de publicar.")
    return {'mediana_m': round(mediana, 2), 'p90_m': round(p90, 2), 'puntos': n}


def main():
    print("=" * 74)
    print(" CAPAS GEORREFERENCIADAS DE LA REPRESA")
    print("=" * 74)

    for f in (GPKG_PLANO, GEORREF):
        if not os.path.exists(f):
            print("ERROR: falta {}".format(f))
            return 1

    par, meta = cargar_transformacion()
    print("\n  transformacion: RMS {:.3f} m, escala 1:{:,.0f}, rotacion {:+.3f} grados"
          .format(meta['rms_m'], meta['escala_m_por_unidad'] * 72 / 0.0254,
                  meta['rotacion_grados']))

    # ── transformar los trazos publicables ──
    ds = ogr.Open(GPKG_PLANO, 0)
    capa = ds.GetLayerByName('trazos')
    capas_utm = {}
    for ft in capa:
        ocg = ft.GetField('ocg') or ''
        if ocg not in MAPEO:
            continue
        destino, tol = MAPEO[ocg]
        if ocg == 'C3D-Eje Horizontal':
            destino = ('bancos_materiales'
                       if (ft.GetField('color') or '') == COLOR_BANCOS else 'ejes')
        geo = transformar_geom(ft.GetGeometryRef(), par)
        if tol:
            geo = geo.SimplifyPreserveTopology(tol)
        if geo is None or geo.IsEmpty():
            continue
        capas_utm.setdefault(destino, []).append(
            (geo, {'capa_cad': ocg, 'color': ft.GetField('color') or ''}))
    ds = None

    print("\n  capas obtenidas del plano:")
    for nombre in sorted(capas_utm):
        print("      {:22s} {:,} elementos".format(nombre, len(capas_utm[nombre])))

    # ── rótulos del plano, ya en UTM ──
    rotulos = leer_rotulos(par)
    obras_pt = [(t, p) for t, p in rotulos if t in ROTULOS_OBRA]
    print("\n  rotulos de obra georreferenciados: {}".format(len(obras_pt)))

    # ── superficie de cada banco de materiales ──
    # El plano dibuja los bancos como sombreado hexagonal, no como polígono: no
    # hay un contorno que extraer. Para poder medirlos se agrupa el sombreado
    # por cercanía a su rótulo y se toma la envolvente convexa del grupo. Es una
    # ESTIMACIÓN de la superficie, no el polígono topográfico del consorcio.
    bancos = [(t, p) for t, p in obras_pt if t.startswith('BANCO')]
    poligonos_banco = []
    if bancos and 'bancos_materiales' in capas_utm:
        grupos = {t: ogr.Geometry(ogr.wkbMultiPoint) for t, _ in bancos}
        for geo, _ in capas_utm['bancos_materiales']:
            for ln in partes(geo):
                x, y, *_ = ln.GetPoint(0)
                cual = min(bancos, key=lambda b: math.hypot(b[1][0] - x, b[1][1] - y))
                if math.hypot(cual[1][0] - x, cual[1][1] - y) > 500:
                    continue
                for j in range(ln.GetPointCount()):
                    px, py, *_ = ln.GetPoint(j)
                    p = ogr.Geometry(ogr.wkbPoint)
                    p.AddPoint_2D(px, py)
                    grupos[cual[0]].AddGeometry(p)
        print("  bancos de materiales (envolvente del sombreado):")
        for t, _ in bancos:
            if grupos[t].GetGeometryCount() < 3:
                continue
            env = grupos[t].ConvexHull()
            ha = abs(env.GetArea()) / 10000.0
            poligonos_banco.append((env, {'nombre': t, 'area_ha': round(ha, 3),
                                          'nota': 'superficie estimada por '
                                                  'envolvente del sombreado'}))
            print("      {:24s} {:7.2f} ha".format(t, ha))

    validacion = validar_contra_curvas_5m(capas_utm)

    # ── el límite de proyecto, desde la tabla oficial ──
    limite = poligono_limite()
    print("\n  limite de proyecto (tabla oficial, vertice 23 corregido)")
    print("      area: {:,.3f} m2  =  {:.3f} ha"
          .format(abs(limite.GetArea()), abs(limite.GetArea()) / 10000))

    # ── escribir ──
    os.makedirs(WEB, exist_ok=True)
    utm = osr.SpatialReference(); utm.ImportFromEPSG(32717)
    wgs = osr.SpatialReference(); wgs.ImportFromEPSG(4326)
    utm.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    wgs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    a_wgs = osr.CoordinateTransformation(utm, wgs)

    drv_g = ogr.GetDriverByName('GPKG')
    if os.path.exists(GPKG_SALIDA):
        drv_g.DeleteDataSource(GPKG_SALIDA)
    ds_utm = drv_g.CreateDataSource(GPKG_SALIDA)
    drv_j = ogr.GetDriverByName('GeoJSON')

    def escribir(nombre, elementos, tipo, campos):
        cap = ds_utm.CreateLayer(nombre, srs=utm, geom_type=tipo)
        for c in campos:
            cap.CreateField(ogr.FieldDefn(c, ogr.OFTString if c != 'area_ha'
                                          else ogr.OFTReal))
        defn = cap.GetLayerDefn()
        ruta = os.path.join(WEB, nombre + '.geojson')
        if os.path.exists(ruta):
            os.remove(ruta)
        ds_web = drv_j.CreateDataSource(ruta)
        cap_web = ds_web.CreateLayer(nombre, srs=wgs, geom_type=tipo)
        for c in campos:
            cap_web.CreateField(ogr.FieldDefn(c, ogr.OFTString if c != 'area_ha'
                                              else ogr.OFTReal))
        defn_web = cap_web.GetLayerDefn()

        for geo, props in elementos:
            for d, g2 in ((defn, geo.Clone()), (defn_web, geo.Clone())):
                if d is defn_web:
                    g2.Transform(a_wgs)
                ft = ogr.Feature(d)
                for c in campos:
                    if c in props:
                        ft.SetField(c, props[c])
                ft.SetGeometry(g2)
                (cap if d is defn else cap_web).CreateFeature(ft)
                ft = None
        ds_web = None
        return ruta

    print("\n  archivos para la web:")
    total = 0

    # puntos de obra rotulados
    pts = []
    for t, (E, N) in obras_pt:
        p = ogr.Geometry(ogr.wkbPoint)
        p.AddPoint_2D(E, N)
        pts.append((p, {'nombre': t, 'fuente': 'rotulo del plano 1000'}))
    escribir('rotulos_obra', pts, ogr.wkbPoint, ['nombre', 'fuente'])

    if poligonos_banco:
        escribir('bancos_superficie', poligonos_banco, ogr.wkbPolygon,
                 ['nombre', 'area_ha', 'nota'])

    escribir('limite_proyecto', [(limite, {
        'nombre': 'LIMITE DE PROYECTO',
        'fuente': 'tabla de coordenadas del plano CCSPT-GEN-AMB-PL-DT-1000-R1',
        'nota': 'vertice 23 corregido: la tabla del consorcio lo situa a 2,5 km',
        'area_ha': round(abs(limite.GetArea()) / 10000, 3),
    })], ogr.wkbPolygon, ['nombre', 'fuente', 'nota', 'area_ha'])

    for nombre in sorted(capas_utm):
        ruta = escribir(nombre, capas_utm[nombre], ogr.wkbMultiLineString,
                        ['capa_cad', 'color', 'nombre', 'area_ha'])
        kb = os.path.getsize(ruta) / 1024
        total += kb
        print("      {:22s} {:8,.0f} KB".format(nombre + '.geojson', kb))
    kb = os.path.getsize(os.path.join(WEB, 'limite_proyecto.geojson')) / 1024
    total += kb
    print("      {:22s} {:8,.0f} KB".format('limite_proyecto.geojson', kb))
    print("      {:22s} {:8,.0f} KB".format('TOTAL', total))

    ds_utm = None
    with open(os.path.join(PROCESADO, 'validacion.json'), 'w', encoding='utf-8') as f:
        json.dump({'rms_georreferenciacion_m': meta['rms_m'],
                   'escala_ajustada': meta['escala_m_por_unidad'] * 72 / 0.0254,
                   'contraste_curvas_5m': validacion}, f, indent=2)

    print("\n  QGIS: {}".format(os.path.relpath(GPKG_SALIDA, RAIZ)))
    print("=" * 74)
    return 0


if __name__ == '__main__':
    sys.exit(main())
