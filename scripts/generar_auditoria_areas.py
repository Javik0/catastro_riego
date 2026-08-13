# -*- coding: utf-8 -*-
"""
Datos de la pantalla «Auditoría de áreas» (/auditoria-areas, solo equipo).

Qué resuelve
------------
La superficie del padrón no cuadra con el catastro, y hasta ahora eso se
revisaba en documentos sueltos que envejecían. Este script lee el `data.gpkg`
en el momento de ejecutarse y arma el paquete que consume la pantalla web, así
que **el visor siempre muestra el estado real**: a medida que se depura, los
casos desaparecen solos.

Qué detecta
-----------
* **exceso** — varias fichas sobre el mismo predio, y entre todas declaran más
  de lo que mide el polígono del catastro. Es el grueso del descuadre.
* **dividido** — varias fichas sobre el mismo predio pero repartiéndoselo bien:
  la suma da el polígono. Se incluyen para tener el contraste a la vista.
* **triple** — el área total, la de riego y la de sin riego traen el mismo
  número. No afecta al total del padrón pero rompe el reparto riego/sin riego.
* **clave_mala** — la clave catastral no existe en el catastro del GADM. Casi
  siempre está mal escrita (le sobran o faltan dígitos).

El área escondida en las observaciones
--------------------------------------
El hallazgo que más trabajo ahorra: en muchos predios compartidos el técnico
**sí anotó cuánto le corresponde a cada regante, pero en el campo de
observaciones** en vez de en el de área. Por ejemplo, cinco hermanos sobre un
predio de 98.056 m² declaran los cinco esa cifra, y sus observaciones dicen
12.500, 15.266, 14.420, 12.623 y 16.053.

Por eso cada ficha lleva `obs_area`: el número con pinta de superficie que
aparezca en su observación. Cuando las `obs_area` de un predio suman el
polígono, el caso se resuelve copiando datos, sin salir a campo. La pantalla lo
marca con `resuelto_por_obs`.

Cómo se ejecuta
---------------
    "C:\\OSGeo4W\\bin\\python-qgis.bat" -X utf8 scripts/generar_auditoria_areas.py

Va en la cadena de sincronización, después de `export_geojson.py`.

Salida
------
public/geo/auditoria_areas.json
"""
import json
import os
import re
import sys
from datetime import datetime

from osgeo import ogr, osr

ogr.UseExceptions()

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
GPKG = os.path.join(os.path.expanduser('~'), 'QField', 'cloud',
                    'porotog_levantamiento_offline', 'data.gpkg')
CATASTRO = os.path.join(BASE, 'public', 'geo', 'catastro_geo.geojson')
CANAL = os.path.join(BASE, 'public', 'geo', 'ramales_riego.geojson')
SALIDA = os.path.join(BASE, 'public', 'geo', 'auditoria_areas.json')

CAPA = 'Fichas_Predios_880eb10d_d887_4fc6_99a2_8af3ac63877e'

# Un predio «con exceso» tiene que pasarse de esto para contar. Medio metro
# cuadrado de diferencia es ruido de redondeo, no un caso a revisar.
TOLERANCIA_M2 = 1000
# Y un predio se considera «bien dividido» si la suma cae dentro de este margen.
MARGEN_DIVIDIDO = 0.15

# Números con pinta de superficie dentro de un texto libre. Los técnicos lo
# escriben de muchas maneras y todas estas aparecen en el padrón:
#   «solo le corresponde un area total de 23654.79 mts cuadrados»
#   «Dueña de 2000 metros»   ·   «Es dueño de los 3500m»   ·   «1.247,42 m2»
AREA_EN_TEXTO = re.compile(
    r'(\d[\d.,]{1,12})\s*'
    r'(?:M2|M²|M\s*2|MTS?\b\.?|METROS?\b|HAS?\b|HECTAREAS?\b|M\b)'
    r'\s*(?:CUADRADOS?|CUADRADAS?)?', re.IGNORECASE)


def num_del_texto(txt):
    """El área que menciona una observación, o None.

    Los técnicos escriben tanto «23654.79» como «2.000» y «1,247.42», así que
    hay que decidir si el punto separa decimales o miles.
    """
    if not txt:
        return None
    m = AREA_EN_TEXTO.search(txt)
    if not m:
        return None
    crudo = m.group(1).strip().rstrip('.,')
    try:
        if ',' in crudo and '.' in crudo:          # 1,247.42
            v = float(crudo.replace(',', ''))
        elif re.search(r'[.,]\d{1,2}$', crudo):    # 23654.79  ·  1247,42
            v = float(crudo.replace(',', '.'))
        else:                                       # 2.000  ·  2000
            v = float(crudo.replace('.', '').replace(',', ''))
    except ValueError:
        return None
    # si venía en hectáreas, a metros
    if re.search(r'HAS?\b|HECTAREAS?\b', m.group(0), re.IGNORECASE):
        v *= 10000
    # descartar lo que no puede ser la superficie de un predio
    return round(v) if 10 <= v <= 5_000_000 else None


def cargar_catastro():
    """Área y contorno de cada predio, en coordenadas geográficas."""
    with open(CATASTRO, encoding='utf-8') as f:
        datos = json.load(f)
    areas, contorno = {}, {}
    for ft in datos.get('features', []):
        p = ft.get('properties') or {}
        clave = str(p.get('clave_cata') or '').strip()
        if not clave:
            continue
        if p.get('area_predi'):
            areas[clave] = float(p['area_predi'])
        g = ft.get('geometry') or {}
        if g.get('type') == 'Polygon':
            contorno[clave] = g['coordinates'][0]
        elif g.get('type') == 'MultiPolygon':
            contorno[clave] = g['coordinates'][0][0]
    return areas, contorno


def redondear(anillo, dec=6):
    """Menos decimales = archivo más liviano. 6 decimales son ~11 cm."""
    return [[round(x, dec), round(y, dec)] for x, y in anillo]


def main():
    print("=" * 74)
    print(" DATOS DE LA AUDITORIA DE AREAS")
    print("=" * 74)

    for ruta, que in ((GPKG, 'data.gpkg'), (CATASTRO, 'catastro_geo.geojson')):
        if not os.path.exists(ruta):
            print("ERROR: no se encuentra {}:\n  {}".format(que, ruta))
            return 1

    areas_cat, contorno = cargar_catastro()
    print("\n  catastro: {:,} predios con área".format(len(areas_cat)))

    # UTM 17S (lo que guarda QField) → geográficas (lo que dibuja Leaflet)
    utm = osr.SpatialReference(); utm.ImportFromEPSG(32717)
    geo = osr.SpatialReference(); geo.ImportFromEPSG(4326)
    utm.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    geo.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    a_geo = osr.CoordinateTransformation(utm, geo)

    ds = ogr.Open(GPKG, 0)          # SOLO LECTURA
    res = ds.ExecuteSQL(
        "SELECT COALESCE(clave_catastral,''), COALESCE(area_total,0), "
        "COALESCE(area_riego,0), COALESCE(area_sin_riego,0), "
        "TRIM(COALESCE(apellidos,'') || ' ' || COALESCE(nombres,'')), "
        "COALESCE(cedula,''), COALESCE(telefono_celular,''), "
        "COALESCE(comunidad,''), COALESCE(sector_investigacion,''), "
        "COALESCE(creado_por,''), SUBSTR(CAST(fecha_creacion AS TEXT),1,10), "
        "COALESCE(observaciones,''), COALESCE(coord_x_utm,0), "
        "COALESCE(coord_y_utm,0), "
        "CASE WHEN es_ficha_hija IS NULL OR es_ficha_hija NOT IN "
        "('1','true','SI','Si','si') THEN 1 ELSE 0 END "
        "FROM \"{}\"".format(CAPA), dialect='SQLITE')
    filas = [[ft.GetField(i) for i in range(15)] for ft in res]
    ds.ReleaseResultSet(res)
    corte = max((f[10] or '') for f in filas)
    ds = None
    print("  padrón  : {:,} fichas · corte {}".format(len(filas), corte))

    # ── una entrada por ficha, ya en coordenadas geográficas ──
    por_clave = {}
    claves_malas = {}
    for (clave, at, ar, asr, nom, ced, tel, com, sec, tec, fecha, obs,
         x, y, pri) in filas:
        clave = (clave or '').strip()
        lon = lat = None
        if x and y:
            lon, lat, _ = a_geo.TransformPoint(x, y)
            lon, lat = round(lon, 6), round(lat, 6)
        obs = (obs or '').strip()
        f = {'n': nom or '—', 'ced': ced or '', 'tel': tel or '',
             'a': round(at or 0), 'ar': round(ar or 0), 'asr': round(asr or 0),
             'tec': tec or '', 'f': fecha or '', 'p': pri,
             'lon': lon, 'lat': lat}
        if obs:
            f['obs'] = obs[:400]
            oa = num_del_texto(obs)
            if oa:
                f['oa'] = oa
        destino = por_clave if clave in areas_cat else claves_malas
        destino.setdefault(clave, {'com': com, 'sec': sec, 'fichas': []})
        destino[clave]['fichas'].append(f)
        if com and not destino[clave]['com']:
            destino[clave]['com'] = com

    # ── clasificar ──
    casos = []
    for clave, d in por_clave.items():
        pol = areas_cat[clave]
        fichas = d['fichas']
        dec = sum(f['a'] for f in fichas)
        exceso = dec - pol
        con_area = [f['a'] for f in fichas if f['a'] > 0]

        triple = [f for f in fichas
                  if f['a'] > 0 and abs(f['a'] - f['ar']) < 1
                  and abs(f['a'] - f['asr']) < 1]

        tipo = None
        if len(fichas) > 1 and exceso > TOLERANCIA_M2:
            iguales = len(set(con_area)) == 1 and len(con_area) > 1
            tipo = 'exceso'
        elif len(fichas) > 1 and pol and abs(exceso) / pol <= MARGEN_DIVIDIDO:
            tipo = 'dividido'
        elif triple:
            tipo = 'triple'
        if not tipo:
            continue

        caso = {
            'clave': clave, 'tipo': tipo,
            'com': d['com'] or '(sin comunidad)', 'sec': d['sec'] or '',
            'pol': round(pol), 'dec': round(dec), 'exc': round(exceso),
            'nf': len(fichas), 'fichas': fichas,
        }
        # «área repetida tres veces» puede convivir con los otros casos: un
        # predio con exceso puede además tener fichas con el triple valor. Si
        # fuera solo un tipo excluyente, esas fichas desaparecerían del filtro
        # y el recuento no daría las 54 que sabemos que hay.
        if triple:
            caso['triple'] = len(triple)
        if clave in contorno:
            caso['geo'] = redondear(contorno[clave])
        # ¿lo resuelven las observaciones?
        obs_areas = [f['oa'] for f in fichas if f.get('oa')]
        if tipo == 'exceso' and obs_areas:
            caso['obs_n'] = len(obs_areas)
            caso['obs_suma'] = sum(obs_areas)
            caso['resuelto_por_obs'] = (
                len(obs_areas) == len(fichas) and pol > 0
                and abs(sum(obs_areas) - pol) / pol <= MARGEN_DIVIDIDO)
        casos.append(caso)

    for clave, d in claves_malas.items():
        if not clave:
            continue
        casos.append({
            'clave': clave, 'tipo': 'clave_mala',
            'com': d['com'] or '(sin comunidad)', 'sec': d['sec'] or '',
            'pol': 0, 'dec': round(sum(f['a'] for f in d['fichas'])),
            'exc': 0, 'nf': len(d['fichas']), 'fichas': d['fichas'],
            'digitos': len(clave),
        })

    orden = {'exceso': 0, 'triple': 1, 'clave_mala': 2, 'dividido': 3}
    casos.sort(key=lambda c: (orden[c['tipo']], -c['exc'], -c['nf']))

    # ── canal, como referencia en el mapa ──
    canal = []
    if os.path.exists(CANAL):
        with open(CANAL, encoding='utf-8') as f:
            for ft in json.load(f).get('features', []):
                g = ft.get('geometry') or {}
                partes = (g['coordinates'] if g.get('type') == 'MultiLineString'
                          else [g.get('coordinates', [])])
                for parte in partes:
                    if len(parte) > 1:
                        canal.append(redondear(parte, 5))

    cuenta = {t: sum(1 for c in casos if c['tipo'] == t) for t in orden}
    exc_total = sum(c['exc'] for c in casos if c['tipo'] == 'exceso')
    resueltos = sum(1 for c in casos if c.get('resuelto_por_obs'))
    con_obs = sum(1 for c in casos if c.get('obs_n'))
    # fichas con el triple valor, estén en el caso que estén
    n_triple = sum(c.get('triple', 0) for c in casos)

    salida = {
        'generado': datetime.now().strftime('%Y-%m-%d %H:%M'),
        'corte': corte,
        'resumen': {
            'fichas': len(filas),
            'exceso': cuenta['exceso'], 'dividido': cuenta['dividido'],
            'triple': n_triple, 'triple_solo': cuenta['triple'],
            'clave_mala': cuenta['clave_mala'],
            'exc_ha': round(exc_total / 10000.0, 2),
            'con_obs': con_obs, 'resueltos_por_obs': resueltos,
        },
        'casos': casos,
        'canal': canal,
    }
    os.makedirs(os.path.dirname(SALIDA), exist_ok=True)
    with open(SALIDA, 'w', encoding='utf-8') as f:
        json.dump(salida, f, ensure_ascii=False, separators=(',', ':'))

    print("\n  predios con exceso      : {:>4}  ({:,.2f} ha de más)"
          .format(cuenta['exceso'], exc_total / 10000.0))
    print("     con área en las observaciones : {:>4}".format(con_obs))
    print("     que se resuelven copiándola   : {:>4}".format(resueltos))
    print("  bien divididos          : {:>4}".format(cuenta['dividido']))
    print("  área repetida tres veces: {:>4} fichas ({} en predios que además "
          "tienen otro problema)".format(n_triple, n_triple - cuenta['triple']))
    print("  clave inexistente       : {:>4}".format(cuenta['clave_mala']))
    print("\n  guardado: {} ({:,.0f} KB)"
          .format(os.path.relpath(SALIDA, BASE), os.path.getsize(SALIDA) / 1024))
    print("=" * 74)
    return 0


if __name__ == '__main__':
    sys.exit(main())
