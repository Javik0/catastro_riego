# -*- coding: utf-8 -*-
"""
Modelo digital del terreno de la zona de la represa (DEM híbrido) y malla 3D.

El problema de las cotas
------------------------
Hay dos cartografías y cada una tiene la mitad de lo que hace falta:

* Las curvas de 5 m regionales (`curvas_5m_zona.gpkg`) traen el campo `ELEV`:
  saben a qué altura está cada curva, pero son de todo el cantón y su detalle es
  el que es.
* Las curvas del levantamiento del consorcio (del plano, equidistancia 1 m) son
  mucho más precisas en la zona de obra, pero NO traen la cota: en el plano la
  altura está escrita al lado de cada curva, y AutoCAD vectorizó esos rótulos
  (fuente SHX), así que no hay ningún texto que leer.

Cómo se resuelve
----------------
Se le pregunta la cota a la cartografía que sí la tiene:

1. Con las curvas de 5 m se interpola un DEM base por triangulación (TIN).
2. A cada curva del levantamiento se le muestrea ese DEM a lo largo de todo su
   recorrido. Como una curva de nivel tiene UNA sola altura, la mediana de esas
   muestras es su cota, y la dispersión dice si la asignación es de fiar: una
   curva bien asignada varía poco; una que cruza terreno de todo tipo (porque el
   trazo no era en realidad una curva de nivel) varía mucho y se descarta.
3. Las curvas que superan la prueba se suman a la nube de puntos y se interpola
   el DEM definitivo: el levantamiento manda donde existe, las regionales
   rellenan alrededor. Eso es el «híbrido».

Además se mide el DESFASE VERTICAL entre ambas fuentes. Si las dos midieran la
altura desde referencias distintas, el terreno tendría un escalón en el borde de
la zona levantada; el informe lo dice explícitamente.

Salidas
-------
CARTOGRAFIA REPRESA/procesado/dem_represa.tif   GeoTIFF UTM 17S, para QGIS (vista 3D nativa)
padron-app/public/geo/represa/terreno.json      malla de alturas para el visor 3D web
padron-app/public/geo/represa/curvas_cota.geojson  curvas del levantamiento CON cota
"""
import json
import math
import os
import statistics
import sys

from osgeo import gdal, ogr, osr

gdal.UseExceptions()
ogr.UseExceptions()
osr.UseExceptions()

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
RAIZ = os.path.abspath(os.path.join(BASE, '..'))
PROCESADO = os.path.join(RAIZ, 'CARTOGRAFIA REPRESA', 'procesado')
CURVAS_5M = os.path.join(PROCESADO, 'curvas_5m_zona.gpkg')
REPRESA_UTM = os.path.join(PROCESADO, 'represa_utm.gpkg')
DEM_BASE = os.path.join(PROCESADO, 'dem_base_5m.tif')
DEM_FINAL = os.path.join(PROCESADO, 'dem_represa.tif')
WEB = os.path.join(BASE, 'public', 'geo', 'represa')

MARGEN = 600.0        # m alrededor del límite de proyecto
RES = 2.0             # m por píxel del DEM final
PASO_MUESTREO = 8.0   # m entre muestras a lo largo de cada curva
MALLA_3D = 320        # lado de la malla que se manda al visor web

# Criterio para dar por buena la cota de una curva del levantamiento.
#
# Filtrar por la dispersión bruta de las muestras era el criterio equivocado:
# las dos cartografías difieren 3,4 m en planta y en ladera eso se traduce en
# varios metros de altura, así que la dispersión de una curva perfectamente
# válida ronda los 4-10 m. Descartando por ahí sobrevivían 87 de 575.
#
# Lo que decide es la precisión de la MEDIANA, que mejora con el número de
# muestras (error tipico = dispersion / raiz(n)): con 100 muestras y 6 m de
# dispersión, la mediana queda determinada a ~0,6 m. Y hay una restricción que
# ayuda mucho más: la cota no es un número cualquiera. Las curvas «mayores» del
# levantamiento son múltiplos de 5 y las «menores» van de metro en metro, así
# que basta con que la mediana caiga inequívocamente cerca de uno de esos
# valores. Si cae a mitad de camino entre dos, la curva se descarta: no se
# inventa una cota que no se puede determinar.
ERROR_MAX_MAYOR = 1.2   # m de error tipico admisible en curvas de 5 en 5
ERROR_MAX_MENOR = 0.45  # m; mucho mas exigente porque el paso es de 1 m
AMBIGUEDAD_MAX = 0.35   # fraccion del paso: mas lejos del valor valido = dudosa
MUESTRAS_MIN = 12
LARGO_MIN = 60.0        # m; los trazos cortos no son curvas utiles, solo ruido


def bbox_proyecto():
    """Extensión del límite de proyecto más un margen."""
    ds = ogr.Open(REPRESA_UTM, 0)
    capa = ds.GetLayerByName('limite_proyecto')
    x0, x1, y0, y1 = capa.GetExtent()
    ds = None
    return (x0 - MARGEN, y0 - MARGEN, x1 + MARGEN, y1 + MARGEN)


def puntos_de_curvas_5m(bbox):
    """Nube de puntos (E, N, cota) de las curvas regionales, submuestreada."""
    ds = ogr.Open(CURVAS_5M, 0)
    capa = ds.GetLayer(0)
    capa.SetSpatialFilterRect(*bbox)
    pts = []
    for ft in capa:
        cota = ft.GetField('cota')
        g = ft.GetGeometryRef()
        for i in range(g.GetGeometryCount() or 1):
            ln = g.GetGeometryRef(i) if g.GetGeometryCount() else g
            n = ln.GetPointCount()
            acumulado, ultimo = PASO_MUESTREO, None
            for j in range(n):
                x, y, *_ = ln.GetPoint(j)
                if ultimo is not None:
                    acumulado += math.dist((x, y), ultimo)
                ultimo = (x, y)
                if acumulado >= PASO_MUESTREO:
                    pts.append((x, y, cota))
                    acumulado = 0.0
    ds = None
    return pts


def interpolar(pts, bbox, res, destino, algoritmo='linear'):
    """Nube de puntos -> raster, por triangulación de Delaunay."""
    mem = ogr.GetDriverByName('Memory').CreateDataSource('nube')
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(32717)
    capa = mem.CreateLayer('p', srs=srs, geom_type=ogr.wkbPoint25D)
    capa.CreateField(ogr.FieldDefn('z', ogr.OFTReal))
    defn = capa.GetLayerDefn()
    for x, y, z in pts:
        ft = ogr.Feature(defn)
        ft.SetField('z', float(z))
        g = ogr.Geometry(ogr.wkbPoint25D)
        g.AddPoint(x, y, float(z))
        ft.SetGeometry(g)
        capa.CreateFeature(ft)
        ft = None

    x0, y0, x1, y1 = bbox
    ancho = int((x1 - x0) / res)
    alto = int((y1 - y0) / res)
    gdal.Grid(destino, mem, options=gdal.GridOptions(
        format='GTiff', outputType=gdal.GDT_Float32,
        algorithm='{}:radius=0.0:nodata=-9999'.format(algoritmo),
        zfield='z', outputBounds=[x0, y1, x1, y0],
        width=ancho, height=alto,
        creationOptions=['COMPRESS=DEFLATE', 'TILED=YES']))
    mem = None
    return ancho, alto


def muestrear(ds, gt, banda, x, y):
    """Valor del raster en una coordenada UTM (None si cae fuera o es nodata)."""
    px = int((x - gt[0]) / gt[1])
    py = int((y - gt[3]) / gt[5])
    if px < 0 or py < 0 or px >= ds.RasterXSize or py >= ds.RasterYSize:
        return None
    v = banda.ReadAsArray(px, py, 1, 1)
    if v is None:
        return None
    v = float(v[0][0])
    return None if v <= -9998 else v


def partes(geo):
    """Líneas de una geometría, sea MULTILINESTRING o LINESTRING."""
    if geo is None or geo.IsEmpty():
        return []
    if geo.GetGeometryName() == 'LINESTRING':
        return [geo]
    return [geo.GetGeometryRef(i) for i in range(geo.GetGeometryCount())]


def cotas_del_levantamiento(bbox):
    """
    Asigna cota a cada curva del levantamiento leyéndola del DEM base.

    CADA SUBTRAZO ES UNA CURVA DISTINTA. El PDF pinta decenas de curvas de nivel
    en una sola operación de dibujo, así que un «elemento» del plano puede
    contener 40 curvas de cotas distintas. Medirlas juntas da una dispersión
    enorme y las descarta todas (en la primera versión de esto sobrevivían 44 de
    575). Hay que separar por subtrazo antes de medir.

    Devuelve (curvas_con_cota, descartadas, desfases).
    """
    ds_dem = gdal.Open(DEM_BASE)
    gt = ds_dem.GetGeoTransform()
    banda = ds_dem.GetRasterBand(1)

    ds = ogr.Open(REPRESA_UTM, 0)
    buenas, descartadas, desfases, histograma = [], 0, [], []

    for nombre in ('curvas_5m', 'curvas_1m'):
        capa = ds.GetLayerByName(nombre)
        if capa is None:
            continue
        for ft in capa:
            for ln in partes(ft.GetGeometryRef()):
                if ln.Length() < LARGO_MIN:
                    descartadas += 1
                    continue
                muestras, puntos = [], []
                n = ln.GetPointCount()
                acumulado, ultimo = PASO_MUESTREO, None
                for j in range(n):
                    x, y, *_ = ln.GetPoint(j)
                    if ultimo is not None:
                        acumulado += math.dist((x, y), ultimo)
                    ultimo = (x, y)
                    if acumulado >= PASO_MUESTREO:
                        acumulado = 0.0
                        v = muestrear(ds_dem, gt, banda, x, y)
                        if v is not None:
                            muestras.append(v)
                            puntos.append((x, y))
                if len(muestras) < MUESTRAS_MIN:
                    descartadas += 1
                    continue
                mediana = statistics.median(muestras)
                disp = statistics.pstdev(muestras)
                error = disp / math.sqrt(len(muestras))

                # las «mayores» del levantamiento son multiplos de 5; las
                # «menores», metros enteros
                es_mayor = (nombre == 'curvas_5m')
                paso = 5 if es_mayor else 1
                tope = ERROR_MAX_MAYOR if es_mayor else ERROR_MAX_MENOR

                cota = round(mediana / paso) * paso
                ambiguedad = abs(mediana - cota) / paso
                histograma.append((error, ambiguedad, es_mayor))

                if error > tope or ambiguedad > AMBIGUEDAD_MAX:
                    descartadas += 1
                    continue
                desfases.append(mediana - cota)
                buenas.append((cota, puntos, error, nombre))

    ds = None
    ds_dem = None
    return buenas, descartadas, desfases, histograma


def escribir_curvas_cota(buenas):
    """GeoJSON de las curvas del levantamiento, ya con su cota."""
    utm = osr.SpatialReference(); utm.ImportFromEPSG(32717)
    wgs = osr.SpatialReference(); wgs.ImportFromEPSG(4326)
    utm.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    wgs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    tr = osr.CoordinateTransformation(utm, wgs)

    ruta = os.path.join(WEB, 'curvas_cota.geojson')
    if os.path.exists(ruta):
        os.remove(ruta)
    ds = ogr.GetDriverByName('GeoJSON').CreateDataSource(ruta)
    capa = ds.CreateLayer('curvas_cota', srs=wgs, geom_type=ogr.wkbLineString)
    capa.CreateField(ogr.FieldDefn('cota', ogr.OFTInteger))
    capa.CreateField(ogr.FieldDefn('indice', ogr.OFTInteger))   # múltiplo de 5
    defn = capa.GetLayerDefn()
    for cota, puntos, _, _ in buenas:
        if len(puntos) < 2:
            continue
        ln = ogr.Geometry(ogr.wkbLineString)
        for x, y in puntos:
            ln.AddPoint_2D(x, y)
        ln.Transform(tr)
        ft = ogr.Feature(defn)
        ft.SetField('cota', int(cota))
        ft.SetField('indice', 1 if cota % 5 == 0 else 0)
        ft.SetGeometry(ln)
        capa.CreateFeature(ft)
        ft = None
    ds = None
    return ruta


def malla_para_web(bbox):
    """
    Malla de alturas para el visor 3D.

    Se manda un JSON con la rejilla en crudo en vez de un PNG codificado: el
    navegador no tiene que decodificar imagen ni interpretar ningún esquema de
    bits, y a esta resolución pesa poco. Las alturas van en decímetros enteros
    (precisión 10 cm, de sobra para visualizar el relieve) para que el JSON no
    se llene de decimales.
    """
    ds = gdal.Open(DEM_FINAL)
    x0, y0, x1, y1 = bbox
    lado_x, lado_y = x1 - x0, y1 - y0
    nx = MALLA_3D
    ny = max(2, int(round(MALLA_3D * lado_y / lado_x)))

    remuestreo = gdal.Warp('', ds, options=gdal.WarpOptions(
        format='MEM', width=nx, height=ny, resampleAlg='cubic',
        outputBounds=[x0, y0, x1, y1], dstNodata=-9999))
    arr = remuestreo.GetRasterBand(1).ReadAsArray()

    validos = [float(v) for fila in arr for v in fila if v > -9998]
    if not validos:
        return None
    zmin, zmax = min(validos), max(validos)

    alturas = []
    for fila in arr:
        for v in fila:
            v = float(v)
            alturas.append(-32768 if v <= -9998 else int(round(v * 10)))

    utm = osr.SpatialReference(); utm.ImportFromEPSG(32717)
    wgs = osr.SpatialReference(); wgs.ImportFromEPSG(4326)
    utm.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    wgs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    tr = osr.CoordinateTransformation(utm, wgs)
    (oe, on, _), (ee, en, _) = tr.TransformPoint(x0, y0), tr.TransformPoint(x1, y1)

    datos = {
        'crs_datos': 'EPSG:32717',
        'nx': nx, 'ny': ny,
        'bbox_utm': [x0, y0, x1, y1],
        'bbox_wgs84': [oe, on, ee, en],
        'ancho_m': round(lado_x, 1), 'alto_m': round(lado_y, 1),
        'cota_min': round(zmin, 2), 'cota_max': round(zmax, 2),
        'unidad': 'decimetros enteros; -32768 = sin dato',
        'alturas': alturas,
    }
    ruta = os.path.join(WEB, 'terreno.json')
    with open(ruta, 'w', encoding='utf-8') as f:
        json.dump(datos, f, separators=(',', ':'))
    return ruta, nx, ny, zmin, zmax


def main():
    print("=" * 74)
    print(" MODELO DIGITAL DEL TERRENO - ZONA REPRESA POROTOG")
    print("=" * 74)

    for f in (CURVAS_5M, REPRESA_UTM):
        if not os.path.exists(f):
            print("ERROR: falta {}".format(f))
            return 1
    os.makedirs(WEB, exist_ok=True)

    bbox = bbox_proyecto()
    print("\n  area de trabajo: {:.2f} x {:.2f} km (limite de proyecto + {:.0f} m)"
          .format((bbox[2] - bbox[0]) / 1000, (bbox[3] - bbox[1]) / 1000, MARGEN))

    # ── 1. DEM base con las curvas regionales ──
    print("\n  [1] DEM base con las curvas de 5 m (las que traen cota)")
    pts = puntos_de_curvas_5m(bbox)
    if len(pts) < 100:
        print("      ERROR: solo {} puntos; insuficiente.".format(len(pts)))
        return 1
    cotas = [p[2] for p in pts]
    print("      puntos de apoyo : {:,}".format(len(pts)))
    print("      rango de cotas  : {:,.0f} a {:,.0f} m".format(min(cotas), max(cotas)))
    ancho, alto = interpolar(pts, bbox, 5.0, DEM_BASE)
    print("      raster base     : {} x {} px a 5 m".format(ancho, alto))

    # ── 2. cota de las curvas del levantamiento ──
    print("\n  [2] Cota de las curvas del levantamiento (leida del DEM base)")
    buenas, descartadas, desfases, histograma = cotas_del_levantamiento(bbox)
    mayores = [c for c in buenas if c[3] == 'curvas_5m']
    menores = [c for c in buenas if c[3] != 'curvas_5m']
    print("      curvas con cota fiable : {:,}  ({} de 5 en 5, {} de metro en metro)"
          .format(len(buenas), len(mayores), len(menores)))
    print("      descartadas            : {:,}".format(descartadas))
    if histograma:
        print("      reparto del error tipico de la mediana:")
        rangos = [(0, 0.45), (0.45, 1.2), (1.2, 2.5), (2.5, 1e9)]
        etqs = ["< 0,45 m  (sirve hasta para curvas de 1 m)",
                "0,45-1,2  (sirve para las de 5 en 5)",
                "1,2-2,5   (no determina la cota)",
                "> 2,5 m   (inservible)"]
        for (lo, hi), etq in zip(rangos, etqs):
            n = sum(1 for e, _, _ in histograma if lo <= e < hi)
            if not n:
                continue
            print("        {:4d}  {}  {}".format(
                n, '#' * max(1, int(30.0 * n / len(histograma))), etq))
        amb = sum(1 for e, a, _ in histograma if a > AMBIGUEDAD_MAX)
        print("      con la cota a medio camino entre dos validas: {}".format(amb))
    if buenas:
        cs = sorted(c for c, _, _, _ in buenas)
        print("      rango de cotas         : {:,} a {:,} m".format(cs[0], cs[-1]))
        print("      niveles distintos      : {}".format(len(set(cs))))
        print("      error tipico mediano   : {:.2f} m"
              .format(statistics.median(d for _, _, d, _ in buenas)))

    # ── 3. coherencia de las cotas asignadas ──
    # OJO con lo que este numero significa y lo que NO significa. La cota del
    # levantamiento se está leyendo del DEM regional, así que comparar ambas
    # fuentes aquí sería circular: esto NO verifica que las dos midan la altura
    # desde la misma referencia. Eso no es verificable con lo que hay — haría
    # falta un dato de cota del propio levantamiento, y en el PDF los rótulos de
    # cota están vectorizados. Lo que sí mide es si las curvas caen limpiamente
    # sobre valores redondos, que es señal de que la asignación es coherente.
    print("\n  [3] Coherencia de las cotas asignadas")
    if desfases:
        med = statistics.median(desfases)
        print("      resto mediano frente al valor redondo : {:+.2f} m".format(med))
        print("      (no es una verificacion de datum vertical: la cota se")
        print("       deduce del propio DEM regional, comparar ambos seria")
        print("       circular. El datum del levantamiento no es verificable")
        print("       con estos datos.)")
    else:
        print("      sin datos suficientes para estimarlo.")

    # ── 4. DEM híbrido ──
    print("\n  [4] DEM hibrido (levantamiento donde existe, regional alrededor)")
    nube = list(pts)
    añadidos = 0
    for cota, puntos, _, _ in buenas:
        for x, y in puntos:
            nube.append((x, y, cota))
            añadidos += 1
    print("      puntos regionales    : {:,}".format(len(pts)))
    print("      puntos levantamiento : {:,}".format(añadidos))
    print("      NOTA: la resolucion vertical del modelo es la de la cartografia")
    print("            regional (5 m). Las curvas de 1 m del levantamiento no se")
    print("            pueden aprovechar: su cota no figura como texto en el PDF")
    print("            y el DEM regional no da para determinarla de metro en")
    print("            metro. Para un modelo con precision de obra hay que pedir")
    print("            al consorcio la superficie de Civil 3D (LandXML o raster).")
    ancho, alto = interpolar(nube, bbox, RES, DEM_FINAL)
    print("      raster final         : {} x {} px a {:.0f} m  ({:.1f} MB)"
          .format(ancho, alto, RES, os.path.getsize(DEM_FINAL) / 1e6))

    ruta = escribir_curvas_cota(buenas)
    print("\n      curvas con cota -> {} ({:.0f} KB)"
          .format(os.path.basename(ruta), os.path.getsize(ruta) / 1024))

    # ── 5. malla para el visor 3D ──
    print("\n  [5] Malla para el visor 3D de la web")
    r = malla_para_web(bbox)
    if r:
        ruta, nx, ny, zmin, zmax = r
        print("      malla    : {} x {} vertices".format(nx, ny))
        print("      cotas    : {:,.1f} a {:,.1f} m (desnivel {:,.0f} m)"
              .format(zmin, zmax, zmax - zmin))
        print("      archivo  : {} ({:.0f} KB)"
              .format(os.path.basename(ruta), os.path.getsize(ruta) / 1024))
    else:
        print("      ERROR: no se pudo generar la malla.")
        return 1

    print("\n  QGIS: abre {} y activa la vista 3D"
          .format(os.path.relpath(DEM_FINAL, RAIZ)))
    print("=" * 74)
    return 0


if __name__ == '__main__':
    sys.exit(main())
