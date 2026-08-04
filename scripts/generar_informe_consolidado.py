# -*- coding: utf-8 -*-
"""
Informe consolidado: reúne los seis capítulos en un solo documento entregable.

Toma los HTML que ya generan los scripts de cada capítulo, les quita cabecera y
pie individuales, renumera sus secciones (1.1, 2.3…) y los monta bajo una
portada única con índice, resumen ejecutivo y anexo de datos a verificar.

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

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
DOCS = os.path.join(BASE, 'docs')
SALIDA = os.path.join(DOCS, 'INFORME-CONSOLIDADO-padron-regantes.html')

# Orden del informe: (archivo, título del capítulo, script que lo genera)
CAPITULOS = [
    ('CAPITULO-estructura-del-padron.html', 'Estructura del padrón',
     'generar_capitulo_estructura.py'),
    ('CAPITULO-perfil-del-regante.html', 'Perfil del regante',
     'generar_capitulo_perfil.py'),
    ('CAPITULO-predio-y-agua.html', 'El predio y el acceso al agua',
     'generar_capitulo_riego.py'),
    ('CAPITULO-produccion-agropecuaria.html', 'Producción agropecuaria',
     'generar_capitulo_produccion.py'),
    ('CAPITULO-conocimiento-y-gobernanza.html', 'Conocimiento y gobernanza',
     'generar_informe_encuesta.py'),
    ('CAPITULO-servicios-basicos.html', 'Servicios básicos y hábitat',
     'generar_capitulo_servicios.py'),
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
"""


def cuerpo_de(ruta):
    """Contenido útil de un capítulo: sin cabecera, sin pie, sin aviso de corte
    (el aviso va una sola vez en el consolidado)."""
    html = open(ruta, encoding='utf-8').read()
    cuerpo = html[html.index('</header>') + len('</header>'):html.index('<footer')]
    cuerpo = re.sub(r'<div class="corte">.*?</div>', '', cuerpo, flags=re.S)
    return cuerpo.strip()


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

    # corte y cifras del primer capítulo disponible
    primero = open(os.path.join(DOCS, CAPITULOS[0][0]), encoding='utf-8').read()
    corte = re.search(r'Datos de avance al ([^<.]+)\.', primero).group(1)
    m = re.search(r'se registran <b>([\d,\.]+) fichas de regante</b> y quedan '
                  r'<b>([\d,\.]+) predios adicionales</b>', primero)
    entrevistas, pendientes = (m.group(1), m.group(2)) if m else ('—', '—')

    cuerpos, resumen_kpis = [], []
    for i, (arch, titulo, _) in enumerate(CAPITULOS, 1):
        c = cuerpo_de(os.path.join(DOCS, arch))
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
    A(f'<p class="fecha"><b>Datos con corte al {corte}</b><br>'
      f'Documento generado el {date.today().strftime("%d/%m/%Y")}</p>')
    A('</div>')

    A('<div class="indice">')
    A('<h2>Contenido</h2>')
    A('<ol>')
    for _, titulo, _ in CAPITULOS:
        A(f'<li>{titulo}</li>')
    A('</ol>')
    A('<h2 style="margin-top:26px">Sobre este informe</h2>')
    # El aviso viene redactado para un capítulo suelto; aquí encabeza el documento.
    A(E.aviso_corte(corte, int(entrevistas.replace(',', '').replace('.', '')),
                    int(pendientes.replace(',', '').replace('.', '')))
      .replace('de este capítulo', 'de este informe'))
    A('<p>El presente informe sintetiza los resultados del empadronamiento de '
      'usuarios del sistema de riego, levantado predio a predio mediante ficha '
      'digital georreferenciada. Cada capítulo corresponde a una sección de esa '
      'ficha y puede leerse de forma independiente.</p>')
    A('<p>Las cifras provienen directamente de la base de datos de campo, sin '
      'transcripción intermedia. Cuando un dato requiere una advertencia '
      'metodológica —una cobertura parcial, un registro que debe verificarse o un '
      'criterio de cálculo que condiciona el resultado— esa advertencia acompaña a '
      'la cifra en el propio capítulo, para que ninguna se cite fuera de contexto.</p>')
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
    A('<h3>Cuatro registros a verificar en campo</h3>')
    A('<p>El análisis detectó cuatro casos cuyos valores no son consistentes con el '
      'resto del padrón. Están excluidos de las cifras de este informe y en proceso '
      'de verificación con los usuarios:</p>')
    A('<ol>')
    A('<li>Tarifas de 672 y 308 USD mensuales declaradas en 491 predios de una '
      'misma comunidad, frente a una mediana de 3 USD en el resto del sistema.</li>')
    A('<li>Una explotación avícola declarada de forma repetida por seis titulares '
      'sobre un mismo predio, equivalente a 60.000 aves.</li>')
    A('<li>Tres usuarios individuales cuyo caudal declarado coincide exactamente '
      'con el de su comunidad de origen, por 71,5 l/s.</li>')
    A('<li>El apartado de servicios básicos, cuyo levantamiento continúa y alcanza '
      'el 68 % de los predios.</li>')
    A('</ol>')
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
    print(f'\n  INFORME CONSOLIDADO: {os.path.relpath(SALIDA, BASE)}  ({kb:,.0f} KB)')
    print(f'  {len(CAPITULOS)} capítulos · corte al {corte}')


if __name__ == '__main__':
    main()
