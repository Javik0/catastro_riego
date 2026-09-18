# -*- coding: utf-8 -*-
"""
El resumen de las 6.830 fichas en PDF, vertical y sobre el membrete.

Es el mismo listado que generar_indice_pdf.py, pero con otro rotulo: sin
mencionar "padron" ni el nombre del sistema de riego, solo "Resumen de
fichas". Lo pidio Javiko como version alterna del mismo documento.

Sale del mismo `INDICE DE FICHAS.xlsx` que va en la entrega, con las siete
columnas que identifican cada ficha; la octava del Excel es la ruta del
archivo y no aporta en papel.

Cierra con el bloque de las tres firmas. El sello de la firma electronica no
se dibuja aqui: lo estampa el programa de firmado cuando se firma el PDF, asi
que lo que queda es la linea y el nombre debajo.

Uso:  python -X utf8 scripts/generar_indice_pdf.py
"""
import os
import sys

from openpyxl import load_workbook
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
)

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)

os.environ['MEMBRETE_PREFECTURA'] = '1'
import membrete_prefectura  # noqa: E402

ESCRITORIO = r'C:\Users\HP\OneDrive\Escritorio'
EXCEL = os.path.join(ESCRITORIO, 'FICHAS PDF POROTOG', 'INDICE DE FICHAS.xlsx')
SALIDA = os.path.join(ESCRITORIO, 'RESUMEN DE FICHAS.pdf')

AZUL = colors.HexColor('#1E3A8A')
TINTA = colors.HexColor('#1F2937')

# Las siete primeras del Excel; la octava es la ruta del PDF y no va en papel.
COLUMNAS = 7

FIRMAS = [
    ('ARQ. ARMANDO PROAÑO', 'CONSULTOR DE CATASTROS'),
    ('TNLGO. STEVEN PROAÑO', 'TÉCNICO SUPERVISOR'),
    ('TNLGO. MARLON DAVILA', 'TÉCNICO EN SISTEMAS Y GIS'),
]


def leer():
    ws = load_workbook(EXCEL, read_only=True).active
    filas = list(ws.iter_rows(values_only=True))
    cab = [str(c) if c is not None else '' for c in filas[0][:COLUMNAS]]
    datos = [[('' if c is None else str(c)) for c in f[:COLUMNAS]] for f in filas[1:]]
    return cab, datos


def bloque_firmas(ancho):
    """Las tres firmas en una fila, con su linea y el cargo debajo."""
    st_n = ParagraphStyle('n', fontName='Helvetica-Bold', fontSize=8,
                          leading=10, alignment=1, textColor=TINTA)
    st_c = ParagraphStyle('c', fontName='Helvetica', fontSize=7.5,
                          leading=9, alignment=1, textColor=TINTA)
    ancho_col = ancho / len(FIRMAS)
    fila_linea = [''] * len(FIRMAS)
    fila_nom = [Paragraph(n, st_n) for n, _ in FIRMAS]
    fila_car = [Paragraph(c, st_c) for _, c in FIRMAS]
    t = Table([fila_linea, fila_nom, fila_car],
              colWidths=[ancho_col] * len(FIRMAS),
              rowHeights=[22 * mm, None, None])
    t.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'BOTTOM'),
        # la raya sobre la que se firma
        ('LINEBELOW', (0, 0), (-1, 0), 0.7, TINTA),
        ('TOPPADDING', (0, 1), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 1),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
    ]))
    return t


def main():
    cab, datos = leer()
    print(f'Filas del índice: {len(datos)}', flush=True)

    marg = membrete_prefectura.MARGENES
    ancho = A4[0] - marg['leftMargin'] - marg['rightMargin']

    doc = SimpleDocTemplate(
        SALIDA, pagesize=A4, title='Resumen de fichas',
        author='AP&CATASTROS', **marg)

    st_h = ParagraphStyle('h', fontName='Helvetica-Bold', fontSize=12.5,
                          leading=15, alignment=1, textColor=AZUL)
    st_s = ParagraphStyle('s', fontName='Helvetica', fontSize=9, leading=11.5,
                          alignment=1, textColor=colors.HexColor('#475569'))
    st_c = ParagraphStyle('c', fontName='Helvetica-Bold', fontSize=6.2,
                          leading=7.6, textColor=colors.white)
    st_d = ParagraphStyle('d', fontName='Helvetica', fontSize=6, leading=7.4,
                          textColor=TINTA)

    # Repartidas sobre el ancho util: el titular se lleva lo que sobra porque
    # es el unico que de verdad necesita envolver.
    proporciones = [0.075, 0.175, 0.145, 0.145, 0.285, 0.10, 0.075]
    anchos = [ancho * p for p in proporciones]

    historia = [
        Paragraph('Resumen de fichas', st_h), Spacer(0, 1.5 * mm),
        Paragraph('Catastro socioeconómico y productivo predial', st_s),
        Spacer(0, 1 * mm),
        Paragraph(f'{len(datos):,}'.replace(',', '.') + ' fichas · '
                  'información al 19 de agosto de 2026', st_s),
        Spacer(0, 4 * mm),
    ]

    cuerpo = [[Paragraph(c, st_c) for c in cab]]
    cuerpo += [[Paragraph(v, st_d) for v in f] for f in datos]

    t = Table(cuerpo, colWidths=anchos, repeatRows=1)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), AZUL),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.25, colors.HexColor('#CBD5E1')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1),
         [colors.white, colors.HexColor('#F8FAFC')]),
        ('TOPPADDING', (0, 0), (-1, -1), 1.6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 1.6),
        ('LEFTPADDING', (0, 0), (-1, -1), 3),
        ('RIGHTPADDING', (0, 0), (-1, -1), 3),
    ]))
    historia.append(t)

    # Las firmas no se parten de la hoja: van juntas o pasan a la siguiente.
    historia.append(KeepTogether([Spacer(0, 10 * mm), bloque_firmas(ancho)]))

    doc.build(historia,
              onFirstPage=lambda c, d: membrete_prefectura.cabecera_pie(c, d),
              onLaterPages=lambda c, d: membrete_prefectura.cabecera_pie(c, d))
    print('✔', SALIDA, f'({os.path.getsize(SALIDA) / 1048576:.1f} MB)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
