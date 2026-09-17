# -*- coding: utf-8 -*-
"""
Arma la carpeta de entrega del Producto 5 del contrato.

El contrato pide siete cosas en una sola celda de una tabla. Quien recibe la
carpeta la tiene que poder cotejar con esa celda SIN saber que es un shapefile
ni un geopackage, asi que las carpetas se numeran en el mismo orden en que el
contrato enumera los productos y se nombran con lo que contienen, no con el
formato. La guia (documento 0) hace la correspondencia linea por linea.

Genera tres documentos nuevos y copia el resto de lo ya producido:
  0 - LEA ESTO PRIMERO       la correspondencia con el contrato
  3 - LINK DE LA PLATAFORMA  la direccion y como se entra
  6 - AVANCE Y FECHA         el porcentaje de avance y la fecha de corte

Uso:  python -X utf8 scripts/armar_producto5.py
"""
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import membrete_prefectura  # noqa: E402

from generar_fichas_pdf import (  # noqa: E402
    A4, AZUL, TINTA, cabecera_pie, colors, mm, Paragraph,
    ParagraphStyle, Spacer, tabla_datos, titulo_seccion,
)
from reportlab.platypus import SimpleDocTemplate  # noqa: E402

ESCRITORIO = r'C:\Users\HP\OneDrive\Escritorio'
ORIGEN = os.path.join(ESCRITORIO, 'FICHAS PDF POROTOG')
DESTINO = os.path.join(ESCRITORIO, 'PRODUCTO 5 - ENTREGA 18-SEP-2026')

URL = 'https://invs-riego-comunitario.web.app'

# Las dos fechas son distintas y el documento lo dice: la informacion dejo de
# moverse el 19 de agosto —es la que llevan impresa las 6.830 fichas ya
# entregadas— y el informe se emite el 15 de septiembre. Mezclarlas obligaria a
# rehacer todo lo entregado para que las fechas coincidieran.
CORTE = '19 de agosto de 2026'
EMISION = '15 de septiembre de 2026'

CARPETAS = [
    '1 - BASE DE DATOS GEOESPACIAL DE LOS PREDIOS',
    os.path.join('1 - BASE DE DATOS GEOESPACIAL DE LOS PREDIOS', '1.1 - FORMATO SHP'),
    os.path.join('1 - BASE DE DATOS GEOESPACIAL DE LOS PREDIOS', '1.2 - FORMATO CAD'),
    os.path.join('1 - BASE DE DATOS GEOESPACIAL DE LOS PREDIOS', '1.3 - PROYECTO QGIS'),
    '2 - DICCIONARIO DE DATOS',
    '3 - LINK DE LA PLATAFORMA',
    '4 - MEMORIA TECNICA DEL GEOVISOR',
    '5 - MANUAL DE USO DEL GEOVISOR',
    '6 - PORCENTAJE DE AVANCE Y FECHA DE CORTE',
]


def _doc(ruta, titulo):
    return SimpleDocTemplate(
        ruta, pagesize=A4, title=titulo,
        author='AP&CATASTROS — Padrón Guanguilquí–Porotog',
        **membrete_prefectura.margenes(dict(
            leftMargin=10 * mm, rightMargin=10 * mm,
            topMargin=27 * mm, bottomMargin=13 * mm)))


def _estilos():
    return {
        'h': ParagraphStyle('h', fontName='Helvetica-Bold', fontSize=12.5,
                            leading=15, textColor=AZUL, alignment=1),
        'sub': ParagraphStyle('sub', fontName='Helvetica', fontSize=9.5,
                              leading=12, alignment=1,
                              textColor=colors.HexColor('#475569')),
        'p': ParagraphStyle('p', fontName='Helvetica', fontSize=9, leading=12.5,
                            textColor=TINTA, alignment=4),
        'li': ParagraphStyle('li', fontName='Helvetica', fontSize=9, leading=12.5,
                             textColor=TINTA, alignment=4, leftIndent=8 * mm,
                             spaceAfter=2),
        'url': ParagraphStyle('url', fontName='Courier-Bold', fontSize=12,
                              leading=15, textColor=AZUL, alignment=1),
    }


def _cerrar(doc, historia):
    cab = {'creado_por': None, '_investigador': 'AP&CATASTROS'}
    doc.build(historia, onFirstPage=lambda c, d: cabecera_pie(c, d, cab),
              onLaterPages=lambda c, d: cabecera_pie(c, d, cab))


# ─────────────────────────────────────────────────────────────────────────────
# 0 — La guía: qué carpeta responde a qué línea del contrato
# ─────────────────────────────────────────────────────────────────────────────
def guia():
    ruta = os.path.join(DESTINO, '0 - LEA ESTO PRIMERO - GUIA DE LA ENTREGA.pdf')
    st = _estilos()
    h = [Paragraph('Guía de esta entrega', st['h']), Spacer(0, 1.5 * mm),
         Paragraph('Producto 5 · Catastro socioeconómico y productivo predial · '
                   'Sistema de riego comunitario Guanguilquí–Porotog', st['sub']),
         Spacer(0, 5 * mm),
         Paragraph('Esta carpeta responde, una por una, a las siete cosas que pide '
                   'el Producto 5 del contrato. <b>Las carpetas están numeradas en el '
                   'mismo orden en que el contrato las enumera</b>, así que se pueden '
                   'cotejar de corrido contra la tabla de entregables.', st['p'])]

    h += titulo_seccion('Qué pide el contrato y dónde está')
    filas = [
        ['Base de datos geoespacial de todos los predios del área de influencia, '
         'en formato SHP, mpk, CAD',
         '1 — Base de datos geoespacial de los predios\n'
         '(1.1 SHP · 1.2 CAD · 1.3 Proyecto QGIS)'],
        ['Cada polígono deberá contener en su tabla de atributos la información '
         'levantada mediante la ficha, con identificador único para vincularla con '
         'la base alfanumérica',
         '1.1 — La capa «fichas» lleva el código\nS00-C00-R000-F00 en el campo '
         'CODIGO_FIC'],
        ['Adjuntar el diccionario de datos que describa la estructura, campos, '
         'dominios y contenido de la información',
         '2 — Diccionario de datos\n(en PDF y en Excel)'],
        ['Compartir el link de la plataforma donde se gestiona la información',
         '3 — Link de la plataforma'],
        ['Anexar memoria técnica de diseño del geovisor',
         '4 — Memoria técnica del geovisor'],
        ['Y el manual de guía para su manejo',
         '5 — Manual de uso del geovisor'],
        ['Especificar el porcentaje de avance del universo total de predios y la '
         'fecha de corte de la información',
         '6 — Porcentaje de avance y fecha de corte'],
    ]
    h.append(tabla_datos(['Lo que dice el contrato', 'Carpeta de esta entrega'],
                         filas, [110 * mm, 80 * mm]))

    h += titulo_seccion('Qué es cada formato, en palabras simples')
    h += [Paragraph('<b>SHP (carpeta 1.1).</b> Es el formato de mapas más difundido '
                    'del mundo: lo abre cualquier programa de información geográfica. '
                    'Cada capa no es un archivo sino un grupo de archivos con el mismo '
                    'nombre y distinta extensión (.shp, .dbf, .prj, .shx): '
                    '<b>se copian todos juntos o la capa no abre</b>.', st['li']),
          Paragraph('<b>CAD (carpeta 1.2).</b> Los mismos predios en formato de dibujo '
                    'técnico (.dxf), para quien trabaje en AutoCAD o Civil 3D.', st['li']),
          Paragraph('<b>Proyecto QGIS (carpeta 1.3).</b> Un solo archivo con todas las '
                    'capas dentro (.gpkg) más el proyecto que las abre ya pintadas '
                    '(.qgz): se hace doble clic y está todo listo, sin configurar nada.',
                    st['li']),
          Spacer(0, 2 * mm),
          Paragraph('<b>Sobre el formato mpk.</b> El contrato lo menciona junto al SHP '
                    'y al CAD. El «mpk» es un paquete de mapas propio del programa '
                    'ArcGIS, de licencia comercial. Este estudio se desarrolló '
                    'íntegramente en software libre, y lo que el mpk resuelve —llevar '
                    'en una sola pieza las capas junto con su simbología, listas para '
                    'abrir— se entrega resuelto en la carpeta 1.3, con el GeoPackage y '
                    'el proyecto QGIS. La información va además en SHP y en CAD, que '
                    'son formatos abiertos: <b>cualquier programa del mercado, ArcGIS '
                    'incluido, puede leerla</b>.', st['p'])]

    h += titulo_seccion('Cómo se abre cada cosa')
    h += [Paragraph('<b>Los documentos en PDF</b> (carpetas 2, 4, 5 y 6) se abren con '
                    'cualquier lector de PDF.', st['li']),
          Paragraph('<b>El diccionario en Excel</b> (carpeta 2) se abre con Excel y '
                    'permite buscar un campo concreto.', st['li']),
          Paragraph('<b>Los mapas</b> (carpeta 1) necesitan un programa de información '
                    'geográfica. El más directo es QGIS, que es gratuito: se descarga '
                    'de qgis.org, se instala, y se abre el archivo .qgz de la carpeta '
                    '1.3. El manual de la carpeta 5 lo explica paso a paso.', st['li']),
          Paragraph('<b>La plataforma</b> (carpeta 3) se abre en cualquier navegador, '
                    'sin instalar nada.', st['li'])]

    h += titulo_seccion('Una advertencia al copiar')
    h += [Paragraph('Al pasar esta carpeta a otro disco o a una memoria, <b>cópiela '
                    'completa y sin renombrar nada</b>. Las capas de la carpeta 1.1 '
                    'dejan de funcionar si se separa un archivo de sus compañeros, y '
                    'el proyecto de la carpeta 1.3 busca su base de datos en la misma '
                    'carpeta donde está.', st['p'])]

    _cerrar(_doc(ruta, 'Guía de esta entrega — Producto 5'), h)
    return ruta


# ─────────────────────────────────────────────────────────────────────────────
# 3 — El link de la plataforma
# ─────────────────────────────────────────────────────────────────────────────
def link():
    ruta = os.path.join(DESTINO, '3 - LINK DE LA PLATAFORMA',
                        'LINK DE LA PLATAFORMA.pdf')
    st = _estilos()
    h = [Paragraph('Link de la plataforma', st['h']), Spacer(0, 1.5 * mm),
         Paragraph('Producto 5 · Catastro socioeconómico y productivo predial', st['sub']),
         Spacer(0, 6 * mm),
         Paragraph('La información del catastro socioeconómico y productivo predial se '
                   'gestiona y se consulta en línea, en esta dirección:', st['p']),
         Spacer(0, 4 * mm), Paragraph(URL, st['url']), Spacer(0, 5 * mm)]

    h += titulo_seccion('Cómo se entra')
    h += [Paragraph('1. Escriba la dirección en cualquier navegador. No hay que '
                    'instalar nada.', st['li']),
          Paragraph('2. Ingrese con el usuario y la contraseña entregados al '
                    'consorcio.', st['li']),
          Paragraph('3. Se abre el tablero. A la izquierda están los tres módulos: '
                    '<b>Tablero</b>, <b>Mapa</b> y <b>Fichas</b>.', st['li']),
          Spacer(0, 3 * mm),
          Paragraph('El <b>manual de uso</b> de la carpeta 5 explica cada pantalla con '
                    'capturas y señala dónde pulsar.', st['p'])]

    h += titulo_seccion('Qué se puede hacer desde ahí')
    h += [Paragraph('Consultar el padrón completo y abrir la ficha de cualquier '
                    'titular, con sus siete secciones.', st['li']),
          Paragraph('Imprimir cualquier ficha en A4, idéntica a las que se entregaron '
                    'en PDF.', st['li']),
          Paragraph('Ver el catastro sobre imagen satelital, por estado de '
                    'investigación o por condición de riego.', st['li']),
          Paragraph('Descargar toda la cartografía en un solo archivo, con el proyecto '
                    'de QGIS listo para abrir.', st['li'])]

    _cerrar(_doc(ruta, 'Link de la plataforma'), h)
    return ruta


# ─────────────────────────────────────────────────────────────────────────────
# 6 — El porcentaje de avance y la fecha de corte
# ─────────────────────────────────────────────────────────────────────────────
def avance():
    ruta = os.path.join(DESTINO, '6 - PORCENTAJE DE AVANCE Y FECHA DE CORTE',
                        'PORCENTAJE DE AVANCE Y FECHA DE CORTE.pdf')
    st = _estilos()
    h = [Paragraph('Porcentaje de avance y fecha de corte', st['h']), Spacer(0, 1.5 * mm),
         Paragraph('Producto 5 · Catastro socioeconómico y productivo predial · '
                   'Sistema de riego comunitario Guanguilquí–Porotog', st['sub']),
         Spacer(0, 5 * mm)]

    h += titulo_seccion('Fecha de corte de la información')
    h += [Paragraph(f'La información de este producto corresponde al <b>{CORTE}</b>, '
                    'fecha en que se cerró el levantamiento de campo. Esa es la fecha '
                    'que llevan impresa las 6.830 fichas entregadas, la base '
                    'cartográfica y la plataforma en línea: después de ella el padrón '
                    'no incorporó fichas nuevas.', st['p']),
          Spacer(0, 2 * mm),
          Paragraph(f'El presente informe se emite el <b>{EMISION}</b>. Las dos fechas '
                    'se declaran por separado a propósito: una dice hasta cuándo se '
                    'levantó el dato y la otra cuándo se reporta, y confundirlas haría '
                    'parecer que el padrón siguió creciendo después del cierre.', st['p'])]

    h += titulo_seccion('Lo levantado')
    filas = [
        ['Fichas principales', '4.307', 'Una por titular entrevistado'],
        ['Fichas adicionales', '2.523', 'Los demás predios de ese mismo titular'],
        ['Fichas totales', '6.830', 'El padrón completo'],
        ['Predios investigados', '5.987', 'Predios del catastro rural con al menos una ficha'],
        ['Superficie catastrada', '8.093,34 ha', 'Medición catastral, cada predio una vez'],
        ['Comunidades cubiertas', '50', 'Las 50 del sistema, en sus 3 sectores'],
    ]
    h.append(tabla_datos(['Concepto', 'Cantidad', 'Qué es'], filas,
                         [45 * mm, 30 * mm, 115 * mm]))

    h += titulo_seccion('Avance sobre el universo')
    h += [Paragraph('El avance se midió contra dos universos independientes, y ambos '
                    'arrojan el mismo resultado:', st['p']), Spacer(0, 2 * mm)]
    filas2 = [
        ['Listados de las 50 comunidades', '3.681 comuneros registrados',
         'Se levantaron 4.307 fichas principales, más titulares que comuneros '
         'registrados en los listados'],
        ['Área de influencia del TDR', '2.370 ha · 4.261 usuarios estimados',
         'Se registraron 4.307 titulares, un 1 % por encima de lo estimado, y la '
         'superficie catastrada supera el área de influencia'],
    ]
    h.append(tabla_datos(['Universo de referencia', 'Tamaño', 'Resultado del levantamiento'],
                         filas2, [48 * mm, 45 * mm, 97 * mm]))

    h += [Paragraph('<b>El levantamiento del catastro socioeconómico y productivo '
                    'predial está concluido: se completa el 100 % de las propiedades '
                    'declaradas por los comuneros regantes.</b>', st['p']),
          Spacer(0, 2 * mm),
          Paragraph('No es posible un comparativo exacto contra el número de '
                    'propiedades, por cuanto no se dispone del dato original de cuántas '
                    'propiedades poseen en total los comuneros registrados en los '
                    'listados. El universo catastrado es, en consecuencia, el que los '
                    'propios comuneros declararon al llenar las fichas: 6.830 predios '
                    'declarados por 4.307 titulares.', st['p']),
          Spacer(0, 2 * mm),
          Paragraph('La superficie catastrada supera el área de influencia definida en '
                    'los términos de referencia porque el padrón cubre los dos sistemas '
                    'de riego completos, y no únicamente la franja regable con el '
                    'embalse.', st['p'])]

    h += titulo_seccion('Para leer bien estas cifras')
    h += [Paragraph('<b>Un predio puede tener varias fichas.</b> En los terrenos '
                    'familiares cada heredero declara su parte, de modo que el número '
                    'de fichas es mayor que el de predios. Por eso el padrón se cuenta '
                    'en fichas.', st['li']),
          Paragraph('<b>Las fichas adicionales no son personas nuevas.</b> Son otros '
                    'lotes del mismo titular: no se suman a las principales para contar '
                    'usuarios.', st['li']),
          Paragraph('<b>Hay dos mediciones de superficie.</b> La catastral mide el '
                    'polígono municipal y cuenta cada predio una vez; la declarada es '
                    'la que informó cada titular. No se suman entre sí.', st['li'])]

    _cerrar(_doc(ruta, 'Porcentaje de avance y fecha de corte'), h)
    return ruta


# ─────────────────────────────────────────────────────────────────────────────
def armar():
    if os.path.exists(DESTINO):
        shutil.rmtree(DESTINO)
    for c in CARPETAS:
        os.makedirs(os.path.join(DESTINO, c), exist_ok=True)

    copias = [
        (os.path.join(ORIGEN, 'SHP - Capas de Investigacion'),
         os.path.join(DESTINO, CARPETAS[1]), 'carpeta'),
        (os.path.join(ORIGEN, 'CAD - DXF'),
         os.path.join(DESTINO, CARPETAS[2]), 'carpeta'),
        (os.path.join(ORIGEN, 'GPKG - Proyecto QGIS'),
         os.path.join(DESTINO, CARPETAS[3]), 'carpeta'),
        (os.path.join(ORIGEN, '0 - DICCIONARIO DE DATOS.pdf'),
         os.path.join(DESTINO, CARPETAS[4], 'DICCIONARIO DE DATOS.pdf'), 'archivo'),
        (os.path.join(ORIGEN, 'DICCIONARIO DE DATOS.xlsx'),
         os.path.join(DESTINO, CARPETAS[4], 'DICCIONARIO DE DATOS.xlsx'), 'archivo'),
        (os.path.join(ORIGEN, '0 - MEMORIA TECNICA DEL GEOVISOR.pdf'),
         os.path.join(DESTINO, CARPETAS[6], 'MEMORIA TECNICA DEL GEOVISOR.pdf'), 'archivo'),
        (os.path.join(ORIGEN, '0 - MANUAL DE USO DEL GEOVISOR.pdf'),
         os.path.join(DESTINO, CARPETAS[7], 'MANUAL DE USO DEL GEOVISOR.pdf'), 'archivo'),
    ]
    for origen, destino, clase in copias:
        if not os.path.exists(origen):
            print('  ! falta el origen:', origen)
            continue
        if clase == 'carpeta':
            for nombre in os.listdir(origen):
                shutil.copy2(os.path.join(origen, nombre),
                             os.path.join(destino, nombre))
            print(f'  copiada  {os.path.basename(origen)}')
        else:
            shutil.copy2(origen, destino)
            print(f'  copiado  {os.path.basename(destino)}')

    for hacer in (guia, link, avance):
        print('  generado', os.path.basename(hacer()))

    total = sum(os.path.getsize(os.path.join(r, f))
                for r, _, fs in os.walk(DESTINO) for f in fs)
    print(f'\n{DESTINO}\n{total / 1048576:.1f} MB')
    return 0


if __name__ == '__main__':
    sys.exit(armar())
