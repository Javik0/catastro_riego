# -*- coding: utf-8 -*-
"""
Extracción e integración de la vía de acceso a la represa desde CAD (DWG/DXF).

Fuente
------
`CARTOGRAFIA REPRESA/procesado/proyecto_ploter_v1.dxf` (convertido desde
`PROYECTO PLOTER V1.dwg`, AutoCAD Civil 3D AC1032, ya en EPSG:32717 UTM 17S).

Qué genera en `padron-app/public/geo/represa/`
----------------------------------------------
1. `via_acceso.geojson`       Eje vial (`Eje1`, 6.011,78 m) + calzada cerrada
                              (`berma1`, ~6 m, 3,55 ha) + 4 líneas de berma.
2. `obras_via_acceso.geojson` 7 alcantarillas nuevas (`ALC-06` a `ALC-12`),
                              muro H.A., cruce de canal, campamento/caminería
                              en zona de presa e hitos PK cada 1 km.
3. `curvas_via_acceso.geojson` 1.454 curvas maestras (`CVL_CURV_G`, cada 5 m)
                              simplificadas (0,4 m) con su cota de elevación.
4. `predios_via_acceso.geojson` 28 predios del catastro rural GADM Cayambe
                              que intersecan `berma1` / `Eje1` (polígono
                              completo + franja de ocupación vial).
5. Actualiza `magnitud.json` añadiendo el bloque `via_acceso` sin alterar
   las cifras existentes del vaso ni del sistema de riego.

Uso
---
  C:\\OSGeo4W\\bin\\python-qgis.bat -X utf8 scripts/represa/08_via_acceso_cad.py
"""
import json
import math
import os
import re
import sys

PYLIBS_CARTO = os.path.expanduser(r'~\.pylibs\carto')
if os.path.isdir(PYLIBS_CARTO) and PYLIBS_CARTO not in sys.path:
    # append (no insert(0)) para no sombrear el numpy de Python 3.12 de OSGeo4W
    sys.path.append(PYLIBS_CARTO)

import ezdxf
from osgeo import ogr, osr

ogr.UseExceptions()
osr.UseExceptions()

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
RAIZ = os.path.abspath(os.path.join(BASE, '..'))
PROCESADO = os.path.join(RAIZ, 'CARTOGRAFIA REPRESA', 'procesado')
WEB = os.path.join(BASE, 'public', 'geo', 'represa')
GEO = os.path.join(BASE, 'public', 'geo')

DXF_CANDIDATOS = [
    os.path.join(PROCESADO, 'proyecto_ploter_v1.dxf'),
    os.path.join(os.environ.get('TEMP', ''), 'proyecto_ploter_v1.dxf'),
]
FICHAS = os.path.join(GEO, 'fichas_predios.geojson')
CODIFICACION = os.path.join(GEO, 'codificacion_fichas.json')
CATASTRO_GPKG = os.path.join(
    os.path.expanduser('~'), 'QField', 'cloud', 'porotog_levantamiento_offline',
    'CATASTROACTUALIZADORURALCATASTRORURALACTUALIZADO.gpkg')
CATASTRO_TABLA = 'CATASTROACTUALIZADORURALCATASTRORURALACTUALIZADO'

# Caja UTM 17S estricta de la zona Porotog–Izacata para descartar bloques o
# perfiles dibujados fuera de sitio en el CAD (ej. X ~ 26.650.000 o 748.000).
UTM_MIN_X, UTM_MAX_X = 816000.0, 825000.0
UTM_MIN_Y, UTM_MAX_Y = 9982000.0, 9991000.0

NOTA_CATASTRAL = {
    '1702606901': {
        'nombre': 'PÁRAMO CHICO',
        'tipo': 'Polígono Especial de Colindancia',
        'condicion': 'En litigio comunidad–Estado',
        'detalle': (
            'El GADM Cayambe informó en agosto de 2026 que este predio está en '
            'litigio entre las comunidades y el Estado; el pronunciamiento por '
            'escrito está pendiente. Un oficio de 2018 (Nº 269-JACR-2018, '
            'inspección Nº 422) lo daba por revertido al Estado desde la cota 3680 msnm.'
        ),
    },
}


def en_caja_utm(x, y):
    return UTM_MIN_X <= x <= UTM_MAX_X and UTM_MIN_Y <= y <= UTM_MAX_Y


def puntos_en_caja(pts):
    return bool(pts) and all(en_caja_utm(x, y) for x, y in pts)


def redondear_coords(obj, dec=6):
    if isinstance(obj, list):
        if obj and isinstance(obj[0], (int, float)):
            return [round(v, dec) for v in obj]
        return [redondear_coords(x, dec) for x in obj]
    return obj


def a_geojson_geom(geom_utm, tr_inv, dec=6):
    g = geom_utm.Clone()
    g.Transform(tr_inv)
    gj = json.loads(g.ExportToJson())
    if 'coordinates' in gj:
        gj['coordinates'] = redondear_coords(gj['coordinates'], dec)
    elif 'geometries' in gj:
        for sub in gj['geometries']:
            if 'coordinates' in sub:
                sub['coordinates'] = redondear_coords(sub['coordinates'], dec)
    return gj


def solo_poligonos(geom):
    """Extrae únicamente geometrías poligonales válidas de un resultado OGR."""
    if geom is None or geom.IsEmpty():
        return None
    t = ogr.GT_Flatten(geom.GetGeometryType())
    if t in (ogr.wkbPolygon, ogr.wkbMultiPolygon):
        return geom if geom.GetArea() > 0 else None
    if t == ogr.wkbGeometryCollection:
        mp = ogr.Geometry(ogr.wkbMultiPolygon)
        for i in range(geom.GetGeometryCount()):
            sub = solo_poligonos(geom.GetGeometryRef(i))
            if sub is None:
                continue
            st = ogr.GT_Flatten(sub.GetGeometryType())
            if st == ogr.wkbPolygon:
                mp.AddGeometry(sub)
            elif st == ogr.wkbMultiPolygon:
                for j in range(sub.GetGeometryCount()):
                    mp.AddGeometry(sub.GetGeometryRef(j))
        return mp if mp.GetGeometryCount() > 0 and mp.GetArea() > 0 else None
    return None


def puntos_hitos_eje(pts, paso_m=1000.0):
    """Interpola puntos kilométricos cada `paso_m` metros a lo largo de Eje1."""
    if len(pts) < 2:
        return []
    acum = [0.0]
    for i in range(1, len(pts)):
        dx = pts[i][0] - pts[i - 1][0]
        dy = pts[i][1] - pts[i - 1][1]
        acum.append(acum[-1] + math.hypot(dx, dy))
    total = acum[-1]

    objetivos = []
    d = 0.0
    while d < total - 1.0:
        objetivos.append((d, f'K{int(d // 1000)}+000'))
        d += paso_m
    km_fin = int(total // 1000)
    m_fin = int(round(total % 1000))
    objetivos.append((total, f'PF K{km_fin}+{m_fin:03d}'))

    hitos = []
    idx = 0
    for dist_obj, etiqueta in objetivos:
        while idx < len(acum) - 2 and acum[idx + 1] < dist_obj:
            idx += 1
        d0, d1 = acum[idx], acum[idx + 1]
        frac = 0.0 if d1 == d0 else max(0.0, min(1.0, (dist_obj - d0) / (d1 - d0)))
        x = pts[idx][0] + frac * (pts[idx + 1][0] - pts[idx][0])
        y = pts[idx][1] + frac * (pts[idx + 1][1] - pts[idx][1])
        hitos.append((etiqueta, round(dist_obj, 1), x, y))
    return hitos


def cargar_indices_padron():
    with open(CODIFICACION, encoding='utf-8') as f:
        cods = json.load(f).get('fichas', {})
    with open(FICHAS, encoding='utf-8') as f:
        datos = json.load(f)
    idx = {}
    for ft in datos.get('features', []):
        p = ft.get('properties') or {}
        claves = {
            str(p.get('clave_catastral') or '').strip(),
            str(p.get('cod_poligono') or '').strip(),
        }
        for c in claves:
            if c:
                idx.setdefault(c, []).append((p, cods.get(p.get('id'), '') or p.get('codigo_final') or ''))
    return idx


def leer_dxf():
    ruta_dxf = next((p for p in DXF_CANDIDATOS if p and os.path.exists(p)), None)
    if not ruta_dxf:
        raise FileNotFoundError('No se encontró proyecto_ploter_v1.dxf en procesado ni en TEMP')
    print(f'  leyendo DXF: {ruta_dxf}')
    doc = ezdxf.readfile(ruta_dxf)
    msp = doc.modelspace()

    eje_pts = None
    berma_poly_pts = None
    berma_lines = []
    curvas_5m = []
    obras_vec = []
    etiquetas_viales = []

    capas_obras_lin = {'AR-CAMINERIA', 'AR-DRENAJES', 'AR-PROYECCIONES', 'MURO H.A.', 'CVL_CANAL', 'SOBREANCHO'}

    for e in msp:
        lyr = e.dxf.layer
        t = e.dxftype()

        if lyr == 'Eje1' and t == 'LWPOLYLINE':
            pts = [(float(x), float(y)) for x, y in e.get_points('xy')]
            if len(pts) > 10 and puntos_en_caja(pts):
                eje_pts = pts

        elif lyr == 'berma1' and t == 'LWPOLYLINE':
            pts = [(float(x), float(y)) for x, y in e.get_points('xy')]
            if len(pts) > 10 and puntos_en_caja(pts):
                if e.closed:
                    berma_poly_pts = pts
                else:
                    berma_lines.append(pts)

        elif lyr == 'CVL_CURV_G' and t == 'LWPOLYLINE':
            pts = [(float(x), float(y)) for x, y in e.get_points('xy')]
            if len(pts) >= 2 and puntos_en_caja(pts):
                elev = float(getattr(e.dxf, 'elevation', 0.0) or 0.0)
                curvas_5m.append((elev, pts))

        elif lyr == 'C-ROAD-SCTN-TITL' and t in ('TEXT', 'MTEXT'):
            x, y = float(e.dxf.insert.x), float(e.dxf.insert.y)
            if en_caja_utm(x, y):
                txt = (e.dxf.text if t == 'TEXT' else e.plain_text()).replace('\n', ' ').strip()
                if txt:
                    etiquetas_viales.append((txt, x, y))

        elif lyr == 'CAMPAMENTO' and t == 'LWPOLYLINE':
            pts = [(float(x), float(y)) for x, y in e.get_points('xy')]
            if puntos_en_caja(pts):
                etiquetas_viales.append(('Campamento de obra', pts[0][0], pts[0][1]))

        elif lyr in capas_obras_lin:
            if t == 'LWPOLYLINE':
                pts = [(float(x), float(y)) for x, y in e.get_points('xy')]
                if len(pts) >= 2 and puntos_en_caja(pts):
                    obras_vec.append((lyr, e.closed, pts))
            elif t == 'LINE':
                pts = [(float(e.dxf.start.x), float(e.dxf.start.y)),
                       (float(e.dxf.end.x), float(e.dxf.end.y))]
                if puntos_en_caja(pts) and pts[0] != pts[1]:
                    obras_vec.append((lyr, False, pts))

    # Alcantarillas y rótulos dentro de bloques nombrados en coordenadas UTM reales
    alcantarillas = []
    if 'Alcantarillas Nuevas Porotog' in doc.blocks:
        for e in doc.blocks['Alcantarillas Nuevas Porotog']:
            t = e.dxftype()
            if t in ('TEXT', 'MTEXT'):
                x, y = float(e.dxf.insert.x), float(e.dxf.insert.y)
                if en_caja_utm(x, y):
                    txt = (e.dxf.text if t == 'TEXT' else e.plain_text()).replace('\n', ' ').strip()
                    txt = re.sub(r'\s+', ' ', txt)
                    m_num = re.search(r'N°\s*(\d+)', txt)
                    m_abs = re.search(r'Abs\.?\s*([0-9]+\+[0-9]+)', txt)
                    nombre = f"Alcantarilla N°{m_num.group(1)}" if m_num else 'Alcantarilla nueva'
                    if m_abs:
                        nombre += f" (Abs. {m_abs.group(1)})"
                    alcantarillas.append((nombre, txt, x, y))

    rotulos_presa = []
    if 'PresaTunelRapida' in doc.blocks:
        for e in doc.blocks['PresaTunelRapida']:
            t = e.dxftype()
            if t in ('TEXT', 'MTEXT'):
                x, y = float(e.dxf.insert.x), float(e.dxf.insert.y)
                if en_caja_utm(x, y):
                    txt = (e.dxf.text if t == 'TEXT' else e.plain_text()).replace('\n', ' ').strip()
                    if txt:
                        rotulos_presa.append((txt, x, y))

    if not eje_pts or not berma_poly_pts:
        raise RuntimeError('No se encontró Eje1 o el polígono cerrado de berma1 en el DXF')

    return {
        'eje_pts': eje_pts,
        'berma_poly_pts': berma_poly_pts,
        'berma_lines': berma_lines,
        'curvas_5m': curvas_5m,
        'obras_vec': obras_vec,
        'etiquetas_viales': etiquetas_viales,
        'alcantarillas': alcantarillas,
        'rotulos_presa': rotulos_presa,
    }


def wkt_linestring(pts):
    return 'LINESTRING (' + ', '.join(f'{x:.3f} {y:.3f}' for x, y in pts) + ')'


def wkt_polygon(pts):
    cerrada = list(pts)
    if cerrada[0] != cerrada[-1]:
        cerrada.append(cerrada[0])
    return 'POLYGON ((' + ', '.join(f'{x:.3f} {y:.3f}' for x, y in cerrada) + '))'


def main():
    print('=' * 74)
    print(' INTEGRACIÓN CAD VÍA DE ACCESO A LA REPRESA (PROYECTO PLOTER V1)')
    print('=' * 74)

    os.makedirs(WEB, exist_ok=True)
    utm = osr.SpatialReference()
    utm.ImportFromEPSG(32717)
    utm.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    wgs = osr.SpatialReference()
    wgs.ImportFromEPSG(4326)
    wgs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    tr_inv = osr.CoordinateTransformation(utm, wgs)

    cad = leer_dxf()

    eje_geom = ogr.CreateGeometryFromWkt(wkt_linestring(cad['eje_pts']))
    berma_geom = ogr.CreateGeometryFromWkt(wkt_polygon(cad['berma_poly_pts']))
    if not berma_geom.IsValid():
        berma_geom = berma_geom.MakeValid()
    berma_geom = solo_poligonos(berma_geom) or berma_geom

    longitud_m = round(eje_geom.Length(), 2)
    area_m2 = round(berma_geom.GetArea(), 2)
    area_ha = round(area_m2 / 10000.0, 2)
    print(f'  Eje1 longitud : {longitud_m:,.2f} m ({longitud_m / 1000:.2f} km)')
    print(f'  berma1 área   : {area_m2:,.2f} m² ({area_ha:.2f} ha)')

    # ── 1. via_acceso.geojson ────────────────────────────────────────────────
    via_feats = [
        {
            'type': 'Feature',
            'properties': {
                'tipo': 'calzada',
                'nombre': 'Calzada y berma vía de acceso (berma 6 m)',
                'area_m2': area_m2,
                'area_ha': area_ha,
                'longitud_m': longitud_m,
                'fuente': 'PROYECTO PLOTER V1.dwg (capa berma1)',
            },
            'geometry': a_geojson_geom(berma_geom, tr_inv),
        },
        {
            'type': 'Feature',
            'properties': {
                'tipo': 'eje',
                'nombre': 'Eje vial Eje 1 (K0+000 a PF)',
                'longitud_m': longitud_m,
                'fuente': 'PROYECTO PLOTER V1.dwg (capa Eje1)',
            },
            'geometry': a_geojson_geom(eje_geom, tr_inv),
        },
    ]
    for idx_b, bpts in enumerate(cad['berma_lines'], 1):
        bg = ogr.CreateGeometryFromWkt(wkt_linestring(bpts))
        via_feats.append({
            'type': 'Feature',
            'properties': {
                'tipo': 'berma',
                'nombre': f'Línea de berma {idx_b}',
                'longitud_m': round(bg.Length(), 2),
                'fuente': 'PROYECTO PLOTER V1.dwg (capa berma1)',
            },
            'geometry': a_geojson_geom(bg, tr_inv),
        })
    ruta_via = os.path.join(WEB, 'via_acceso.geojson')
    with open(ruta_via, 'w', encoding='utf-8') as f:
        json.dump({'type': 'FeatureCollection', 'features': via_feats}, f, ensure_ascii=False)
    print(f'  archivo: via_acceso.geojson ({os.path.getsize(ruta_via) / 1024:,.1f} KB)')

    # ── 2. obras_via_acceso.geojson ──────────────────────────────────────────
    obras_feats = []
    for nombre, detalle, x, y in cad['alcantarillas']:
        pt = ogr.CreateGeometryFromWkt(f'POINT ({x:.3f} {y:.3f})')
        obras_feats.append({
            'type': 'Feature',
            'properties': {
                'tipo_obra': 'alcantarilla',
                'nombre': nombre,
                'detalle': detalle,
                'fuente': 'PROYECTO PLOTER V1.dwg (Alcantarillas Nuevas Porotog)',
            },
            'geometry': a_geojson_geom(pt, tr_inv),
        })

    for txt, x, y in cad['etiquetas_viales']:
        pt = ogr.CreateGeometryFromWkt(f'POINT ({x:.3f} {y:.3f})')
        es_camp = 'campamento' in txt.lower()
        obras_feats.append({
            'type': 'Feature',
            'properties': {
                'tipo_obra': 'campamento' if es_camp else 'estructura_vial',
                'nombre': txt.title() if txt.isupper() else txt,
                'detalle': 'Zona norte (inicio vía)' if not es_camp else 'Zona de presa',
                'fuente': 'PROYECTO PLOTER V1.dwg',
            },
            'geometry': a_geojson_geom(pt, tr_inv),
        })

    for txt, x, y in cad['rotulos_presa']:
        pt = ogr.CreateGeometryFromWkt(f'POINT ({x:.3f} {y:.3f})')
        obras_feats.append({
            'type': 'Feature',
            'properties': {
                'tipo_obra': 'campamento',
                'nombre': txt,
                'detalle': 'Rótulo de zona de presa/maniobra en DWG',
                'fuente': 'PROYECTO PLOTER V1.dwg (PresaTunelRapida)',
            },
            'geometry': a_geojson_geom(pt, tr_inv),
        })

    for lyr, closed, pts in cad['obras_vec']:
        g = ogr.CreateGeometryFromWkt(wkt_polygon(pts) if (closed and len(pts) >= 3) else wkt_linestring(pts))
        if g.IsEmpty():
            continue
        es_camp = lyr in ('AR-CAMINERIA', 'AR-DRENAJES', 'AR-PROYECCIONES', 'SOBREANCHO')
        obras_feats.append({
            'type': 'Feature',
            'properties': {
                'tipo_obra': 'campamento' if es_camp else 'estructura_vial',
                'nombre': f'Obra CAD ({lyr})',
                'capa_cad': lyr,
                'fuente': 'PROYECTO PLOTER V1.dwg',
            },
            'geometry': a_geojson_geom(g, tr_inv),
        })

    for etiq, dist_m, x, y in puntos_hitos_eje(cad['eje_pts'], 1000.0):
        pt = ogr.CreateGeometryFromWkt(f'POINT ({x:.3f} {y:.3f})')
        obras_feats.append({
            'type': 'Feature',
            'properties': {
                'tipo_obra': 'abscisa',
                'nombre': etiq,
                'detalle': f'Abscisa {dist_m:,.0f} m sobre Eje 1',
                'fuente': 'PROYECTO PLOTER V1.dwg (Eje1)',
            },
            'geometry': a_geojson_geom(pt, tr_inv),
        })

    ruta_obras = os.path.join(WEB, 'obras_via_acceso.geojson')
    with open(ruta_obras, 'w', encoding='utf-8') as f:
        json.dump({'type': 'FeatureCollection', 'features': obras_feats}, f, ensure_ascii=False)
    print(f'  archivo: obras_via_acceso.geojson ({len(obras_feats)} elem, {os.path.getsize(ruta_obras) / 1024:,.1f} KB)')

    # ── 3. curvas_via_acceso.geojson ─────────────────────────────────────────
    curvas_feats = []
    for elev, pts in cad['curvas_5m']:
        g = ogr.CreateGeometryFromWkt(wkt_linestring(pts))
        gs = g.SimplifyPreserveTopology(0.4)
        if gs and not gs.IsEmpty():
            g = gs
        curvas_feats.append({
            'type': 'Feature',
            'properties': {'cota': round(elev, 1) if elev % 1 else int(elev)},
            'geometry': a_geojson_geom(g, tr_inv),
        })
    ruta_curvas = os.path.join(WEB, 'curvas_via_acceso.geojson')
    with open(ruta_curvas, 'w', encoding='utf-8') as f:
        json.dump({'type': 'FeatureCollection', 'features': curvas_feats}, f, ensure_ascii=False)
    print(f'  archivo: curvas_via_acceso.geojson ({len(curvas_feats)} curvas, {os.path.getsize(ruta_curvas) / 1024:,.1f} KB)')

    # ── 4. predios_via_acceso.geojson ────────────────────────────────────────
    fichas_idx = cargar_indices_padron()
    corredor = berma_geom.Union(eje_geom.Buffer(2.0))
    ds = ogr.Open(CATASTRO_GPKG, 0)
    capa = ds.GetLayerByName(CATASTRO_TABLA) or ds.GetLayer(0)
    capa.SetSpatialFilter(corredor)

    predios_reg = []
    predios_feats = []
    for ft in capa:
        geom_utm = ft.GetGeometryRef()
        if geom_utm is None or geom_utm.IsEmpty():
            continue
        geom_utm = geom_utm.Clone()
        toca_eje = geom_utm.Intersects(eje_geom)
        toca_berma = geom_utm.Intersects(berma_geom)
        if not (toca_eje or toca_berma):
            continue

        len_eje = geom_utm.Intersection(eje_geom).Length() if toca_eje else 0.0
        solape_raw = geom_utm.Intersection(berma_geom) if toca_berma else None
        solape_poly = solo_poligonos(solape_raw)
        m2_via = solape_poly.GetArea() if solape_poly else 0.0

        clave = str(ft.GetField('clave_cata') or '').strip()
        area_predio_m2 = geom_utm.GetArea()
        area_predio_ha = area_predio_m2 / 10000.0

        asociadas = fichas_idx.get(clave, [])
        principal = next((item for item in asociadas if not (item[0].get('es_ficha_hija') in (True, 1))), None)
        ficha, cod_ficha = (principal or (asociadas[0] if asociadas else (None, None)))

        muni_ap = str(ft.GetField('CATASTRO_U') or '').strip()
        muni_nom = str(ft.GetField('CATASTRO_1') or '').strip()
        muni_ced = str(ft.GetField('CATASTRO_2') or '').strip()
        muni_com = str(ft.GetField('CATASTRO_4') or '').strip()
        muni_nombre = ' '.join(x for x in (muni_ap, muni_nom) if x)

        if ficha:
            fuente = 'padron'
            propietario = ' '.join(
                x for x in (str(ficha.get('apellidos') or '').strip(), str(ficha.get('nombres') or '').strip()) if x
            ) or None
            cedula = (ficha.get('cedula') or '').strip() or None
            comunidad = (ficha.get('comunidad') or '').strip() or None
        elif muni_nombre:
            fuente = 'catastro_municipal'
            propietario = muni_nombre
            cedula = muni_ced or None
            comunidad = muni_com or None
        else:
            fuente = None
            propietario = None
            cedula = None
            comunidad = None

        nota = NOTA_CATASTRAL.get(clave, {})
        reg = {
            'clave': clave,
            'nombre_predio': nota.get('nombre'),
            'tipo_predio': nota.get('tipo'),
            'condicion': nota.get('condicion'),
            'detalle_condicion': nota.get('detalle'),
            'investigado': bool(asociadas),
            'fuente_propietario': fuente,
            'propietario': propietario,
            'cedula': cedula,
            'comunidad': comunidad,
            'codigo_ficha': cod_ficha or None,
            'tenencia': (ficha or {}).get('tenencia_predio'),
            'caudal_ls': (ficha or {}).get('caudal_valor'),
            'observaciones': ((ficha or {}).get('observaciones') or '').strip() or None,
            'fichas_en_el_predio': len(asociadas),
            'area_predio_ha': round(area_predio_ha, 2),
            'm2_en_via': round(m2_via, 1),
            'ha_en_via': round(m2_via / 10000.0, 4),
            'longitud_eje_m': round(len_eje, 1),
            'pct_del_predio': round(100.0 * m2_via / area_predio_m2, 2) if area_predio_m2 else 0.0,
        }
        predios_reg.append(reg)

        props_base = {
            'clave': reg['clave'],
            'nombre_predio': reg['nombre_predio'],
            'condicion': reg['condicion'],
            'investigado': reg['investigado'],
            'fuente_propietario': reg['fuente_propietario'],
            'propietario': reg['propietario'],
            'cedula': reg['cedula'],
            'comunidad': reg['comunidad'],
            'codigo_ficha': reg['codigo_ficha'],
            'tenencia': reg['tenencia'],
            'fichas_en_el_predio': reg['fichas_en_el_predio'],
            'area_predio_ha': reg['area_predio_ha'],
            'm2_en_via': reg['m2_en_via'],
            'ha_en_via': reg['ha_en_via'],
            'longitud_eje_m': reg['longitud_eje_m'],
            'pct_del_predio': reg['pct_del_predio'],
        }
        predios_feats.append({
            'type': 'Feature',
            'properties': {'tipo': 'predio', **props_base},
            'geometry': a_geojson_geom(geom_utm, tr_inv),
        })
        if solape_poly is not None:
            predios_feats.append({
                'type': 'Feature',
                'properties': {'tipo': 'solape', **props_base},
                'geometry': a_geojson_geom(solape_poly, tr_inv),
            })

    ds = None
    orden_fuente = {'padron': 0, 'catastro_municipal': 1, None: 2}
    predios_reg.sort(key=lambda r: (orden_fuente.get(r['fuente_propietario'], 2), -r['m2_en_via'], -r['longitud_eje_m'], r['clave']))

    ruta_pv = os.path.join(WEB, 'predios_via_acceso.geojson')
    with open(ruta_pv, 'w', encoding='utf-8') as f:
        json.dump({'type': 'FeatureCollection', 'features': predios_feats}, f, ensure_ascii=False)
    print(f'  archivo: predios_via_acceso.geojson ({len(predios_reg)} predios, {len(predios_feats)} features, {os.path.getsize(ruta_pv) / 1024:,.1f} KB)')

    # ── 5. Actualizar magnitud.json ──────────────────────────────────────────
    ruta_mag = os.path.join(WEB, 'magnitud.json')
    with open(ruta_mag, encoding='utf-8') as f:
        magnitud = json.load(f)

    n_padron = sum(1 for r in predios_reg if r['fuente_propietario'] == 'padron')
    n_muni = sum(1 for r in predios_reg if r['fuente_propietario'] == 'catastro_municipal')
    n_sin = sum(1 for r in predios_reg if r['fuente_propietario'] is None)

    magnitud['via_acceso'] = {
        'longitud_km': round(longitud_m / 1000.0, 2),
        'longitud_m': round(longitud_m, 1),
        'ancho_m': 6.0,
        'area_ha': area_ha,
        'area_m2': round(area_m2, 1),
        'total_predios': len(predios_reg),
        'predios_padron': n_padron,
        'predios_catastro_muni': n_muni,
        'predios_sin_titular': n_sin,
        'm2_padron': round(sum(r['m2_en_via'] for r in predios_reg if r['fuente_propietario'] == 'padron'), 1),
        'm2_catastro_muni': round(sum(r['m2_en_via'] for r in predios_reg if r['fuente_propietario'] == 'catastro_municipal'), 1),
        'm2_sin_titular': round(sum(r['m2_en_via'] for r in predios_reg if r['fuente_propietario'] is None), 1),
        'alcantarillas': len(cad['alcantarillas']),
        'predios': predios_reg,
    }
    with open(ruta_mag, 'w', encoding='utf-8') as f:
        json.dump(magnitud, f, ensure_ascii=False, indent=2)

    print(f'  predios en vía: {len(predios_reg)} total ({n_padron} padrón, {n_muni} municipal, {n_sin} sin titular)')
    print('  magnitud.json actualizado con bloque via_acceso.')
    print('=' * 74)
    return 0


if __name__ == '__main__':
    sys.exit(main())
