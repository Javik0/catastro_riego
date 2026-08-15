# -*- coding: utf-8 -*-
"""
Informe para leer en la comunidad, sin internet.

Para qué
--------
Las reuniones son en la comunidad, donde puede no haber señal, y el público no
es el contratante: son los regantes y la directiva de la junta. Este informe se
abre con doble clic desde una laptop o un celular —**un solo archivo, sin
conexión, sin servidor**— y responde a lo que la junta pidió: cuántas encuestas
hay por comunidad, cuántas hectáreas tiene cada una según el catastro, cuántas
riega y cuánta agua recibe.

Decisiones de forma, que aquí importan tanto como el dato
---------------------------------------------------------
* **Cifras grandes y barras**, no tablas densas: se lee proyectado en una pared
  o pasando el celular de mano en mano.
* **Sin jerga**: no aparece «polígono catastral» ni «ficha madre». Se habla de
  terrenos, familias y hectáreas.
* **Una sola superficie a la vista.** El padrón maneja dos —lo que declara la
  gente y lo que mide el catastro— y enseñarlas juntas en una asamblea abre una
  discusión que no toca ahí. Manda la del catastro, que cuenta cada terreno una
  vez, y la diferencia se explica al pie en una frase.
* Todo el CSS va incrustado y no hay ni una imagen externa: si el archivo viaja
  por WhatsApp, sigue viéndose igual.

Uso
---
    python -X utf8 scripts/generar_informe_comunidades.py --sector "Sector 1"
    python -X utf8 scripts/generar_informe_comunidades.py --sector todos

Sale en `docs/INFORME-COMUNIDADES-<sector>.html` y se copia al Escritorio, a la
carpeta de entrega.
"""
import argparse
import json
import os
import sys
import unicodedata
from datetime import datetime

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
GEO = os.path.join(BASE, 'public', 'geo')
DOCS = os.path.join(BASE, 'docs')
ENTREGA = (r"C:\Users\HP\OneDrive\Escritorio\INFORME ENCUESTA REGANTES")

MESES = ('enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio',
         'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre')


def n(v, dec=0):
    """Número con punto de miles y coma decimal, como se lee aquí."""
    s = '{:,.{}f}'.format(v or 0, dec)
    return s.replace(',', 'X').replace('.', ',').replace('X', '.')


def sin_tildes(s):
    s = unicodedata.normalize('NFKD', str(s or ''))
    return ''.join(c for c in s if not unicodedata.combining(c))


def fecha_larga(iso):
    try:
        d = datetime.strptime(iso, '%Y-%m-%d')
        return '{} de {} de {}'.format(d.day, MESES[d.month - 1], d.year)
    except Exception:
        return iso


CSS = """
:root{--tinta:#14261c;--suave:#5b6b62;--linea:#dfe6e1;--agua:#1a73a7;
      --tierra:#c86a1e;--verde:#2f7d4f;--fondo:#fbfaf7;--caja:#fff}
*{box-sizing:border-box}
body{margin:0;background:var(--fondo);color:var(--tinta);
     font:16px/1.55 "Segoe UI",system-ui,-apple-system,sans-serif}
.hoja{max-width:1000px;margin:0 auto;padding:22px 18px 60px}
header{border-bottom:4px solid var(--verde);padding-bottom:14px;margin-bottom:22px}
h1{font-size:29px;margin:0 0 4px;line-height:1.15}
.sub{color:var(--suave);font-size:15px}
h2{font-size:21px;margin:34px 0 12px;padding-left:11px;border-left:5px solid var(--verde)}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(158px,1fr));gap:12px;margin:16px 0}
.kpi{background:var(--caja);border:1px solid var(--linea);border-radius:12px;padding:15px 16px}
.kpi .n{font-size:31px;font-weight:800;line-height:1.05;letter-spacing:-.5px}
.kpi .t{font-size:13px;color:var(--suave);margin-top:3px}
.agua{color:var(--agua)}.tierra{color:var(--tierra)}.verde{color:var(--verde)}
table{width:100%;border-collapse:collapse;background:var(--caja);font-size:15px;
      border:1px solid var(--linea);border-radius:12px;overflow:hidden}
th{background:#eef3ef;text-align:left;padding:11px 12px;font-size:13px;
   text-transform:uppercase;letter-spacing:.4px;color:#3d4f45}
td{padding:10px 12px;border-top:1px solid var(--linea)}
td.n,th.n{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
tr:nth-child(even) td{background:#fcfdfc}
tfoot td{font-weight:800;background:#eef3ef;border-top:2px solid var(--verde)}
.barra{height:9px;border-radius:5px;background:#e8eeea;overflow:hidden;min-width:70px}
.barra i{display:block;height:100%;border-radius:5px}
.nota{background:#f2f7fb;border-left:5px solid var(--agua);padding:13px 15px;
      border-radius:0 10px 10px 0;margin:16px 0;font-size:14.5px}
.ojo{background:#fdf6ec;border-left-color:var(--tierra)}
.pie{margin-top:40px;padding-top:14px;border-top:1px solid var(--linea);
     color:var(--suave);font-size:13px}
.chip{display:inline-block;background:#eef3ef;border-radius:20px;padding:3px 11px;
      font-size:13px;margin:2px 3px 2px 0}
/* La tabla nunca debe cortar una cifra: si no cabe, se desplaza. */
.tabla{overflow-x:auto;-webkit-overflow-scrolling:touch}
@media print{body{background:#fff}.hoja{max-width:none;padding:0}
  h2{page-break-after:avoid}table{page-break-inside:avoid}
  .tabla{overflow:visible}}
@media (max-width:620px){.kpi .n{font-size:26px}h1{font-size:23px}
  td,th{padding:7px 5px;font-size:13px}.ocultar-movil{display:none}
  /* el nombre de la comunidad puede partirse; las cifras jamás */
  td:first-child{white-space:normal;min-width:88px}
  th{white-space:normal;font-size:11px;letter-spacing:0}}
"""


def barra(valor, maximo, color):
    pct = 0 if not maximo else max(2, round(100 * valor / maximo))
    return ('<div class="barra"><i style="width:{}%;background:{}"></i></div>'
            .format(pct, color))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--sector', default='Sector 1',
                    help='«Sector 1», «Sector 2», «Sector 3» o «todos»')
    args = ap.parse_args()

    with open(os.path.join(GEO, 'superficie_por_comunidad.json'), encoding='utf-8') as f:
        SUP = json.load(f)
    with open(os.path.join(GEO, 'caudal_por_comunidad.json'), encoding='utf-8') as f:
        CAU = json.load(f)
    with open(os.path.join(GEO, 'auditoria_areas.json'), encoding='utf-8') as f:
        corte = json.load(f)['corte']

    todos = args.sector.lower() == 'todos'
    coms = [c for c in SUP['comunidades'] if todos or c['sector'] == args.sector]
    if not coms:
        print('No hay comunidades en «{}»'.format(args.sector))
        return 1
    coms.sort(key=lambda c: -c['superficie_catastral_ha'])
    titulo_sector = 'todo el sistema' if todos else args.sector.lower()

    tot = {k: sum(c[k] for c in coms) for k in
           ('fichas', 'regantes', 'predios_catastrales',
            'superficie_catastral_ha', 'riego_ajustado_ha')}
    max_area = max(c['superficie_catastral_ha'] for c in coms)
    caudales = CAU['comunidades']

    B = []
    A = B.append
    A('<!-- Informe autocontenido: no necesita internet -->')
    A('<meta charset="utf-8">')
    A('<meta name="viewport" content="width=device-width,initial-scale=1">')
    A('<title>Padrón de riego · {}</title>'.format(args.sector if not todos else 'Sistema'))
    A('<style>{}</style>'.format(CSS))
    A('<div class="hoja">')
    A('<header>')
    A('<h1>El padrón de riego en {}</h1>'.format(
        'nuestras comunidades' if todos else 'el ' + args.sector))
    A('<div class="sub">Sistema de riego comunitario Guanguilquí–Porotog · '
      'Cangahua, Cayambe<br>Información levantada casa por casa hasta el {}</div>'
      .format(fecha_larga(corte)))
    A('</header>')

    # ── las cifras de arriba ──
    A('<div class="grid">')
    A('<div class="kpi"><div class="n verde">{}</div>'
      '<div class="t">familias regantes encuestadas</div></div>'.format(n(tot['regantes'])))
    A('<div class="kpi"><div class="n">{}</div>'
      '<div class="t">terrenos registrados</div></div>'.format(n(tot['predios_catastrales'])))
    A('<div class="kpi"><div class="n tierra">{}</div>'
      '<div class="t">hectáreas en total</div></div>'.format(n(tot['superficie_catastral_ha'])))
    A('<div class="kpi"><div class="n agua">{}</div>'
      '<div class="t">hectáreas que reciben riego</div></div>'.format(n(tot['riego_ajustado_ha'])))
    A('</div>')
    pct_riego = (100 * tot['riego_ajustado_ha'] / tot['superficie_catastral_ha']
                 if tot['superficie_catastral_ha'] else 0)
    A('<p>De cada 100 hectáreas registradas, <b>{:.0f} reciben agua del sistema</b>. '
      'El resto son pastos sin riego, bosque o terreno que no se cultiva.</p>'
      .format(pct_riego))

    # ── tabla por comunidad ──
    A('<h2>Comunidad por comunidad</h2>')
    A('<div class="tabla">')
    A('<table><thead><tr><th>Comunidad</th>'
      '<th class="n">Familias</th><th class="n ocultar-movil">Terrenos</th>'
      '<th class="n">Hectáreas</th><th class="ocultar-movil"></th>'
      '<th class="n"><span class="ocultar-movil">Con </span>Riego</th>'
      '</tr></thead><tbody>')
    for c in coms:
        A('<tr><td><b>{}</b></td>'
          '<td class="n">{}</td><td class="n ocultar-movil">{}</td>'
          '<td class="n">{}</td><td class="ocultar-movil">{}</td>'
          '<td class="n agua">{}</td></tr>'
          .format(c['comunidad'],
                  n(c['regantes']), n(c['predios_catastrales']),
                  n(c['superficie_catastral_ha']),
                  barra(c['superficie_catastral_ha'], max_area, '#c86a1e'),
                  n(c['riego_ajustado_ha'])))
    A('</tbody><tfoot><tr><td>TOTAL</td><td class="n">{}</td>'
      '<td class="n ocultar-movil">{}</td><td class="n">{}</td>'
      '<td class="ocultar-movil"></td><td class="n">{}</td></tr></tfoot></table>'
      .format(n(tot['regantes']), n(tot['predios_catastrales']),
              n(tot['superficie_catastral_ha']), n(tot['riego_ajustado_ha'])))
    A('</div>')

    A('<div class="nota"><b>Cómo se cuentan estas hectáreas.</b> Cada terreno se '
      'cuenta <b>una sola vez</b>, con la medida que tiene en el catastro del '
      'Municipio de Cayambe. Cuando un terreno familiar está a nombre de varios '
      'hermanos y cada uno declaró el terreno completo, aquí aparece una vez y no '
      'varias. Por eso estas cifras pueden ser menores que la suma de lo que cada '
      'familia declaró.</div>')

    # ── el agua ──
    #
    # El caudal NO se publica por comunidad y no es un olvido: en 8 comunidades
    # los técnicos anotaron el caudal que recibe cada familia (0,54 l/s en Comuna
    # Porotog) y en las otras 42 el de la acequia entera (37 l/s en Cochapamba).
    # Puestos en la misma tabla no son comparables, y enseñar «Comuna Porotog:
    # 0,5 l/s» en una asamblea de Comuna Porotog es indefendible. El caudal del
    # sistema completo sí es sólido y se da como cifra única.
    A('<h2>El agua del sistema</h2>')
    A('<p>El sistema entero mueve <b>{} litros por segundo</b>. Ese caudal entra '
      'por las acequias y se reparte por turnos entre las comunidades y, dentro '
      'de cada una, entre las familias regantes.</p>'
      .format(n(CAU['totales']['caudal_sistema_ls'], 0)))
    A('<div class="nota"><b>El caudal de cada comunidad todavía se está '
      'verificando.</b> En unas comunidades se anotó el agua que entra por la '
      'acequia y en otras la que recibe cada familia, y hasta que se unifique el '
      'criterio no se pueden poner una al lado de la otra sin confundir. Se '
      'revisará con cada directiva.</div>')

    # ── cómo va el trabajo ──
    A('<h2>Cómo va el trabajo</h2>')
    # Las dos cifras conviven en el informe (3.409 y 3.092) y se prestan a
    # confusión si no se explica: son fichas levantadas y terrenos distintos.
    A('<p>Se visitó a <b>{}</b> familias regantes y se llenaron <b>{}</b> fichas, '
      'una por cada parcela: muchas familias tienen más de un terreno y cada uno '
      'se levantó por separado. Esas fichas corresponden a <b>{}</b> terrenos '
      'distintos del catastro — hay menos terrenos que fichas porque, cuando '
      'varios hermanos comparten un lote, cada uno llenó su ficha sobre el mismo '
      'terreno.</p>'
      .format(n(tot['regantes']), n(tot['fichas']), n(tot['predios_catastrales'])))
    A('<p>')
    for c in coms:
        A('<span class="chip">{} · {} {}</span>'
          .format(c['comunidad'], n(c['regantes']),
                  'familia' if c['regantes'] == 1 else 'familias'))
    A('</p>')

    A('<div class="nota ojo"><b>Si su comunidad aparece con menos familias de las '
      'que usted conoce</b>, puede ser por dos razones: que algunas familias no '
      'estuvieran el día de la visita, o que estén registradas en otra comunidad '
      'vecina. En la reunión se puede revisar caso por caso: el padrón todavía '
      'admite correcciones.</div>')

    A('<div class="pie">Padrón de usuarios del sistema de riego comunitario '
      'Guanguilquí–Porotog · Prefectura de Pichincha · Consorcio Cayambe SPT<br>'
      'Datos al {} · documento generado el {}</div>'
      .format(fecha_larga(corte), fecha_larga(datetime.now().strftime('%Y-%m-%d'))))
    A('</div>')

    nombre = 'INFORME-COMUNIDADES-{}.html'.format(
        'sistema' if todos else args.sector.replace(' ', '').lower())
    ruta = os.path.join(DOCS, nombre)
    with open(ruta, 'w', encoding='utf-8') as f:
        f.write('\n'.join(B))

    print('=' * 74)
    print(' INFORME PARA LA COMUNIDAD — {}'.format(args.sector))
    print('=' * 74)
    print('  comunidades : {}'.format(len(coms)))
    print('  familias    : {:,}'.format(int(tot['regantes'])))
    print('  terrenos    : {:,}'.format(int(tot['predios_catastrales'])))
    print('  hectáreas   : {:,.2f}  ({:,.2f} con riego)'
          .format(tot['superficie_catastral_ha'], tot['riego_ajustado_ha']))
    print('  archivo     : docs/{}  ({:,.0f} KB)'.format(nombre, os.path.getsize(ruta) / 1024))
    if os.path.isdir(ENTREGA):
        etiqueta = ('todo el sistema' if todos else args.sector)
        destino = os.path.join(
            ENTREGA, '21 - Informe para la comunidad ({}).html'.format(etiqueta))
        with open(ruta, encoding='utf-8') as o, open(destino, 'w', encoding='utf-8') as d:
            d.write(o.read())
        print('  copia       : {}'.format(destino))
    print('=' * 74)
    return 0


if __name__ == '__main__':
    sys.exit(main())
