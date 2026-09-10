# -*- coding: utf-8 -*-
"""
Informe consolidado: reúne los seis capítulos en un solo documento entregable.

Toma los HTML que ya generan los scripts de cada capítulo, les quita cabecera y
pie individuales, renumera sus secciones (1.1, 2.3…) y los monta bajo una
portada única con índice, una sección de alcance y método y un resumen
ejecutivo. Los gráficos vienen DENTRO de cada capítulo (PNG en base64 a 200
ppp, dibujados por `informe_graficos.py`), así que el consolidado los hereda
sin tocarlos.

ACENTO (aprobado por JAVIKO, 4-sep-2026)
----------------------------------------
Es un informe de resultados: afirma, no advierte. Las explicaciones de método
van UNA vez, en «Alcance y método»; los capítulos no llevan recuadros de
advertencia ni vocabulario de gestión («a verificar», «pendiente», nombres
de archivos o de la aplicación). Lo que el equipo necesita saber está en
CONTINUAR-AQUI.md y en las cabeceras de los scripts, no en el entregable.

POR QUÉ SE ARMA DESDE LOS CAPÍTULOS YA GENERADOS
------------------------------------------------
Así no existen dos versiones de la misma cifra. Si un capítulo se regenera con
datos nuevos, basta volver a ejecutar este script para que el consolidado quede
al día. Los capítulos siguen sirviendo como entregables sueltos.

Uso:
  python scripts/generar_informe_consolidado.py     (regenera antes cada capítulo)
  python scripts/generar_informe_consolidado.py --solo-unir
"""

import os
import re
import subprocess
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import informe_estilo as E  # noqa: E402
from informe_estilo import esn

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
DOCS = os.path.join(BASE, 'docs')
SALIDA = os.path.join(DOCS, 'INFORME-CONSOLIDADO-padron-regantes.html')

# Orden del informe: (archivo, título del capítulo, script que lo genera)
CAPITULOS = [
    ('CAPITULO-estructura-del-padron.html', 'Estructura del padrón',
     'generar_capitulo_estructura.py'),
    ('CAPITULO-perfil-del-titular.html', 'Perfil del titular',
     'generar_capitulo_perfil.py'),
    ('CAPITULO-predio-y-agua.html', 'El predio y el acceso al agua',
     'generar_capitulo_riego.py'),
    ('CAPITULO-produccion-agropecuaria.html', 'Producción agropecuaria',
     'generar_capitulo_produccion.py'),
    ('CAPITULO-conocimiento-y-gobernanza.html', 'Conocimiento y gobernanza',
     'generar_informe_encuesta.py'),
    ('CAPITULO-servicios-basicos.html', 'Servicios básicos y hábitat',
     'generar_capitulo_servicios.py'),
    ('CAPITULO-los-tres-sectores.html', 'Los tres sectores de un vistazo',
     'generar_capitulo_sectores.py'),
]

CSS_EXTRA = """
  .portada { text-align: center; padding: 46mm 0 0; break-after: page; }
  .portada .marca { font-size: 10pt; color: #1e4d8c; letter-spacing: 3px;
                    text-transform: uppercase; margin-bottom: 26px; }
  .portada h1 { font-size: 27pt; line-height: 1.2; margin: 0 0 12px; border: 0; }
  .portada .lema { font-size: 12.5pt; color: #444; margin-bottom: 34px; }
  .portada .linea { width: 90px; height: 3px; background: #1e4d8c; margin: 0 auto 34px; }
  .portada .inst { font-size: 11pt; color: #333; line-height: 1.9; }
  .portada .fecha { margin-top: 40px; font-size: 10pt; color: #666; }

  .indice { break-after: page; }
  .indice ol { counter-reset: cap; list-style: none; margin: 0; padding: 0; }
  .indice > ol > li { counter-increment: cap; font-size: 11.5pt; font-weight: 600;
                      padding: 7px 0; border-bottom: 1px dotted #ccd; color: #1e4d8c; }
  .indice > ol > li::before { content: counter(cap) ". "; }

  .cap { break-before: page; }
  .cap-titulo { display: flex; align-items: baseline; gap: 12px;
                border-bottom: 3px solid #1e4d8c; padding-bottom: 7px; margin-bottom: 4px; }
  .cap-titulo .num { font-size: 30pt; font-weight: 700; color: #dbe3ee; line-height: 1; }
  .cap-titulo h2 { border: 0; margin: 0; font-size: 16pt; }
  .resumen { break-after: page; }
  .resumen h2 { margin-top: 0; }
  .cifra { font-weight: 700; color: #1e4d8c; }
  .metodo { break-after: page; }
  .metodo h2 { margin-top: 0; }
  .portada .corte-portada { margin-top: 40px; font-size: 10pt; color: #666; }
"""


def cuerpo_de(ruta):
    """Contenido útil de un capítulo: sin cabecera, sin pie, sin aviso de corte
    (el aviso va una sola vez en el consolidado)."""
    html = open(ruta, encoding='utf-8').read()
    cuerpo = html[html.index('</header>') + len('</header>'):html.index('<footer')]
    cuerpo = re.sub(r'<div class="corte">.*?</div>', '', cuerpo, flags=re.S)
    return cuerpo.strip()


def kpi(resumen_kpis, etiqueta):
    """Valor del KPI cuya etiqueta contiene `etiqueta` (para la prosa del
    resumen); '—' si ningún capítulo lo publica."""
    for _, pares in resumen_kpis:
        for valor, et in pares:
            if etiqueta in et:
                return valor
    return '—'


def kpis_de(html_cuerpo):
    """Extrae los pares (valor, etiqueta) de los KPI para el resumen ejecutivo."""
    return re.findall(r'<div class="n">([^<]+)</div><div class="t">([^<]+)</div>',
                      html_cuerpo.replace('\n', ''))


def renumerar(cuerpo, n_cap):
    """'<h2>3. Ganadería</h2>' -> '<h2>4.3 Ganadería</h2>' en el capítulo 4."""
    return re.sub(r'<h2>(\d+)\.\s*', lambda m: f'<h2>{n_cap}.{m.group(1)} ', cuerpo)


def main():
    if '--solo-unir' not in sys.argv:
        print('Regenerando capítulos…')
        for _, titulo, script in CAPITULOS:
            r = subprocess.run([sys.executable, '-X', 'utf8',
                                os.path.join(os.path.dirname(os.path.abspath(__file__)), script)],
                               capture_output=True, text=True,
                               env={**os.environ, 'PYTHONUTF8': '1'})
            estado = 'ok' if r.returncode == 0 else f'ERROR ({r.returncode})'
            print(f'   {titulo:<34} {estado}')
            if r.returncode != 0:
                print(r.stderr[-600:])
                raise SystemExit('Abortado: falló un capítulo')

    # corte y cifras del primer capítulo disponible (línea de corte de
    # informe_estilo.aviso_corte: «Datos al X. N fichas principales · …»)
    primero = open(os.path.join(DOCS, CAPITULOS[0][0]), encoding='utf-8').read()
    corte = re.search(r'Datos al ([^<.]+)\.', primero).group(1)
    m = re.search(r'([\d,\.]+) fichas principales', primero)
    entrevistas = m.group(1) if m else '—'

    cuerpos, resumen_kpis = [], []
    for i, (arch, titulo, _) in enumerate(CAPITULOS, 1):
        c = cuerpo_de(os.path.join(DOCS, arch))
        if titulo != 'Los tres sectores de un vistazo':
            resumen_kpis.append((titulo, kpis_de(c)))
        cuerpos.append(
            f'<section class="cap"><div class="cap-titulo">'
            f'<span class="num">{i}</span><h2>{titulo}</h2></div>'
            f'{renumerar(c, i)}</section>')

    H = []
    A = H.append

    A('<div class="portada">')
    A('<p class="marca">Consorcio Cayambe SPT</p>')
    A('<h1>Padrón de Usuarios del<br>Sistema de Riego Comunitario<br>'
      'Guanguilquí–Porotog</h1>')
    A('<p class="lema">Informe técnico de resultados del empadronamiento</p>')
    A('<div class="linea"></div>')
    A('<p class="inst">Provincia de Pichincha · Cantón Cayambe<br>'
      'Parroquias de Cangahua, Otón, Cusubamba y Ascázubi</p>')
    A(f'<p class="fecha"><b>Datos al {corte}</b><br>'
      f'Documento generado el {date.today().strftime("%d/%m/%Y")}</p>')
    A('</div>')

    A('<div class="indice">')
    A('<h2>Contenido</h2>')
    A('<ol>')
    for _, titulo, _ in CAPITULOS:
        A(f'<li>{titulo}</li>')
    A('</ol>')
    A('</div>')

    total_fichas = kpi(resumen_kpis, 'fichas de predio')
    A('<div class="metodo">')
    A('<h2>Alcance y método</h2>')
    A('<p>Este informe presenta los resultados del empadronamiento de usuarios '
      'del sistema de riego comunitario Guanguilquí–Porotog, levantado predio a '
      'predio con una ficha digital georreferenciada y cerrado en campo con '
      f'<b>{total_fichas} fichas</b> al {corte}. Cada capítulo corresponde a una '
      'sección de esa ficha y puede leerse por separado; el último compara los '
      'tres sectores de investigación. Las cifras salen directamente de la base '
      'de datos de campo, sin transcripción intermedia, y cada gráfico nombra al '
      'pie el universo sobre el que se calcula.</p>')
    A('<p><b>Fichas principales y adicionales.</b> Cada ficha es un predio. La '
      f'<i>ficha principal</i> recoge la entrevista al titular ({entrevistas} '
      'fichas); las <i>fichas adicionales</i> son los demás predios del mismo '
      'titular, levantados sin repetir la entrevista. Por eso las cifras sobre '
      'personas —instrucción, familia, tenencia, conocimiento del proyecto y '
      'capacitación— se calculan sobre las fichas principales, y las cifras '
      'sobre territorio y producción —superficie, cultivos, ganado— sobre todas '
      'las fichas. Los dos universos no se suman entre sí.</p>')
    A('<p><b>Dos mediciones de superficie.</b> La <i>catastral</i> suma cada '
      'polígono del catastro municipal una sola vez y es la superficie del '
      'sistema; la <i>declarada</i> es lo que cada titular considera suyo en la '
      'entrevista, y en los predios familiares varios herederos declaran el '
      'mismo terreno. Las dos describen el mismo territorio, cada cuadro nombra '
      'la suya y nunca se combinan. El tamaño de los predios se cuenta por '
      'predio catastral, no por ficha.</p>')
    A('<p><b>Caudal, tarifas y sector.</b> El caudal se contabiliza una sola vez '
      'por comunidad, porque los técnicos anotaron en cada ficha el caudal que '
      'recibe la comunidad entera. Las tarifas se resumen con la mediana, el '
      'valor que paga efectivamente la mayoría; los valores del fraccionamiento '
      'Alpaka corresponden a otro concepto y no entran en ese cálculo. El sector '
      'de cada ficha es el de su comunidad según el listado oficial de '
      'organizaciones de riego.</p>')
    A('<p><b>Producción y vivienda.</b> El inventario pecuario no incluye una '
      'explotación avícola industrial de 60.000 aves registrada en una '
      'comunidad, ajena a la producción familiar que describe el informe. Los '
      'servicios de agua y energía se calculan sobre las viviendas, es decir, '
      'sobre las fichas que declaran una construcción en el predio; un predio '
      'sin casa no es una vivienda sin servicio.</p>')
    A('</div>')

    A('<div class="resumen">')
    A('<h2>Resumen ejecutivo</h2>')
    A('<p>El sistema de riego Guanguilquí–Porotog atiende a una población '
      'campesina de minifundio, organizada comunitariamente, cuya producción se '
      'destina principalmente al consumo familiar. Los datos del empadronamiento '
      'permiten dimensionarlo con precisión:</p>')
    for titulo, kpis in resumen_kpis:
        if not kpis:
            continue
        A(f'<h3>{titulo}</h3>')
        A('<ul>')
        for valor, etiqueta in kpis:
            A(f'<li><span class="cifra">{valor}</span> — {etiqueta}</li>')
        A('</ul>')
    A('<h3>Cuatro rasgos que definen el sistema</h3>')
    A(f'<p><b>Minifundio bajo riego.</b> El sistema riega '
      f'{kpi(resumen_kpis, "bajo riego")}, el {kpi(resumen_kpis, "del área del sistema")} '
      f'de su superficie catastral, con un caudal de {kpi(resumen_kpis, "caudal del sistema")}; '
      'la mayoría de los predios no llega a la hectárea y '
      f'{kpi(resumen_kpis, "con más de un predio")} de los titulares tiene más de un '
      'predio.</p>')
    A(f'<p><b>Producción para la familia.</b> El '
      f'{kpi(resumen_kpis, "destino autoconsumo")} de las declaraciones agrícolas se '
      'destinan al autoconsumo y la mayor parte de la superficie cultivada son '
      'pastos que sostienen una ganadería de traspatio: el riego asegura antes la '
      'alimentación de las familias que una cadena comercial.</p>')
    A(f'<p><b>Titulares con instrucción básica y sin título.</b> El '
      f'{kpi(resumen_kpis, "con instrucción básica o menos")} de los titulares no '
      f'superó la primaria y el {kpi(resumen_kpis, "sin título de propiedad")} ocupa '
      'su predio sin título: toda comunicación y todo programa de inversión deben '
      'partir de ahí.</p>')
    A(f'<p><b>Una Junta reconocida y una demanda de capacitación.</b> El '
      f'{kpi(resumen_kpis, "identifica al presidente")} identifica al presidente de '
      f'la Junta, el {kpi(resumen_kpis, "conoce el proyecto de la presa")} conoce el '
      f'proyecto de la presa y el {kpi(resumen_kpis, "quiere capacitación")} quiere '
      'capacitarse, sobre todo en manejo del riego.</p>')
    A('</div>')

    H += cuerpos

    A(f'<footer><span>{E.PIE_INSTITUCION}</span>'
      f'<span>Corte: {corte}</span></footer>')

    doc = E.documento('Informe técnico — Padrón de Usuarios Guanguilquí–Porotog',
                      '\n'.join(H))
    doc = doc.replace('</style>', CSS_EXTRA + '</style>')
    with open(SALIDA, 'w', encoding='utf-8') as f:
        f.write(doc)

    kb = os.path.getsize(SALIDA) / 1024
    print(f'\n  INFORME CONSOLIDADO: {os.path.relpath(SALIDA, BASE)}  ({esn(kb, 0)} KB)')
    print(f'  {len(CAPITULOS)} capítulos · corte al {corte}')


if __name__ == '__main__':
    main()
