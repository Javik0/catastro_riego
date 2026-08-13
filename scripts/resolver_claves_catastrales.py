# -*- coding: utf-8 -*-
"""
Encuentra la clave catastral correcta de las fichas cuya clave no existe.

El problema
-----------
Un puñado de fichas trae una clave catastral que no está en el catastro del
GADM Cayambe. Mientras no se resuelvan, esos predios quedan fuera de cualquier
cálculo que se apoye en el catastro — y desde que el área oficial es la del
catastro, eso importa.

Casi todas las claves del catastro tienen 13 dígitos (5.959 de 5.994), pero hay
28 de 23 dígitos y 7 de 10, así que **el número de dígitos por sí solo no dice
si una clave es válida**. Lo que decide es si existe o no en el catastro.

Cómo la deduce
--------------
Estas fichas sí tienen coordenadas, así que se mira **sobre qué predio del
catastro cae el punto**. Si cae limpio dentro de uno solo, esa es su clave.

Antes de proponer nada se leen las **observaciones del técnico**, y ahí está la
razón de ser de este orden: ocho de estas fichas son de Asociación Rosalía y su
observación dice «el predio posee clave catastral perteneciente al DMQ». No son
erratas — son predios del **Distrito Metropolitano de Quito**, con su clave
correcta de otro catastro. Corregirlas por ubicación habría machacado un dato
bueno. Por eso cualquier ficha con observación se lista aparte para que la vea
una persona, aunque el punto caiga limpio dentro de un predio.

Cuando la propuesta es buena suele confirmarse sola: el área que declaró el
técnico coincide **exactamente** con la del polígono propuesto, lo que indica
que copió bien la superficie del catastro y se equivocó solo al teclear la
clave.

De regalo, el script compara la clave escrita con la del predio donde cae y
dice en qué se diferencian: casi siempre es un dígito de más, uno de menos o
dos cambiados de sitio, y verlo confirma que la propuesta es la buena.

Uso
---
    "C:\\OSGeo4W\\bin\\python-qgis.bat" -X utf8 scripts/resolver_claves_catastrales.py
    "C:\\OSGeo4W\\bin\\python-qgis.bat" -X utf8 scripts/resolver_claves_catastrales.py --aplicar

Sin `--aplicar` no escribe nada (regla 7). Solo se aplican las que caen dentro
de un único predio y no tienen observación que las explique.
"""
import argparse
import json
import os
import sqlite3
import sys
import time

from osgeo import ogr, osr

ogr.UseExceptions()

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
GPKG = os.path.join(os.path.expanduser('~'), 'QField', 'cloud',
                    'porotog_levantamiento_offline', 'data.gpkg')
CATASTRO = os.path.join(BASE, 'public', 'geo', 'catastro_geo.geojson')
RAIZ_RESPALDOS = (r"C:\Users\HP\OneDrive\Escritorio\CAYAMBE CATASTRO RIEGO"
                  r"\respaldos_qgs")
TABLA = 'Fichas_Predios_880eb10d_d887_4fc6_99a2_8af3ac63877e'

# Hasta esta distancia se acepta «cae justo al lado del predio»; más allá, no.
BORDE_M = 15
# Si el área declarada y la del polígono coinciden dentro de esto, la propuesta
# se confirma sola: el técnico copió bien la superficie y falló al teclear.
COINCIDE_AREA = 0.02


def respaldo_sqlite(origen, etiqueta):
    carpeta = os.path.join(RAIZ_RESPALDOS, time.strftime('%Y-%m-%d'))
    os.makedirs(carpeta, exist_ok=True)
    destino = os.path.join(carpeta, '{}.{}-{}.bak'.format(
        os.path.basename(origen), time.strftime('%H%M'), etiqueta))
    src = sqlite3.connect(origen); dst = sqlite3.connect(destino)
    with dst:
        src.backup(dst)
    dst.close(); src.close()
    return destino


def diferencia(escrita, real):
    """En qué se diferencian dos claves, en lenguaje llano."""
    if escrita == real:
        return 'idéntica'
    if len(escrita) == len(real) + 1 and real in escrita:
        return 'le sobra un dígito'
    if len(escrita) + 1 == len(real) and escrita in real:
        return 'le falta un dígito'
    if escrita.startswith(real):
        return 'le sobran {} dígitos al final'.format(len(escrita) - len(real))
    if real.startswith(escrita):
        return 'le faltan {} dígitos al final'.format(len(real) - len(escrita))
    if sorted(escrita) == sorted(real):
        return 'los mismos dígitos en otro orden'
    iguales = sum(1 for a, b in zip(escrita, real) if a == b)
    return 'coincide en {} de {} dígitos'.format(iguales, max(len(escrita), len(real)))


def analizar(gpkg=None, catastro=None):
    """Clasifica las fichas de clave inexistente. Sin efectos secundarios.

    Devuelve (proponibles, con_obs, sin_resolver). Lo usa tanto este script
    como `generar_auditoria_areas.py`, para que la pantalla web muestre la
    misma propuesta que se aplicaría y no haya dos criterios distintos.
    """
    gpkg = gpkg or GPKG
    catastro = catastro or CATASTRO

    geo = osr.SpatialReference(); geo.ImportFromEPSG(4326)
    utm = osr.SpatialReference(); utm.ImportFromEPSG(32717)
    geo.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    utm.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    tr = osr.CoordinateTransformation(geo, utm)

    with open(catastro, encoding='utf-8') as f:
        datos = json.load(f)
    predios, validas = [], set()
    for ft in datos.get('features', []):
        p = ft.get('properties') or {}
        clave = str(p.get('clave_cata') or '').strip()
        if not clave:
            continue
        validas.add(clave)
        g = ogr.CreateGeometryFromJson(json.dumps(ft['geometry']))
        if g is None:
            continue
        g.Transform(tr)
        predios.append((clave, float(p.get('area_predi') or 0), g))

    con = sqlite3.connect(gpkg)
    cur = con.cursor()
    cur.execute(
        "SELECT COALESCE(id,''), TRIM(COALESCE(clave_catastral,'')), "
        "TRIM(COALESCE(apellidos,'') || ' ' || COALESCE(nombres,'')), "
        "COALESCE(comunidad,''), COALESCE(coord_x_utm,0), COALESCE(coord_y_utm,0), "
        "COALESCE(observaciones,''), COALESCE(area_total,0), COALESCE(creado_por,'') "
        'FROM "{}" WHERE TRIM(COALESCE(clave_catastral,\'\')) <> \'\''.format(TABLA))
    malas = [f for f in cur.fetchall() if f[1] not in validas]
    con.close()

    proponibles, con_obs, sin_resolver = [], [], []
    for uid, clave, nombre, com, x, y, obs, area, tec in malas:
        item = {'uid': uid, 'clave': clave, 'nombre': nombre, 'com': com,
                'obs': (obs or '').strip(), 'area': area, 'tec': tec,
                'digitos': len(clave)}
        dentro, cerca = [], None
        if x and y:
            p = ogr.Geometry(ogr.wkbPoint); p.AddPoint_2D(x, y)
            for ck, ca, g in predios:
                if g.Contains(p):
                    dentro.append((ck, ca))
            if not dentro:
                d = sorted((p.Distance(g), ck, ca) for ck, ca, g in predios)
                if d and d[0][0] <= BORDE_M:
                    cerca = d[0]
        item['dentro'] = dentro
        item['cerca'] = cerca

        if item['obs']:
            # Ocho de estas dicen que la clave es del DMQ: no es una errata.
            item['dmq'] = 'DMQ' in item['obs'].upper() or 'QUITO' in item['obs'].upper()
            con_obs.append(item)
        elif len(dentro) == 1:
            item['propuesta'], item['area_pol'] = dentro[0]
            item['dif'] = diferencia(clave, dentro[0][0])
            item['area_confirma'] = (
                item['area_pol'] > 0
                and abs(area - item['area_pol']) / item['area_pol'] <= COINCIDE_AREA)
            proponibles.append(item)
        elif cerca:
            item['motivo'] = 'a {:.0f} m del predio {}'.format(cerca[0], cerca[1])
            sin_resolver.append(item)
        elif len(dentro) > 1:
            item['motivo'] = 'cae en {} predios a la vez'.format(len(dentro))
            sin_resolver.append(item)
        else:
            item['motivo'] = ('sin coordenadas' if not (x and y)
                              else 'no cae en ningún predio del catastro')
            sin_resolver.append(item)
    return proponibles, con_obs, sin_resolver


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--aplicar', action='store_true',
                    help='escribe en el data.gpkg (sin esto solo simula)')
    args = ap.parse_args()

    print("=" * 80)
    print(" CLAVES CATASTRALES QUE NO EXISTEN" +
          ("  [APLICAR]" if args.aplicar else "  [SIMULACION - no escribe nada]"))
    print("=" * 80)

    for ruta, que in ((GPKG, 'data.gpkg'), (CATASTRO, 'catastro_geo.geojson')):
        if not os.path.exists(ruta):
            print("ERROR: no se encuentra {}:\n  {}".format(que, ruta))
            return 1

    proponibles, con_obs, sin_resolver = analizar()
    print("\n  fichas con clave inexistente: {}"
          .format(len(proponibles) + len(con_obs) + len(sin_resolver)))
    # ── 1. las que tienen observación: las mira una persona ──
    print("\n" + "-" * 80)
    print(" CON OBSERVACION DEL TECNICO — no se tocan, la observación manda")
    print("-" * 80)
    if not con_obs:
        print("   ninguna")
    for i in con_obs:
        print("\n   {:<20} {} dígitos · {} · {}".format(
            i['clave'], i['digitos'], i['com'][:22], i['nombre'][:30]))
        print("      obs: {}".format(i['obs'][:150]))
        if len(i['dentro']) == 1:
            print("      (el punto cae dentro del predio {}, por si sirve)"
                  .format(i['dentro'][0][0]))
        elif i['cerca']:
            print("      (el punto está a {:.0f} m del predio {})"
                  .format(i['cerca'][0], i['cerca'][1]))
        else:
            print("      (el punto no cae dentro de ningún predio)")

    # ── 2. sin observación y con predio claro: propuesta ──
    print("\n" + "-" * 80)
    print(" SIN OBSERVACION Y CAEN EN UN SOLO PREDIO — se puede corregir")
    print("-" * 80)
    if not proponibles:
        print("   ninguna")
    else:
        print("   {:<20} {:>4}  {:<15} {:<26} {}".format(
            'CLAVE ESCRITA', 'díg', 'CLAVE DEL PREDIO', 'EN QUE SE DIFERENCIAN', 'REGANTE'))
        for i in proponibles:
            print("   {:<20} {:>4}  {:<15} {:<26} {}".format(
                i['clave'], i['digitos'], i['propuesta'], i['dif'], i['nombre'][:26]))
        print("\n   comprobación independiente — el área declarada contra la del polígono:")
        confirmadas = sum(1 for i in proponibles if i['area_confirma'])
        for i in proponibles:
            print("      {} · declara {:>9,.0f} m² · polígono {:>9,.0f} m²  {}"
                  .format(i['propuesta'], i['area'], i['area_pol'],
                          'COINCIDE' if i['area_confirma'] else '(no coincide)'))
        print("\n   {} de {} quedan confirmadas por el área: el técnico copió bien la"
              .format(confirmadas, len(proponibles)))
        print("   superficie del catastro y se equivocó solo al teclear la clave.")

    # ── 3. el resto ──
    print("\n" + "-" * 80)
    print(" SIN RESOLVER — hace falta mirarlas")
    print("-" * 80)
    if not sin_resolver:
        print("   ninguna")
    for i in sin_resolver:
        print("   {:<20} {} dígitos · {:<20} {:<28} {}".format(
            i['clave'], i['digitos'], i['com'][:20], i['nombre'][:28], i['motivo']))

    print("\n" + "=" * 80)
    print("  con observación (no se tocan) : {:>3}".format(len(con_obs)))
    print("  se pueden corregir            : {:>3}".format(len(proponibles)))
    print("  sin resolver                  : {:>3}".format(len(sin_resolver)))

    if not args.aplicar:
        print("\n  SIMULACION: no se escribió nada.")
        print("  Para aplicar solo las corregibles, repetir con --aplicar.")
        print("=" * 80)
        return 0

    if not proponibles:
        print("\n  Nada que aplicar.")
        return 0

    print("\n  respaldando antes de tocar nada...")
    print("     {}".format(respaldo_sqlite(GPKG, 'antes-claves-catastrales')))

    t = '"{}"'.format(TABLA)
    con = sqlite3.connect(GPKG)
    cur = con.cursor()
    cur.execute("SELECT name, sql FROM sqlite_master "
                "WHERE type='trigger' AND tbl_name=?", (TABLA,))
    triggers = cur.fetchall()
    for nombre, _ in triggers:
        cur.execute('DROP TRIGGER IF EXISTS "{}"'.format(nombre))
    try:
        n = 0
        for i in proponibles:
            cur.execute("UPDATE {} SET clave_catastral = ? WHERE id = ?".format(t),
                        (i['propuesta'], i['uid']))
            n += cur.rowcount
    finally:
        for _, sql in triggers:
            if sql:
                cur.execute(sql)
    con.commit()
    cur.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    con.close()
    print("     {} fichas actualizadas · {} triggers recreados".format(n, len(triggers)))

    # verificación releyendo del disco: se vuelve a clasificar desde cero
    p2, o2, s2 = analizar()
    esperado = len(con_obs) + len(sin_resolver)
    quedan = len(p2) + len(o2) + len(s2)
    print("\n  VERIFICACION (releyendo del disco):")
    print("     fichas con clave inexistente: {} · se esperaban {}"
          .format(quedan, esperado))
    print("     (las que tienen observación y las que no se pudieron ubicar)")
    print("\n  {}".format('CORRECCION APLICADA Y VERIFICADA' if quedan == esperado
                          else '!! REVISAR: no coincide con lo previsto'))
    print("=" * 80)
    return 0 if quedan == esperado else 1


if __name__ == '__main__':
    sys.exit(main())
