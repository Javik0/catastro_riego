# -*- coding: utf-8 -*-
"""
Documento que presenta las capas Shapefile al consorcio.

Acompaña a la carpeta `SHP - Capas de Investigacion` dentro de la entrega de
fichas. Explica qué trae cada capa, en qué sistema de referencia está, cómo se
relacionan entre sí y por qué algunos nombres de campo aparecen abreviados (el
formato Shapefile los limita a 10 caracteres).

Las capas salen del GeoPackage del contratante (`generar_gpkg_cliente.py`),
convertidas con ogr2ogr. Ese GeoPackage es el conjunto ya definido como
entregable: capas de solo lectura, sin las expresiones ni el andamiaje del
proyecto de campo.

Uso:
    python -X utf8 scripts/generar_leeme_shp.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from generar_fichas_pdf import (  # noqa: E402
    A4, AZUL, BORDE, TINTA, ANCHO_UTIL, ST_TD, ST_TH,
    cabecera_pie, colors, fmt_num, mm, Paragraph, ParagraphStyle, Spacer,
    Table, TableStyle, tabla_datos, titulo_seccion,
)
from informe_estilo import FECHA_CORTE  # noqa: E402
from reportlab.platypus import SimpleDocTemplate  # noqa: E402

SALIDA = (r'C:\Users\HP\OneDrive\Escritorio\FICHAS PDF POROTOG'
          r'\SHP - Capas de Investigacion\0 - COMO LEER ESTAS CAPAS.pdf')

# archivo, qué es, registros
CAPAS = [
    ('predios_investigados.shp', 'Predios con ficha de empadronamiento, con su '
     'condición de riego y el resumen de sus fichas', 5987),
    ('catastro_completo.shp', 'Catastro rural del cantón, como contexto territorial', 30978),
    ('fichas.shp', 'Una por ficha, ubicada en el punto GPS levantado en campo', 6830),
    ('comunas_oficiales.shp', 'Límites de comunas, según la capa oficial del GADM', 53),
    ('sectores.shp', 'Sectores de investigación', 3),
    ('canales_riego.shp', 'Red de conducción del sistema', 1),
    ('cultivos.dbf', 'Cultivos declarados (tabla, sin geometría)', 13617),
    ('animales.dbf', 'Especies pecuarias declaradas (tabla, sin geometría)', 9651),
]

RENOMBRES = [
    ('predios_investigados', 'propietarios', 'TITULARES',
     'Titulares con ficha en el predio'),
    ('predios_investigados', 'propietario_catastro', 'PROP_CATAS',
     'Propietario según el catastro municipal'),
    ('fichas', 'telefono_celular', 'TEL_CEL', 'Teléfono celular'),
    ('fichas', 'telefono_casa', 'TEL_CASA', 'Teléfono domiciliario'),
]


def main():
    os.makedirs(os.path.dirname(SALIDA), exist_ok=True)
    doc = SimpleDocTemplate(
        SALIDA, pagesize=A4, leftMargin=10 * mm, rightMargin=10 * mm,
        topMargin=27 * mm, bottomMargin=13 * mm,
        title='Capas de investigación en formato Shapefile',
        author='AP&CATASTROS — Padrón Guanguilquí–Porotog')

    st_h = ParagraphStyle('h', fontName='Helvetica-Bold', fontSize=12.5,
                          leading=15, textColor=AZUL, alignment=1)
    st_sub = ParagraphStyle('sub', fontName='Helvetica', fontSize=9.5,
                            leading=12, alignment=1,
                            textColor=colors.HexColor('#475569'))
    st_p = ParagraphStyle('p', fontName='Helvetica', fontSize=9,
                          leading=12.5, textColor=TINTA, alignment=4)
    st_li = ParagraphStyle('li', parent=st_p, leftIndent=8 * mm, spaceAfter=2)
    st_mono = ParagraphStyle('m', fontName='Courier-Bold', fontSize=8.5,
                             leading=11.5, textColor=AZUL)

    h = [Paragraph('Capas de investigación en formato Shapefile', st_h),
         Spacer(0, 1.5 * mm),
         Paragraph('Sistema de riego comunitario Guanguilquí–Porotog', st_sub),
         Spacer(0, 5 * mm),
         Paragraph('Estas capas acompañan a las fichas individuales del padrón: '
                   'llevan la misma información al mapa, listas para abrir en '
                   'QGIS o ArcGIS. Los datos corresponden al levantamiento de '
                   f'campo cerrado al {FECHA_CORTE}.', st_p)]

    h += titulo_seccion('Contenido')
    filas = [[a, q, fmt_num(n)] for a, q, n in CAPAS]
    h.append(tabla_datos(['Archivo', 'Qué contiene', 'Registros'], filas,
                         [46 * mm, 118 * mm, 26 * mm]))

    h += titulo_seccion('Sistema de referencia')
    h += [Paragraph('Todas las capas están en <b>WGS 84 / UTM zona 17S '
                    '(EPSG:32717)</b>, el sistema del catastro municipal: áreas '
                    'y distancias se calculan en metros sin configurar nada. '
                    'Los archivos <b>.cpg</b> declaran codificación UTF-8, así '
                    'que las tildes y la ñ se leen correctamente.', st_p)]

    h += titulo_seccion('Cómo se relacionan las capas')
    h += [Paragraph('<b>clave_cata</b> · la clave catastral enlaza '
                    'predios_investigados, catastro_completo y fichas.', st_li),
          Paragraph('<b>ficha_id</b> · enlaza cada ficha con sus cultivos y sus '
                    'animales (cultivos.dbf y animales.dbf).', st_li),
          Spacer(0, 2 * mm),
          Paragraph('Un predio puede tener varias fichas —el terreno familiar '
                    'declarado por varios titulares—, así que la relación entre '
                    'predios_investigados y fichas es de uno a varios.', st_p)]

    h += titulo_seccion('Nombres de campo')
    h += [Paragraph('El formato Shapefile limita los nombres de campo a 10 '
                    'caracteres, de modo que algunos aparecen abreviados: '
                    '<b>clave_catastral</b> se lee <b>clave_cata</b>, '
                    '<b>fichas_principales</b> se lee <b>fichas_pri</b>, y así. '
                    'Cuatro campos se renombraron a propósito, porque al '
                    'recortarlos quedaban iguales entre sí:', st_p),
          Spacer(0, 2.5 * mm)]
    filas_r = [[c, o, n, q] for c, o, n, q in RENOMBRES]
    h.append(tabla_datos(['Capa', 'Campo original', 'En el Shapefile', 'Qué es'],
                         filas_r, [46 * mm, 46 * mm, 32 * mm, 66 * mm]))

    h += titulo_seccion('Texto de observaciones')
    h += [Paragraph('El formato guarda hasta 254 caracteres por campo de texto. '
                    'En 48 de las 6.830 fichas el campo <b>observacio</b> supera '
                    'ese largo y aparece recortado; el texto completo consta en '
                    'la ficha individual en PDF de esta misma entrega.', st_p)]

    h += titulo_seccion('Equivalencia con las fichas en PDF')
    h += [Paragraph('Cada ficha de la carpeta de PDF corresponde a un registro '
                    'de <b>fichas.shp</b>. El campo <b>codigo_fic</b> trae el '
                    'código del padrón con el que se nombra cada documento, así '
                    'que del mapa se llega a la ficha y de la ficha al mapa. El '
                    'campo <b>codigo_pre</b> es otra cosa: el código del '
                    'formulario de campo, que se repite entre fichas.', st_p),
          Spacer(0, 2 * mm),
          Paragraph('codigo_fic = S01-C22-R001-F01<br/>'
                    'FICHAS PDF POROTOG \\ Sector 1 \\ MATIAS IMBAGO \\<br/>'
                    'S01-C22-R001-F01 - 1702520440024 - '
                    'IMBAGO LANCHIMBA SEGUNDO MATIAS.pdf',
                    st_mono)]

    cab = {'creado_por': None, '_investigador': 'AP&CATASTROS'}
    doc.build(h, onFirstPage=lambda c, d: cabecera_pie(c, d, cab),
              onLaterPages=lambda c, d: cabecera_pie(c, d, cab))
    print(f'✔ {SALIDA}')


if __name__ == '__main__':
    main()
