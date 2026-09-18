# -*- coding: utf-8 -*-
"""
Convierte a Word los mismos bloques con que se arma un PDF de reportlab.

Por que asi y no reescribiendo el texto: si el documento se redactara dos
veces —una para el PDF y otra para el Word— con el tiempo se separarian y
nadie sabria cual manda. Aqui hay una sola fuente: los generadores construyen
su lista de bloques como siempre, y este modulo la pinta en Word.

La plantilla es el propio `membrete.docx` de la Prefectura, de modo que el
Word sale con su cabecera y su pie reales, no con una imitacion.
"""
import os
import re

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt, RGBColor

AZUL = RGBColor(0x1E, 0x3A, 0x8A)
GRIS = RGBColor(0x47, 0x55, 0x69)
TINTA = RGBColor(0x1F, 0x29, 0x37)

ALINEACION = {
    0: WD_ALIGN_PARAGRAPH.LEFT,
    1: WD_ALIGN_PARAGRAPH.CENTER,
    2: WD_ALIGN_PARAGRAPH.RIGHT,
    4: WD_ALIGN_PARAGRAPH.JUSTIFY,
}


def _limpiar(t):
    """El texto de reportlab trae marcado propio; se pasa a texto llano."""
    t = re.sub(r'<br\s*/?>', '\n', t or '')
    t = t.replace('&nbsp;', ' ').replace('&amp;', '&')
    t = t.replace('&lt;', '<').replace('&gt;', '>')
    return t


def _escribir_con_negritas(parrafo, texto, tam, color):
    """Reparte el texto en tramos, respetando los <b> del original."""
    for tramo in re.split(r'(<b>.*?</b>)', _limpiar(texto)):
        if not tramo:
            continue
        negrita = tramo.startswith('<b>')
        limpio = re.sub(r'</?b>', '', tramo)
        limpio = re.sub(r'<[^>]+>', '', limpio)      # cualquier otra etiqueta
        if not limpio:
            continue
        r = parrafo.add_run(limpio)
        r.bold = negrita
        r.font.size = Pt(tam)
        r.font.color.rgb = color
        r.font.name = 'Calibri'


def _es_titulo_seccion(tabla):
    """titulo_seccion() devuelve una tabla de una sola celda con el rotulo."""
    return len(tabla._cellvalues) == 1 and len(tabla._cellvalues[0]) == 1


def _texto_celda(c):
    """El texto de una celda, venga como venga.

    Algunas celdas no traen el parrafo suelto sino dentro de una lista —es lo
    que hace titulo_seccion()—, y sin desenvolverlo se acaba escribiendo el
    objeto entero en el documento.
    """
    if c is None:
        return ''
    if isinstance(c, (list, tuple)):
        return '\n'.join(_texto_celda(x) for x in c if x is not None).strip()
    if hasattr(c, 'text'):
        return re.sub(r'<[^>]+>', '', _limpiar(c.text))
    return str(c)


def _poner_tabla(doc, tabla):
    filas = tabla._cellvalues
    if not filas:
        return
    t = doc.add_table(rows=len(filas), cols=len(filas[0]))
    t.style = 'Table Grid'
    for i, fila in enumerate(filas):
        for j, celda in enumerate(fila):
            if j >= len(t.columns):
                continue
            p = t.cell(i, j).paragraphs[0]
            r = p.add_run(_texto_celda(celda))
            r.font.size = Pt(8.5)
            r.font.name = 'Calibri'
            if i == 0:                      # la primera fila es la cabecera
                r.bold = True
                r.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
                _sombrear(t.cell(i, j), '1E3A8A')
    doc.add_paragraph()


def _sombrear(celda, hex_color):
    from docx.oxml.ns import qn
    from docx.oxml import OxmlElement
    sombra = OxmlElement('w:shd')
    sombra.set(qn('w:val'), 'clear')
    sombra.set(qn('w:fill'), hex_color)
    celda._tc.get_or_add_tcPr().append(sombra)


def _pintar(doc, bloques, primero):
    """Recorre los bloques del PDF y los va escribiendo en el documento."""
    for b in bloques:
        nombre = type(b).__name__

        if nombre == 'KeepTogether':
            _pintar(doc, getattr(b, '_content', []), primero)
            continue

        if nombre == 'Spacer':
            continue

        if nombre == 'Image':
            ruta = getattr(b, 'filename', None)
            if isinstance(ruta, str) and os.path.exists(ruta):
                from docx.shared import Mm
                p = doc.add_paragraph()
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                # El ancho util de la hoja membretada son unos 165 mm.
                ancho = min(165, (getattr(b, 'drawWidth', 400) or 400) / 72 * 25.4)
                p.add_run().add_picture(ruta, width=Mm(ancho))
            continue

        if nombre == 'Table':
            if _es_titulo_seccion(b):
                rotulo = _texto_celda(b._cellvalues[0][0])
                p = doc.add_paragraph()
                p.space_before = Pt(10)
                r = p.add_run(rotulo)
                r.bold = True
                r.font.size = Pt(11)
                r.font.color.rgb = AZUL
                r.font.name = 'Calibri'
            else:
                _poner_tabla(doc, b)
            continue

        if nombre == 'Paragraph':
            estilo = getattr(b, 'style', None)
            tam = getattr(estilo, 'fontSize', 9) or 9
            alin = getattr(estilo, 'alignment', 0)
            sangria = getattr(estilo, 'leftIndent', 0) or 0
            p = doc.add_paragraph()
            p.alignment = ALINEACION.get(alin, WD_ALIGN_PARAGRAPH.LEFT)
            if sangria:
                from docx.shared import Mm
                p.paragraph_format.left_indent = Mm(sangria / 72 * 25.4)
            color = TINTA
            if alin == 1 and tam >= 12:
                color, tam = AZUL, 14          # titulo del documento
            elif alin == 1 and tam < 10:
                color = GRIS                   # subtitulo
            _escribir_con_negritas(p, getattr(b, 'text', ''), tam, color)
            continue
    return doc


def escribir(bloques, destino, plantilla):
    """Arma el .docx sobre la plantilla membretada."""
    doc = Document(plantilla)
    # La plantilla trae el cuerpo vacio con un parrafo suelto: se retira para
    # que el documento no empiece con una linea en blanco.
    for p in list(doc.paragraphs):
        if not p.text.strip():
            p._element.getparent().remove(p._element)
    _pintar(doc, bloques, True)
    doc.save(destino)
    return destino
