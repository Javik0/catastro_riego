# -*- coding: utf-8 -*-
"""
Capítulo del informe técnico: "El predio y el acceso al agua".

Cubre la sección 2 de la ficha de campo (Predio y riego): superficies, caudal,
frecuencia y turnos, grado de tecnificación, tarifas y reservorios.

CRITERIOS DE ANÁLISIS
---------------------
· Universo: las fichas PRINCIPALES. Cada una es un predio con su titular; las
  adicionales son otros predios del mismo titular y se cuentan aparte para no
  duplicar al entrevistado.
· Los porcentajes de método de riego vacíos son CEROS, no datos faltantes: el
  93,8 % de las fichas suma exactamente 100 % entre gravedad, aspersión y goteo.
· En dinero y turnos se usa la MEDIANA, no el promedio: unas pocas fichas con
  valores extremos desplazan el promedio y darían una cifra que no representa a
  nadie.
· ALPAKA declara tarifas de 672 y 308 USD "mensuales" en 491 fichas, cuando la
  mediana del sistema es 3 USD. No es la tarifa de riego sino otro concepto del
  fraccionamiento; se excluye del análisis económico y se reporta como anomalía.
· El caudal NO se suma ficha a ficha (ver docs/METODOLOGIA-CAUDAL.md): se toma
  de caudal_por_comunidad.json, que lo calcula una vez por comunidad.

SALIDAS
  docs/CAPITULO-predio-y-agua.html            capítulo imprimible
  build_entrega/Predio_y_Agua.xlsx            datos por comunidad y sector
"""

import json
import os
import sqlite3
import statistics as st
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from comunidades_canon import canonica, nombre_publico, normalizar  # noqa: E402
import informe_estilo as E  # noqa: E402
import informe_graficos as G  # noqa: E402
from informe_estilo import esn

GPKG = r"C:\Users\HP\QField\cloud\porotog_levantamiento_offline\data.gpkg"
T = 'Fichas_Predios_880eb10d_d887_4fc6_99a2_8af3ac63877e'
BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
HTML = os.path.join(BASE, 'docs', 'CAPITULO-predio-y-agua.html')
XLSX = os.path.join(BASE, 'build_entrega', 'Predio_y_Agua.xlsx')
CAUDAL_JSON = os.path.join(BASE, 'public', 'geo', 'caudal_por_comunidad.json')
# Fuente única de superficie: la del territorio y la que declararon los titulares
SUPERFICIE_JSON = os.path.join(BASE, 'public', 'geo', 'superficie_por_comunidad.json')

# Comunidad cuyas tarifas no son comparables (ver encabezado).
TARIFA_ANOMALA = 'ALPAKA'


def num(p, k):
    try:
        return float(p.get(k) or 0)
    except (TypeError, ValueError):
        return 0.0


def lleno(v):
    return v not in (None, '') and str(v).strip() != ''


def pct(a, b):
    return 100.0 * a / b if b else 0.0


def cargar():
    con = sqlite3.connect(GPKG)
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    cur.execute(f'SELECT * FROM "{T}" WHERE es_ficha_hija IS NOT 1')
    pri = [dict(r) for r in cur.fetchall()]
    cur.execute(f'SELECT MAX(fecha_creacion), MAX(fecha_completado) FROM "{T}"')
    f1, f2 = cur.fetchone()
    cur.execute(f'SELECT COUNT(*) FROM "{T}" WHERE es_ficha_hija = 1 AND '
                f'coalesce(estado_investigacion, "pendiente_produccion") != "completada"')
    pendientes = cur.fetchone()[0]
    con.close()

    from generar_capas_sectores_comunidades import COM_A_SECTOR
    vistos = defaultdict(Counter)
    for p in pri:
        crudo = p.get('comunidad') or ''
        p['_comk'] = canonica(crudo) or '(sin comunidad)'
        vistos[p['_comk']][nombre_publico(crudo) or '(sin comunidad)'] += 1
    display = {}
    for k, c in vistos.items():
        validas = [(n_, v) for n_, v in c.most_common() if normalizar(n_) == k]
        display[k] = validas[0][0] if validas else k
    for p in pri:
        p['_com'] = display[p['_comk']]
        # El sector es el de la COMUNIDAD según el catálogo oficial, como la
        # web y los informes del sociólogo. Hasta el 4-sep-2026 mandaba el
        # campo `sector_investigacion` de la ficha (vacío en 556 principales
        # y contradictorio con su comunidad en otras 27), y los cortes por
        # sector no cuadraban entre documentos. Decisión de JAVIKO.
        p['_sec'] = COM_A_SECTOR.get(p['_comk'], '(sin sector)')

    # Fecha de corte editorial única del paquete (informe_estilo.FECHA_CORTE),
    # no la última fecha de ficha del gpkg: las depuraciones de gabinete
    # posteriores no mueven esas fechas (decisión de JAVIKO, 4-sep-2026).
    corte_txt = E.FECHA_CORTE
    return pri, corte_txt, pendientes


def tamanos_por_predio():
    """Superficie catastral de cada predio distinto del padrón publicado y su
    distribución por los rangos del proyecto. Devuelve (áreas en m², [(rango, n)])."""
    import json
    from generar_informe_sociologo import RANGOS_PREDIO
    from generar_informe_sociologo_sector import area_por_clave
    with open(os.path.join(BASE, 'public', 'geo', 'fichas_predios.geojson'),
              encoding='utf-8') as f:
        fichas = [x['properties'] for x in json.load(f)['features']]
    areas_clave = area_por_clave()
    vistas, areas = set(), []
    for p in fichas:
        if p.get('es_ficha_hija') == 1 and                 (p.get('estado_investigacion') or '') != 'completada':
            continue
        clave = (str(p.get('clave_catastral') or '').strip() or
                 str(p.get('cod_poligono') or '').strip())
        if not clave or clave in vistas or clave not in areas_clave:
            continue
        vistas.add(clave)
        areas.append(float(areas_clave[clave]))
    areas.sort()
    dist = [(et, sum(1 for a in areas if lo <= a < hi)) for lo, hi, et in RANGOS_PREDIO]
    return areas, dist


def metodo_predominante(p):
    m = {'Gravedad': num(p, 'metodo_gravedad_pct'),
         'Aspersión': num(p, 'metodo_aspersion_pct'),
         'Goteo': num(p, 'metodo_goteo_pct')}
    return max(m, key=m.get) if sum(m.values()) > 0 else None


def main():
    pri, corte_txt, pendientes = cargar()
    N = len(pri)

    # ── superficies (fuente única: superficie_por_comunidad.json) ──
    #
    # La superficie del sistema NO se obtiene sumando fichas. En los predios de
    # herederos cada titular declara el predio familiar completo, así que sumar
    # fichas cuenta ese terreno tantas veces como titulares tenga: 1.780 ha de
    # más sobre 435 predios. Se mide sumando polígonos catastrales distintos.
    #
    # Lo declarado se conserva y se publica al lado, porque no es un error: es
    # lo que cada titular considera suyo, y eso es material de análisis.
    # Decisión del proyecto del 14-ago-2026.
    with open(SUPERFICIE_JSON, encoding='utf-8') as f:
        SUP = json.load(f)['total']
    ha_t = SUP['superficie_catastral_ha']       # la del territorio
    ha_dec = SUP['superficie_declarada_ha']     # la de las fichas
    ha_r = SUP['riego_ajustado_ha']             # riego que cabe en el polígono
    ha_r_dec = SUP['riego_declarado_ha']
    a_total, a_riego = ha_t * 10000, ha_r * 10000
    # El riego declarado arrastra la misma duplicación que la superficie, así
    # que las superficies por método —que salen de las fichas— se expresan
    # sobre el riego ajustado, repartiendo el recorte en proporción.
    AJUSTE = (ha_r / ha_r_dec) if ha_r_dec else 1.0
    # Tamaño del predio: por PREDIO CATASTRAL, no por ficha. Es la misma regla
    # del informe por sector y del reporte «Terrenos por rango de superficie»:
    # los predios familiares tienen varias fichas y contarlos por ficha
    # multiplica los tramos grandes; y la superficie es la del catastro, que
    # es la familia de toda esta sección (regla 12). Hasta el 4-sep-2026 esta
    # tabla contaba fichas principales por área declarada; JAVIKO decidió
    # unificarla. Las claves salen de las fichas publicadas (regla 14:
    # clave_catastral manda, cod_poligono es el respaldo).
    areas, dist_area = tamanos_por_predio()
    med_area = st.median(areas)

    # ── caudal (fuente única) ──
    with open(CAUDAL_JSON, encoding='utf-8') as f:
        caudal = json.load(f)
    tot_c = caudal['totales']

    # ── frecuencia / turnos ──
    frec = Counter(str(p['frecuencia_riego']).strip() for p in pri
                   if lleno(p.get('frecuencia_riego')))
    dias = [num(p, 'dias_riego') for p in pri if lleno(p.get('dias_riego'))]
    horas = [num(p, 'horas_turno') for p in pri if lleno(p.get('horas_turno'))]
    dias_ok = [d for d in dias if 0 < d <= 7]
    horas_ok = [h for h in horas if 0 < h <= 24]

    # ── tecnificación ──
    pred = Counter(metodo_predominante(p) for p in pri if metodo_predominante(p))
    sup_met = {'Gravedad': 0.0, 'Aspersión': 0.0, 'Goteo': 0.0}
    for p in pri:
        a = num(p, 'area_riego')
        for campo, et in (('metodo_gravedad_pct', 'Gravedad'),
                          ('metodo_aspersion_pct', 'Aspersión'),
                          ('metodo_goteo_pct', 'Goteo')):
            sup_met[et] += a * num(p, campo) / 100
    # al venir de las fichas arrastran la duplicación de los predios de
    # herederos: se llevan a la misma escala que el riego del sistema
    for et in sup_met:
        sup_met[et] *= AJUSTE
    sup_total_met = sum(sup_met.values())

    tecnificada = sup_met['Aspersión'] + sup_met['Goteo']

    # tecnificación por sector
    tec_sector = {}
    for sec in sorted({p['_sec'] for p in pri if not p['_sec'].startswith('(')}):
        ps = [p for p in pri if p['_sec'] == sec]
        s_tec = sum(num(p, 'area_riego') * (num(p, 'metodo_aspersion_pct')
                                            + num(p, 'metodo_goteo_pct')) / 100 for p in ps)
        s_tot = sum(num(p, 'area_riego') * (num(p, 'metodo_gravedad_pct')
                                            + num(p, 'metodo_aspersion_pct')
                                            + num(p, 'metodo_goteo_pct')) / 100 for p in ps)
        tec_sector[sec] = (s_tec * AJUSTE / 10000, s_tot * AJUSTE / 10000,
                           pct(s_tec, s_tot))

    # ── tarifas (excluye la comunidad con valores no comparables) ──
    def tarifa(tipo, excluir_anomala=True):
        return [num(p, 'valor_tarifa') for p in pri
                if str(p.get('tipo_tarifa') or '').strip() == tipo
                and lleno(p.get('valor_tarifa'))
                and not (excluir_anomala and p['_comk'] == TARIFA_ANOMALA)]
    t_mes, t_anio = tarifa('fijo mensual'), tarifa('fijo anual')
    anomalas = [p for p in pri if p['_comk'] == TARIFA_ANOMALA and lleno(p.get('valor_tarifa'))]
    val_anom = Counter(num(p, 'valor_tarifa') for p in anomalas)

    reserv = Counter(str(p['tiene_reservorio']).strip() for p in pri
                     if lleno(p.get('tiene_reservorio')))
    n_res = sum(reserv.values())

    # ── documento ──
    G.preparar()
    G.configurar(os.path.join(BASE, 'docs'), 'graficos-capitulos')
    W = G.sistema()   # matrices del tablero web (motor compartido)
    from generar_informe_sociologo import COLOR_SECTOR
    B = []
    A = B.append
    A(E.cabecera('El predio y el acceso al agua',
                 'Superficies, caudal, turnos, tecnificación y tarifas · '
                 'Capítulo del informe técnico'))
    A(E.aviso_corte(corte_txt, N, pendientes))
    A(E.kpis([
        (f'{esn(ha_r, 0)} ha', 'bajo riego'),
        (f'{esn(pct(a_riego, a_total), 1, False)}%', 'del área del sistema'),
        (f'{esn(tot_c["caudal_sistema_ls"], 0)} l/s', 'caudal del sistema'),
        (f'{esn(pct(tecnificada, sup_total_met), 1, False)}%', 'superficie tecnificada'),
    ]))

    A('<h2>1. Superficie del sistema y superficie bajo riego</h2>')
    A(f'<p>El padrón cubre <b>{esn(SUP["predios_catastrales"], 0)} predios</b> que '
      f'suman <b>{esn(ha_t, 1)} hectáreas</b>, de las cuales <b>{esn(ha_r, 1)} ha '
      f'({esn(pct(a_riego, a_total), 1, False)} %) cuentan con riego</b>. El resto '
      # «secano» se retiró de toda la interfaz web por pedido del cliente
      # (12-ago-2026) y los informes usan el mismo término: «sin riego».
      'corresponde a áreas sin dotación: pastos sin riego, bosque o terreno no '
      'cultivable dentro del mismo predio.</p>')
    A('<p>Esta superficie se mide sumando cada predio <b>una sola vez</b>, según '
      'el polígono del catastro municipal. Lo que los titulares declaran en la '
      f'entrevista suma <b>{esn(ha_dec, 1)} ha</b>: en los {SUP["predios_compartidos"]} '
      'predios de herederos cada titular declara el terreno familiar completo, y '
      'esa cifra se conserva como dato social. Las dos mediciones describen el '
      'mismo territorio y no se suman entre sí.</p>')
    b64 = G.g_donut('riego-uso-suelo',
                    [('Con riego', ha_r, '#3b82f6'),
                     ('Sin riego', SUP['sin_riego_catastral_ha'], '#f59e0b')],
                    lambda v: f'{esn(v, 2)} ha', centro=f'{esn(ha_t, 2)} ha')
    A(E.figura(b64, 'Uso del suelo: con riego y sin riego (ha)',
               f'Medición catastral, {esn(ha_t, 2)} ha en {esn(SUP["predios_catastrales"], 0)} '
               'predios; riego ajustado al polígono.'))
    A(f'<p>El predio catastral tiene una superficie <b>mediana de {esn(med_area, 0)} m²</b> '
      f'({esn(len(areas), 0)} predios distintos, cada uno contado una sola vez aunque '
      'tenga varias fichas). La distribución muestra una estructura de '
      '<b>minifundio</b>:</p>')
    A('<table class="evitar-corte"><tr><th>Tamaño del predio (catastral)</th>'
      '<th class="n">Predios</th><th>Peso</th></tr>')
    for et, n in dist_area:
        A(f'<tr><td>{et}</td><td class="n">{esn(n, 0)}</td><td>{E.barra(pct(n, len(areas)))}</td></tr>')
    A('</table>')
    if dist_area != W['tamanos']:
        print('  ⚠ tamaños: el capítulo y el tablero no cuentan igual')
    b64 = G.g_barras_h('riego-tamanos', dist_area, lambda i, n: '#0ea5e9', alto=3.4)
    A(E.figura(b64, 'Tamaño de los predios', f'Predios catastrales, {esn(len(areas), 0)}.'))
    A('<p>Esta estructura condiciona cualquier intervención: el sistema atiende a '
      'una mayoría de productores con parcelas pequeñas, para quienes el acceso al '
      'agua es determinante de la viabilidad productiva.</p>')

    A('<h2>2. Caudal del sistema</h2>')
    A(f'<p>El sistema entrega <b>{esn(tot_c["caudal_sistema_ls"], 2)} l/s</b>, '
      f'resultado de sumar el caudal de las <b>{len(caudal["comunidades"])} '
      f'comunidades</b> ({esn(tot_c["caudal_comunidades_ls"], 2)} l/s) y las '
      f'{tot_c["fichas_individuales"]} concesiones individuales '
      f'({esn(tot_c["caudal_individual_ls"], 2)} l/s).</p>')
    A('<p>El caudal se contabiliza <b>una sola vez por comunidad</b>: los '
      'técnicos anotaron en cada ficha el caudal que recibe su comunidad, de modo '
      'que el mismo valor se repite en todas las fichas de esa comunidad.</p>')
    # Solo comunidades con llave propia: las de caudal heredado repiten el valor
    # de otra y aparecerían como si aportaran un caudal que no existe.
    #
    # Antes esta tabla se recortaba a las 8 mayores y NO lo decía: el texto de
    # arriba habla de «las 50 comunidades» y debajo aparecían ocho filas, así
    # que se leía como si faltaran 42. Lo reportó el sociólogo del proyecto el
    # 2-sep-2026 («el caudal solo se anota de 8 comunidades»). Ahora se listan
    # todas, ordenadas de mayor a menor.
    filas_c = sorted(((k, v) for k, v in caudal['comunidades'].items()
                      if 'caudal_heredado_de' not in v),
                     key=lambda x: -x[1]['caudal_ls'])
    A(f'<p>Las <b>{len(filas_c)} comunidades con llave propia</b>, ordenadas '
      'por el caudal que reciben:</p>')
    A('<table><tr><th>Comunidad</th><th class="n">Caudal (l/s)</th>'
      '<th class="n">Fichas</th><th>Origen del dato</th></tr>')
    for com, d in filas_c:
        A(f'<tr><td>{com}</td><td class="n">{esn(d["caudal_ls"], 2)}</td>'
          f'<td class="n">{esn(d["fichas"], 0)}</td><td>{d["origen"].capitalize()}</td></tr>')
    A(f'<tr class="dest"><td><b>Total</b></td><td class="n">'
      f'{esn(sum(d["caudal_ls"] for _, d in filas_c), 2)}</td>'
      f'<td class="n">{esn(sum(d["fichas"] for _, d in filas_c), 0)}</td><td></td></tr>')
    A('</table>')
    heredadas = caudal.get('caudal_heredado', {})
    if heredadas:
        A(f'<p class="pie-fig">{len(heredadas)} usuarios individuales comparten la '
          'llave de su comunidad de origen y su caudal está incluido en el de '
          'ella.</p>')

    A('<h2>3. Frecuencia y turnos de riego</h2>')
    A('<table class="evitar-corte"><tr><th>Frecuencia</th><th class="n">Predios</th>'
      '<th>Peso</th></tr>')
    for k, n in frec.most_common():
        A(f'<tr><td>{k}</td><td class="n">{esn(n, 0)}</td>'
          f'<td>{E.barra(pct(n, sum(frec.values())))}</td></tr>')
    A('</table>')
    b64 = G.g_barras_v('riego-frecuencia', frec.most_common(),
                       lambda i, n: G.PIE_COLORS[i % 8])
    A(E.figura(b64, 'Frecuencia de riego',
               f'Fichas principales con el dato, {esn(sum(frec.values()), 0)}.'))
    A(f'<p>El turno <b>semanal</b> es el régimen dominante '
      f'({esn(pct(frec.get("Semanal", 0), sum(frec.values())), 1, False)} %). La mediana es de '
      f'<b>{esn(st.median(dias_ok), 0, False)} días de riego</b> por turno y '
      f'<b>{esn(st.median(horas_ok), 0, False)} horas</b> por jornada de riego.</p>')

    A('<h2>4. Tecnificación del riego</h2>')
    A('<p>Se midió la superficie regada por cada método, ponderando el área de '
      'cada predio por el porcentaje declarado. Es una medida más precisa que '
      'contar predios, porque una hectárea por aspersión pesa lo mismo tenga uno '
      'o diez propietarios.</p>')
    A('<table class="evitar-corte"><tr><th>Método</th><th class="n">Superficie (ha)</th>'
      '<th class="n">Predios donde predomina</th><th>Peso en superficie</th></tr>')
    for met in ('Aspersión', 'Gravedad', 'Goteo'):
        A(f'<tr><td>{met}</td><td class="n">{esn(sup_met[met] / 10000, 1)}</td>'
          f'<td class="n">{esn(pred.get(met, 0), 0)}</td>'
          f'<td>{E.barra(pct(sup_met[met], sup_total_met))}</td></tr>')
    A('</table>')
    A(f'<p>El <b>{esn(pct(tecnificada, sup_total_met), 1, False)} % de la superficie regada '
      f'ya usa métodos tecnificados</b> (aspersión o goteo): {esn(tecnificada / 10000, 1)} ha '
      f'de {esn(sup_total_met / 10000, 1)} ha. La aspersión es el método dominante del '
      f'sistema, mientras el goteo apenas alcanza {esn(sup_met["Goteo"] / 10000, 1)} ha '
      f'({esn(pct(sup_met["Goteo"], sup_total_met), 1, False)} %) y representa el mayor margen '
      'de mejora en eficiencia.</p>')
    met_web = {n_: v for n_, v, _ in W['metodo']}
    A(f'<p>Contado por ficha y no por hectárea —el promedio simple del porcentaje '
      f'que declara cada ficha—, el reparto es {met_web.get("Aspersión", 0)} % '
      f'aspersión, {met_web.get("Gravedad", 0)} % gravedad y '
      f'{met_web.get("Goteo", 0)} % goteo.</p>')
    b64 = G.g_donut('riego-metodo', [(n_, v, c) for n_, v, c in W['metodo']],
                    lambda v: f'{v} %')
    A(E.figura(b64, 'Método de riego (promedio %)',
               f'Todas las fichas, {esn(W["n_todas"], 0)}; promedio simple del porcentaje '
               'declarado en cada ficha, redondeado a enteros.'))
    A('<h3>Tecnificación por sector</h3>')
    A('<table class="evitar-corte"><tr><th>Sector</th>'
      '<th class="n">Superficie regada (ha)</th><th class="n">Tecnificada (ha)</th>'
      '<th>% tecnificado</th></tr>')
    for sec, (s_tec, s_tot, p) in sorted(tec_sector.items()):
        A(f'<tr><td>{sec}</td><td class="n">{esn(s_tot, 1)}</td>'
          f'<td class="n">{esn(s_tec, 1)}</td><td>{E.barra(p)}</td></tr>')
    A('</table>')
    b64 = G.g_barras_v('riego-tecnificacion-sector',
                       [(sec, round(p, 1)) for sec, (_, _, p) in sorted(tec_sector.items())],
                       [COLOR_SECTOR.get(sec, '#3b82f6') for sec in sorted(tec_sector)],
                       fmt=lambda v: f'{esn(v, 1, False)} %')
    A(E.figura(b64, 'Riego tecnificado por sector (% de la superficie regada)',
               'Fichas principales; superficie ponderada por el porcentaje '
               'declarado de cada método.'))

    A('<h2>5. Tarifas y reservorios</h2>')
    A(f'<p>La tarifa <b>fija mensual</b> es la modalidad más extendida '
      f'({esn(len(t_mes), 0)} predios), con una <b>mediana de {esn(st.median(t_mes), 2)} USD</b>. '
      f'La modalidad <b>anual</b> ({esn(len(t_anio), 0)} predios) tiene una mediana de '
      f'<b>{esn(st.median(t_anio), 2)} USD</b>.</p>')
    A('<p>Se reporta la mediana —el valor central— porque describe lo que paga '
      'efectivamente la mayoría; unos pocos registros altos desplazarían el '
      'promedio hasta una cifra que no representa a ningún titular.</p>')
    if anomalas:
        A(f'<p>Las {len(anomalas)} fichas del fraccionamiento {TARIFA_ANOMALA.title()} '
          'registran valores de '
          + ' y '.join(f'{esn(v, 0)}' for v, _ in val_anom.most_common(2))
          + ' USD que corresponden a otro concepto del proceso de fraccionamiento, '
          'no a la tarifa de riego, y no entran en este cálculo.</p>')
    A('<h3>Reservorios</h3>')
    A('<table class="evitar-corte"><tr><th>Tipo de reservorio</th>'
      '<th class="n">Predios</th><th>Peso</th></tr>')
    for k, n in reserv.most_common():
        et = {'No': 'Sin reservorio'}.get(k, f'Reservorio {k.lower()}')
        A(f'<tr><td>{et}</td><td class="n">{esn(n, 0)}</td><td>{E.barra(pct(n, n_res))}</td></tr>')
    A('</table>')
    b64 = G.g_donut('riego-reservorios',
                    [({'No': 'Sin reservorio'}.get(k, f'Reservorio {k.lower()}'), n,
                      G.PIE_COLORS[i % 8]) for i, (k, n) in enumerate(reserv.most_common())],
                    G.fnum, centro=f'{esn(n_res, 0)}')
    A(E.figura(b64, 'Reservorios', f'Fichas principales con el dato, {esn(n_res, 0)}.'))
    A(f'<p>El <b>{esn(pct(reserv.get("Comunitario", 0), n_res), 1, False)} %</b> de los predios '
      'se sirve de un <b>reservorio comunitario</b>, lo que confirma el carácter '
      'colectivo de la infraestructura de almacenamiento: la gestión del agua no '
      'es predio a predio sino comunitaria.</p>')

    A('<h2>6. Conclusiones</h2>')
    A('<ul>')
    A(f'<li>El padrón registra <b>{esn(ha_t, 0)} ha</b>, de las cuales '
      f'<b>{esn(ha_r, 0)} ha ({esn(pct(a_riego, a_total), 0, False)} %) tienen riego</b>.</li>')
    A(f'<li>Predomina el <b>minifundio</b>: la mitad de los predios no supera los '
      f'{esn(med_area, 0)} m².</li>')
    A(f'<li>La <b>tecnificación alcanza el {esn(pct(tecnificada, sup_total_met), 1, False)} %</b> '
      f'de la superficie regada, concentrada en aspersión; el goteo, con '
      f'{esn(pct(sup_met["Goteo"], sup_total_met), 1, False)} %, es el margen de mejora.</li>')
    A(f'<li>El régimen es <b>semanal</b> para el '
      f'{esn(pct(frec.get("Semanal", 0), sum(frec.values())), 0, False)} % y el almacenamiento '
      f'es <b>comunitario</b> para el {esn(pct(reserv.get("Comunitario", 0), n_res), 0, False)} %.</li>')
    A(f'<li>La tarifa mediana es de <b>{esn(st.median(t_mes), 2)} USD mensuales</b>, '
      'una contribución baja que sostiene la operación del sistema.</li>')
    A('</ul>')
    A(E.pie(corte_txt))

    os.makedirs(os.path.dirname(HTML), exist_ok=True)
    with open(HTML, 'w', encoding='utf-8') as f:
        f.write(E.documento('El predio y el acceso al agua — Padrón Guanguilquí–Porotog',
                            '\n'.join(B)))
    print(f'  capítulo: {os.path.relpath(HTML, BASE)}  (corte: {corte_txt})')

    # ── Excel ──
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill
    wb = Workbook()
    azul, blanco = PatternFill('solid', fgColor='1e4d8c'), Font(color='FFFFFF', bold=True)

    def hoja(nombre, cab, filas):
        ws = wb.create_sheet(nombre)
        ws.append(cab)
        for c in ws[1]:
            c.fill, c.font = azul, blanco
        for f_ in filas:
            ws.append(f_)
        for col in ws.columns:
            ws.column_dimensions[col[0].column_letter].width = max(
                12, min(42, max(len(str(c.value or '')) for c in col) + 2))

    hoja('Resumen', ['Indicador', 'Valor'], [
        ['Predios registrados', N], ['Superficie total (ha)', round(ha_t, 2)],
        ['Superficie con riego (ha)', round(ha_r, 2)],
        ['% con riego', round(pct(a_riego, a_total), 1)],
        ['Superficie mediana del predio catastral (m2)', round(med_area)],
        ['Caudal del sistema (l/s)', tot_c['caudal_sistema_ls']],
        ['Superficie tecnificada (ha)', round(tecnificada / 10000, 1)],
        ['% tecnificado', round(pct(tecnificada, sup_total_met), 1)],
        ['Tarifa mediana mensual (USD)', round(st.median(t_mes), 2)],
        ['Tarifa mediana anual (USD)', round(st.median(t_anio), 2)],
    ])

    filas = []
    for com in sorted({p['_com'] for p in pri}):
        ps = [p for p in pri if p['_com'] == com]
        ar = sum(num(p, 'area_riego') for p in ps)
        at = sum(num(p, 'area_total') for p in ps)
        s_tec = sum(num(p, 'area_riego') * (num(p, 'metodo_aspersion_pct')
                                            + num(p, 'metodo_goteo_pct')) / 100 for p in ps)
        tar = [num(p, 'valor_tarifa') for p in ps
               if str(p.get('tipo_tarifa') or '').strip() == 'fijo mensual'
               and lleno(p.get('valor_tarifa')) and p['_comk'] != TARIFA_ANOMALA]
        filas.append([com, ps[0]['_sec'], len(ps), round(at / 10000, 2), round(ar / 10000, 2),
                      round(pct(ar, at), 1), round(s_tec / 10000, 2),
                      round(pct(s_tec, ar), 1) if ar else None,
                      round(st.median(tar), 2) if tar else None])
    hoja('Por comunidad', ['Comunidad', 'Sector', 'Predios', 'Área total (ha)',
                           'Área riego (ha)', '% riego', 'Tecnificada (ha)',
                           '% tecnificado', 'Tarifa mediana mensual'], filas)
    hoja('Métodos', ['Método', 'Superficie (ha)', 'Predios donde predomina', '% superficie'],
         [[m, round(sup_met[m] / 10000, 2), pred.get(m, 0), round(pct(sup_met[m], sup_total_met), 1)]
          for m in ('Aspersión', 'Gravedad', 'Goteo')])
    hoja('Frecuencia', ['Frecuencia', 'Predios'], [[k, v] for k, v in frec.most_common()])
    hoja('Reservorios', ['Tipo', 'Predios'], [[k, v] for k, v in reserv.most_common()])
    hoja('Tarifas anómalas', ['Comunidad', 'Valor declarado (USD)', 'Fichas'],
         [[TARIFA_ANOMALA, v, n] for v, n in val_anom.most_common()])

    del wb['Sheet']
    os.makedirs(os.path.dirname(XLSX), exist_ok=True)
    wb.save(XLSX)
    # Sin esto, hay builds de Excel que heredan «sin relleno» del estilo
    # base y los colores no se pintan. Ver excel_compat.py.
    from excel_compat import aplicar_formatos
    aplicar_formatos(XLSX)
    print(f'  excel   : {os.path.relpath(XLSX, BASE)}')
    print(f'\n  {esn(ha_r, 0)} ha bajo riego ({esn(pct(a_riego, a_total), 1, False)}%) | '
          f'tecnificado {esn(pct(tecnificada, sup_total_met), 1, False)}% | '
          f'tarifa mediana {esn(st.median(t_mes), 2)} USD/mes')


if __name__ == '__main__':
    main()
