# -*- coding: utf-8 -*-
"""
Contraste de nuestra georreferenciación contra la geometría oficial del consorcio.

Qué es esto
-----------
El consorcio entregó `CARTOGRAFIA REPRESA/GIS POROTOG.gpkg`. El archivo trae un
proyecto QGIS con 71 capas, pero **los datos de esas capas no vinieron**: todas
apuntan a un `./POROTOG.gpkg` que no está. Lo que sí llegó son 43 geometrías
sueltas, en coordenadas UTM 17S reales (EPSG:32717).

Esas 43 son poco para trabajar, pero valen mucho para una cosa: dos de sus capas
—`01-01-CAPTACION$0$CA-0.05` y `03-01-TANQUE$0$CH-0.05`— son capas que nosotros
reconstruimos desde el PDF. Comparar ambas versiones mide el error de nuestra
georreferenciación **contra el dato del propio consorcio**, que es la única
comprobación verdaderamente externa que se puede hacer.

Hasta ahora la georreferenciación se validó contra la tabla de coordenadas del
plano (RMS 0,216 m), contra la escala declarada (1:1.998 frente a 1:2.000) y
contra las curvas regionales de 5 m (3,4 m de mediana). Esto es distinto: es la
geometría original, la misma que salió del CAD del consorcio.

Uso
---
    python 07_validar_contra_consorcio.py
"""
import os
import statistics
import sys

from osgeo import ogr

ogr.UseExceptions()

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
RAIZ = os.path.abspath(os.path.join(BASE, '..'))
CARTO = os.path.join(RAIZ, 'CARTOGRAFIA REPRESA')
CONSORCIO = os.path.join(CARTO, 'GIS POROTOG.gpkg')
NUESTRO = os.path.join(CARTO, 'procesado', 'represa_utm.gpkg')

# capas del consorcio que también tenemos reconstruidas, y en qué capa nuestra
# buscarlas (el campo `capa_cad` conserva el nombre original de AutoCAD)
COMPARABLES = [
    ('hatches', '03-01-TANQUE$0$CH-0.05', 'obras'),
    ('lines', '01-01-CAPTACION$0$CA-0.05', 'obras'),
]


def lineal(geom):
    """Compound curve / circular string -> geometría lineal comparable."""
    if geom is None:
        return None
    g = geom.GetLinearGeometry() if geom.HasCurveGeometry() else geom.Clone()
    g.FlattenTo2D()
    return g


def geometria_nuestra(capa_nombre, capa_cad):
    ds = ogr.Open(NUESTRO, 0)
    capa = ds.GetLayerByName(capa_nombre)
    if capa is None:
        return None, 0
    capa.SetAttributeFilter("capa_cad = '{}'".format(capa_cad.replace("'", "''")))
    union = ogr.Geometry(ogr.wkbMultiLineString)
    n = 0
    for ft in capa:
        g = ft.GetGeometryRef()
        if g is None:
            continue
        if g.GetGeometryName() == 'LINESTRING':
            union.AddGeometry(g.Clone())
        else:
            for i in range(g.GetGeometryCount()):
                union.AddGeometry(g.GetGeometryRef(i).Clone())
        n += 1
    ds = None
    return (union if n else None), n


def main():
    print("=" * 74)
    print(" CONTRASTE CONTRA LA GEOMETRIA OFICIAL DEL CONSORCIO")
    print("=" * 74)

    for f in (CONSORCIO, NUESTRO):
        if not os.path.exists(f):
            print("ERROR: falta {}".format(f))
            return 1

    ds_c = ogr.Open(CONSORCIO, 0)
    total_dist = []

    for tabla, capa_cad, capa_nuestra in COMPARABLES:
        print("\n  capa CAD: {}".format(capa_cad))
        capa = ds_c.GetLayerByName(tabla)
        if capa is None:
            print("      la tabla '{}' no esta en el archivo del consorcio".format(tabla))
            continue
        capa.SetAttributeFilter("layer = '{}'".format(capa_cad.replace("'", "''")))

        nuestra, n_nuestras = geometria_nuestra(capa_nuestra, capa_cad)
        if nuestra is None or nuestra.IsEmpty():
            print("      no tenemos nada reconstruido de esa capa; se omite")
            continue

        distancias = []
        n_oficiales = 0
        for ft in capa:
            g = lineal(ft.GetGeometryRef())
            if g is None or g.IsEmpty():
                continue
            n_oficiales += 1
            # se mide vértice a vértice: la distancia entre geometrías completas
            # escondería un desplazamiento a lo largo de la propia línea
            puntos = []
            if g.GetGeometryName() in ('POLYGON', 'CURVEPOLYGON'):
                for i in range(g.GetGeometryCount()):
                    anillo = g.GetGeometryRef(i)
                    puntos += [anillo.GetPoint(j)[:2] for j in range(anillo.GetPointCount())]
            elif g.GetGeometryName() == 'LINESTRING':
                puntos = [g.GetPoint(j)[:2] for j in range(g.GetPointCount())]
            else:
                for i in range(g.GetGeometryCount()):
                    sub = g.GetGeometryRef(i)
                    puntos += [sub.GetPoint(j)[:2] for j in range(sub.GetPointCount())]

            for x, y in puntos:
                p = ogr.Geometry(ogr.wkbPoint)
                p.AddPoint_2D(x, y)
                distancias.append(p.Distance(nuestra))

        if not distancias:
            print("      sin vertices que comparar")
            continue

        distancias.sort()
        n = len(distancias)
        print("      elementos del consorcio : {}".format(n_oficiales))
        print("      elementos nuestros      : {}".format(n_nuestras))
        print("      vertices comparados     : {:,}".format(n))
        print("      distancia mediana       : {:.3f} m".format(distancias[n // 2]))
        print("      percentil 90            : {:.3f} m".format(distancias[int(n * 0.9)]))
        print("      maxima                  : {:.3f} m".format(distancias[-1]))
        total_dist += distancias

    ds_c = None

    if total_dist:
        total_dist.sort()
        n = len(total_dist)
        mediana = total_dist[n // 2]
        print("\n" + "-" * 74)
        print("  CONJUNTO: {:,} vertices".format(n))
        print("      mediana        : {:.3f} m".format(mediana))
        print("      media          : {:.3f} m".format(statistics.mean(total_dist)))
        print("      percentil 90   : {:.3f} m".format(total_dist[int(n * 0.9)]))
        if mediana < 1.0:
            print("\n      -> nuestra reconstruccion desde el PDF coincide con la")
            print("         geometria original del consorcio por debajo del metro.")
            print("         La georreferenciacion queda validada contra el dato")
            print("         oficial, no solo contra el propio plano.")
        else:
            print("\n      -> ATENCION: la separacion es mayor de lo esperado.")
            print("         Revisar antes de dar por buenas las capas publicadas.")
    print("=" * 74)
    return 0


if __name__ == '__main__':
    sys.exit(main())
