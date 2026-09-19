# -*- coding: utf-8 -*-
"""
Informe de las 12 comunidades que pidió Armando, con estadísticas y totales
jerárquicos: fichas, superficie, caudal y servicios básicos, con gráficos.

De dónde sale cada dato
------------------------
* Fichas: `fichas_predios.geojson` (recuento directo, principal/adicional).
* Superficie: `superficie_por_comunidad.json` — mide el PREDIO CATASTRAL una
  sola vez, no la ficha. Sumar el área declarada de cada ficha inflaría el
  total en los terrenos familiares, donde varios hermanos declaran partes del
  mismo predio (regla 12 del proyecto: catastral y declarada no se mezclan).
* Caudal: `caudal_por_comunidad.json` — la moda de las fichas de cada
  comunidad, NUNCA la suma de `caudal_valor` ficha a ficha (regla 3).
* Servicios básicos: sobre fichas PRINCIPALES con `material_construccion`
  registrado (eso es «tener vivienda»); agua y energía solo cuentan el 1
  (regla 18), igual que en `generar_capitulo_servicios.py`.

Las 12 filas del informe y sus decisiones de mapeo
---------------------------------------------------
Nueve nombres cruzan directo contra el catálogo oficial. Los otros tres se
resolvieron con JAVIKO el 18-sep-2026:
  - «Porotog» sola          → ASOCIACIÓN POROTOG + COMUNA POROTOG combinadas.
  - «San Vicente de Porotog» → COMUNA POROTOG (está así en los filtros de la
    web; no existe un «San Vicente» propio de Porotog en el catálogo).
  - «Porotog Avellaneda»     → AVELLANEDA sola (nombre oficial ELIOT
    AVELLANEDA), que comparte su caudal registrado con 17 de Junio.
Como consecuencia, COMUNA POROTOG aparece en dos filas: sola («San Vicente de
Porotog») y dentro del combinado («Porotog»). Se avisa en el propio documento
para que no se lea como un error.

«Guanguilqui» = HDA. GUANGUILQUI: una hacienda de 601 ha con 4 fichas y un
solo regante, muy distinta en escala a las otras once. Se incluye tal cual,
con nota aparte para que no distorsione la lectura de los gráficos.

Uso:  python -X utf8 scripts/generar_informe_comunidades_armando.py
"""
import io
import os
import sys
import unicodedata

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)

from generar_fichas_pdf import (  # noqa: E402
    A4, AZUL, TINTA, cabecera_pie, colors, mm, Paragraph,
    ParagraphStyle, Spacer, tabla_datos, titulo_seccion,
)
from reportlab.platypus import (  # noqa: E402
    Image, KeepTogether, SimpleDocTemplate, Table, TableStyle,
)

BASE = os.path.abspath(os.path.join(AQUI, '..'))
GEO = os.path.join(BASE, 'public', 'geo')
SALIDA = r'C:\Users\HP\OneDrive\Escritorio\INFORME COMUNIDADES ARMANDO.pdf'

VERDE = colors.HexColor('#15803D')
NARANJA = colors.HexColor('#C2410C')
GRIS = colors.HexColor('#64748B')

# ── Las 12 filas del informe, en el orden que dio Armando ──────────────────
# etiqueta mostrada, comunidad(es) canónicas que la componen, nota si aplica.
GRUPOS = [
    ('Larcachaca', ['LARCACHACA'], None),
    ('Libertad', ['LA LIBERTAD'], None),
    ('San Antonio', ['SAN ANTONIO'], None),
    ('San José', ['SAN JOSÉ'], None),
    ('Milagro', ['MILAGRO'], None),
    ('Candelaria', ['LA CANDELARIA'], None),
    ('Chambitola', ['CHAMBITOLA'], None),
    ('17 de Junio', ['ASOCIACIÓN 17 DE JUNIO'], None),
    ('San Vicente de Porotog', ['COMUNA POROTOG'],
     'Es la comunidad COMUNA POROTOG.'),
    ('Porotog', ['ASOCIACIÓN POROTOG', 'COMUNA POROTOG'],
     'Suma de Asociación Porotog y Comuna Porotog: esta última repite los '
     'datos de la fila «San Vicente de Porotog».'),
    ('Porotog Avellaneda', ['AVELLANEDA'],
     'Es la comunidad AVELLANEDA (nombre oficial Eliot Avellaneda).'),
    ('Guanguilqui', ['HDA. GUANGUILQUI'],
     'Es la hacienda HDA. GUANGUILQUI: 601 ha con 4 fichas y un solo '
     'regante, escala muy distinta a las otras once.'),
]


def sin_tildes(s):
    s = unicodedata.normalize('NFD', str(s or ''))
    return ''.join(c for c in s if unicodedata.category(c) != 'Mn').upper().strip()


def lleno(v):
    return v not in (None, '') and str(v).strip() != ''


def si(v):
    return str(v).strip() in ('1', 'True', 'Sí', 'Si')


def pct(a, b):
    return 100.0 * a / b if b else 0.0


def esn(v, dec=0):
    """Número con punto de miles y coma decimal."""
    s = '{:,.{}f}'.format(v or 0, dec)
    return s.replace(',', 'X').replace('.', ',').replace('X', '.')


def cargar():
    import json
    with io.open(os.path.join(GEO, 'fichas_predios.geojson'), encoding='utf-8') as f:
        fichas = [ft['properties'] for ft in json.load(f)['features']]
    with io.open(os.path.join(GEO, 'superficie_por_comunidad.json'), encoding='utf-8') as f:
        sup = {c['comunidad']: c for c in json.load(f)['comunidades']}
    with io.open(os.path.join(GEO, 'caudal_por_comunidad.json'), encoding='utf-8') as f:
        cau_raw = json.load(f)['comunidades']
    cau = {sin_tildes(k): v for k, v in cau_raw.items()}
    return fichas, sup, cau


def calcular(fichas, sup, cau):
    """Una fila de datos por cada grupo de GRUPOS."""
    filas = []
    for etiqueta, coms, nota in GRUPOS:
        del_grupo = [p for p in fichas if (p.get('comunidad') or '').strip() in coms]
        principales = [p for p in del_grupo if not p.get('es_ficha_hija')]
        adicionales = [p for p in del_grupo if p.get('es_ficha_hija')]

        viv = [p for p in principales if lleno(p.get('material_construccion'))]
        con_agua = sum(1 for p in viv if si(p.get('agua_consumo')))
        con_luz = sum(1 for p in viv if si(p.get('energia_electrica')))

        cat_ha = sum(sup.get(c, {}).get('superficie_catastral_ha', 0) for c in coms)
        riego_ha = sum(sup.get(c, {}).get('riego_ajustado_ha', 0) for c in coms)
        sin_riego_ha = sum(sup.get(c, {}).get('sin_riego_catastral_ha', 0) for c in coms)
        predios = sum(sup.get(c, {}).get('predios_catastrales', 0) for c in coms)

        caudales = [(c, cau.get(sin_tildes(c))) for c in coms]

        filas.append({
            'etiqueta': etiqueta, 'comunidades': coms, 'nota': nota,
            'principales': len(principales), 'adicionales': len(adicionales),
            'total': len(del_grupo),
            'predios': predios,
            'cat_ha': cat_ha, 'riego_ha': riego_ha, 'sin_riego_ha': sin_riego_ha,
            'n_viv': len(viv), 'con_agua': con_agua, 'con_luz': con_luz,
            'caudales': caudales,
        })
    return filas


# ── gráficos ────────────────────────────────────────────────────────────────
def _grafico_barras(etiquetas, valores, color, fmt_valor, alto=8.2, destacar=None):
    """Barras horizontales con el valor rotulado al final de cada una.

    `color` y el color de resalte son cadenas hex ('#1E3A8A'), no objetos
    Color de reportlab: matplotlib los necesita como texto.
    """
    fig, ax = plt.subplots(figsize=(15.2 / 2.54, alto / 2.54), dpi=200)
    y = range(len(etiquetas))
    colores = ['#C2410C' if destacar and e in destacar else color
               for e in etiquetas]
    ax.barh(list(y)[::-1], valores, color=colores, height=0.62)
    ax.set_yticks(list(y)[::-1])
    ax.set_yticklabels(etiquetas, fontsize=8.5, color='#1F2937')
    maxv = max(valores) if valores else 1
    for i, v in enumerate(valores):
        ax.text(v + maxv * 0.015, len(etiquetas) - 1 - i, fmt_valor(v),
                va='center', fontsize=8, color='#1F2937')
    ax.set_xlim(0, maxv * 1.18 if maxv else 1)
    for s in ('top', 'right', 'bottom'):
        ax.spines[s].set_visible(False)
    ax.xaxis.set_visible(False)
    ax.tick_params(left=False)
    fig.tight_layout(pad=0.4)
    buf = io.BytesIO()
    fig.savefig(buf, format='png', transparent=True)
    plt.close(fig)
    buf.seek(0)
    return buf


def _tabla_con_parrafos(cabeceras, filas, anchos):
    """Como tabla_datos(), pero acepta Paragraph ya construidos en las celdas.

    tabla_datos() pasa cada celda por esc(), que escapa `<` y `>`: cualquier
    <br/> que se le pase sale literal en el PDF. Hace falta cuando una celda
    necesita mas de una linea, como el caudal de «Porotog», que junta dos
    comunidades.
    """
    st_cab = ParagraphStyle('cab', fontName='Helvetica-Bold', fontSize=8,
                            leading=10, textColor=colors.white)
    st_celda = ParagraphStyle('celda', fontName='Helvetica', fontSize=8,
                              leading=10.5, textColor=TINTA)
    data = [[Paragraph(h.upper(), st_cab) for h in cabeceras]]
    for fila in filas:
        data.append([c if hasattr(c, 'getPlainText') else Paragraph(str(c), st_celda)
                     for c in fila])
    t = Table(data, colWidths=anchos, repeatRows=1)
    t.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
        ('BACKGROUND', (0, 0), (-1, 0), AZUL),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1),
         [colors.white, colors.HexColor('#F8FAFC')]),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    return t


def _imagen(buf, ancho_mm=160):
    from PIL import Image as PILImage
    buf.seek(0)
    with PILImage.open(buf) as im:
        proporcion = im.height / im.width
    buf.seek(0)
    return Image(buf, width=ancho_mm * mm, height=ancho_mm * mm * proporcion)


def main():
    fichas, sup, cau = cargar()
    filas = calcular(fichas, sup, cau)

    tot_fichas = len(fichas)  # universo completo, 6.830
    grupo_total = sum(f['total'] for f in filas)
    grupo_principales = sum(f['principales'] for f in filas)
    grupo_cat_ha = sum(f['cat_ha'] for f in filas)

    st_h = ParagraphStyle('h', fontName='Helvetica-Bold', fontSize=13,
                          leading=16, textColor=AZUL, alignment=1)
    st_sub = ParagraphStyle('sub', fontName='Helvetica', fontSize=9.5,
                            leading=12, alignment=1, textColor=GRIS)
    st_p = ParagraphStyle('p', fontName='Helvetica', fontSize=9, leading=12.5,
                          textColor=TINTA, alignment=4)
    st_li = ParagraphStyle('li', parent=st_p, leftIndent=6 * mm, spaceAfter=2,
                           fontSize=8.3, leading=11)
    st_pie = ParagraphStyle('pie', fontName='Helvetica-Oblique', fontSize=7.5,
                            leading=10, textColor=GRIS, alignment=4)

    h = [
        Paragraph('Informe de comunidades', st_h), Spacer(0, 1.5 * mm),
        Paragraph('Fichas, superficie, caudal y servicios básicos de las 12 '
                  'comunidades solicitadas', st_sub),
        Spacer(0, 5 * mm),
        Paragraph(f'Este informe reúne <b>{esn(grupo_total)} fichas</b> '
                  f'({esn(grupo_principales)} principales) sobre '
                  f'<b>{esn(grupo_cat_ha, 1)} ha catastrales</b>, en las doce '
                  'comunidades siguientes: Larcachaca, Libertad, San Antonio, '
                  'San José, Milagro, Candelaria, Chambitola, 17 de Junio, San '
                  'Vicente de Porotog, Porotog, Porotog Avellaneda y '
                  'Guanguilqui. Representan el '
                  f'{esn(pct(grupo_total, tot_fichas), 1)} % de las '
                  f'{esn(tot_fichas)} fichas del padrón completo.', st_p),
        Spacer(0, 3 * mm),
    ]

    # ── nota de mapeo, transparente sobre las decisiones tomadas ──
    notas = [f['nota'] for f in filas if f['nota']]
    if notas:
        h.append(Paragraph(
            '<b>Sobre tres nombres de la lista:</b> ' + ' '.join(notas), st_pie))
        h.append(Spacer(0, 4 * mm))

    etiquetas = [f['etiqueta'] for f in filas]

    # ── 1. fichas ──
    h += titulo_seccion('1. Fichas por comunidad')
    filas_tabla = [[f['etiqueta'], esn(f['principales']), esn(f['adicionales']),
                    esn(f['total']), f'{esn(pct(f["total"], grupo_total), 1)} %']
                   for f in filas]
    h.append(tabla_datos(
        ['Comunidad', 'Principales', 'Adicionales', 'Total', '% del grupo'],
        filas_tabla, [55 * mm, 30 * mm, 30 * mm, 25 * mm, 30 * mm]))
    h.append(Spacer(0, 3 * mm))
    grafico = _grafico_barras(etiquetas, [f['total'] for f in filas],
                              '#1E3A8A', lambda v: esn(v))
    h.append(KeepTogether([_imagen(grafico)]))
    h.append(Spacer(0, 4 * mm))

    # ── 2. superficie ──
    h += titulo_seccion('2. Superficie catastral y con riego')
    h.append(Paragraph('Medición catastral: cada predio cuenta una sola vez, '
                       'aunque varios herederos hayan declarado su parte por '
                       'separado.', st_pie))
    h.append(Spacer(0, 2 * mm))
    filas_tabla = [[f['etiqueta'], f'{esn(f["cat_ha"], 1)} ha',
                    f'{esn(f["riego_ha"], 1)} ha',
                    f'{esn(pct(f["riego_ha"], f["cat_ha"]), 1)} %']
                   for f in filas]
    h.append(tabla_datos(
        ['Comunidad', 'Superficie catastral', 'Con riego', '% con riego'],
        filas_tabla, [55 * mm, 40 * mm, 35 * mm, 30 * mm]))
    h.append(Spacer(0, 3 * mm))
    grafico = _grafico_barras(etiquetas, [f['cat_ha'] for f in filas],
                              '#15803D', lambda v: f'{esn(v, 1)} ha',
                              destacar=['Guanguilqui'])
    h.append(KeepTogether([_imagen(grafico)]))
    h.append(Paragraph('En naranja, Guanguilqui: una sola hacienda de 601 ha '
                       'con 4 fichas, fuera de escala frente a las demás.',
                       st_pie))
    h.append(Spacer(0, 4 * mm))

    # ── 3. caudal ──
    h += titulo_seccion('3. Caudal registrado')
    h.append(Paragraph(
        '<b>Estas cifras no son directamente comparables entre comunidades.</b> '
        'En unas fichas los técnicos anotaron el caudal que recibe cada '
        'familia y en otras el de la acequia completa; hasta que se unifique '
        'el criterio con cada directiva, un valor bajo no significa menos '
        'agua, puede significar que se midió distinto. Asociación Porotog '
        '(1,08 l/s) y Comuna Porotog (0,54 l/s) son los casos más claros de '
        'medición por familia, frente a valores de 12 a 42 l/s en el resto.',
        st_p))
    h.append(Spacer(0, 2 * mm))
    filas_cau = []
    for f in filas:
        partes = []
        for com, dato in f['caudales']:
            if dato:
                partes.append(f'{com.title()}: {esn(dato["caudal_ls"], 2)} l/s')
            else:
                partes.append(f'{com.title()}: sin dato')
        filas_cau.append([f['etiqueta'], Paragraph('<br/>'.join(partes), st_li)])
    h.append(_tabla_con_parrafos(['Comunidad', 'Caudal registrado'], filas_cau,
                                 [55 * mm, 105 * mm]))
    h.append(Spacer(0, 4 * mm))

    # ── 4. servicios básicos ──
    h += titulo_seccion('4. Servicios básicos, sobre viviendas')
    h.append(Paragraph('Solo se cuentan las fichas principales con vivienda '
                       'declarada (material de construcción registrado). Los '
                       'predios sin construcción no entran en el cálculo.',
                       st_pie))
    h.append(Spacer(0, 2 * mm))
    filas_tabla = [[f['etiqueta'], esn(f['n_viv']),
                    f'{esn(pct(f["con_agua"], f["n_viv"]), 1)} %',
                    f'{esn(pct(f["con_luz"], f["n_viv"]), 1)} %']
                   for f in filas]
    h.append(tabla_datos(
        ['Comunidad', 'Viviendas', '% con agua', '% con energía'],
        filas_tabla, [55 * mm, 30 * mm, 40 * mm, 40 * mm]))
    h.append(Spacer(0, 3 * mm))
    grafico = _grafico_barras(
        etiquetas, [pct(f['con_agua'], f['n_viv']) for f in filas],
        '#0EA5E9', lambda v: f'{esn(v, 1)} %', alto=8.2)
    h.append(KeepTogether([_imagen(grafico)]))
    h.append(Paragraph('% de viviendas con agua de consumo, por comunidad.',
                       st_pie))

    cab = {'creado_por': None, '_investigador': 'AP&CATASTROS'}
    doc = SimpleDocTemplate(
        SALIDA, pagesize=A4, leftMargin=14 * mm, rightMargin=14 * mm,
        topMargin=27 * mm, bottomMargin=13 * mm,
        title='Informe de comunidades',
        author='AP&CATASTROS — Padrón Guanguilquí–Porotog')
    doc.build(h, onFirstPage=lambda c, d: cabecera_pie(c, d, cab),
              onLaterPages=lambda c, d: cabecera_pie(c, d, cab))

    print('Fichas del grupo :', esn(grupo_total), f'({esn(pct(grupo_total, tot_fichas), 1)} % del padrón)')
    print('Superficie catastral del grupo:', esn(grupo_cat_ha, 1), 'ha')
    print('✔', SALIDA)
    return 0


if __name__ == '__main__':
    sys.exit(main())
