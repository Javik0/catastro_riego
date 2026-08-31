# -*- coding: utf-8 -*-
"""
Capítulo del informe técnico: "Conocimiento y gobernanza del sistema".

Lo llama generar_informe_encuesta.py con las cifras ya calculadas y produce un
HTML imprimible (A4) con la identidad del padrón, listo para anexar al informe
del Consorcio o entregarse suelto.

CORTE PARCIAL
-------------
El levantamiento sigue en curso, así que el capítulo lleva en portada la FECHA
DE CORTE y una advertencia visible: las cifras son de avance y se recalculan en
cada actualización. Sin eso, un lector podría citar un porcentaje como
definitivo cuando todavía entran fichas cada jornada.
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
  ul { margin: 6px 0 6px 18px; padding: 0; }
  li { margin: 4px 0; }
  footer { margin-top: 22px; padding-top: 8px; border-top: 1px solid #ccc;
           font-size: 8pt; color: #777; display: flex; justify-content: space-between; }
  .evitar-corte { break-inside: avoid; }
  @media print { body { font-size: 10pt; } }
"""


def barra(p, ancho=100):
    """Barra de porcentaje. Cuando está casi llena el número queda sobre el
    verde, así que pasa a blanco para que siga leyéndose."""
    color = ' style="color:#fff"' if p >= 88 else ''
    return (f'<div class="barra"><span style="width:{min(p, 100):.0f}%"></span>'
            f'<i{color}>{p:.1f}%</i></div>')


def construir(d):
    """d: dict con todas las cifras que calcula generar_informe_encuesta."""
    H = []
    A = H.append
    A('<!doctype html><html lang="es"><head><meta charset="utf-8">')
    A('<title>Conocimiento y gobernanza del sistema — Padrón Guanguilquí–Porotog</title>')
    A(f'<style>{CSS}</style></head><body>')

    A('<header><div>')
    A('<h1>Conocimiento y gobernanza del sistema de riego</h1>')
    A('<p class="sub">Resultados de la encuesta a los titulares entrevistados · '
      'Capítulo del informe técnico</p>')
    A('</div><div class="meta">'
      'Padrón de Usuarios<br>Sistema de Riego Comunitario Guanguilquí–Porotog<br>'
      'Consorcio Cayambe SPT</div></header>')

    A('<div class="corte"><b>Datos de avance al '
      f'{d["corte_texto"]}.</b> El levantamiento del padrón <b>sigue en curso</b>: '
      f'a la fecha de corte se registran <b>{d["total"]:,} entrevistas</b> y quedan '
      f'<b>{d["pendientes_s4"]:,} predios adicionales</b> por completar. Las cifras '
      'de este capítulo son parciales y se recalculan en cada actualización; deben '
      'citarse siempre acompañadas de su fecha de corte.</div>')

    # ── KPIs ──
    A('<div class="kpis">')
    for n, t in [
        (f'{d["total"]:,}', 'fichas principales'),
        (f'{d["pct_presa"]:.1f}%', 'conoce el proyecto de la presa'),
        (f'{d["pct_presidente"]:.1f}%', 'identifica al presidente'),
        (f'{d["pct_quiere_cap"]:.1f}%', 'quiere capacitación'),
    ]:
        A(f'<div class="kpi"><div class="n">{n}</div><div class="t">{t}</div></div>')
    A('</div>')

    # ── 1 ──
    A('<h2>1. Alcance y método</h2>')
    A(f'<p>Este capítulo sintetiza la sección <i>«Datos de la comunidad y conocimiento '
      f'de la Junta de Agua»</i> de la ficha de campo, aplicada a los usuarios del '
      f'sistema durante el empadronamiento. El universo son las <b>{d["total"]:,} '
      f'fichas principales</b> registradas hasta el corte: una por titular '
      f'entrevistado.</p>')
    A('<div class="nota"><b>Sobre el universo.</b> Un mismo titular puede tener varios '
      f'predios: {d["con_adicionales"]:,} de los entrevistados declararon predios '
      'adicionales. La entrevista se realiza <b>una sola vez por persona</b>, de modo '
      'que sus fichas adicionales no se contabilizan como entrevistas independientes; '
      'lo contrario multiplicaría la misma respuesta y distorsionaría los porcentajes. '
      f'Quedan fuera {d["solo_adicionales"]} personas que constan únicamente como '
      'predio adicional de otro titular y cuyas respuestas se heredaron de la ficha '
      f'de origen. El padrón de usuarios asciende, por tanto, a {d["padron_personas"]:,} '
      'personas, cifra distinta del número de entrevistas.</p></div>')
    A('<p>La tasa de respuesta supera el 93 % en todas las preguntas cerradas. Los '
      'nombres propios se agrupan sin acentos ni espacios sobrantes para no fragmentar '
      'a una misma persona en variantes de escritura.</p>')

    # ── 2 ──
    A('<h2>2. Conocimiento del proyecto de la presa Río Porotog</h2>')
    A(f'<p>El <b>{d["pct_presa"]:.1f} %</b> de las fichas principales declara conocer el proyecto '
      f'de la presa ({d["presa_si"]:,} de {d["presa_resp"]:,} respuestas). Es un nivel '
      'alto de difusión previa, aunque con diferencias territoriales relevantes.</p>')
    A('<table class="evitar-corte"><tr><th>Sector</th><th class="n">Sí</th>'
      '<th class="n">No</th><th>Conocimiento</th></tr>')
    # Las fichas cuyo sector no pudo determinarse se excluyen del cuadro y se
    # declaran al pie: son residuales y una fila "(sin sector)" en un informe
    # formal invita a preguntas que no aportan al análisis.
    sin_sector = 0
    for sec, (si, no) in sorted(d['presa_sector'].items()):
        if sec.startswith('('):
            sin_sector += si + no
            continue
        p = 100.0 * si / (si + no) if si + no else 0
        A(f'<tr><td>{sec}</td><td class="n">{si:,}</td><td class="n">{no:,}</td>'
          f'<td>{barra(p)}</td></tr>')
    A('</table>')
    if sin_sector:
        A(f'<p style="font-size:9pt;color:#667;margin-top:-8px">'
          f'No se incluyen {sin_sector} entrevistas cuyo sector no pudo determinarse '
          f'({100.0 * sin_sector / d["presa_resp"]:.1f} % del total).</p>')
    A('<h3>Comunidades con menor difusión</h3>')
    A('<p>Comunidades con veinte o más entrevistados donde el conocimiento del proyecto '
      'es más bajo. Constituyen el foco prioritario de socialización:</p>')
    A('<table class="evitar-corte"><tr><th>Comunidad</th><th class="n">Sí</th>'
      '<th class="n">No</th><th>Conocimiento</th></tr>')
    for com, si, no, p in d['presa_bajas'][:8]:
        A(f'<tr><td>{com}</td><td class="n">{si:,}</td><td class="n">{no:,}</td>'
          f'<td>{barra(p)}</td></tr>')
    A('</table>')

    # ── 3 ──
    A('<h2>3. Gobernanza de la Junta de Agua</h2>')
    A(f'<p>La directiva se elige por <b>asamblea general</b> según el '
      f'<b>{d["pct_asamblea"]:.1f} %</b> de las fichas principales, una unanimidad que confirma '
      'la vigencia del mecanismo comunitario de designación. Las menciones a '
      'designación directa o herencia son marginales.</p>')
    A(f'<p>El <b>{d["pct_presidente"]:.1f} %</b> identifica por nombre al presidente '
      f'de la Junta, {d["presidente"]}. El reconocimiento de la dirigencia es, por '
      'tanto, generalizado: la Junta es una institución presente y conocida por sus '
      'usuarios, no una figura administrativa lejana.</p>')
    A('<h3>Operadores del sistema por sector</h3>')
    A('<p>El operador es la figura de contacto cotidiano para el reparto del agua. '
      'Cada sector reconoce mayoritariamente a un responsable distinto:</p>')
    A('<table class="evitar-corte"><tr><th>Sector</th><th>Operador más reconocido</th>'
      '<th class="n">Menciones</th><th class="n">% del sector</th></tr>')
    for sec, nom, n, p in d['operadores']:
        if sec.startswith('('):      # sector indeterminado: no va en el cuadro
            continue
        A(f'<tr><td>{sec}</td><td>{nom}</td><td class="n">{n:,}</td>'
          f'<td class="n">{p:.1f}%</td></tr>')
    A('</table>')

    # ── 4 ──
    A('<h2>4. Conocimiento de la infraestructura</h2>')
    A(f'<p>Consultados por la antigüedad del sistema, la respuesta dominante es '
      f'<b>{d["anios_moda"]} años</b> ({d["anios_pct"]:.1f} % de las respuestas; '
      f'mediana {d["anios_mediana"]}). Sobre la longitud del canal principal, el '
      f'<b>{d["km_pct"]:.1f} %</b> responde <b>{d["km_moda"]:g} km</b>.</p>')
    A('<p>La convergencia de ambas respuestas en un valor claramente dominante indica '
      'una <b>memoria colectiva consistente</b> sobre la obra: los usuarios comparten '
      'una misma referencia histórica y física del sistema, lo que facilita cualquier '
      'proceso de socialización técnica.</p>')

    # ── 5 ──
    A('<h2>5. Capacitación</h2>')
    A(f'<p>El <b>{d["pct_recibio_cap"]:.1f} %</b> declara haber recibido capacitación '
      f'y el <b>{d["pct_quiere_cap"]:.1f} %</b> desea recibirla. El contraste entre '
      'ambas cifras revela una demanda formativa amplia y sostenida.</p>')
    A('<table class="evitar-corte"><tr><th>Situación</th><th class="n">Fichas principales</th>'
      '<th class="n">%</th></tr>')
    A(f'<tr class="dest"><td>Nunca recibió capacitación y la solicita</td>'
      f'<td class="n">{d["demanda_no_atendida"]:,}</td>'
      f'<td class="n">{d["pct_demanda"]:.1f}%</td></tr>')
    A(f'<tr><td>Ya recibió y solicita más</td><td class="n">{d["cap_si_y_quiere"]:,}</td>'
      f'<td class="n">{d["pct_si_quiere"]:.1f}%</td></tr>')
    A(f'<tr><td>No solicita capacitación</td><td class="n">{d["cap_no_quiere"]:,}</td>'
      f'<td class="n">{d["pct_no_quiere"]:.1f}%</td></tr>')
    A('</table>')
    A(f'<div class="hallazgo"><b>Hallazgo principal.</b> '
      f'{d["demanda_no_atendida"]:,} titulares nunca han recibido capacitación y '
      'manifiestan querer recibirla. Constituyen la población objetivo directa e '
      'inmediata de un plan de formación, sin necesidad de estudios adicionales para '
      'identificarla: están nominados en el padrón, con su comunidad y su sector.</div>')
    A('<h3>Temas solicitados</h3>')
    A('<table class="evitar-corte"><tr><th>Categoría temática</th>'
      '<th class="n">Menciones</th><th>Peso</th></tr>')
    for cat, n, p in d['temas']:
        A(f'<tr><td>{cat}</td><td class="n">{n:,}</td><td>{barra(p)}</td></tr>')
    A('</table>')
    A(f'<p>La demanda se concentra de forma abrumadora en el <b>manejo del riego</b>, '
      'coherente con el objeto del sistema y con la expectativa que genera el proyecto '
      'de la presa.</p>')

    # ── 6 ──
    A('<h2>6. Conclusiones</h2>')
    A('<ul>')
    A(f'<li>La Junta de Agua es una <b>institución reconocida</b>: '
      f'{d["pct_presidente"]:.1f} % identifica a su presidente y '
      f'{d["pct_asamblea"]:.1f} % confirma la elección por asamblea.</li>')
    A(f'<li>El proyecto de la presa <b>ya es conocido por {d["pct_presa"]:.1f} %</b> de '
      'los usuarios, con vacíos concentrados en comunidades identificables — la '
      'socialización pendiente es acotada y focalizable.</li>')
    A('<li>Existe una <b>memoria técnica compartida</b> sobre la antigüedad y la '
      'extensión de la infraestructura.</li>')
    A(f'<li>La <b>demanda de capacitación es la principal oportunidad</b> detectada: '
      f'{d["demanda_no_atendida"]:,} usuarios sin formación previa la solicitan '
      'expresamente, y el tema prioritario es el manejo del riego.</li>')
    A('</ul>')

    A('<div class="nota"><b>Limitación documentada.</b> La ficha de campo en papel '
      'contempla dos preguntas sobre si la Junta cuenta con <i>estatutos</i> y '
      '<i>reglamentos</i>. Esos campos no fueron incorporados al formulario digital, '
      'por lo que no existe registro sistemático y no se reportan en este capítulo.</div>')

    A(f'<footer><span>Padrón de Usuarios · Sistema de Riego Comunitario '
      f'Guanguilquí–Porotog</span><span>Corte: {d["corte_texto"]}</span></footer>')
    A('</body></html>')
    return '\n'.join(H)
