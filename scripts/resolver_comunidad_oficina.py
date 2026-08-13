# -*- coding: utf-8 -*-
"""
Asigna comunidad a las fichas que no la tienen, sin salir a campo.

Por qué en oficina y no en campo
--------------------------------
Hasta el 9 de agosto de 2026 estas fichas figuraban como trabajo de campo. No
lo son: **todas tienen coordenadas**, así que la comunidad se deduce de dónde
está el predio. Decisión del cliente ese día; ver `generar_revision_campo.py`.

Cómo lo deduce, por orden de confianza
--------------------------------------
1. **Por el predio** — si otra ficha con la misma clave catastral ya tiene
   comunidad, es esa. Es la vía más segura: no depende de ninguna geometría,
   solo de que dos fichas hablen del mismo predio.
2. **Por traslape** — el punto de la ficha dentro del polígono de una comunidad
   (`public/geo/comunidades.geojson`). Es el cruce que ya usa
   `scripts/represa/06_capas_padron.py`.
3. **Por vecindad** — la comunidad de las fichas vecinas que sí la tienen.

Por qué hace falta la vía 3, que no es la obvia
-----------------------------------------------
El traslape por sí solo resuelve muy poco, y la razón es circular: la capa de
comunidades es el **dissolve de los predios que ya tienen comunidad**, así que
los que no la tienen quedan fuera de ella por construcción. Medido: de 120
fichas, solo 16 caen dentro de un polígono; el resto se queda a 5–90 m del
borde, casi siempre de una única comunidad candidata.

Mirar a los vecinos evita esa trampa: se toman las `--vecinos` fichas con
comunidad más cercanas y, si hay consenso suficiente (`--consenso`) y están lo
bastante cerca (`--radio`), esa es la comunidad. Un predio a 18 m del borde de
San José y rodeado de fichas de San José es de San José.

Cuando dos vías dan resultados distintos, la ficha se marca para revisar en vez
de elegir por su cuenta.

Los nombres se comparan canonizados con `comunidades_canon.py` (regla 4 del
proyecto): «ASOCIACIÓN 17 DE JUNIO» y «ASOCIACION 17 DE JUNIO» son la misma.

⚠ El cruce es SIEMPRE espacial, nunca por nombre. Hay comunidades homónimas que
designan sitios distintos: “Asociación Porotog” del shapefile oficial es nuestra
*Asociación 17 de Junio*, mientras que nuestra *Asociación Porotog* cae en “San
Vicente de Porotog”.

Uso
---
    "C:\\OSGeo4W\\bin\\python-qgis.bat" -X utf8 scripts/resolver_comunidad_oficina.py
    "C:\\OSGeo4W\\bin\\python-qgis.bat" -X utf8 scripts/resolver_comunidad_oficina.py --aplicar

Sin `--aplicar` no escribe nada (regla 7). Con `--aplicar` respalda antes con la
API de backup de SQLite, retira y recrea los triggers espaciales, y verifica
releyendo del disco.
"""
import argparse
import json
import os
import shutil
import sqlite3
import sys
import tempfile
import time

from osgeo import ogr, osr

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from comunidades_canon import canonica  # noqa: E402

ogr.UseExceptions()

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
GPKG = os.path.join(os.path.expanduser('~'), 'QField', 'cloud',
                    'porotog_levantamiento_offline', 'data.gpkg')
COMUNIDADES = os.path.join(BASE, 'public', 'geo', 'comunidades.geojson')
RAIZ_RESPALDOS = (r"C:\Users\HP\OneDrive\Escritorio\CAYAMBE CATASTRO RIEGO"
                  r"\respaldos_qgs")
TABLA = 'Fichas_Predios_880eb10d_d887_4fc6_99a2_8af3ac63877e'

VACIA = ("(comunidad IS NULL OR TRIM(comunidad) = '' "
         "OR TRIM(CAST(comunidad AS TEXT)) IN ('None','NULL'))")
# Más allá de esto, «la comunidad más cercana» ya no dice nada útil.
CERCA_MAX_M = 500


def respaldo_sqlite(origen, etiqueta):
    carpeta = os.path.join(RAIZ_RESPALDOS, time.strftime('%Y-%m-%d'))
    os.makedirs(carpeta, exist_ok=True)
    destino = os.path.join(carpeta, '{}.{}-{}.bak'.format(
        os.path.basename(origen), time.strftime('%H%M'), etiqueta))
    src = sqlite3.connect(origen)
    dst = sqlite3.connect(destino)
    with dst:
        src.backup(dst)
    dst.close(); src.close()
    return destino


def cargar_comunidades():
    """Polígonos de las 50 comunidades, proyectados a UTM 17S."""
    with open(COMUNIDADES, encoding='utf-8') as f:
        datos = json.load(f)
    geo = osr.SpatialReference(); geo.ImportFromEPSG(4326)
    utm = osr.SpatialReference(); utm.ImportFromEPSG(32717)
    geo.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    utm.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    tr = osr.CoordinateTransformation(geo, utm)

    salida = []
    for ft in datos.get('features', []):
        nombre = (ft.get('properties') or {}).get('comunidad')
        if not nombre:
            continue
        g = ogr.CreateGeometryFromJson(json.dumps(ft['geometry']))
        if g is None:
            continue
        g.Transform(tr)
        salida.append((nombre, (ft['properties'].get('sector') or ''), g))
    return salida


def analizar(n_vecinos=12, consenso=0.7, radio=400.0, con_vecinos=False):
    """Deduce la comunidad de cada ficha que no la tiene. Sin efectos.

    Devuelve (resueltas, revisar, avisos). Lo usa este script y también
    `generar_auditoria_areas.py`, para que la pantalla web enseñe exactamente
    la misma propuesta que se aplicaría.

    Con `con_vecinos=True` cada resultado incluye las vecinas que sustentan la
    propuesta, para poder dibujarlas en un mapa.
    """
    comunidades = cargar_comunidades()
    con = sqlite3.connect(GPKG)
    cur = con.cursor()
    t = '"{}"'.format(TABLA)

    cur.execute("SELECT TRIM(COALESCE(clave_catastral,'')), TRIM(comunidad), COUNT(*) "
                "FROM {} WHERE NOT {} AND TRIM(COALESCE(clave_catastral,'')) <> '' "
                "GROUP BY 1, 2".format(t, VACIA))
    por_predio = {}
    for clave, com, n in cur.fetchall():
        d = por_predio.setdefault(clave, {})
        d[com] = d.get(com, 0) + n
    por_predio = {k: max(v, key=v.get) for k, v in por_predio.items() if len(v) == 1}

    cur.execute("SELECT TRIM(comunidad), COALESCE(coord_x_utm,0), COALESCE(coord_y_utm,0) "
                "FROM {} WHERE NOT {} AND coord_x_utm IS NOT NULL "
                "AND coord_x_utm <> 0".format(t, VACIA))
    vecinas = cur.fetchall()

    cur.execute("SELECT TRIM(comunidad), COUNT(*) FROM {} WHERE NOT {} GROUP BY 1"
                .format(t, VACIA))
    variantes = {}
    for nom, n in cur.fetchall():
        variantes.setdefault(canonica(nom) or nom, []).append((n, nom))
    forma_usual = {k: max(v)[1] for k, v in variantes.items()}
    dobles = {k: sorted(v, reverse=True) for k, v in variantes.items() if len(v) > 1}

    cur.execute(
        "SELECT COALESCE(id,''), TRIM(COALESCE(clave_catastral,'')), "
        "TRIM(COALESCE(apellidos,'') || ' ' || COALESCE(nombres,'')), "
        "COALESCE(coord_x_utm,0), COALESCE(coord_y_utm,0), "
        "COALESCE(sector_investigacion,''), "
        "CASE WHEN es_ficha_hija IS NULL OR es_ficha_hija NOT IN "
        "('1','true','SI','Si','si') THEN 1 ELSE 0 END, "
        "COALESCE(cedula,''), COALESCE(telefono_celular,''), "
        "COALESCE(creado_por,''), COALESCE(observaciones,'') "
        "FROM {} WHERE {}".format(t, VACIA))
    fichas = cur.fetchall()
    con.close()

    def mismas(a, b):
        return a and b and canonica(a) == canonica(b)

    resueltas, revisar = [], []
    for (uid, clave, nombre, x, y, sector, pri, ced, tel, tec, obs) in fichas:
        por_cl = por_predio.get(clave)
        por_geo = por_vec = None
        detalle_vec = ''
        cerca = None
        soporte = []

        if x and y:
            p = ogr.Geometry(ogr.wkbPoint); p.AddPoint_2D(x, y)
            for com, _sec, g in comunidades:
                if g.Contains(p):
                    por_geo = com
                    break
            if not por_geo:
                d = sorted((p.Distance(g), com) for com, _, g in comunidades)
                if d and d[0][0] <= CERCA_MAX_M:
                    cerca = d[0]

            cand = sorted(((x - vx) ** 2 + (y - vy) ** 2, com, vx, vy)
                          for com, vx, vy in vecinas)[:n_vecinos]
            cand = [c for c in cand if c[0] <= radio ** 2]
            if cand:
                votos = {}
                for _d2, c, _vx, _vy in cand:
                    k = canonica(c) or c
                    votos.setdefault(k, [0, c])
                    votos[k][0] += 1
                ganador = max(votos.values(), key=lambda v: v[0])
                if ganador[0] / len(cand) >= consenso:
                    por_vec = ganador[1]
                    detalle_vec = '{} de {} vecinas'.format(ganador[0], len(cand))
                if con_vecinos:
                    soporte = [{'com': c, 'x': vx, 'y': vy, 'd': round(d2 ** 0.5)}
                               for d2, c, vx, vy in cand]

        item = {'uid': uid, 'clave': clave, 'nombre': nombre, 'pri': pri,
                'x': x, 'y': y, 'sec': sector, 'ced': ced, 'tel': tel,
                'tec': tec, 'obs': (obs or '').strip(), 'vecinas': soporte}
        propuestas = [v for v in (por_cl, por_geo, por_vec) if v]
        chocan = any(not mismas(a, b)
                     for i, a in enumerate(propuestas) for b in propuestas[i + 1:])

        if chocan:
            item['motivo'] = ' · '.join(filter(None, [
                'predio «{}»'.format(por_cl) if por_cl else '',
                'ubicación «{}»'.format(por_geo) if por_geo else '',
                'vecinas «{}»'.format(por_vec) if por_vec else '']))
            revisar.append(item)
        elif propuestas:
            elegida = por_cl or por_geo or por_vec
            item['com'] = forma_usual.get(canonica(elegida) or elegida, elegida)
            if item['com'] != elegida:
                item['ojo'] = 'la vecina decía «{}»'.format(elegida)
            vias = []
            if por_cl:
                vias.append('predio')
            if por_geo:
                vias.append('ubicación')
            if por_vec:
                vias.append('vecinas ({})'.format(detalle_vec))
            item['via'] = ' + '.join(vias)
            item['n_vias'] = len(vias)
            resueltas.append(item)
        else:
            item['motivo'] = ('sin coordenadas' if not (x and y)
                              else ('a {:.0f} m de {}, sin consenso de vecinas'
                                    .format(*cerca) if cerca
                                    else 'aislada, fuera de toda comunidad'))
            revisar.append(item)
    return resueltas, revisar, {'dobles': dobles, 'n_comunidades': len(comunidades)}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--aplicar', action='store_true',
                    help='escribe en el data.gpkg (sin esto solo simula)')
    ap.add_argument('--vecinos', type=int, default=12,
                    help='fichas con comunidad que se consultan alrededor')
    ap.add_argument('--consenso', type=float, default=0.7,
                    help='proporción de esos vecinos que debe coincidir (0-1)')
    ap.add_argument('--radio', type=float, default=400,
                    help='metros máximos hasta el vecino más lejano consultado')
    args = ap.parse_args()

    print("=" * 78)
    print(" COMUNIDAD POR UBICACION" +
          ("  [APLICAR]" if args.aplicar else "  [SIMULACION - no escribe nada]"))
    print("=" * 78)

    for ruta, que in ((GPKG, 'data.gpkg'), (COMUNIDADES, 'comunidades.geojson')):
        if not os.path.exists(ruta):
            print("ERROR: no se encuentra {}:\n  {}".format(que, ruta))
            return 1

    resueltas, revisar, avisos = analizar(args.vecinos, args.consenso, args.radio)
    print("\n  capa de comunidades: {} polígonos".format(avisos['n_comunidades']))
    if avisos['dobles']:
        print("  ojo: {} comunidades se escriben de dos maneras en el gpkg"
              .format(len(avisos['dobles'])))
        for k, v in sorted(avisos['dobles'].items()):
            print("     {:<20} se usará «{}» ({}), convive con {}"
                  .format(k, v[0][1], v[0][0],
                          ' y '.join('«{}» ({})'.format(nom, n) for n, nom in v[1:])))
    print("  fichas sin comunidad: {} ({} principales)"
          .format(len(resueltas) + len(revisar),
                  sum(r['pri'] for r in resueltas + revisar)))


    print("\n  {:<52} {:>5}".format('RESUELTAS', len(resueltas)))
    print("     confirmadas por más de una vía: {}"
          .format(sum(1 for r in resueltas if r['n_vias'] > 1)))
    vias = {}
    for r in resueltas:
        clave_via = r['via'].split(' (')[0]
        vias[clave_via] = vias.get(clave_via, 0) + 1
    for v, n in sorted(vias.items(), key=lambda x: -x[1]):
        print("     por {:<46} {:>5}".format(v, n))
    dest = {}
    for r in resueltas:
        dest[r['com']] = dest.get(r['com'], 0) + 1
    print("\n     a qué comunidad van:")
    for com, n in sorted(dest.items(), key=lambda x: -x[1]):
        print("        {:<44} {:>4}".format(com[:44], n))
    corregidas = [r for r in resueltas if r.get('ojo')]
    if corregidas:
        print("\n     {} escritas con la forma que usa el padrón, no la del vecino:"
              .format(len(corregidas)))
        for r in corregidas[:6]:
            print("        {} -> «{}» ({})".format(r['clave'], r['com'], r['ojo']))

    print("\n  {:<52} {:>5}".format('PARA REVISAR A MANO', len(revisar)))
    for r in revisar:
        print("     {:<15} {:<32} {}".format(
            r['clave'] or '(sin clave)', (r['nombre'] or '—')[:32], r['motivo']))

    if not args.aplicar:
        print("\n  " + "=" * 74)
        print("  SIMULACION: no se escribió nada.")
        print("  Para aplicarlo, repetir con --aplicar (respalda antes).")
        print("  " + "=" * 74)
        return 0

    if not resueltas:
        print("\n  Nada que aplicar.")
        return 0

    print("\n  respaldando antes de tocar nada...")
    print("     {}".format(respaldo_sqlite(GPKG, 'antes-comunidad-oficina')))

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
        for r in resueltas:
            cur.execute("UPDATE {} SET comunidad = ? WHERE id = ?".format(t),
                        (r['com'], r['uid']))
            n += cur.rowcount
    finally:
        for _, sql in triggers:
            if sql:
                cur.execute(sql)
    con.commit()
    cur.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    con.close()
    print("     {} fichas actualizadas · {} triggers recreados".format(n, len(triggers)))

    con = sqlite3.connect(GPKG)
    cur = con.cursor()
    cur.execute("SELECT COUNT(*) FROM {} WHERE {}".format(t, VACIA))
    quedan = cur.fetchone()[0]
    con.close()
    print("\n  VERIFICACION (releyendo del disco): quedan {} fichas sin comunidad"
          .format(quedan))
    print("  {}".format('OK, coincide con lo previsto' if quedan == len(revisar)
                        else '!! REVISAR: se esperaban {}'.format(len(revisar))))
    print("\n  Siguiente: regenerar capas e informes para que recojan el cambio.")
    print("=" * 78)
    return 0


if __name__ == '__main__':
    sys.exit(main())
