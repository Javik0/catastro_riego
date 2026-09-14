# -*- coding: utf-8 -*-
"""
Memoria técnica de diseño del geovisor del catastro.

La pide el Producto 5 del contrato: «compartir el link de la plataforma […] y
anexar memoria técnica de diseño del geovisor […]. Especificar el porcentaje de
avance del universo total de predios y la fecha de corte de la información».

El porcentaje de avance se declara contra el ÁREA DE INFLUENCIA QUE DEFINE EL
TDR (2.370 ha brutas, parroquia Cangahua, 2.800–3.600 msnm, con 4.261 usuarios
estimados), porque es el universo que el contrato manda catastrar. El catastro
rural completo del cantón se muestra como contexto, no como denominador: sobre
él el avance daría 24,5 %, una cifra que sugeriría un producto a un cuarto de
camino cuando en realidad el padrón levantado desborda el área exigida.
Decisión de JAVIKO, 14-sep-2026.

Las cifras del padrón NO se escriben a mano: se leen de
public/geo/universo_estudio.json y stats.json.

Uso:
    python -X utf8 scripts/generar_memoria_geovisor.py
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
SALIDA = os.path.join(ENTREGA, '0 - MEMORIA TECNICA DEL GEOVISOR.pdf')

URL = 'https://invs-riego-comunitario.web.app'

# Área de influencia según el TDR (informe de alcance del 24-ago-2026).
TDR_HA = 2370
TDR_REGABLE_HA = 1390
TDR_USUARIOS = 4261


def cargar(nombre):
    with open(os.path.join(GEO, nombre), encoding='utf-8') as f:
        return json.load(f)


def main():
    u = cargar('universo_estudio.json')
    s = cargar('stats.json')
    inv, uni = u['investigado'], u['universo']
    principales = s['fichas']
    adicionales = s['fichas_hijas']
    total_fichas = principales + adicionales

    doc = SimpleDocTemplate(
        SALIDA, pagesize=A4, leftMargin=10 * mm, rightMargin=10 * mm,
        topMargin=27 * mm, bottomMargin=13 * mm,
        title='Memoria técnica de diseño del geovisor',
        author='AP&CATASTROS — Padrón Guanguilquí–Porotog')

    st_h = ParagraphStyle('h', fontName='Helvetica-Bold', fontSize=12.5,
                          leading=15, textColor=AZUL, alignment=1)
    st_sub = ParagraphStyle('sub', fontName='Helvetica', fontSize=9.5, leading=12,
                            alignment=1, textColor=colors.HexColor('#475569'))
    st_p = ParagraphStyle('p', fontName='Helvetica', fontSize=9, leading=12.5,
                          textColor=TINTA, alignment=4)
    st_li = ParagraphStyle('li', parent=st_p, leftIndent=8 * mm, spaceAfter=2)
    st_url = ParagraphStyle('url', fontName='Courier-Bold', fontSize=11,
                            leading=14, textColor=AZUL, alignment=1)

    h = [Paragraph('Memoria técnica de diseño del geovisor', st_h), Spacer(0, 1.5 * mm),
         Paragraph('Catastro socioeconómico y productivo predial · Sistema de riego '
                   'comunitario Guanguilquí–Porotog', st_sub), Spacer(0, 5 * mm)]

    # ── la plataforma ──
    h += titulo_seccion('La plataforma')
    h += [Paragraph('El catastro socioeconómico y productivo predial se gestiona y se '
                    'consulta en una plataforma web propia, en línea y con acceso '
                    'controlado:', st_p),
          Spacer(0, 2.5 * mm), Paragraph(URL, st_url), Spacer(0, 3 * mm),
          Paragraph('La plataforma reúne, sobre la misma base de datos, el mapa '
                    'catastral, la ficha de cada titular, los tableros de indicadores y '
                    'la descarga de la información en formatos abiertos. No es un visor '
                    'de imágenes: cada predio del mapa está enlazado a las fichas '
                    'levantadas en campo, y de la ficha se llega al documento y al '
                    'revés.', st_p)]

    # ── avance y fecha de corte ──
    h += titulo_seccion('Avance del catastro y fecha de corte')
    h += [Paragraph(f'La información corresponde al levantamiento de campo cerrado al '
                    f'<b>{FECHA_CORTE}</b>. A esa fecha el catastro registra '
                    f'<b>{fmt_num(total_fichas)} fichas</b> '
                    f'({fmt_num(principales)} principales y {fmt_num(adicionales)} '
                    f'adicionales) sobre <b>{fmt_num(inv["predios"])} predios</b>, que '
                    f'suman <b>{fmt_num(inv["area_ha"], 2)} ha</b> catastrales.', st_p),
          Spacer(0, 2 * mm),
          Paragraph('El universo que el contrato manda catastrar es el <b>área de '
                    'influencia definida en el TDR</b>: '
                    f'{fmt_num(TDR_HA)} ha brutas en la parroquia Cangahua, entre 2.800 '
                    f'y 3.600 msnm, de las cuales {fmt_num(TDR_REGABLE_HA)} ha serían '
                    f'regables con el embalse, y para las que el propio TDR estima '
                    f'{fmt_num(TDR_USUARIOS)} usuarios. Medido contra ese universo, el '
                    'levantamiento está <b>concluido</b>: se registraron '
                    f'{fmt_num(principales)} titulares —un 1 % por encima de los '
                    f'{fmt_num(TDR_USUARIOS)} estimados— y la superficie catastrada '
                    'supera el área de influencia, porque el padrón cubre los dos '
                    'sistemas de riego completos y no solo la franja regable.', st_p)]
    filas = [
        ['Área de influencia del TDR', f'{fmt_num(TDR_HA)} ha',
         f'{fmt_num(TDR_USUARIOS)} usuarios estimados', 'Universo contractual'],
        ['Catastro levantado', f'{fmt_num(inv["area_ha"], 2)} ha',
         f'{fmt_num(principales)} titulares', 'Concluido'],
        ['Catastro rural del cantón', f'{fmt_num(uni["area_ha"], 2)} ha',
         f'{fmt_num(uni["predios"])} predios', 'Contexto territorial'],
    ]
    h += [Spacer(0, 2 * mm),
          tabla_datos(['Referencia', 'Superficie', 'Usuarios o predios', 'Alcance'],
                      filas, [56 * mm, 34 * mm, 50 * mm, 50 * mm]),
          Paragraph('El catastro rural del cantón se incluye como capa de contexto para '
                    'situar el sistema en su territorio. No es el universo del producto: '
                    'medir el avance contra él compararía el sistema de riego con todo '
                    'el cantón, que no es lo que el contrato define.', st_p)]

    # ── arquitectura ──
    h += titulo_seccion('Arquitectura')
    h += [Paragraph('<b>Captura en campo.</b> Los técnicos levantan la ficha en tabletas '
                    'con QField, sobre un proyecto QGIS con el formulario de las siete '
                    'secciones y la cartografía catastral precargada. El trabajo se '
                    'sincroniza contra QFieldCloud.', st_li),
          Paragraph('<b>Base de datos de campo.</b> La sincronización consolida un '
                    'GeoPackage único, que es la fuente de verdad del levantamiento.', st_li),
          Paragraph('<b>Publicación.</b> Un proceso de exportación lee ese GeoPackage, '
                    'canoniza los nombres de comunidad, resuelve el predio de cada ficha '
                    'por su clave catastral y publica las capas en GeoJSON, junto con los '
                    'agregados de superficie y caudal. Ese paso es el único camino por el '
                    'que el dato llega a la plataforma: la web nunca escribe en la base '
                    'de campo.', st_li),
          Paragraph('<b>Plataforma web.</b> Aplicación de página única servida como '
                    'contenido estático, con autenticación y control de acceso por rol. '
                    'Lee las capas publicadas y las presenta en el mapa, las fichas, los '
                    'tableros y los reportes.', st_li),
          Spacer(0, 2 * mm),
          Paragraph('La información viaja en una sola dirección —campo → base → '
                    'publicación → visor—, de modo que la consulta no puede alterar el '
                    'levantamiento.', st_p)]

    h += titulo_seccion('Componentes técnicos')
    comp = [
        ['Interfaz', 'React 19 con TypeScript, construida con Vite'],
        ['Cartografía', 'Leaflet, con imagen satelital Esri World Imagery como base'],
        ['Relieve 3D', 'Three.js, para la vista del emplazamiento de la obra'],
        ['Gráficos', 'Recharts, para los tableros de indicadores'],
        ['Exportación', 'jsPDF para los reportes en PDF; SheetJS para los de Excel'],
        ['Autenticación y alojamiento', 'Firebase (Authentication y Hosting)'],
        ['Datos', 'GeoJSON publicados desde el GeoPackage de campo'],
        ['Sistema de referencia', 'WGS 84 en el visor; UTM 17S (EPSG:32717) en la entrega'],
    ]
    h.append(tabla_datos(['Componente', 'Tecnología'], comp, [56 * mm, 134 * mm]))

    # ── pantallas ──
    h += titulo_seccion('Módulos de la plataforma')
    mod = [
        ['Tablero', 'Indicadores del padrón: composición, superficies, riego, producción '
                    'y servicios, con filtros por sector, comunidad, parroquia y técnico.'],
        ['Mapa', 'Predios investigados sobre imagen satelital, con la vista de condición '
                 'de riego, los límites comunales oficiales, los canales y el catastro '
                 'rural de contexto. Al pulsar un predio se abre su ficha.'],
        ['Fichas', 'Listado del padrón con buscador y filtros. Cada ficha se abre en su '
                   'detalle por secciones y se imprime en formato A4.'],
        ['Represa', 'Emplazamiento de la obra propuesta, con el relieve en 3D y las '
                    'capas del proyecto.'],
        ['Reportes', 'Generación de reportes en PDF y Excel por sector, comunidad, '
                     'parroquia, técnico o rango de fechas.'],
        ['Encuestas', 'Módulo de captura y revisión de la encuesta comunitaria.'],
        ['Auditoría', 'Control de las fichas adicionales y de las áreas declaradas '
                      'frente al polígono catastral.'],
    ]
    h.append(tabla_datos(['Módulo', 'Qué permite'], mod, [34 * mm, 156 * mm]))

    # ── identificación ──
    h += titulo_seccion('Identificación de cada ficha')
    h += [Paragraph('Cada ficha tiene un código único con la forma '
                    '<b>S01-C22-R001-F01</b>: sector de investigación, comunidad según el '
                    'listado oficial, titular dentro de su comunidad y ficha de ese '
                    'titular. Es el mismo código en los tres lados de la entrega: lo '
                    'muestra la plataforma, nombra la ficha individual en PDF y viaja en '
                    'el campo <b>codigo_fic</b> de la capa de fichas. Con él se va del '
                    'mapa al documento y del documento al mapa.', st_p),
          Spacer(0, 2 * mm),
          Paragraph('Un predio puede tener varias fichas, porque el terreno familiar lo '
                    'declara más de un titular. Por eso el vínculo entre el polígono y la '
                    'ficha es de uno a varios, y así está resuelto en el proyecto de QGIS '
                    'que acompaña a la entrega: al pulsar un predio se despliegan sus '
                    'fichas, sus cultivos y sus animales.', st_p)]

    # ── acceso ──
    h += titulo_seccion('Acceso y perfiles')
    h += [Paragraph('El acceso es con credencial nominal. Hay tres perfiles: '
                    '<b>administrador</b>, con acceso completo; <b>técnico</b>, para el '
                    'equipo de levantamiento y revisión; y <b>cliente</b>, para la '
                    'consulta institucional. Los módulos y los indicadores que cada '
                    'perfil ve se ajustan a su rol.', st_p)]

    # ── descarga ──
    h += titulo_seccion('Descarga de la información')
    h += [Paragraph('Desde el propio mapa se descarga el paquete cartográfico completo: '
                    'un GeoPackage con todas las capas y un proyecto de QGIS que las abre '
                    'ya simbolizadas, sin configurar nada. La entrega añade las mismas '
                    'capas en Shapefile y en CAD, y el diccionario de datos que describe '
                    'cada campo y sus dominios. Todos los formatos son abiertos y se '
                    'trabajan con software libre.', st_p)]

    cab = {'creado_por': None, '_investigador': 'AP&CATASTROS'}
    doc.build(h, onFirstPage=lambda c, d: cabecera_pie(c, d, cab),
              onLaterPages=lambda c, d: cabecera_pie(c, d, cab))
    print('✔ {}'.format(SALIDA))
    print('   avance declarado contra el área de influencia del TDR '
          '({} ha, {} usuarios estimados)'.format(fmt_num(TDR_HA), fmt_num(TDR_USUARIOS)))
    print('   padrón: {} fichas · {} predios · {} ha'.format(
        fmt_num(total_fichas), fmt_num(inv['predios']), fmt_num(inv['area_ha'], 2)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
