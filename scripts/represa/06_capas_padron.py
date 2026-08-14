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

Sobre qué predios se levanta la obra
------------------------------------
Se cruza el límite de proyecto contra el **catastro rural completo** del GADM
—los 24.460 polígonos, no solo los que tienen ficha— y se mide la intersección
en UTM 17S (en grados el área no significa nada).

Contra el catastro completo y no contra los predios investigados por un motivo
concreto: en agosto de 2026 se comprobó que el vaso cae sobre el PÁRAMO CHICO,
un predio **sin ficha** porque es del Estado. Mirando solo lo investigado, la
pantalla no diría nada y parecería que la obra no toca predio alguno.

Y no se resuelve con los puntos GPS de las fichas: ninguno cae dentro del
límite, porque el punto es donde el técnico levantó la encuesta, no el predio.
Buscando por puntos el resultado es «no hay nada» y es engañoso.

Salidas
-------
public/geo/represa/predios_por_sector.geojson   puntos: solo sector y comunidad
public/geo/represa/sectores_huella.geojson      3 poligonos simplificados
public/geo/represa/predios_en_vaso.geojson      predios que ocupa la obra + solape
public/geo/represa/magnitud.json                cifras para el panel de la vista
"""
import json
import os
import sys

from osgeo import ogr, osr

ogr.UseExceptions()

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
RAIZ = os.path.abspath(os.path.join(BASE, '..'))
GEO = os.path.join(BASE, 'public', 'geo')
WEB = os.path.join(GEO, 'represa')

FICHAS = os.path.join(GEO, 'fichas_predios.geojson')
SECTORES = os.path.join(GEO, 'sectores.geojson')
CATASTRO = os.path.join(GEO, 'catastro_geo.geojson')
LIMITE = os.path.join(WEB, 'limite_proyecto.geojson')

# Catastro rural completo del GADM Cayambe, tal como llega al proyecto de campo.
CATASTRO_GPKG = os.path.join(
    os.path.expanduser('~'), 'QField', 'cloud', 'porotog_levantamiento_offline',
    'CATASTROACTUALIZADORURALCATASTRORURALACTUALIZADO.gpkg')
CATASTRO_TABLA = 'CATASTROACTUALIZADORURALCATASTRORURALACTUALIZADO'

# Lo que el polígono no dice y hay que saber para decidir.
#
# El GeoPackage del catastro trae la geometría y la clave, pero los campos de
# titular y observaciones vienen vacíos en estos predios: esa información está
# en el sistema catastral del municipio, no en el archivo. Se transcribe aquí
# lo consultado en la ficha catastral del GADM Cayambe, con su oficio, para que
# la pantalla pueda explicar sobre qué se levanta la obra.
#
# Fuente: ficha catastral del GADM Cayambe, consultada por Armando Proaño el
# 13 de agosto de 2026; copia de los oficios en su poder.
NOTA_CATASTRAL = {
    '1702606901': {
        'nombre': 'PÁRAMO CHICO',
        'tipo': 'Polígono Especial de Colindancia',
        'condicion': 'Predio del Estado',
        'detalle': ('Revertido al Estado a partir de la cota 3680 msnm — Oficio '
                    'Nº 269-JACR-2018, inspección Nº 422 del 26/09/2018 (GADM Cayambe).'),
    },
}

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


def transformadores():
    """(WGS84 → UTM 17S, UTM 17S → WGS84).

    Las áreas solo se miden en metros, nunca en grados; la web solo entiende
    grados. Por eso hacen falta los dos sentidos.
    """
    wgs = osr.SpatialReference()
    wgs.ImportFromEPSG(4326)
    wgs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    utm = osr.SpatialReference()
    utm.ImportFromEPSG(32717)
    utm.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    return (osr.CoordinateTransformation(wgs, utm),
            osr.CoordinateTransformation(utm, wgs))


def indice_fichas_por_clave():
    """clave catastral → fichas del padrón que la declaran.

    Se indexa por `clave_catastral` y por `cod_poligono` porque no siempre
    coinciden y el polígono del catastro puede venir por cualquiera de las dos.
    """
    with open(FICHAS, encoding='utf-8') as f:
        datos = json.load(f)
    idx = {}
    for ft in datos.get('features', []):
        p = ft.get('properties') or {}
        claves = {str(p.get('clave_catastral') or '').strip(),
                  str(p.get('cod_poligono') or '').strip()}
        for c in claves:
            if c:
                idx.setdefault(c, []).append((p, ft.get('geometry')))
    return idx


def ocupacion_del_vaso(limite, tr):
    """Predios catastrales sobre los que se levanta la obra.

    Recorre el catastro rural completo con filtro espacial —así no hay que
    reproyectar 24.460 polígonos para quedarse con dos— y para cada predio que
    toca el límite dice cuánto ocupa, si el padrón lo investigó y qué se sabe de
    su condición jurídica.

    Devuelve (resumen, features): el resumen alimenta el panel de la pantalla y
    los features se escriben como capa para resaltarlos en el mapa.
    """
    limite_utm = limite.Clone()
    limite_utm.Transform(tr)
    area_vaso = limite_utm.GetArea() / 10000.0

    fichas = indice_fichas_por_clave()
    ds = ogr.Open(CATASTRO_GPKG, 0)
    if ds is None:
        raise IOError('no se pudo abrir {}'.format(CATASTRO_GPKG))
    capa = ds.GetLayerByName(CATASTRO_TABLA) or ds.GetLayer(0)
    # El catastro del GADM viene en UTM 17S y el límite en grados: el filtro hay
    # que dárselo ya reproyectado o no encuentra nada y el resultado es un cero
    # que parece un dato.
    capa.SetSpatialFilter(limite_utm)

    predios, features = [], []
    for ft in capa:
        geom_utm = ft.GetGeometryRef()
        if geom_utm is None or geom_utm.IsEmpty():
            continue
        geom_utm = geom_utm.Clone()
        solape = geom_utm.Intersection(limite_utm)
        ha = solape.GetArea() / 10000.0 if solape and not solape.IsEmpty() else 0.0
        if ha < 0.01:
            continue          # roce de bordes, no ocupación real

        clave = str(ft.GetField('clave_cata') or '').strip()
        # el titular se resuelve desde la ficha: el catastro lo trae vacío en
        # los predios grandes, justo en los que interesan aquí
        asociadas = fichas.get(clave, [])
        principal = next((f for f in asociadas
                          if not (f[0].get('es_ficha_hija') in (True, 1))), None)
        ficha, punto = (principal or (asociadas[0] if asociadas else (None, None)))

        dist = None
        if punto and punto.get('type') == 'Point':
            pt = ogr.CreateGeometryFromJson(json.dumps(punto))
            pt.Transform(tr)
            dist = round(pt.Distance(limite_utm))

        nombre = ''
        if ficha:
            nombre = ' '.join(x for x in [str(ficha.get('apellidos') or '').strip(),
                                          str(ficha.get('nombres') or '').strip()] if x)

        nota = NOTA_CATASTRAL.get(clave, {})
        area_predio = geom_utm.GetArea() / 10000.0
        registro = {
            'clave': clave,
            'nombre_predio': nota.get('nombre'),
            'tipo_predio': nota.get('tipo'),
            'condicion': nota.get('condicion'),
            'detalle_condicion': nota.get('detalle'),
            'investigado': bool(asociadas),
            'propietario': nombre or None,
            'cedula': (ficha or {}).get('cedula'),
            'comunidad': (ficha or {}).get('comunidad'),
            'codigo_ficha': (ficha or {}).get('codigo_final'),
            'tenencia': (ficha or {}).get('tenencia_predio'),
            'caudal_ls': (ficha or {}).get('caudal_valor'),
            'observaciones': ((ficha or {}).get('observaciones') or '').strip() or None,
            'fichas_en_el_predio': len(asociadas),
            'area_predio_ha': round(area_predio, 2),
            'ha_en_vaso': round(ha, 2),
            'pct_del_vaso': round(100 * ha / area_vaso, 1) if area_vaso else None,
            'pct_del_predio': round(100 * ha / area_predio, 1) if area_predio else None,
            'distancia_punto_m': dist,
        }
        predios.append(registro)
        features.append({'tipo': 'predio', 'geom_utm': geom_utm, 'reg': registro})
        features.append({'tipo': 'solape', 'geom_utm': solape, 'reg': registro})
    ds = None

    predios.sort(key=lambda r: r['ha_en_vaso'], reverse=True)
    cubierta = sum(r['ha_en_vaso'] for r in predios)
    investigada = sum(r['ha_en_vaso'] for r in predios if r['investigado'])
    resumen = {
        'area_ha': round(area_vaso, 2),
        'cubierta_ha': round(cubierta, 2),
        'cubierta_pct': round(100 * cubierta / area_vaso, 1) if area_vaso else None,
        'libre_ha': round(area_vaso - cubierta, 2),
        # lo que de verdad obliga a negociar con alguien del padrón
        'investigada_ha': round(investigada, 2),
        'predios': predios,
    }
    return resumen, features


def escribir_predios_en_vaso(features, tr_inverso):
    """Capa de resaltado: el predio completo y la parte que ocupa la obra."""
    ruta = os.path.join(WEB, 'predios_en_vaso.geojson')
    if os.path.exists(ruta):
        os.remove(ruta)
    salida = {'type': 'FeatureCollection', 'features': []}
    for f in features:
        geom = f['geom_utm'].Clone()
        geom.Transform(tr_inverso)          # todo se mide en UTM y se publica en grados
        r = f['reg']
        salida['features'].append({
            'type': 'Feature',
            'properties': {
                'tipo': f['tipo'], 'clave': r['clave'], 'propietario': r['propietario'],
                'comunidad': r['comunidad'], 'codigo_ficha': r['codigo_ficha'],
                'ha_en_vaso': r['ha_en_vaso'], 'pct_del_vaso': r['pct_del_vaso'],
                'area_predio_ha': r['area_predio_ha'],
                'nombre_predio': r['nombre_predio'], 'condicion': r['condicion'],
                'investigado': r['investigado'],
            },
            'geometry': json.loads(geom.ExportToJson()),
        })
    with open(ruta, 'w', encoding='utf-8') as fh:
        json.dump(salida, fh, ensure_ascii=False)
    return ruta


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
    limite_geom = ft.GetGeometryRef().Clone()
    ds = None

    # ── sobre qué predios se levanta la obra ──
    vaso = None
    if os.path.exists(CATASTRO_GPKG):
        tr, tr_inv = transformadores()
        vaso, feats = ocupacion_del_vaso(limite_geom, tr)
        ruta_v = escribir_predios_en_vaso(feats, tr_inv)
        print("\n  sobre que se levanta la obra")
        print("      area de proyecto         : {:,.2f} ha".format(vaso['area_ha']))
        print("      sobre predio catastrado  : {:,.2f} ha ({}%)"
              .format(vaso['cubierta_ha'], vaso['cubierta_pct']))
        print("      sin predio catastrado    : {:,.2f} ha".format(vaso['libre_ha']))
        print("      sobre predio INVESTIGADO : {:,.2f} ha".format(vaso['investigada_ha']))
        for r in vaso['predios']:
            print("      · {} {} · {:,.2f} ha ({}% del vaso, {}% del predio)"
                  .format(r['clave'], '— ' + r['nombre_predio'] if r['nombre_predio'] else '',
                          r['ha_en_vaso'], r['pct_del_vaso'], r['pct_del_predio']))
            if r['condicion']:
                print("        {}".format(r['condicion']))
            if r['investigado']:
                print("        ⚠ INVESTIGADO por el padron: ficha {} de {}"
                      .format(r['codigo_ficha'], r['propietario']))
            else:
                print("        sin ficha en el padron")
        print("      archivo: {}  ({:,.0f} KB)"
              .format(os.path.basename(ruta_v), os.path.getsize(ruta_v) / 1024))
    else:
        print("\n  ⚠ falta el gpkg del catastro rural: no se calcula la ocupacion del vaso")

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
        'vaso': vaso,
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
