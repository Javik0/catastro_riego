# -*- coding: utf-8 -*-
"""
Clasifica los 298 predios de «Auditoría de áreas» en dos bandejas, antes de
gastar en revisarlos: los que un script puede cerrar solo, y los que
necesitan criterio (de un agente o de una persona). Solo lectura.

Por qué existe
--------------
El 18-ago-2026 se revisaron 4 predios a mano y salieron 4 patrones distintos:
una familia donde las 5 fichas dan su parte de riego pero no de propiedad
(Asociación Rosalía), un predio con las dos cosas mezcladas —riego y
propiedad— en la misma comunidad (Pitana Alto), un predio donde el dato de una
ficha en realidad habla de *otra* clave catastral (Carrera), y un predio que
ni siquiera es un caso de herencia sino una ficha representativa de un comité
sobre 154 lotes (Promej. Pitana Bajo). Tres subagentes (Sonnet, Opus, Fable)
resolvieron el caso mixto de Pitana Alto correctamente pero gastaron 40-47 mil
tokens cada uno. Sobre 298 predios eso son 9-13 millones de tokens si se
revisan todos con un agente — antes de eso, hay que separar cuáles
verdaderamente lo necesitan.

Qué mide, por predio
---------------------
* **con_numero** — a cuántas fichas `num_del_texto` (la misma función de
  `generar_auditoria_areas.py`) les encuentra un número propio en la
  observación.
* **tipo_dato** — si ese número habla de RIEGO («le corresponde un área de
  riego de…», «solo riega…») o de PROPIEDAD («dueño de…», sin mención de
  riego). Confundir los dos fue el error que un lector automático simple
  cometería en Pitana Alto.
* **cruza_clave** — si la observación menciona otra clave catastral. Pasa en
  Carrera: el número que aparece no es de este predio.
* **es_organizacion** — si el titular de la ficha es un comité, asociación,
  junta o comuna en vez de una persona (regex sobre apellidos/nombres). Pasa
  en Promej. Pitana Bajo.

Las dos bandejas
----------------
**AUTOMATICO** — todas las fichas dan número, todas del mismo tipo (todas
riego o todas propiedad), ninguna cruza a otra clave, ninguna es de una
organización. Con esas condiciones hay una regla fija y documentable:

  - si todas dan PROPIEDAD y suman cerca del polígono → se usan tal cual
  - si todas dan RIEGO (ninguna da propiedad) → se reparte la propiedad en
    partes iguales entre todas, y se conserva el riego que cada una declaró
    (la regla de Asociación Rosalía)

**AGENTE** — todo lo demás: alguna ficha sin observación, tipos mezclados
(riego y propiedad en el mismo predio), alguna referencia cruzada, alguna
ficha de organización, o números que num_del_texto no pudo leer. Estos son
los que de verdad necesitan comprensión de lectura, no una fórmula.

Este script NO escribe nada ni corrige nada — solo separa y cuenta, para
decidir cuántos predios (y cuántos tokens) requiere cada bandeja antes de
lanzar cualquier corrección.

Uso
---
    "C:\\OSGeo4W\\bin\\python-qgis.bat" -X utf8 scripts/clasificar_predios_exceso.py
"""
import os
import re
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from generar_auditoria_areas import (  # noqa: E402
    cargar_catastro, num_del_texto, TOLERANCIA_M2,
)

GPKG = os.path.join(os.path.expanduser('~'), 'QField', 'cloud',
                    'porotog_levantamiento_offline', 'data.gpkg')

RIEGO_KW = re.compile(
    r'\bRIEGO\b|\bREGAD?\w*\b', re.IGNORECASE)
PROPIEDAD_KW = re.compile(
    r'DUE[NÑ][AO]|PROPIETARI[OA]|PROPIEDAD|LOTE\s+ASIGNAD', re.IGNORECASE)
CLAVE_KW = re.compile(
    r'CLAVE\s*(?:CATASTRAL)?\s*[:\-]?\s*(\d{8,15})', re.IGNORECASE)
ORG_KW = re.compile(
    r'\bCOMIT[EÉ]\b|\bASOCIACI[OÓ]N\b|\bJUNTA\b|\bCOMUNA\b|\bCONSORCIO\b|'
    r'\bCOOPERATIVA\b|\bFUNDACI[OÓ]N\b|\bORGANIZACI[OÓ]N\b', re.IGNORECASE)


def tabla(cur, clave):
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    for (t,) in cur.fetchall():
        if clave in t and not any(x in t for x in ('rtree_', 'log_', 'gpkg_')):
            return t
    raise SystemExit('No se encontró la tabla %s' % clave)


def tipo_de(obs, num_pos):
    """RIEGO, PROPIEDAD, o AMBIGUO, según qué palabra está más cerca del número."""
    riego_m = list(RIEGO_KW.finditer(obs))
    prop_m = list(PROPIEDAD_KW.finditer(obs))
    if not riego_m and not prop_m:
        return 'AMBIGUO'
    d_riego = min((abs(m.start() - num_pos) for m in riego_m), default=10**9)
    d_prop = min((abs(m.start() - num_pos) for m in prop_m), default=10**9)
    if d_riego < d_prop:
        return 'RIEGO'
    if d_prop < d_riego:
        return 'PROPIEDAD'
    return 'AMBIGUO'


def main():
    areas_cat, _ = cargar_catastro()
    print('  catastro: {:,} predios con área'.format(len(areas_cat)))

    con = sqlite3.connect(GPKG)
    cur = con.cursor()
    t_fic = tabla(cur, 'Fichas_Predios')
    cur.execute('SELECT clave_catastral, apellidos, nombres, area_total, '
                'observaciones FROM "{}"'.format(t_fic))
    filas = cur.fetchall()
    con.close()

    por_clave = {}
    for clave, ape, nom, area, obs in filas:
        clave = (clave or '').strip()
        if not clave or clave not in areas_cat:
            continue
        por_clave.setdefault(clave, []).append({
            'ape': ape or '', 'nom': nom or '',
            'area': area or 0, 'obs': (obs or '').strip(),
        })

    automatico, agente = [], []
    for clave, fichas in por_clave.items():
        pol = areas_cat[clave]
        dec = sum(f['area'] for f in fichas)
        exceso = dec - pol
        if not (len(fichas) > 1 and exceso > TOLERANCIA_M2):
            continue  # no es un caso 'exceso' (mismo filtro que la pantalla)

        analizadas = []
        for f in fichas:
            es_org = bool(ORG_KW.search(f['ape']) or ORG_KW.search(f['nom']))
            cruza = None
            m_clave = CLAVE_KW.search(f['obs'])
            if m_clave and m_clave.group(1) != clave:
                cruza = m_clave.group(1)
            num = num_del_texto(f['obs']) if f['obs'] and not cruza else None
            tipo = None
            if num is not None:
                m = re.search(re.escape(str(int(num))), f['obs'])
                pos = m.start() if m else 0
                tipo = tipo_de(f['obs'].upper(), pos)
            analizadas.append({**f, 'es_org': es_org, 'cruza': cruza,
                               'num': num, 'tipo': tipo})

        n = len(analizadas)
        con_num = [a for a in analizadas if a['num'] is not None]
        tipos = set(a['tipo'] for a in con_num)
        hay_org = any(a['es_org'] for a in analizadas)
        hay_cruce = any(a['cruza'] for a in analizadas)
        todas_tienen_num = len(con_num) == n
        tipo_unico = len(tipos - {'AMBIGUO'}) <= 1 and 'AMBIGUO' not in tipos

        caso = {'clave': clave, 'nf': n, 'pol': pol, 'exc': exceso,
                'fichas': analizadas}

        cero_numeros = len(con_num) == 0

        if todas_tienen_num and tipo_unico and not hay_org and not hay_cruce:
            caso['bandeja'] = 'AUTOMATICO'
            automatico.append(caso)
        elif cero_numeros and not hay_org and not hay_cruce:
            # nadie anotó nada: no hay texto que interpretar, es reparto por
            # defecto — no se gana nada mandándolo a un agente
            caso['bandeja'] = 'SIN_DATO'
            caso['razon'] = 'ninguna ficha dio un número'
            agente.append(caso)
        else:
            razon = []
            if not todas_tienen_num and not cero_numeros:
                razon.append('{} de {} sin número'.format(n - len(con_num), n))
            if not tipo_unico:
                razon.append('mezcla riego/propiedad')
            if hay_org:
                razon.append('ficha de organización')
            if hay_cruce:
                razon.append('cruza a otra clave')
            caso['razon'] = ', '.join(razon) or 'sin número legible'
            caso['bandeja'] = 'AGENTE'
            agente.append(caso)

    sin_dato = [c for c in agente if c['bandeja'] == 'SIN_DATO']
    genuino = [c for c in agente if c['bandeja'] == 'AGENTE']

    print('\n' + '=' * 78)
    print(' RESULTADO')
    print('=' * 78)
    total = len(automatico) + len(agente)
    print('  Total predios con exceso (mismo filtro que /auditoria-areas): {}'
          .format(total))
    print('  AUTOMATICO  (regla fija, sin agente, sin costo)   : {}'.format(len(automatico)))
    print('  SIN_DATO    (nadie anotó nada, reparto por defecto): {}'.format(len(sin_dato)))
    print('  AGENTE      (mezcla de datos, necesita criterio)   : {}'.format(len(genuino)))
    n_fichas_agente = sum(c['nf'] for c in genuino)
    print('\n  Fichas totales en la bandeja AGENTE: {} (sobre {} predios)'
          .format(n_fichas_agente, len(genuino)))

    print('\n' + '-' * 78)
    print(' Ejemplos AUTOMATICO (primeros 8)')
    print('-' * 78)
    for c in automatico[:8]:
        tipos_vistos = set(a['tipo'] for a in c['fichas'] if a['num'] is not None)
        print('  {}  {} fichas  exceso {:,.0f} m²  tipo: {}'.format(
            c['clave'], c['nf'], c['exc'], '/'.join(tipos_vistos)))

    print('\n' + '-' * 78)
    print(' Motivos en la bandeja AGENTE (conteo, solo bandeja genuina)')
    print('-' * 78)
    from collections import Counter
    motivos = Counter()
    for c in genuino:
        for parte in c['razon'].split(', '):
            key = re.sub(r'\d+ de \d+ ', '', parte)
            motivos[key] += 1
    for motivo, n in motivos.most_common():
        print('  {:<28} {}'.format(motivo, n))

    print('\n' + '-' * 78)
    print(' Ejemplos AGENTE genuino (primeros 10, con el motivo)')
    print('-' * 78)
    for c in genuino[:10]:
        print('  {}  {} fichas  exceso {:,.0f} m²  ->  {}'.format(
            c['clave'], c['nf'], c['exc'], c['razon']))

    print('\n' + '-' * 78)
    print(' Ejemplos SIN_DATO (primeros 5)')
    print('-' * 78)
    for c in sin_dato[:5]:
        print('  {}  {} fichas  exceso {:,.0f} m²'.format(c['clave'], c['nf'], c['exc']))


if __name__ == '__main__':
    main()
