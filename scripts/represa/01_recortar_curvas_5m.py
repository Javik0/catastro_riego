# -*- coding: utf-8 -*-
"""
Recorte de las curvas de nivel de 5 m a la zona de la represa de Porotog.

Por qué existe este script
--------------------------
La capa `PROYECTOAGUACANGAHUACATASTROCURVASNIVEL5M.gpkg` cubre TODO el cantón
Cayambe: 7.878 curvas, 68 MB, de la cota 1.990 a la 5.755. Para la zona de la
represa sobran: en un cuadro de 4 x 4 km alrededor del eje de presa hay 153
curvas y pesa 800 KB. Servir los 68 MB a la web sería absurdo, y el recorte
además es el insumo del modelo de terreno.

Dos reglas duras que este script respeta
----------------------------------------
1. **El archivo de origen vive dentro de la carpeta de QFieldCloud.** Se abre
   en SOLO LECTURA y jamás se escribe nada ahí: todo lo que quede dentro de esa
   carpeta QFieldSync se lo lleva a las tablets de los técnicos. La salida se
   escribe fuera, y el script aborta si alguien cambia la ruta de salida a un
   sitio dentro de QField.
2. **No se modifica el GPKG original.** Si algún día conviene aligerar el
   proyecto de campo reemplazando la capa por este recorte, es un cambio
   deliberado con QFieldSync y ventana coordinada, no un efecto colateral.

De dónde salen estas curvas
---------------------------
Son cartografía regional (equidistancia 5 m, todo el cantón). NO son el
levantamiento topográfico de la obra: ese está en los PDF del consorcio, con
equidistancia 1 m, y es más preciso dentro del área del proyecto. En la zona
de obra manda el levantamiento; estas curvas dan el contexto alrededor.

Salida
------
CARTOGRAFIA REPRESA/procesado/curvas_5m_zona.gpkg   (EPSG:32717, sin tocar)
"""
import os
import sys

from osgeo import ogr, osr

ogr.UseExceptions()
osr.UseExceptions()

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
RAIZ = os.path.abspath(os.path.join(BASE, '..'))

ORIGEN = os.path.join(
    os.path.expanduser('~'), 'QField', 'cloud', 'porotog_levantamiento_offline',
    'PROYECTOAGUACANGAHUACATASTROCURVASNIVEL5M.gpkg')
PROCESADO = os.path.join(RAIZ, 'CARTOGRAFIA REPRESA', 'procesado')
SALIDA = os.path.join(PROCESADO, 'curvas_5m_zona.gpkg')

# Cuadro de trabajo en UTM 17S (EPSG:32717). Generoso a propósito: el límite de
# proyecto va de E 818.534-820.757 / N 9.982.773-9.984.834, pero el plano 1002
# incluye la vía de acceso, que se extiende más. Sobra capacidad: 8 x 8 km de
# curvas cada 5 m siguen siendo unos pocos MB.
BBOX = (815000.0, 9980000.0, 823000.0, 9988000.0)  # xmin, ymin, xmax, ymax

CAMPO_COTA = 'ELEV'


def ruta_es_de_qfield(ruta):
    """True si la ruta cae dentro de la carpeta que sincroniza QFieldCloud."""
    ruta = os.path.normcase(os.path.abspath(ruta))
    qfield = os.path.normcase(os.path.abspath(
        os.path.join(os.path.expanduser('~'), 'QField')))
    return ruta.startswith(qfield)


def main():
    print("=" * 74)
    print(" RECORTE DE CURVAS DE NIVEL 5 m - ZONA REPRESA POROTOG")
    print("=" * 74)

    if not os.path.exists(ORIGEN):
        print("ERROR: no se encuentra la capa de origen:\n  {}".format(ORIGEN))
        return 1

    if ruta_es_de_qfield(SALIDA):
        print("ERROR: la salida apunta dentro de la carpeta de QFieldCloud.")
        print("       QFieldSync subiria ese archivo a las tablets. Abortado.")
        return 1

    os.makedirs(PROCESADO, exist_ok=True)

    # ── origen, en SOLO LECTURA (update=0) ──
    src = ogr.Open(ORIGEN, 0)
    if src is None:
        print("ERROR: no se pudo abrir el GPKG de origen.")
        return 1
    capa = src.GetLayer(0)
    srs = capa.GetSpatialRef()
    epsg = srs.GetAuthorityCode(None) if srs else None
    total = capa.GetFeatureCount()
    print("\n  origen : {}".format(os.path.basename(ORIGEN)))
    print("           {:,} curvas - {:.0f} MB - EPSG:{}"
          .format(total, os.path.getsize(ORIGEN) / 1e6, epsg))

    if epsg != '32717':
        print("  AVISO: se esperaba EPSG:32717 (WGS84 / UTM 17S) y vino {}."
              .format(epsg))
        print("         El recorte usa coordenadas UTM 17S; revisa antes de seguir.")
        return 1

    if capa.FindFieldIndex(CAMPO_COTA, 1) < 0:
        print("  ERROR: la capa no trae el campo de cota '{}'.".format(CAMPO_COTA))
        print("         Sin cota no sirve para el modelo de terreno.")
        return 1

    # ── filtro espacial ──
    xmin, ymin, xmax, ymax = BBOX
    capa.SetSpatialFilterRect(xmin, ymin, xmax, ymax)
    n_zona = capa.GetFeatureCount()
    print("\n  recorte: E {:,.0f}-{:,.0f}  N {:,.0f}-{:,.0f}  ({:.1f} x {:.1f} km)"
          .format(xmin, xmax, ymin, ymax, (xmax - xmin) / 1000, (ymax - ymin) / 1000))
    print("           {:,} curvas intersecan el cuadro ({:.1f}% del total)"
          .format(n_zona, 100.0 * n_zona / total))

    if n_zona == 0:
        print("  ERROR: ninguna curva cae en el cuadro. Revisa el BBOX.")
        return 1

    # ── salida ──
    drv = ogr.GetDriverByName('GPKG')
    if os.path.exists(SALIDA):
        drv.DeleteDataSource(SALIDA)
    dst = drv.CreateDataSource(SALIDA)
    out = dst.CreateLayer('curvas_5m', srs=srs, geom_type=ogr.wkbMultiLineString)
    out.CreateField(ogr.FieldDefn('cota', ogr.OFTReal))

    recorte = ogr.CreateGeometryFromWkt(
        'POLYGON(({0} {1},{2} {1},{2} {3},{0} {3},{0} {1}))'
        .format(xmin, ymin, xmax, ymax))

    cotas, escritas, metros = set(), 0, 0.0
    defn = out.GetLayerDefn()
    capa.ResetReading()
    for ft in capa:
        g = ft.GetGeometryRef()
        if g is None:
            continue
        g = g.Intersection(recorte)          # cortar, no solo seleccionar
        if g is None or g.IsEmpty():
            continue
        cota = ft.GetField(CAMPO_COTA)
        nueva = ogr.Feature(defn)
        nueva.SetField('cota', cota)
        nueva.SetGeometry(ogr.ForceToMultiLineString(g))
        out.CreateFeature(nueva)
        metros += g.Length()
        cotas.add(cota)
        escritas += 1
        nueva = None

    dst = None
    src = None

    faltantes = []
    if cotas:
        c = sorted(cotas)
        esperadas = set(range(int(min(c)), int(max(c)) + 1, 5))
        faltantes = sorted(esperadas - {int(x) for x in cotas})

    print("\n  escritas          : {:,} curvas".format(escritas))
    print("  cotas             : {:,.0f} a {:,.0f} m (equidistancia 5 m)"
          .format(min(cotas), max(cotas)))
    print("  niveles distintos : {}".format(len(cotas)))
    print("  huecos de nivel   : {}".format(
        "ninguno" if not faltantes else
        "{} -> {}".format(len(faltantes), faltantes[:12])))
    print("  longitud total    : {:,.0f} km".format(metros / 1000))
    print("\n  guardado: {}  ({:.1f} MB, era {:.0f} MB)".format(
        os.path.relpath(SALIDA, RAIZ),
        os.path.getsize(SALIDA) / 1e6, os.path.getsize(ORIGEN) / 1e6))
    print("  el archivo original NO fue modificado.")
    print("=" * 74)
    return 0


if __name__ == '__main__':
    sys.exit(main())
