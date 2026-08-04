# -*- coding: utf-8 -*-
"""
Capa de LÍMITES DE COMUNAS OFICIALES, recortada al ámbito del sistema de riego.

Qué es y en qué se diferencia de comunidades.geojson
----------------------------------------------------
Son dos cosas distintas y NO se sustituyen entre sí:

* `comunidades.geojson`  — lo generamos nosotros por dissolve de los predios
  investigados. Es la huella real del levantamiento (6.797 ha) y es la base de
  las áreas y del caudal que salen en los informes.
* `comunas_oficiales.geojson` (este archivo) — límite comunal territorial que
  entregó el contratante (`capas_recibidas/comunas_cy.shp`, 117 comunas de todo
  el cantón Cayambe, 50.133 ha).

Una comuna oficial puede contener VARIAS de nuestras organizaciones de riego:
p. ej. la comuna MONTESERRIN abarca Monteserrín Alto, Sr. Coloma Monteserrín
Bajo, El Manzano, Cangahua Pungo y Asociación Rosalía; y la comuna IZACATA
abarca Comuna Izacata, Izacata y Los Andes Izacata (según Armando, era una
comuna anterior que después se dividió).

Criterio de recorte
-------------------
Se conservan las comunas que intersecan al menos MIN_PCT % de SU PROPIA área
con la huella del sistema investigado. Con el 1% quedan 53 de las 117; el resto
son comunas del cantón sin relación con el sistema.

Los nombres se dejan TAL COMO VINIERON en el campo `TEXT` del shapefile
(indicación de Armando: «ponle así como vino»). Eso incluye las erratas de la
conversión desde AutoCAD —CHAUPISTANCIA, PPOROTOG BAJO, LOS VOLCANES SESUS DEL
GRAN PODER, una comuna llamada solo «E»—: corregirlas aquí sería inventar una
canonización paralela a `comunidades_canon.py`, que es justo lo que rompe el
dato en silencio.

NO cruzar estas comunas con las nuestras por nombre: hay nombres iguales que
designan sitios distintos. La comuna «ASOCIACION POROTOG» del shapefile
corresponde a nuestra «Asociación 17 de Junio» (99,6%), mientras que nuestra
«Asociación Porotog» cae en la comuna «SAN VICENTE DE POROTOG» (98,6%).

Salida
------
public/geo/comunas_oficiales.geojson   (WGS84, para la web y el GeoPackage)
"""
import json
import os

import shapefile                       # pyshp
from shapely.geometry import shape, mapping
from shapely.ops import transform, unary_union
from pyproj import Transformer

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
RAIZ = os.path.abspath(os.path.join(BASE, '..'))
SHP = os.path.join(RAIZ, 'capas_recibidas', 'comunas_cy.shp')
DISSOLVE = os.path.join(BASE, 'public', 'geo', 'comunidades.geojson')
SALIDA = os.path.join(BASE, 'public', 'geo', 'comunas_oficiales.geojson')

MIN_PCT = 1.0          # % del área de la comuna que debe caer dentro del sistema
CAMPO_NOMBRE = 'TEXT'  # el resto de campos son basura de la conversión CAD


def main():
    print("=" * 74)
    print(" CAPA DE COMUNAS OFICIALES (recorte al ámbito del sistema)")
    print("=" * 74)

    if not os.path.exists(SHP):
        print("ERROR: falta el shapefile {}".format(SHP))
        return 1
    if not os.path.exists(DISSOLVE):
        print("ERROR: falta {} (ejecuta antes generar_capas_sectores_comunidades.py)"
              .format(DISSOLVE))
        return 1

    # ── huella del sistema: unión de los límites por dissolve, en UTM 17S ──
    a_utm = Transformer.from_crs('EPSG:4326', 'EPSG:32717', always_xy=True).transform
    a_wgs = Transformer.from_crs('EPSG:32717', 'EPSG:4326', always_xy=True).transform
    with open(DISSOLVE, encoding='utf-8') as f:
        nuestras = json.load(f)['features']
    geoms = []
    for ft in nuestras:
        g = shape(ft['geometry'])
        if not g.is_valid:
            g = g.buffer(0)
        geoms.append(transform(a_utm, g))
    huella = unary_union(geoms)
    print("\n  huella investigada : {:,.0f} ha ({} comunidades)"
          .format(huella.area / 10000, len(nuestras)))

    # ── shapefile de comunas (ya viene en UTM 17S) ──
    sf = shapefile.Reader(SHP, encoding='latin-1')
    campos = [c[0] for c in sf.fields[1:]]
    if CAMPO_NOMBRE not in campos:
        print("ERROR: el shapefile no trae el campo {}".format(CAMPO_NOMBRE))
        return 1
    idx = campos.index(CAMPO_NOMBRE)

    total_ha = 0.0
    dentro, descartadas = [], 0
    for sr in sf.shapeRecords():
        g = shape(sr.shape.__geo_interface__)
        if not g.is_valid:
            g = g.buffer(0)
        if g.is_empty or g.area <= 0:
            continue
        total_ha += g.area / 10000
        inter = g.intersection(huella).area
        pct = 100.0 * inter / g.area
        if pct < MIN_PCT:
            descartadas += 1
            continue
        dentro.append({
            'nombre': str(sr.record[idx] or '').strip(),
            'geom': g,
            'area_ha': g.area / 10000,
            'dentro_ha': inter / 10000,
            'pct_dentro': pct,
        })

    print("  shapefile recibido : {:,.0f} ha ({} comunas del cantón)"
          .format(total_ha, len(sf)))
    print("\n  conservadas (>= {:.0f}% dentro): {}".format(MIN_PCT, len(dentro)))
    print("  descartadas (sin relación)    : {}".format(descartadas))

    dentro.sort(key=lambda c: -c['pct_dentro'])
    for c in dentro:
        print("      {:6.1f}%  {:42s} {:9,.0f} ha"
              .format(c['pct_dentro'], c['nombre'][:42] or '(sin nombre)', c['area_ha']))

    # ── escribir GeoJSON en WGS84 ──
    feats = []
    for c in dentro:
        feats.append({
            'type': 'Feature',
            'properties': {
                'comuna': c['nombre'],
                'area_comuna_ha': round(c['area_ha'], 2),
                'area_dentro_ha': round(c['dentro_ha'], 2),
                'pct_dentro': round(c['pct_dentro'], 1),
                'fuente': 'comunas_cy.shp (contratante)',
            },
            'geometry': mapping(transform(a_wgs, c['geom'])),
        })
    with open(SALIDA, 'w', encoding='utf-8') as f:
        json.dump({'type': 'FeatureCollection', 'features': feats}, f, ensure_ascii=False)

    print("\n  guardado: {} ({:.0f} KB)"
          .format(os.path.relpath(SALIDA, BASE), os.path.getsize(SALIDA) / 1024))
    print("=" * 74)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
