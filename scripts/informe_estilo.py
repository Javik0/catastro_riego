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

  .corte { background: #fff8e6; border: 1px solid #e0a800; border-left: 5px solid #e0a800;
           padding: 9px 13px; margin: 12px 0 18px; font-size: 9.5pt; border-radius: 4px; }
  .corte b { color: #8a6100; }

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

PIE_INSTITUCION = ('Padrón de Usuarios · Sistema de Riego Comunitario '
                   'Guanguilquí–Porotog')


def barra(p):
    """Barra de porcentaje; el número pasa a blanco cuando la barra lo taparía."""
    color = ' style="color:#fff"' if p >= 88 else ''
    return (f'<div class="barra"><span style="width:{min(p, 100):.0f}%"></span>'
            f'<i{color}>{p:.1f}%</i></div>')


def cabecera(titulo, subtitulo):
    return (f'<header><div><h1>{titulo}</h1>'
            f'<p class="sub">{subtitulo}</p></div>'
            f'<div class="meta">Padrón de Usuarios<br>'
            f'Sistema de Riego Comunitario Guanguilquí–Porotog<br>'
            f'Consorcio Cayambe SPT</div></header>')


def aviso_corte(corte_texto, entrevistas, pendientes):
    """Aviso de cabecera de cada capítulo.

    El levantamiento de campo se cerró (JAVIKO, 31-ago-2026: todas las
    secciones de la ficha están completadas), así que el texto ya no dice
    «sigue en curso». Si algún día vuelven a quedar adicionales pendientes,
    el aviso lo detecta y vuelve a hablar de levantamiento abierto.

    La frase «se registran N fichas principales y quedan M predios
    adicionales» la LEE con un regex `generar_informe_consolidado.py`: si se
    reescribe, hay que actualizar el regex a la par.
    """
    estado = ('El levantamiento de campo está <b>cerrado</b>: todas las '
              'secciones de la ficha se completaron.' if not pendientes else
              'El levantamiento del padrón <b>sigue en curso</b>.')
    return ('<div class="corte"><b>Datos al '
            f'{corte_texto}.</b> {estado} '
            f'A la fecha de corte se registran <b>{entrevistas:,} fichas principales</b> '
            f'y quedan <b>{pendientes:,} predios adicionales</b> por completar. Las '
            'cifras se recalculan con cada depuración de gabinete; deben '
            'citarse siempre acompañadas de su fecha de corte.'
            '</div>')


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
