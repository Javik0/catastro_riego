# -*- coding: utf-8 -*-
"""
Manual de uso del geovisor, para el consorcio.

Lo pide el Producto 5 del contrato: «anexar […] el manual de guía para su
manejo». Está escrito para el perfil de CONSULTA (rol cliente), que es el que
usa el consorcio: tres módulos —Tablero, Mapa y Fichas— y la descarga de la
cartografía. Los módulos de captura y auditoría no se documentan aquí porque
ese perfil no los ve (Sidebar.tsx: «El cliente (Consorcio) solo consulta:
Dashboard, Mapa y Fichas»). Decisión de JAVIKO, 14-sep-2026.

Todo lo que se describe se verificó entrando a la plataforma con ese perfil.

Uso:
    python -X utf8 scripts/generar_manual_geovisor.py
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from generar_fichas_pdf import (  # noqa: E402
    A4, AZUL, TINTA, cabecera_pie, colors, fmt_num, mm, Paragraph,
    ParagraphStyle, Spacer, tabla_datos, titulo_seccion,
)
from informe_estilo import FECHA_CORTE  # noqa: E402
from reportlab.platypus import SimpleDocTemplate  # noqa: E402

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
GEO = os.path.join(BASE, 'public', 'geo')
ENTREGA = r'C:\Users\HP\OneDrive\Escritorio\FICHAS PDF POROTOG'
SALIDA = os.path.join(ENTREGA, '0 - MANUAL DE USO DEL GEOVISOR.pdf')
URL = 'https://invs-riego-comunitario.web.app'


def main():
    with open(os.path.join(GEO, 'stats.json'), encoding='utf-8') as f:
        s = json.load(f)
    total = s['fichas'] + s['fichas_hijas']

    doc = SimpleDocTemplate(
        SALIDA, pagesize=A4, leftMargin=10 * mm, rightMargin=10 * mm,
        topMargin=27 * mm, bottomMargin=13 * mm,
        title='Manual de uso del geovisor',
        author='AP&CATASTROS — Padrón Guanguilquí–Porotog')

    st_h = ParagraphStyle('h', fontName='Helvetica-Bold', fontSize=12.5,
                          leading=15, textColor=AZUL, alignment=1)
    st_sub = ParagraphStyle('sub', fontName='Helvetica', fontSize=9.5, leading=12,
                            alignment=1, textColor=colors.HexColor('#475569'))
    st_p = ParagraphStyle('p', fontName='Helvetica', fontSize=9, leading=12.5,
                          textColor=TINTA, alignment=4)
    st_li = ParagraphStyle('li', parent=st_p, leftIndent=8 * mm, spaceAfter=2)
    st_paso = ParagraphStyle('paso', parent=st_p, leftIndent=8 * mm,
                             spaceAfter=3, alignment=0)
    st_url = ParagraphStyle('url', fontName='Courier-Bold', fontSize=11,
                            leading=14, textColor=AZUL, alignment=1)

    def paso(n, txt):
        return Paragraph('<b>{}.</b>  {}'.format(n, txt), st_paso)

    h = [Paragraph('Manual de uso del geovisor', st_h), Spacer(0, 1.5 * mm),
         Paragraph('Catastro socioeconómico y productivo predial · Sistema de riego '
                   'comunitario Guanguilquí–Porotog', st_sub), Spacer(0, 5 * mm),
         Paragraph('Esta guía explica cómo consultar el catastro en la plataforma web. '
                   'Está escrita para el perfil de consulta, que es el del consorcio: '
                   'permite ver todo el padrón, abrir la ficha de cualquier titular, '
                   'imprimirla y descargar la cartografía completa.', st_p)]

    # ── entrar ──
    h += titulo_seccion('Cómo entrar')
    h += [Paragraph('La plataforma se abre en cualquier navegador, sin instalar nada:', st_p),
          Spacer(0, 2.5 * mm), Paragraph(URL, st_url), Spacer(0, 3 * mm),
          paso(1, 'Escriba la dirección en el navegador.'),
          paso(2, 'Ingrese con el usuario y la contraseña que se le entregaron.'),
          paso(3, 'Se abre el <b>Tablero</b>. A la izquierda está el menú con los tres '
                  'módulos: <b>Tablero</b>, <b>Mapa</b> y <b>Fichas</b>.'),
          Spacer(0, 2 * mm),
          Paragraph('El botón <b>Claro / Oscuro</b>, arriba a la derecha, cambia el tema '
                    'de la pantalla; el de <b>Salir</b>, cierra la sesión. Si el menú de '
                    'la izquierda está plegado, se despliega con la flecha de su borde.', st_p)]

    # ── filtros ──
    h += titulo_seccion('Los filtros: valen para toda la plataforma')
    h += [Paragraph('En la barra superior hay filtros por <b>parroquia</b>, <b>sector de '
                    'investigación</b>, <b>sector de riego</b>, <b>comunidad</b>, '
                    '<b>técnico</b> y <b>rango de fechas</b>, más un buscador por '
                    'propietario o cédula.', st_p),
          Spacer(0, 2 * mm),
          Paragraph('Lo que elija se aplica a los tres módulos a la vez: si filtra una '
                    'comunidad, el tablero recalcula sus indicadores, el mapa muestra solo '
                    'esos predios y el listado de fichas se reduce a ellos. Para volver a '
                    'ver todo, pulse <b>Limpiar</b>.', st_p)]

    # ── tablero ──
    h += titulo_seccion('Tablero: las cifras del padrón')
    h += [Paragraph('Es la pantalla de entrada. Muestra, en tarjetas, el tamaño del '
                    'padrón y sus indicadores principales:', st_p),
          Paragraph('<b>Fichas principales</b> · una por titular entrevistado.', st_li),
          Paragraph('<b>Fichas adicionales</b> · los demás predios de ese mismo titular.', st_li),
          Paragraph('<b>Fichas totales</b> · la suma de las dos.', st_li),
          Paragraph('<b>Predios investigados</b> · cuántos predios del catastro rural '
                    'tienen al menos una ficha.', st_li),
          Paragraph('<b>Superficie del sistema</b> · la medición catastral, en hectáreas.', st_li),
          Spacer(0, 2 * mm),
          Paragraph('Más abajo están los indicadores de riego, uso del suelo, producción '
                    'agrícola y pecuaria, servicios básicos y perfil de los titulares. Al '
                    'aplicar un filtro, todas las cifras se recalculan sobre lo filtrado.', st_p)]

    # ── mapa ──
    h += titulo_seccion('Mapa: el catastro sobre imagen satelital')
    h += [paso(1, 'Pulse <b>Mapa</b> en el menú de la izquierda.'),
          paso(2, 'Se abre el catastro sobre imagen satelital. Cada predio investigado '
                  'está pintado según su condición: <b>naranja</b>, predio con ficha '
                  'principal; <b>azul</b>, predio adicional investigado; <b>celeste</b>, '
                  'predio adicional pendiente.'),
          paso(3, 'Arriba a la izquierda hay dos vistas: <b>Investigación</b>, que es la '
                  'anterior, y <b>Riego</b>, que pinta cada predio por su condición de '
                  'riego (con riego, sin riego, mixto o sin dato). En los predios mixtos '
                  'el polígono se divide en dos colores según la parte que se riega.'),
          paso(4, 'El ícono de <b>capas</b>, arriba a la derecha, permite encender y '
                  'apagar los canales de riego, los límites comunales oficiales y el '
                  'catastro rural completo.'),
          paso(5, '<b>Pulse cualquier predio</b> para ver quién lo declaró, su clave '
                  'catastral, su superficie y sus fichas. Desde ahí se abre la ficha '
                  'completa.'),
          Spacer(0, 2 * mm),
          Paragraph('La lupa busca un predio por su clave catastral. Los controles + y − '
                    'acercan y alejan; también funciona la rueda del ratón.', st_p)]

    # ── fichas ──
    h += titulo_seccion('Fichas: buscar y leer una ficha')
    h += [paso(1, 'Pulse <b>Fichas</b> en el menú. Se abre el listado del padrón, con '
                  f'las {fmt_num(total)} fichas.'),
          paso(2, 'Use el buscador para encontrar a alguien por <b>nombre</b>, '
                  '<b>cédula</b>, <b>clave catastral</b> o <b>código de la ficha</b>.'),
          paso(3, 'Pulse el ícono del <b>ojo</b>, al final de la fila, para abrir la '
                  'ficha. El ícono del <b>punto</b> la ubica en el mapa.'),
          paso(4, 'La ficha se abre por secciones: propietario, predio y riego, '
                  'servicios, producción, otros predios, encuesta y auditoría.'),
          paso(5, 'El botón <b>Imprimir</b> genera la ficha en formato A4, con sus mapas '
                  'de ubicación, lista para imprimir o guardar en PDF.'),
          Spacer(0, 2 * mm),
          Paragraph('Las columnas del listado se ordenan pulsando su encabezado, y el '
                    'selector de la derecha permite ver todas las fichas o solo las '
                    'principales.', st_p)]

    # ── el codigo ──
    h += titulo_seccion('El código de cada ficha')
    h += [Paragraph('Cada ficha tiene un código único, por ejemplo <b>S01-C22-R001-F01</b>, '
                    'que se lee así:', st_p), Spacer(0, 2 * mm)]
    cod = [['S01', 'Sector de investigación (01 a 03)'],
           ['C22', 'Comunidad, según el listado oficial de las 50 del sistema'],
           ['R001', 'Titular dentro de su comunidad, en orden alfabético de apellidos'],
           ['F01', 'Ficha de ese titular: F01 es la principal y las siguientes, sus '
                   'predios adicionales']]
    h.append(tabla_datos(['Parte', 'Qué significa'], cod, [28 * mm, 162 * mm]))
    h += [Paragraph('Es el mismo código en los tres lados de la entrega: el que muestra '
                    'la plataforma, el que nombra la ficha individual en PDF y el que '
                    'viaja en la capa de fichas del paquete cartográfico. Con él se pasa '
                    'del mapa al documento y del documento al mapa.', st_p)]

    # ── descarga ──
    h += titulo_seccion('Descargar la cartografía')
    h += [paso(1, 'Entre al <b>Mapa</b>.'),
          paso(2, 'Pulse el botón <b>QGIS</b>, arriba a la derecha.'),
          paso(3, 'Se descarga un archivo comprimido con el GeoPackage de todas las '
                  'capas, un proyecto de QGIS y un archivo LÉEME.'),
          paso(4, 'Descomprima y abra el archivo <b>.qgz</b> con QGIS 3.28 o superior. '
                  'Las capas se cargan con su simbología y no hay que configurar nada.'),
          Spacer(0, 2 * mm),
          Paragraph('En ese proyecto, al pulsar un predio se despliegan sus fichas, sus '
                    'cultivos y sus animales: la relación entre el predio y sus fichas ya '
                    'viene configurada. La entrega incluye además las mismas capas en '
                    'Shapefile y en CAD, y el diccionario de datos con el detalle de cada '
                    'campo.', st_p)]

    # ── dudas frecuentes ──
    h += titulo_seccion('Para leer bien las cifras')
    h += [Paragraph('<b>Un predio puede tener varias fichas.</b> En los terrenos '
                    'familiares cada heredero declara su parte, así que el número de '
                    'fichas es mayor que el de predios. Por eso el padrón se cuenta en '
                    'fichas, y los predios, en polígonos del catastro.', st_li),
          Paragraph('<b>Hay dos mediciones de superficie.</b> La catastral mide el '
                    'polígono del municipio y cada predio cuenta una vez; la declarada es '
                    'la que informó cada titular. No se suman entre sí: cada bloque de la '
                    'pantalla dice cuál está usando.', st_li),
          Paragraph('<b>El caudal es por comunidad.</b> El valor que aparece en una ficha '
                    'es el de su comunidad, no el de esa parcela: no debe sumarse ficha a '
                    'ficha.', st_li),
          Spacer(0, 2 * mm),
          Paragraph(f'Toda la información corresponde al levantamiento de campo cerrado '
                    f'al {FECHA_CORTE}.', st_p)]

    cab = {'creado_por': None, '_investigador': 'AP&CATASTROS'}
    doc.build(h, onFirstPage=lambda c, d: cabecera_pie(c, d, cab),
              onLaterPages=lambda c, d: cabecera_pie(c, d, cab))
    print('✔ {}'.format(SALIDA))
    return 0


if __name__ == '__main__':
    sys.exit(main())
