# -*- coding: utf-8 -*-
"""
Capítulo del informe técnico: "Servicios básicos y hábitat".

Cubre la sección 3 de la ficha: agua de consumo, energía eléctrica, material de
la vivienda y altitud del predio.

LA BASE SON LAS VIVIENDAS, NO EL PADRÓN
---------------------------------------
Solo dos de cada tres fichas principales declaran una construcción en el
predio. No es un vacío de levantamiento (el campo está cerrado): un predio
sin casa no tiene agua ni luz porque no hay vivienda. Regla del cliente
(9-ago-2026): sin `material_construccion` no hay vivienda, y agua y energía
vacías son la respuesta correcta. Por eso el denominador de agua y energía
son las fichas CON VIVIENDA (material lleno), la misma regla que aplican los
informes del sociólogo (96,3 % y 92,1 %, no 64,9 % y 61,4 % sobre todas).
Hasta el 4-sep-2026 este capítulo usaba un tercer denominador —solo quienes
respondieron la pregunta— y daba 96,6 % y 95,3 %; JAVIKO decidió unificarlo.

Nunca se atribuye el vacío a personas o a la organización del trabajo: el
informe describe el estado del dato, no el desempeño de quien lo levanta.

SALIDAS
  docs/CAPITULO-servicios-basicos.html
  build_entrega/Servicios_Basicos.xlsx
"""

import os
import sqlite3
import statistics as st
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from comunidades_canon import canonica, nombre_publico, normalizar  # noqa: E402
import informe_estilo as E  # noqa: E402
import informe_graficos as G  # noqa: E402

GPKG = r"C:\Users\HP\QField\cloud\porotog_levantamiento_offline\data.gpkg"
T = 'Fichas_Predios_880eb10d_d887_4fc6_99a2_8af3ac63877e'
BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
HTML = os.path.join(BASE, 'docs', 'CAPITULO-servicios-basicos.html')
XLSX = os.path.join(BASE, 'build_entrega', 'Servicios_Basicos.xlsx')


def lleno(v):
    return v not in (None, '') and str(v).strip() != ''


def si(v):
    return str(v).strip() in ('1', 'True', 'Sí', 'Si')


def pct(a, b):
    return 100.0 * a / b if b else 0.0


def main():
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
        val = [(n_, v) for n_, v in c.most_common() if normalizar(n_) == k]
        display[k] = val[0][0] if val else k
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

    N = len(pri)
    # Viviendas: fichas principales con material de construcción. Es el
    # denominador de agua y energía (ver cabecera).
    viv = [p for p in pri if lleno(p.get('material_construccion'))]
    n_viv = len(viv)
    mat = Counter(str(p['material_construccion']).strip().title() for p in viv)
    n_mat = sum(mat.values())
    # El campo trae 1 (dispone), 0 (no dispone) o vacío (sin dato: los
    # 103 + 216 pendientes de la revisión de campo). Solo el 1 es «dispone».
    con_agua = sum(1 for p in viv if si(p.get('agua_consumo')))
    con_ener = sum(1 for p in viv if si(p.get('energia_electrica')))
    sd_agua = sum(1 for p in viv if not lleno(p.get('agua_consumo')))
    sd_ener = sum(1 for p in viv if not lleno(p.get('energia_electrica')))
    registrado = n_viv
    cot = [float(p['cota_msnm']) for p in pri if lleno(p.get('cota_msnm'))]

    # viviendas por sector
    cob_sector = {}
    for sec in sorted({p['_sec'] for p in pri if not p['_sec'].startswith('(')}):
        ps = [p for p in pri if p['_sec'] == sec]
        r = sum(1 for p in ps if lleno(p.get('material_construccion')))
        cob_sector[sec] = (r, len(ps), pct(r, len(ps)))

    G.preparar()
    G.configurar(os.path.join(BASE, 'docs'), 'graficos-capitulos')
    B = []
    A = B.append
    A(E.cabecera('Servicios básicos y hábitat',
                 'Agua de consumo, energía, vivienda y altitud · '
                 'Capítulo del informe técnico'))
    A(E.aviso_corte(corte_txt, N, pendientes))

    # El 64 % NO es avance de levantamiento (cerrado el 5-ago-2026): es la
    # proporción de predios CON VIVIENDA. Regla 2 del cliente (9-ago-2026):
    # sin material de construcción no hay vivienda, y entonces agua y luz
    # vacías son la respuesta correcta. Leerlo como cobertura pendiente
    # hacía parecer que a un tercio del padrón le falta el servicio.
    A('<p>Este capítulo describe la <b>vivienda</b> del predio: '
      f'<b>{registrado:,} de {N:,} fichas principales ({pct(registrado, N):.1f} %)</b> '
      'declaran una construcción. En los demás predios no hay vivienda, y por eso '
      'los porcentajes de agua y energía se calculan sobre las viviendas, no '
      'sobre el total del padrón.</p>')

    A(E.kpis([
        (f'{pct(registrado, N):.0f}%', 'de las fichas principales con vivienda'),
        (f'{pct(con_agua, n_viv):.1f}%', 'de las viviendas con agua de consumo'),
        (f'{pct(con_ener, n_viv):.1f}%', 'de las viviendas con energía eléctrica'),
        (f'{st.median(cot):,.0f}', 'msnm (altitud mediana)'),
    ]))

    A('<h2>1. Predios con vivienda</h2>')
    A(f'<p>De los {N:,} predios con ficha principal, <b>{registrado:,} '
      f'({pct(registrado, N):.1f} %) declaran una vivienda</b> (material de '
      'construcción registrado). Los demás son predios sin casa: lotes de '
      'cultivo o pastoreo donde no corresponde preguntar por agua de consumo ni '
      'energía. La proporción por sector:</p>')
    A('<table class="evitar-corte"><tr><th>Sector</th><th class="n">Con vivienda</th>'
      '<th class="n">Fichas principales</th><th>Proporción</th></tr>')
    for sec, (r, t, p) in cob_sector.items():
        A(f'<tr><td>{sec}</td><td class="n">{r:,}</td><td class="n">{t:,}</td>'
          f'<td>{E.barra(p)}</td></tr>')
    A('</table>')

    A('<h2>2. Agua de consumo y energía eléctrica</h2>')
    A('<table class="evitar-corte"><tr><th>Servicio</th><th class="n">Dispone</th>'
      '<th class="n">No dispone</th><th class="n">Sin dato</th>'
      '<th class="n">Viviendas</th><th>Cobertura</th></tr>')
    A(f'<tr><td>Agua de consumo</td><td class="n">{con_agua:,}</td>'
      f'<td class="n">{n_viv - con_agua - sd_agua:,}</td><td class="n">{sd_agua:,}</td>'
      f'<td class="n">{n_viv:,}</td><td>{E.barra(pct(con_agua, n_viv))}</td></tr>')
    A(f'<tr><td>Energía eléctrica</td><td class="n">{con_ener:,}</td>'
      f'<td class="n">{n_viv - con_ener - sd_ener:,}</td><td class="n">{sd_ener:,}</td>'
      f'<td class="n">{n_viv:,}</td><td>{E.barra(pct(con_ener, n_viv))}</td></tr>')
    A('</table>')
    A(f'<p>Entre las viviendas, la cobertura de ambos servicios es alta: '
      f'<b>{pct(con_agua, n_viv):.1f} % dispone de agua de consumo</b> y '
      f'<b>{pct(con_ener, n_viv):.1f} % de energía eléctrica</b>. Las viviendas que '
      f'declaran no tener el servicio son {n_viv - con_agua - sd_agua} y '
      f'{n_viv - con_ener - sd_ener} respectivamente, cifras reducidas pero '
      'identificables predio a predio para una eventual intervención focalizada. '
      f'En {sd_agua} y {sd_ener} viviendas el dato quedó sin registrar; figuran en '
      'la revisión de campo y no se cuentan como cobertura.</p>')
    b64 = G.g_barras_agrupadas(
        'servicios-agua-energia', ['Agua de consumo', 'Energía eléctrica'],
        [('Dispone', '#10b981', [con_agua, con_ener]),
         ('No dispone', '#ef4444', [n_viv - con_agua - sd_agua, n_viv - con_ener - sd_ener]),
         ('Sin dato', '#94a3b8', [sd_agua, sd_ener])])
    A(E.figura(b64, 'Servicios de la vivienda', f'Viviendas, {n_viv:,}.'))

    A('<h2>3. Material de la vivienda</h2>')
    A(f'<p>Se registró el material predominante de la vivienda en {n_mat:,} '
      'predios:</p>')
    A('<table class="evitar-corte"><tr><th>Material</th><th class="n">Viviendas</th>'
      '<th>Peso</th></tr>')
    for k, n in mat.most_common():
        A(f'<tr><td>{k}</td><td class="n">{n:,}</td>'
          f'<td>{E.barra(pct(n, n_mat))}</td></tr>')
    A('</table>')
    b64 = G.g_barras_h('servicios-material', mat.most_common(),
                       lambda i, n: G.PIE_COLORS[i % 8])
    A(E.figura(b64, 'Material de la vivienda', f'Viviendas, {n_mat:,}.'))
    trad = sum(n for k, n in mat.items() if k.lower() in ('tapia', 'adobe', 'madera'))
    A(f'<p>Predomina el <b>bloque</b> ({pct(mat.get("Bloque", 0), n_mat):.1f} %), '
      f'seguido del hormigón armado ({pct(mat.get("Hormigón Armado", 0), n_mat):.1f} %). '
      f'Las construcciones de materiales tradicionales —tapia, adobe y madera— '
      f'representan el {pct(trad, n_mat):.1f} % de las viviendas registradas.</p>')

    A('<h2>4. Altitud de los predios</h2>')
    A(f'<p>La cota está registrada en la totalidad de los predios '
      f'({len(cot):,} registros). El sistema se despliega entre los '
      f'<b>{min(cot):,.0f} y los {max(cot):,.0f} msnm</b>, con una mediana de '
      f'<b>{st.median(cot):,.0f} msnm</b>.</p>')
    tramos = [('Bajo 3.000 m', 0, 3000), ('3.000 – 3.200 m', 3000, 3200),
              ('3.200 – 3.400 m', 3200, 3400), ('3.400 – 3.600 m', 3400, 3600),
              ('Sobre 3.600 m', 3600, 9999)]
    A('<table class="evitar-corte"><tr><th>Franja altitudinal</th>'
      '<th class="n">Predios</th><th>Peso</th></tr>')
    filas_alt = []
    for et, lo, hi in tramos:
        n = sum(1 for x in cot if lo <= x < hi)
        filas_alt.append((et, n))
        A(f'<tr><td>{et}</td><td class="n">{n:,}</td>'
          f'<td>{E.barra(pct(n, len(cot)))}</td></tr>')
    A('</table>')
    b64 = G.g_barras_h('servicios-altitud', filas_alt, lambda i, n: '#0ea5e9')
    A(E.figura(b64, 'Altitud de los predios', f'Fichas principales con cota, {len(cot):,}.'))
    A('<p>El rango altitudinal de más de mil metros condiciona los cultivos '
      'posibles y los requerimientos de riego en cada franja, y explica la '
      'diversidad de especies descrita en el capítulo de producción.</p>')

    A('<h2>5. Conclusiones</h2>')
    A('<ul>')
    A(f'<li><b>{pct(registrado, N):.0f} % de las fichas principales declara '
      'una vivienda</b> en el predio; el resto son predios sin construcción y '
      'quedan fuera del cálculo de servicios.</li>')
    A(f'<li>Entre las viviendas, la cobertura de <b>agua de consumo '
      f'({pct(con_agua, n_viv):.1f} %) y energía eléctrica '
      f'({pct(con_ener, n_viv):.1f} %) es prácticamente universal</b>.</li>')
    A(f'<li>La vivienda es mayoritariamente de <b>bloque</b> '
      f'({pct(mat.get("Bloque", 0), n_mat):.0f} %); los materiales tradicionales '
      f'persisten en el {pct(trad, n_mat):.0f} % de los casos.</li>')
    A(f'<li>El sistema abarca desde los {min(cot):,.0f} hasta los {max(cot):,.0f} '
      'msnm, un rango que condiciona la aptitud productiva de cada zona.</li>')
    A('</ul>')
    A(E.pie(corte_txt))

    os.makedirs(os.path.dirname(HTML), exist_ok=True)
    with open(HTML, 'w', encoding='utf-8') as f:
        f.write(E.documento('Servicios básicos y hábitat — Padrón Guanguilquí–Porotog',
                            '\n'.join(B)))
    print(f'  capítulo: {os.path.relpath(HTML, BASE)}  (corte: {corte_txt})')

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
                12, min(40, max(len(str(c.value or '')) for c in col) + 2))

    hoja('Resumen', ['Indicador', 'Valor'], [
        ['Predios con ficha principal', N],
        ['Con vivienda (material registrado)', registrado],
        ['% con vivienda', round(pct(registrado, N), 1)],
        ['% con agua (sobre viviendas)', round(pct(con_agua, n_viv), 1)],
        ['% con energía (sobre viviendas)', round(pct(con_ener, n_viv), 1)],
        ['Altitud mediana (msnm)', round(st.median(cot))],
    ])
    hoja('Viviendas por sector', ['Sector', 'Con vivienda', 'Fichas principales', '% con vivienda'],
         [[s, r, t, round(p, 1)] for s, (r, t, p) in cob_sector.items()])
    hoja('Materiales', ['Material', 'Viviendas', '%'],
         [[k, n, round(pct(n, n_mat), 1)] for k, n in mat.most_common()])
    filas = []
    for com in sorted({p['_com'] for p in pri}):
        ps = [p for p in pri if p['_com'] == com]
        r = [p for p in ps if lleno(p.get('material_construccion'))]
        filas.append([com, ps[0]['_sec'], len(ps), len(r), round(pct(len(r), len(ps)), 1),
                      round(pct(sum(1 for p in r if si(p.get('agua_consumo'))), len(r)), 1) if r else None,
                      round(pct(sum(1 for p in r if si(p.get('energia_electrica'))), len(r)), 1) if r else None])
    hoja('Por comunidad', ['Comunidad', 'Sector', 'Fichas principales', 'Con vivienda',
                           '% con vivienda', '% agua (de viviendas)', '% energía (de viviendas)'], filas)

    del wb['Sheet']
    os.makedirs(os.path.dirname(XLSX), exist_ok=True)
    wb.save(XLSX)
    # Sin esto, hay builds de Excel que heredan «sin relleno» del estilo
    # base y los colores no se pintan. Ver excel_compat.py.
    from excel_compat import aplicar_formatos
    aplicar_formatos(XLSX)
    print(f'  excel   : {os.path.relpath(XLSX, BASE)}')
    print(f'\n  con vivienda {pct(registrado, N):.0f}% | agua {pct(con_agua, n_viv):.1f}% | '
          f'energía {pct(con_ener, n_viv):.1f}% (sobre viviendas)')


if __name__ == '__main__':
    main()
