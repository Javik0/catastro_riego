# -*- coding: utf-8 -*-
"""
Polígono oficial del Parque Nacional Cayambe Coca para la vista de la represa.

Por qué existe
--------------
La capa `area_protegida.geojson` que salió del plano del consorcio NO es el
parque: son dos polilíneas del CAD con el tramo del borde que cabía en el
marco del plano. En pantalla se veía una línea punteada que nadie podía
interpretar — ni siquiera se distinguía si la obra estaba dentro o fuera del
área protegida.

Este script publica el polígono completo del PNCC dentro del cantón Cayambe
a partir del shapefile oficial que consiguió JAVIKO (sep-2026):

    PNCC_CANTON CAYAMBE/PNCC_INTERSECT_CANTON_CAYAMBE.shp
    Fuente: Decreto Supremo Nº 818 (17/11/1970) y registros oficiales
    posteriores · escala 1:250.000 · subsistema ESTATAL · 42.867 ha en el
    cantón.

Lo que el cruce demostró (sep-2026, medido en UTM 17S):
  · La obra (63,59 ha) NO entra al parque y colinda con su límite a 0 m:
    el proyecto está diseñado para llegar hasta el borde sin invadirlo.
  · La línea del plano del consorcio coincide con este límite oficial con
    1 m de mediana y de máximo sobre sus 64 vértices: el consorcio usó el
    límite oficial.
  · El predio PÁRAMO CHICO (1702606901) traslapa ~64,6 ha (20 %) con el
    parque en su parte alta, FUERA del área de la obra. Ojo: el límite del
    parque es de escala 1:250.000, así que ese traslape tiene una
    incertidumbre de decenas de metros — se presenta como referencia, no
    como medición catastral.

Uso
---
    C:\OSGeo4W\bin\python-qgis.bat -X utf8 scripts/represa/07_capa_pncc.py

Solo lee el shapefile y escribe public/geo/represa/pncc_canton.geojson.
Correrlo de nuevo es siempre seguro.
"""
import json
import os

from osgeo import ogr, osr

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
RAIZ = os.path.abspath(os.path.join(BASE, '..'))
SHP = os.path.join(RAIZ, 'PNCC_CANTON CAYAMBE', 'PNCC_INTERSECT_CANTON_CAYAMBE.shp')
SALIDA = os.path.join(BASE, 'public', 'geo', 'represa', 'pncc_canton.geojson')

# El límite es de escala 1:250.000: simplificar a ~10 m no pierde nada real
# y deja la capa liviana para la web.
TOLERANCIA_M = 10.0


def main():
    print('=' * 74)
    print(' POLIGONO OFICIAL DEL PNCC (canton Cayambe) -> capa web')
    print('=' * 74)
    if not os.path.exists(SHP):
        print('ERROR: no se encuentra {}'.format(SHP))
        return 1

    ds = ogr.Open(SHP, 0)
    capa = ds.GetLayer(0)
    srs = capa.GetSpatialRef()

    utm = osr.SpatialReference(); utm.ImportFromEPSG(32717)
    wgs = osr.SpatialReference(); wgs.ImportFromEPSG(4326)
    wgs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    a_utm = osr.CoordinateTransformation(srs, utm)
    a_wgs = osr.CoordinateTransformation(utm, wgs)

    feats = []
    for ft in capa:
        g = ft.GetGeometryRef().Clone()
        g.Transform(a_utm)
        area_ha = g.GetArea() / 10000.0
        g = g.SimplifyPreserveTopology(TOLERANCIA_M)
        g.Transform(a_wgs)
        feats.append({
            'type': 'Feature',
            'properties': {
                'nombre': str(ft.GetField('nam') or 'CAYAMBE COCA').strip(),
                'categoria': str(ft.GetField('map') or 'PARQUE NACIONAL').strip(),
                'area_canton_ha': round(area_ha, 1),
                'escala_fuente': '1:250.000',
                'fuente': ('Decreto Supremo Nº 818 (17/11/1970) y registros '
                           'oficiales posteriores'),
            },
            'geometry': json.loads(g.ExportToJson()),
        })
    ds = None

    with open(SALIDA, 'w', encoding='utf-8') as fh:
        json.dump({'type': 'FeatureCollection', 'features': feats}, fh,
                  ensure_ascii=False)
    kb = os.path.getsize(SALIDA) / 1024
    print('  features : {}'.format(len(feats)))
    print('  area     : {:,.0f} ha en el canton'.format(feats[0]['properties']['area_canton_ha']))
    print('  archivo  : {} ({:,.0f} KB)'.format(os.path.relpath(SALIDA, BASE), kb))
    print('=' * 74)
    return 0


if __name__ == '__main__':
    import sys
    sys.exit(main())
