# -*- coding: utf-8 -*-
"""
Predios investigados y huella de los sectores, para la vista de la represa.

Para qué
--------
La pantalla de la represa muestra una obra de 63,6 ha. Sola, no dice nada: lo
que da la medida es verla contra el sistema de riego al que va a servir, que son
más de 6.000 ha y 6.825 predios levantados. Estas dos capas son ese contraste.

Por qué no se reutilizan las capas que ya existen
-------------------------------------------------
`public/geo/fichas_predios.geojson` pesa 15 MB porque lleva la ficha entera de
cada predio (propietario, cultivos, caudal, servicios…). Aquí solo hace falta el
punto y a qué sector pertenece: recortado baja a una fracción de eso. La
pantalla de la represa no es la del padrón; quien quiera el detalle de una ficha
tiene el mapa del padrón para eso.

De dónde sale el sector de cada predio
--------------------------------------
Del campo `sector_investigacion` de la ficha. Cuando viene vacío —y viene vacío
a menudo— NO se reimplementa aquí la lógica de asignación: se resuelve por
geometría, mirando dentro de qué polígono de `sectores.geojson` cae el punto.
Esa capa ya se generó con la canonización buena (`comunidades_canon.py`), y
duplicar esa regla en otro script es justo lo que hace que el dato se pierda en
silencio (regla 4 del proyecto).

Salidas
-------
public/geo/represa/predios_por_sector.geojson   puntos: solo sector y comunidad
public/geo/represa/sectores_huella.geojson      3 poligonos simplificados
public/geo/represa/magnitud.json                cifras para el panel de la vista
"""
import json
import os
import sys

from osgeo import ogr

ogr.UseExceptions()

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
RAIZ = os.path.abspath(os.path.join(BASE, '..'))
GEO = os.path.join(BASE, 'public', 'geo')
WEB = os.path.join(GEO, 'represa')

FICHAS = os.path.join(GEO, 'fichas_predios.geojson')
SECTORES = os.path.join(GEO, 'sectores.geojson')
LIMITE = os.path.join(WEB, 'limite_proyecto.geojson')

SIN_ASIGNAR = 'Sin asignar'
TOLERANCIA = 0.00002      # ~2 m; los limites por dissolve traen mucho vertice


def cargar_sectores():
    """Polígonos de sector con sus cifras, ya simplificados."""
    ds = ogr.Open(SECTORES, 0)
    capa = ds.GetLayer(0)
    salida = []
    for ft in capa:
        g = ft.GetGeometryRef().Clone()
        simple = g.SimplifyPreserveTopology(TOLERANCIA)
        salida.append({
            'sector': ft.GetField('sector') or SIN_ASIGNAR,
            'total_fichas': ft.GetField('total_fichas') or 0,
            'area_riego_ha': ft.GetField('area_riego_ha') or 0.0,
            'area_dissolve_ha': ft.GetField('area_dissolve_ha') or 0.0,
            'geom': simple if simple and not simple.IsEmpty() else g,
            'geom_original': g,
        })
    ds = None
    return salida


def main():
    print("=" * 74)
    print(" PREDIOS INVESTIGADOS Y HUELLA DE SECTORES (vista de la represa)")
    print("=" * 74)

    for f in (FICHAS, SECTORES, LIMITE):
        if not os.path.exists(f):
            print("ERROR: falta {}".format(os.path.relpath(f, BASE)))
            if f == LIMITE:
                print("       ejecuta antes 04_generar_capas.py")
            return 1
    os.makedirs(WEB, exist_ok=True)

    sectores = cargar_sectores()
    print("\n  sectores: {}".format(len(sectores)))
    for s in sectores:
        print("      {:12s} {:5,} fichas   {:9,.0f} ha de riego   {:9,.0f} ha de huella"
              .format(s['sector'], s['total_fichas'], s['area_riego_ha'],
                      s['area_dissolve_ha']))

    # ── predios ──
    ds = ogr.Open(FICHAS, 0)
    capa = ds.GetLayer(0)
    total = capa.GetFeatureCount()

    drv = ogr.GetDriverByName('GeoJSON')
    ruta_p = os.path.join(WEB, 'predios_por_sector.geojson')
    if os.path.exists(ruta_p):
        os.remove(ruta_p)
    ds_out = drv.CreateDataSource(ruta_p)
    cap_out = ds_out.CreateLayer('predios_por_sector', srs=capa.GetSpatialRef(),
                                 geom_type=ogr.wkbPoint)
    for c in ('sector', 'comunidad'):
        cap_out.CreateField(ogr.FieldDefn(c, ogr.OFTString))
    defn = cap_out.GetLayerDefn()

    por_sector = {}
    del_campo, por_geometria, sin_resolver, sin_geometria = 0, 0, 0, 0

    for ft in capa:
        g = ft.GetGeometryRef()
        if g is None or g.IsEmpty():
            sin_geometria += 1
            continue

        sector = (ft.GetField('sector_investigacion') or '').strip()
        if sector:
            del_campo += 1
        else:
            # sin campo: se resuelve por geometria contra la capa de sectores
            sector = ''
            for s in sectores:
                if s['geom_original'].Contains(g):
                    sector = s['sector']
                    por_geometria += 1
                    break
            if not sector:
                sector = SIN_ASIGNAR
                sin_resolver += 1

        por_sector[sector] = por_sector.get(sector, 0) + 1
        nueva = ogr.Feature(defn)
        nueva.SetField('sector', sector)
        nueva.SetField('comunidad', (ft.GetField('comunidad') or '').strip())
        nueva.SetGeometry(g.Clone())
        cap_out.CreateFeature(nueva)
        nueva = None

    ds_out = None
    ds = None

    print("\n  predios procesados: {:,} de {:,}".format(sum(por_sector.values()), total))
    print("      con sector en la ficha   : {:,}".format(del_campo))
    print("      resueltos por geometria  : {:,}".format(por_geometria))
    print("      sin resolver             : {:,}".format(sin_resolver))
    if sin_geometria:
        print("      sin geometria (omitidos) : {:,}".format(sin_geometria))
    for s, n in sorted(por_sector.items()):
        print("      {:14s} {:5,} predios".format(s, n))
    print("  archivo: predios_por_sector.geojson  ({:,.0f} KB, la capa completa"
          " del padron pesa {:,.0f} KB)"
          .format(os.path.getsize(ruta_p) / 1024, os.path.getsize(FICHAS) / 1024))

    # ── huella de sectores ──
    ruta_s = os.path.join(WEB, 'sectores_huella.geojson')
    if os.path.exists(ruta_s):
        os.remove(ruta_s)
    ds_out = drv.CreateDataSource(ruta_s)
    cap_out = ds_out.CreateLayer('sectores_huella', geom_type=ogr.wkbMultiPolygon)
    cap_out.CreateField(ogr.FieldDefn('sector', ogr.OFTString))
    cap_out.CreateField(ogr.FieldDefn('predios', ogr.OFTInteger))
    cap_out.CreateField(ogr.FieldDefn('area_riego_ha', ogr.OFTReal))
    cap_out.CreateField(ogr.FieldDefn('area_ha', ogr.OFTReal))
    defn = cap_out.GetLayerDefn()
    for s in sectores:
        ft = ogr.Feature(defn)
        ft.SetField('sector', s['sector'])
        ft.SetField('predios', int(s['total_fichas']))
        ft.SetField('area_riego_ha', round(s['area_riego_ha'], 2))
        ft.SetField('area_ha', round(s['area_dissolve_ha'], 2))
        ft.SetGeometry(s['geom'])
        cap_out.CreateFeature(ft)
        ft = None
    ds_out = None
    print("  archivo: sectores_huella.geojson     ({:,.0f} KB, de {:,.0f} KB)"
          .format(os.path.getsize(ruta_s) / 1024, os.path.getsize(SECTORES) / 1024))

    # ── cifras de magnitud para el panel ──
    ds = ogr.Open(LIMITE, 0)
    lim = ds.GetLayer(0)
    ft = lim.GetNextFeature()
    area_represa = float(ft.GetField('area_ha') or 0)
    ds = None

    riego = sum(s['area_riego_ha'] for s in sectores)
    huella = sum(s['area_dissolve_ha'] for s in sectores)
    magnitud = {
        'represa_ha': round(area_represa, 2),
        'riego_ha': round(riego, 1),
        'huella_ha': round(huella, 1),
        'predios': sum(por_sector.values()),
        'ha_regadas_por_ha_de_represa': round(riego / area_represa, 1) if area_represa else None,
        'sectores': [{'sector': s['sector'], 'predios': int(s['total_fichas']),
                      'area_riego_ha': round(s['area_riego_ha'], 1)} for s in sectores],
    }
    with open(os.path.join(WEB, 'magnitud.json'), 'w', encoding='utf-8') as f:
        json.dump(magnitud, f, ensure_ascii=False, indent=2)

    print("\n  magnitud del proyecto")
    print("      represa                  : {:,.2f} ha".format(area_represa))
    print("      superficie bajo riego    : {:,.0f} ha".format(riego))
    print("      predios investigados     : {:,}".format(magnitud['predios']))
    print("      por cada ha de represa   : {:,.0f} ha regadas"
          .format(magnitud['ha_regadas_por_ha_de_represa'] or 0))
    print("=" * 74)
    return 0


if __name__ == '__main__':
    sys.exit(main())
