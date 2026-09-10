# -*- coding: utf-8 -*-
"""
Estilo y piezas comunes de los capítulos del informe técnico.

Todos los capítulos comparten identidad visual, el recuadro de corte parcial y
las mismas tablas, para que al juntarlos parezcan un solo documento y no seis
informes distintos pegados.
"""

CSS = """
  @page { size: A4; margin: 16mm 15mm; }
  * { box-sizing: border-box; }
  body { font-family: "Segoe UI", Roboto, Arial, sans-serif; color: #1a1a1a;
         margin: 0; line-height: 1.5; font-size: 10.5pt; background: #fff; }
  header { border-bottom: 3px solid #1e4d8c; padding-bottom: 10px; margin-bottom: 6px;
           display: flex; justify-content: space-between; align-items: flex-end; gap: 16px; }
  h1 { font-size: 17pt; margin: 0 0 3px; color: #1e4d8c; }
  .sub { font-size: 9.5pt; color: #555; margin: 0; }
  .meta { font-size: 8pt; color: #777; text-align: right; white-space: nowrap; }
  h2 { font-size: 13pt; color: #1e4d8c; margin: 22px 0 8px;
       border-bottom: 1px solid #dbe3ee; padding-bottom: 4px; }
  h3 { font-size: 11pt; margin: 16px 0 6px; color: #24405e; }
  p { margin: 7px 0; text-align: justify; }

  .corte { color: #445; padding: 6px 0 8px; margin: 8px 0 14px; font-size: 9.5pt;
           border-bottom: 1px solid #dbe3ee; }
  .corte b { color: #1e4d8c; }
  .fig { margin: 8px 0 4px; }
  .fig img { max-width: 100%; border: 1px solid #dbe3ee; border-radius: 7px;
             background: #fff; padding: 6px; }
  .pie-fig { font-size: 8.5pt; color: #667; margin: 2px 0 14px; text-align: left; }

  .kpis { display: grid; grid-template-columns: repeat(4, 1fr); gap: 9px; margin: 14px 0; }
  .kpi { border: 1px solid #dbe3ee; border-radius: 7px; padding: 9px 11px; background: #f8fafc; }
  .kpi .n { font-size: 17pt; font-weight: 700; color: #1e4d8c; line-height: 1.1; }
  .kpi .t { font-size: 8pt; color: #556; margin-top: 3px; }

  table { width: 100%; border-collapse: collapse; font-size: 9.5pt; margin: 9px 0 14px; }
  th { background: #1e4d8c; color: #fff; text-align: left; padding: 5px 8px; font-weight: 600; }
  td { padding: 4px 8px; border-bottom: 1px solid #e8edf3; }
  tr:nth-child(even) td { background: #fafbfd; }
  td.n, th.n { text-align: right; }
  .dest { background: #eefbf0 !important; font-weight: 600; }

  .barra { background: #eef2f7; border-radius: 3px; height: 13px; position: relative; min-width: 90px; }
  .barra span { display: block; height: 100%; border-radius: 3px; background: #2e7d4f; }
  .barra i { position: absolute; right: 5px; top: -1px; font-size: 8pt; font-style: normal; color: #24405e; }

  .nota { background: #f0f6ff; border-left: 4px solid #1e4d8c; padding: 8px 12px;
          margin: 12px 0; font-size: 9.5pt; }
  .hallazgo { background: #f4fbf6; border: 1px solid #bfe3cc; border-radius: 6px;
              padding: 10px 14px; margin: 14px 0; }
  .hallazgo b { color: #1d6b35; }
  .alerta { background: #fff5f5; border: 1px solid #f0c2c2; border-radius: 6px;
            padding: 10px 14px; margin: 14px 0; }
  .alerta b { color: #a03030; }
  ul { margin: 6px 0 6px 18px; padding: 0; }
  li { margin: 4px 0; }
  footer { margin-top: 22px; padding-top: 8px; border-top: 1px solid #ccc;
           font-size: 8pt; color: #777; display: flex; justify-content: space-between; }
  .evitar-corte { break-inside: avoid; }
  @media print { body { font-size: 10pt; } }
"""

# Fecha de corte EDITORIAL de todo el paquete de entrega: capítulos, consolidado,
# anexo e informes del sociólogo citan esta misma fecha. Hasta el 4-sep-2026
# los capítulos tomaban la última fecha de ficha del gpkg («5 de agosto») y
# los informes del sociólogo esta constante («19 de agosto»); JAVIKO decidió
# unificarlas aquí. Las depuraciones de gabinete no mueven las fechas de las
# fichas, así que la fecha del gpkg ya no describe el corte real.
FECHA_CORTE = '19 de agosto de 2026'

def esn(valor, dec=0, miles=True):
    """Número escrito en castellano: miles con punto, decimales con coma.

    El formato por defecto de Python es anglosajón y escribía «6,830» y
    «95.3» en documentos en español, donde significan otra cosa. `miles=False`
    formatea sin separador de miles, para lo que no debe llevarlo (años,
    códigos): así la conversión nunca añade un punto donde no lo había.
    """
    if valor is None or valor == '':
        return '—'
    try:
        n = float(valor)
    except (TypeError, ValueError):
        return str(valor)
    s = f'{n:,.{dec}f}' if miles else f'{n:.{dec}f}'
    # el intercambio se hace en dos pasos para no pisar el separador ya puesto
    return s.replace(',', '\x00').replace('.', ',').replace('\x00', '.')


PIE_INSTITUCION = ('Padrón de Usuarios · Sistema de Riego Comunitario '
                   'Guanguilquí–Porotog')


def barra(p):
    """Barra de porcentaje; el número pasa a blanco cuando la barra lo taparía."""
    color = ' style="color:#fff"' if p >= 88 else ''
    # el ancho es CSS y va sin formato de idioma; el número lo lee una persona
    return (f'<div class="barra"><span style="width:{min(p, 100):.0f}%"></span>'
            f'<i{color}>{esn(p, 1, False)} %</i></div>')


def cabecera(titulo, subtitulo):
    return (f'<header><div><h1>{titulo}</h1>'
            f'<p class="sub">{subtitulo}</p></div>'
            f'<div class="meta">Padrón de Usuarios<br>'
            f'Sistema de Riego Comunitario Guanguilquí–Porotog<br>'
            f'Consorcio Cayambe SPT</div></header>')


def aviso_corte(corte_texto, entrevistas, pendientes):
    """Línea de corte de cada capítulo.

    Con el campo cerrado (JAVIKO, 31-ago-2026) es una línea informativa, no
    una advertencia: fecha, tamaño del padrón y estado del levantamiento. Si
    algún día vuelven a quedar adicionales pendientes, vuelve a decirlo.

    La cifra «N fichas principales» la LEE `generar_informe_consolidado.py`
    con un regex: si se reescribe, actualizar el regex a la par.
    """
    if pendientes:
        estado = (f'levantamiento en curso, {esn(pendientes, 0)} predios adicionales '
                  'por completar')
    else:
        estado = 'levantamiento de campo cerrado'
    return (f'<div class="corte"><b>Datos al {corte_texto}.</b> '
            f'{esn(entrevistas, 0)} fichas principales · {estado}.</div>')


def figura(b64, titulo, pie='', nivel='h3'):
    """Gráfico con el estilo de la casa: título opcional, imagen y un pie de
    UNA línea que nombra el universo («Fichas principales, 4.307»)."""
    h = []
    if titulo:
        h.append(f'<{nivel}>{titulo}</{nivel}>')
    h.append(f'<div class="fig evitar-corte"><img src="data:image/png;base64,{b64}" '
             f'alt="{titulo or pie}"></div>')
    if pie:
        h.append(f'<p class="pie-fig">{pie}</p>')
    return '\n'.join(h)


def kpis(pares):
    h = ['<div class="kpis">']
    for n, t in pares:
        h.append(f'<div class="kpi"><div class="n">{n}</div><div class="t">{t}</div></div>')
    h.append('</div>')
    return '\n'.join(h)


def pie(corte_texto):
    return (f'<footer><span>{PIE_INSTITUCION}</span>'
            f'<span>Corte: {corte_texto}</span></footer>')


def documento(titulo_tab, cuerpo):
    return ('<!doctype html><html lang="es"><head><meta charset="utf-8">'
            f'<title>{titulo_tab}</title>'
            f'<style>{CSS}</style></head><body>\n{cuerpo}\n</body></html>')
