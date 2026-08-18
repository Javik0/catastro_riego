# -*- coding: utf-8 -*-
"""
Datos de la pantalla «Asignar comunidad a mano» (/auditoria-areas).

Para qué
--------
Quedan fichas sin comunidad que ningún criterio automático puede cerrar:
están en la frontera entre dos o tres comunidades, o aisladas fuera de todas.
`resolver_comunidad_oficina.py` las deja fuera a propósito —prefiere no
asignar antes que asignar mal—, pero eso las condenaba a «campo» cuando en
realidad **una persona que mire el mapa las resuelve en segundos**.

Este script arma lo que hace falta para decidirlas mirando: el punto de la
ficha, las comunidades candidatas ordenadas por distancia, y el contorno de
cada una para dibujarlo.

Qué incluye por ficha
---------------------
* dónde está el punto (lon/lat) y quién es el regante
* las `N_CANDIDATAS` comunidades más cercanas, con:
  - a cuántos metros está el borde de cada una (0 si el punto cae dentro)
  - cuántas de las 12 fichas vecinas son de esa comunidad
  - el contorno, simplificado, para dibujarlo en el mapa
* la comuna oficial del cantón donde cae, como pista adicional

Lo que NO hace
--------------
No decide nada ni escribe en el `data.gpkg`. La pantalla recoge las
decisiones y las exporta; se aplican después con
`aplicar_comunidad_manual.py`, que sí respalda y verifica.

Uso
---
    "C:\\OSGeo4W\\bin\\python-qgis.bat" -X utf8 scripts/generar_asignar_comunidad.py
"""
import json
import os
import sqlite3
import sys
from collections import Counter

from osgeo import ogr, osr

ogr.UseExceptions()

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from comunidades_canon import canonica  # noqa: E402

GPKG = os.path.join(os.path.expanduser('~'), 'QField', 'cloud',
                    'porotog_levantamiento_offline', 'data.gpkg')
GEO = os.path.join(BASE, 'public', 'geo')
SALIDA = os.path.join(GEO, 'asignar_comunidad.json')
TABLA = 'Fichas_Predios_880eb10d_d887_4fc6_99a2_8af3ac63877e'
VACIA = ("(comunidad IS NULL OR TRIM(comunidad) = '' "
         "OR UPPER(TRIM(comunidad)) IN ('NULL','NONE','(SIN COMUNIDAD)'))")

N_CANDIDATAS = 6
N_VECINAS = 12
TOLERANCIA_SIMPLIFICAR = 0.00012   # ~13 m: suficiente para ver la forma


def main():
    print('=' * 74)
    print(' DATOS PARA ASIGNAR COMUNIDAD A MANO')
    print('=' * 74)

    geo = osr.SpatialReference(); geo.ImportFromEPSG(4326)
    utm = osr.SpatialReference(); utm.ImportFromEPSG(32717)
    geo.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    utm.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    a_utm = osr.CoordinateTransformation(geo, utm)
    a_geo = osr.CoordinateTransformation(utm, geo)

    with open(os.path.join(GEO, 'comunidades.geojson'), encoding='utf-8') as f:
        datos = json.load(f)
    comunidades = []
    for ft in datos.get('features', []):
        p = ft.get('properties') or {}
        nombre = p.get('comunidad')
        if not nombre:
            continue
        try:
            g_geo = ogr.CreateGeometryFromJson(json.dumps(ft['geometry']))
        except Exception:
            continue
        if g_geo is None:
            continue
        g_utm = g_geo.Clone()
        g_utm.Transform(a_utm)
        simple = g_geo.SimplifyPreserveTopology(TOLERANCIA_SIMPLIFICAR) or g_geo
        comunidades.append({
            'nombre': nombre, 'sector': p.get('sector') or '',
            'g_utm': g_utm, 'geo': json.loads(simple.ExportToJson()),
        })
    print('  comunidades con contorno: {}'.format(len(comunidades)))

    # El límite comunal que entregó el contratante (`capas_recibidas/comunas_cy.shp`,
    # recortado al ámbito del sistema por `generar_capa_comunas_oficiales.py`:
    # 53 de las 117 del cantón). Se dibuja de fondo porque es el territorio de
    # verdad —la referencia que reconoce la gente—, mientras que las candidatas
    # a elegir salen de nuestras comunidades de riego, que son las que el padrón
    # admite como valor.
    comunas_of = []
    ruta_of = os.path.join(GEO, 'comunas_oficiales.geojson')
    if os.path.exists(ruta_of):
        with open(ruta_of, encoding='utf-8') as f:
            d = json.load(f)
        for ft in d.get('features', []):
            p = ft.get('properties') or {}
            try:
                g_geo = ogr.CreateGeometryFromJson(json.dumps(ft['geometry']))
            except Exception:
                continue
            if g_geo is None:
                continue
            g_utm = g_geo.Clone()
            g_utm.Transform(a_utm)
            simple = g_geo.SimplifyPreserveTopology(TOLERANCIA_SIMPLIFICAR) or g_geo
            comunas_of.append((p.get('comuna') or '', g_utm,
                               json.loads(simple.ExportToJson())))

    con = sqlite3.connect('file:{}?mode=ro'.format(GPKG.replace('\\', '/')), uri=True)
    cur = con.cursor()
    cur.execute("SELECT TRIM(comunidad), COALESCE(coord_x_utm,0), COALESCE(coord_y_utm,0) "
                'FROM "{}" WHERE NOT {} AND coord_x_utm IS NOT NULL AND coord_x_utm <> 0'
                .format(TABLA, VACIA))
    vecinas = cur.fetchall()

    cur.execute(
        "SELECT COALESCE(id,''), TRIM(COALESCE(clave_catastral,'')), "
        "TRIM(COALESCE(apellidos,'') || ' ' || COALESCE(nombres,'')), "
        "COALESCE(cedula,''), COALESCE(telefono_celular,''), "
        "COALESCE(coord_x_utm,0), COALESCE(coord_y_utm,0), "
        "COALESCE(sector_investigacion,''), COALESCE(observaciones,''), "
        "COALESCE(creado_por,''), COALESCE(area_total,0) "
        'FROM "{}" WHERE {}'.format(TABLA, VACIA))
    fichas = cur.fetchall()
    con.close()
    print('  fichas sin comunidad: {}'.format(len(fichas)))

    salida = []
    usadas = set()
    for (uid, clave, nombre, ced, tel, x, y, sector, obs, tec, area) in fichas:
        item = {'uid': uid, 'clave': clave or '(sin clave)', 'nombre': nombre,
                'ced': ced, 'tel': tel, 'sec': sector, 'tec': tec,
                'area': round(area), 'obs': (obs or '').strip()[:300]}
        if not (x and y):
            item['sin_gps'] = True
            item['candidatas'] = []
            salida.append(item)
            continue

        lon, lat, _ = a_geo.TransformPoint(x, y)
        item['lon'], item['lat'] = round(lon, 6), round(lat, 6)

        p = ogr.Geometry(ogr.wkbPoint); p.AddPoint_2D(x, y)

        votos = Counter()
        cercanas = sorted(((x - vx) ** 2 + (y - vy) ** 2, com)
                          for com, vx, vy in vecinas)[:N_VECINAS]
        for _d2, com in cercanas:
            votos[canonica(com) or com] += 1

        dist = []
        for c in comunidades:
            d = 0.0 if c['g_utm'].Contains(p) else p.Distance(c['g_utm'])
            dist.append((d, c))
        dist.sort(key=lambda t: t[0])

        cands = []
        for d, c in dist[:N_CANDIDATAS]:
            k = canonica(c['nombre']) or c['nombre']
            cands.append({
                'nombre': c['nombre'], 'sector': c['sector'],
                'dist': round(d), 'dentro': d == 0.0,
                'vecinas': votos.get(k, 0),
                'geo': c['geo'],
            })
            usadas.add(c['nombre'])
        item['candidatas'] = cands

        # la comuna oficial donde cae y las que la rodean, para dibujarlas
        cercanas_of = []
        for nom, g, geo_simple in comunas_of:
            d = 0.0 if g.Contains(p) else p.Distance(g)
            if d <= 600:
                cercanas_of.append((d, nom, geo_simple))
        cercanas_of.sort(key=lambda t: t[0])
        item['comunas_oficiales'] = [
            {'nombre': nom, 'dist': round(d), 'dentro': d == 0.0, 'geo': g}
            for d, nom, g in cercanas_of[:4]]
        if cercanas_of and cercanas_of[0][0] == 0.0:
            item['comuna_oficial'] = cercanas_of[0][1]
        salida.append(item)

    salida.sort(key=lambda i: (i.get('sin_gps', False),
                              i['candidatas'][0]['dist'] if i.get('candidatas') else 9e9))

    with open(SALIDA, 'w', encoding='utf-8') as f:
        json.dump({'fichas': salida}, f, ensure_ascii=False, separators=(',', ':'))
    print('  contornos incluidos: {}'.format(len(usadas)))
    print('\n  guardado: {} ({:,.0f} KB)'
          .format(os.path.relpath(SALIDA, BASE), os.path.getsize(SALIDA) / 1024))

    print('\n  las fichas, por cercanía a su candidata más próxima:')
    for i in salida:
        if i.get('sin_gps'):
            print('     {:<16} {:<32} SIN GPS'.format(i['clave'], i['nombre'][:32]))
            continue
        c0 = i['candidatas'][0]
        print('     {:<16} {:<32} {} a {} m ({} vecinas){}'
              .format(i['clave'], i['nombre'][:32], c0['nombre'][:22], c0['dist'],
                      c0['vecinas'], '  DENTRO' if c0['dentro'] else ''))


if __name__ == '__main__':
    main()
