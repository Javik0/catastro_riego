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
* **cultivo** — la superficie sembrada no cabe en el predio. Es la única de las
  cinco que no mira áreas de predio sino la tabla de cultivos, y por eso hacía
  falta: en agosto de 2026 una ficha declaraba 876.733 m² de pasto en un predio
  de 8.767,33 m² —el área del predio con el punto decimal corrido— y ningún
  control de áreas podía verla, porque sus áreas cuadraban perfectamente.

  Ojo al leerla: **un cultivo mayor que el predio no siempre es un error**.
  Sembrar en terreno arrendado fuera del predio propio es práctica corriente en
  la zona. Lo que la pantalla ofrece es el caso ordenado por cuánto se pasa, con
  el detalle de sus cultivos, para decidirlo uno a uno.

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

# Cuánto tiene que pasarse la superficie sembrada del predio para listarla. El
# 10 % deja fuera el redondeo de quien declara «todo el predio» en cifras
# redondas; los 200 m² evitan que un huerto mal medido llene la pantalla.
MARGEN_CULTIVO = 1.10
EXCESO_CULTIVO_M2 = 200

# Números con pinta de superficie dentro de un texto libre. Los técnicos lo
# escriben de muchas maneras y todas estas aparecen en el padrón:
#   «solo le corresponde un area total de 23654.79 mts cuadrados»
#   «Dueña de 2000 metros»   ·   «Es dueño de los 3500m»   ·   «1.247,42 m2»
AREA_EN_TEXTO = re.compile(
    r'(\d[\d.,]{1,12})\s*'
    r'(?:M2|M²|M\s*2|MTS?\b\.?|METROS?\b|HAS?\b|HECTAREAS?\b|M\b)'
    r'\s*(?:CUADRADOS?|CUADRADAS?)?', re.IGNORECASE)


# Cuando el técnico escribe a quién le toca qué, el número que importa es el
# que va DESPUÉS de estas expresiones, no el primero del texto: «El terreno
# area total 29632.85m² se divide para dos personas, le corresponde 14816m²».
PERTENENCIA = re.compile(
    r'(?:LE\s+)?(?:CORRESPONDE[N]?|PERTENECE[N]?|ASIGNAD[AO]|ES\s+DUE[NÑ][AO]\s+DE|'
    r'POSEE|TIENE\s+DERECHO\s+A|POR\s+CADA|CADA\s+UNO)', re.IGNORECASE)


def _a_numero(crudo):
    """Interpreta «3407.335», «1.247,42», «2.000» o «12500» como metros.

    La regla dura es la posición del separador, no su forma: los miles se
    agrupan de tres en tres, así que un punto con **cuatro o más dígitos
    delante** no puede separar miles y solo puede ser decimal. Antes se miraba
    si había uno o dos decimales, y «3407.335 m²» —que los técnicos escriben a
    menudo— se leía como 3.407.335 m², mil veces más grande.

    >>> _a_numero('3407.335')      # 4 dígitos delante: decimal
    3407.335
    >>> _a_numero('2.000')         # miles
    2000.0
    >>> _a_numero('1.247,42')      # coma decimal, punto de miles
    1247.42
    >>> _a_numero('1,247.42')      # al revés, como lo escribe una calculadora
    1247.42
    """
    crudo = crudo.strip().rstrip('.,')
    if ',' in crudo and '.' in crudo:
        # manda el último separador: es el decimal
        dec, mil = (',', '.') if crudo.rfind(',') > crudo.rfind('.') else ('.', ',')
        crudo = crudo.replace(mil, '').replace(dec, '.')
        return float(crudo)
    for sep in ('.', ','):
        if sep in crudo:
            ent, _, frac = crudo.partition(sep)
            # cuatro dígitos delante ⇒ no son miles; tres decimales justos y
            # pocos dígitos delante ⇒ sí lo son («2.000», «12.500»)
            if len(ent) >= 4 or len(frac) != 3:
                return float(crudo.replace(sep, '.'))
            return float(ent + frac)
    return float(crudo)


def num_del_texto(txt):
    """El área que menciona una observación, o None."""
    if not txt:
        return None
    coincidencias = list(AREA_EN_TEXTO.finditer(txt))
    if not coincidencias:
        return None
    # si el texto dice a quién le toca, el número bueno es el que viene después
    marca = PERTENENCIA.search(txt)
    elegida = coincidencias[0]
    if marca:
        posteriores = [m for m in coincidencias if m.start() > marca.start()]
        if posteriores:
            elegida = posteriores[0]
    try:
        v = _a_numero(elegida.group(1))
    except ValueError:
        return None
    # si venía en hectáreas, a metros
    if re.search(r'HAS?\b|HECTAREAS?\b', elegida.group(0), re.IGNORECASE):
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
        "('1','true','SI','Si','si') THEN 1 ELSE 0 END, "
        "COALESCE(id,'') "
        "FROM \"{}\"".format(CAPA), dialect='SQLITE')
    filas = [[ft.GetField(i) for i in range(16)] for ft in res]
    ds.ReleaseResultSet(res)
    corte = max((f[10] or '') for f in filas)

    # ── lo sembrado, por ficha ──
    # La capa se busca por nombre en vez de fijarla como constante porque su
    # sufijo cambia si el proyecto de QField se regenera.
    capa_cult = next((ds.GetLayer(i).GetName() for i in range(ds.GetLayerCount())
                      if 'Cultivos_Agricolas' in ds.GetLayer(i).GetName()), None)
    cultivos_por_ficha = {}
    if capa_cult:
        res = ds.ExecuteSQL(
            "SELECT COALESCE(ficha_id,''), COALESCE(tipo_cultivo,''), "
            "COALESCE(superficie_m2,0) FROM \"{}\" WHERE COALESCE(superficie_m2,0) > 0"
            .format(capa_cult), dialect='SQLITE')
        for ft in res:
            fid, tipo, sup = ft.GetField(0), ft.GetField(1), ft.GetField(2)
            cultivos_por_ficha.setdefault(fid, []).append((tipo or '—', float(sup)))
        ds.ReleaseResultSet(res)
        print("  cultivos: {:,} fichas con siembra registrada".format(len(cultivos_por_ficha)))
    else:
        print("  aviso: no se encontro la capa de cultivos; no se audita la produccion")
    ds = None
    print("  padrón  : {:,} fichas · corte {}".format(len(filas), corte))

    # ── una entrada por ficha, ya en coordenadas geográficas ──
    por_clave = {}
    claves_malas = {}
    fichas_por_id = {}
    for (clave, at, ar, asr, nom, ced, tel, com, sec, tec, fecha, obs,
         x, y, pri, fid) in filas:
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
        # se guarda aparte para cruzar con los cultivos, que van por ficha y no
        # por predio: dos fichas del mismo predio siembran cosas distintas
        if fid:
            fichas_por_id[fid] = {'f': f, 'clave': clave, 'com': com, 'sec': sec}

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
        # ¿lo resuelven las observaciones? Y si no, por qué no: es lo que hace
        # falta para saber qué le falta a cada predio sin abrirlo uno a uno.
        obs_areas = [f['oa'] for f in fichas if f.get('oa')]
        if tipo == 'exceso':
            caso['obs_n'] = len(obs_areas)
            caso['obs_suma'] = sum(obs_areas)
            if not obs_areas:
                caso['falta'] = 'nadie anotó su parte'
            elif len(obs_areas) < len(fichas):
                caso['falta'] = 'faltan {} de {} fichas por anotar'.format(
                    len(fichas) - len(obs_areas), len(fichas))
            elif pol > 0 and abs(sum(obs_areas) - pol) / pol > MARGEN_DIVIDIDO:
                caso['falta'] = ('lo anotado suma {:,.0f} m² sobre un predio de '
                                 '{:,.0f}'.format(sum(obs_areas), pol))
            else:
                caso['resuelto_por_obs'] = True
        casos.append(caso)

    # La propuesta de corrección la calcula `resolver_claves_catastrales`, el
    # mismo módulo que la aplicaría. Así la pantalla enseña exactamente lo que
    # se va a escribir, y no hay dos criterios que puedan separarse con el
    # tiempo.
    try:
        from resolver_claves_catastrales import analizar as analizar_claves
        prop, con_obs_cl, sin_res = analizar_claves()
        estado_clave = {}
        for i in prop:
            estado_clave[i['clave']] = {
                'estado': 'propuesta', 'propuesta': i['propuesta'],
                'dif': i['dif'], 'area_confirma': bool(i['area_confirma']),
                'area_pol': round(i['area_pol']),
            }
        for i in con_obs_cl:
            estado_clave[i['clave']] = {
                'estado': 'del DMQ' if i.get('dmq') else 'lo explica la observación',
                'nota': i['obs'][:200],
            }
        for i in sin_res:
            estado_clave[i['clave']] = {'estado': 'sin resolver', 'nota': i['motivo']}
    except Exception as e:                      # nunca debe tumbar la pantalla
        print("  aviso: no se pudo calcular la propuesta de claves ({})".format(e))
        estado_clave = {}

    for clave, d in claves_malas.items():
        if not clave:
            continue
        caso = {
            'clave': clave, 'tipo': 'clave_mala',
            'com': d['com'] or '(sin comunidad)', 'sec': d['sec'] or '',
            'pol': 0, 'dec': round(sum(f['a'] for f in d['fichas'])),
            'exc': 0, 'nf': len(d['fichas']), 'fichas': d['fichas'],
            'digitos': len(clave),
        }
        caso.update(estado_clave.get(clave, {'estado': 'sin analizar'}))
        casos.append(caso)

    # ── fichas sin comunidad ──
    # No afectan al área, pero son el otro trabajo de oficina pendiente y
    # conviene verlas en el mismo sitio. La propuesta la calcula el módulo que
    # la aplicaría, igual que con las claves.
    try:
        from resolver_comunidad_oficina import analizar as analizar_com
        res_com, rev_com, _avisos = analizar_com(con_vecinos=True)

        def caso_comunidad(r, estado):
            lon = lat = None
            if r['x'] and r['y']:
                lon, lat, _ = a_geo.TransformPoint(r['x'], r['y'])
                lon, lat = round(lon, 6), round(lat, 6)
            f = {'n': r['nombre'] or '—', 'ced': r['ced'], 'tel': r['tel'],
                 'a': 0, 'ar': 0, 'asr': 0, 'tec': r['tec'], 'f': '',
                 'p': r['pri'], 'lon': lon, 'lat': lat}
            if r['obs']:
                f['obs'] = r['obs'][:400]
            c = {'clave': r['clave'] or '(sin clave)', 'tipo': 'sin_comunidad',
                 'com': '(sin comunidad)', 'sec': r['sec'] or '',
                 'pol': 0, 'dec': 0, 'exc': 0, 'nf': 1, 'fichas': [f],
                 'estado': estado, 'uid': r['uid']}
            if estado == 'propuesta':
                c['propuesta'] = r['com']
                c['via'] = r['via']
            else:
                c['nota'] = r.get('motivo', '')
            # las vecinas que sustentan la propuesta, para dibujarlas
            vec = []
            for v in (r.get('vecinas') or [])[:12]:
                vlon, vlat, _ = a_geo.TransformPoint(v['x'], v['y'])
                vec.append({'com': v['com'], 'lon': round(vlon, 6),
                            'lat': round(vlat, 6), 'd': v['d']})
            if vec:
                c['vecinas'] = vec
            if r['clave'] in contorno:
                c['geo'] = redondear(contorno[r['clave']])
            return c

        for r in res_com:
            casos.append(caso_comunidad(r, 'propuesta'))
        for r in rev_com:
            casos.append(caso_comunidad(r, 'revisar'))
    except Exception as e:
        print("  aviso: no se pudieron calcular las comunidades ({})".format(e))
        res_com, rev_com = [], []

    orden = {'exceso': 0, 'triple': 1, 'clave_mala': 2,
             'sin_comunidad': 3, 'dividido': 4}
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

    # ── lo que ya está bien ──
    # Sin esto la pantalla solo enseña lo que falta y parece que no se avanza.
    # Se cuenta de las filas que ya se leyeron del gpkg, así que si mañana se
    # revierte algo el número baja solo.
    con_com = sum(1 for f in filas if (f[7] or '').strip())
    fichas_clave_mala = sum(len(d['fichas']) for d in claves_malas.values())
    cuadran_area = sum(1 for f in filas
                       if (f[1] or 0) > 0
                       and abs((f[2] or 0) + (f[3] or 0) - f[1]) < 1)
    corregido = {
        'total_fichas': len(filas),
        'con_comunidad': con_com,
        'clave_valida': len(filas) - fichas_clave_mala,
        'area_cuadra': cuadran_area,
    }

    # ── la producción que no cabe en el predio ──
    #
    # Va por ficha y no por predio: dos fichas del mismo predio siembran cosas
    # distintas, y lo que se audita es lo que declaró cada regante.
    casos_cultivo = []
    for fid, dat in fichas_por_id.items():
        items = cultivos_por_ficha.get(fid)
        f = dat['f']
        if not items or f['a'] <= 0:
            continue
        sembrado = sum(s for _, s in items)
        if sembrado < f['a'] * MARGEN_CULTIVO or sembrado - f['a'] < EXCESO_CULTIVO_M2:
            continue
        clave = dat['clave']
        pol_m2 = areas_cat.get(clave, 0)
        # Una fila de cultivo que vale casi exacto el poligono catastral no es
        # "sembro de mas": es el mismo default de QField que en area_total,
        # pero en el campo de cultivo. No se corrige (no hay con que
        # reemplazarlo), pero se distingue del caso "terreno arrendado" para
        # no sugerir una explicacion que no aplica.
        coincide_poligono = pol_m2 > 0 and any(
            abs(s - pol_m2) / pol_m2 <= 0.02 for _, s in items)
        caso = {
            'clave': clave or '(sin clave)', 'tipo': 'cultivo',
            'com': dat['com'] or '(sin comunidad)', 'sec': dat['sec'] or '',
            'pol': round(pol_m2), 'dec': round(f['a']),
            'exc': round(sembrado - f['a']), 'nf': 1, 'fichas': [f],
            'cul': round(sembrado), 'factor': round(sembrado / f['a'], 1),
            'items': [{'t': t, 'm2': round(s, 2)}
                      for t, s in sorted(items, key=lambda x: -x[1])],
            'uid': 'cul|' + fid,
        }
        if coincide_poligono:
            caso['coincide_poligono'] = True
        if clave in contorno:
            caso['geo'] = redondear(contorno[clave])
        casos_cultivo.append(caso)

    # de mayor a menor desborde: por ahí se empieza a revisar
    casos_cultivo.sort(key=lambda c: -c['factor'])
    casos.extend(casos_cultivo)
    exc_cultivo = sum(c['exc'] for c in casos_cultivo)
    n_coincide_pol = sum(1 for c in casos_cultivo if c.get('coincide_poligono'))
    print("\n  la produccion no cabe en el predio: {:,} fichas · {:,.2f} ha sembradas de mas"
          .format(len(casos_cultivo), exc_cultivo / 10000.0))
    print("     de esas, con un cultivo que coincide con el poligono (sospechoso, "
          "no es terreno arrendado): {:,}".format(n_coincide_pol))
    for c in casos_cultivo[:5]:
        print("      {:<15} {:<30} x{:.1f}   predio {:>10,} m2   sembrado {:>12,} m2"
              .format(c['clave'], c['fichas'][0]['n'][:30], c['factor'],
                      c['dec'], c['cul']))

    salida = {
        'generado': datetime.now().strftime('%Y-%m-%d %H:%M'),
        'corte': corte,
        'corregido': corregido,
        'resumen': {
            'fichas': len(filas),
            'exceso': cuenta['exceso'], 'dividido': cuenta['dividido'],
            'triple': n_triple, 'triple_solo': cuenta['triple'],
            'clave_mala': cuenta['clave_mala'],
            'sin_comunidad': cuenta['sin_comunidad'],
            'com_propuesta': len(res_com), 'com_revisar': len(rev_com),
            'exc_ha': round(exc_total / 10000.0, 2),
            'con_obs': con_obs, 'resueltos_por_obs': resueltos,
            'cultivo': len(casos_cultivo),
            'cultivo_exc_ha': round(exc_cultivo / 10000.0, 2),
            'cultivo_coincide_poligono': n_coincide_pol,
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
    est = {}
    for c in casos:
        if c['tipo'] == 'clave_mala':
            est[c.get('estado', '?')] = est.get(c.get('estado', '?'), 0) + 1
    for e, n in sorted(est.items(), key=lambda x: -x[1]):
        print("     {:<34} {:>3}".format(e, n))
    print("  sin comunidad           : {:>4} fichas".format(cuenta['sin_comunidad']))
    print("     con propuesta                     {:>3}".format(len(res_com)))
    print("     para revisar                      {:>3}".format(len(rev_com)))
    print("\n  guardado: {} ({:,.0f} KB)"
          .format(os.path.relpath(SALIDA, BASE), os.path.getsize(SALIDA) / 1024))
    print("=" * 74)
    return 0


if __name__ == '__main__':
    sys.exit(main())
