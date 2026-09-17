# -*- coding: utf-8 -*-
"""
Membrete oficial de la Prefectura de Pichincha para los documentos del contrato.

Lo pidio el consorcio: los documentos del Producto 5 tienen que ir en la hoja
membretada de la Prefectura, no en la nuestra. Las dos bandas —el logo con su
doble filete arriba, y el pie de «PICHINCHA INVENCIBLE» con la direccion
abajo— se recortaron del propio `membrete.docx` que entregaron, renderizado a
300 ppp, asi que salen identicas y no hay que reproducirlas a mano.

El numero de pagina NO viene en la banda: el membrete original trae un «1»
fijo, y aqui se dibuja el que toca en cada hoja.

Se activa con la variable de entorno MEMBRETE_PREFECTURA=1, de modo que los
generadores de siempre sirven para las dos versiones sin duplicar codigo: las
fichas del padron siguen saliendo con la cabecera del estudio.
"""
import os

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
BANDAS = os.path.join(BASE, 'assets', 'membrete')
CABECERA = os.path.join(BANDAS, 'banda-cabecera.png')
PIE = os.path.join(BANDAS, 'banda-pie.png')

# Medidas tomadas del membrete original (A4, 595,4 x 841,8 pt):
#   el doble filete de la cabecera termina en y=81,4 desde arriba
#   el filete del pie empieza en y=758 desde arriba
ALTO_CABECERA = 84          # pt, del borde superior
PIE_DESDE = 752             # pt desde arriba donde empieza la banda del pie
PIE_HASTA = 810             # pt desde arriba donde termina
ANCHO_PIE = 498             # pt; a partir de ahi va el numero de pagina
NUM_X = 508                 # pt, donde el membrete pone el numero
NUM_Y_DESDE_ARRIBA = 784    # pt, linea base del numero

# Margenes que dejan libres las dos bandas. Se exponen para que cada generador
# arme su SimpleDocTemplate con ellos en vez de con los suyos.
MARGENES = dict(leftMargin=20 * mm, rightMargin=20 * mm,
                topMargin=32 * mm, bottomMargin=34 * mm)


def activo():
    """¿Toca el membrete de la Prefectura en esta corrida?"""
    return os.environ.get('MEMBRETE_PREFECTURA', '') not in ('', '0')


def margenes(por_defecto):
    """Los margenes del membrete si esta activo; si no, los del documento."""
    return MARGENES if activo() else por_defecto


def cabecera_pie(canv, doc, _ficha=None):
    """Pinta la hoja membretada. Misma firma que la cabecera del estudio."""
    canv.saveState()
    ancho, alto = A4

    if os.path.exists(CABECERA):
        canv.drawImage(CABECERA, 0, alto - ALTO_CABECERA, width=ancho,
                       height=ALTO_CABECERA, mask='auto')
    if os.path.exists(PIE):
        # La banda se recorto entre y=752 y y=810 del membrete original, asi
        # que se coloca en ese mismo sitio contado desde abajo.
        canv.drawImage(PIE, 0, alto - PIE_HASTA, width=ANCHO_PIE,
                       height=PIE_HASTA - PIE_DESDE, mask='auto')
    canv.setFont('Helvetica', 11)
    canv.setFillColor(colors.HexColor('#000000'))
    canv.drawString(NUM_X, alto - NUM_Y_DESDE_ARRIBA, str(canv.getPageNumber()))
    canv.restoreState()
