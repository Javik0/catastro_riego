# -*- coding: utf-8 -*-
"""
Clasifica las fichas cuyas OBSERVACIONES contienen una clave catastral.

CONTEXTO
--------
Antes de que el formulario de QField tuviera la casilla "Es Ficha Hija", el
técnico no podía vincular un predio adicional, así que anotaba la clave
catastral (y a veces la cédula) en el campo de observaciones. Esas fichas hay
que rescatarlas: crear la ficha adicional y vincularla a su regante.

Este script NO ESCRIBE NADA. Solo lee el data.gpkg y produce un informe .md
para que los técnicos y JAVIKO decidan caso por caso. La escritura es un paso
aparte, en ventana coordinada, y solo con los casos aprobados.

CRITERIOS
---------
Una clave del catastro RURAL tiene 13 dígitos (1702521020109) y una del URBANO
23 (17025501500600900010000). Una racha de 10 dígitos es una CÉDULA: los
técnicos la anotaban para identificar al regante principal, así que se resuelve
contra las fichas y se muestra como pista.

Cada clave encontrada se clasifica:

  VINCULABLE  la clave tiene 13 dígitos, existe en el catastro, NO tiene ya una
              ficha propia, y la observación menciona una sola clave
  DUPLICADA   la clave ya tiene ficha levantada: no hay que crear nada, quizá
              solo vincularla como adicional
  DUDOSA      varias claves en la misma observación, o texto ambiguo: necesita
              criterio humano
  INVALIDA    la clave no tiene 13 dígitos (truncada) o no existe en el catastro

Uso:  python scripts/analizar_observaciones_con_clave.py
"""

import os
import re
import sqlite3
from collections import Counter

QFIELD = r"C:\Users\HP\QField\cloud\porotog_levantamiento_offline"
GPKG = os.path.join(QFIELD, 'data.gpkg')
T_FICHAS = 'Fichas_Predios_880eb10d_d887_4fc6_99a2_8af3ac63877e'

# El catastro vive en archivos aparte, no en data.gpkg (rural 24.460 predios +
# urbano 6.518). Se usan para saber si una clave anotada existe de verdad.
CATASTROS = [
    (os.path.join(QFIELD, 'CATASTROACTUALIZADORURALCATASTRORURALACTUALIZADO.gpkg'),
     'CATASTROACTUALIZADORURALCATASTRORURALACTUALIZADO', 'clave_cata'),
    (os.path.join(QFIELD, 'CATASTROURBANOUNIDO.gpkg'),
     'CATASTROURBANOUNIDO', 'pre_codigo'),
]
SALIDA = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                      '..', 'docs', 'REVISION-observaciones-con-clave.md')

# Frases que indican que la observación NO habla de un predio adicional del
# mismo regante, sino de otra cosa (linderos, terceros, aclaraciones).
RUIDO = ('vecin', 'colind', 'linder', 'hermano', 'herman', 'fallec', 'difunt',
         'vendi', 'vendió', 'compr', 'no es', 'error', 'duplic')


def numeros(txt):
    """Rachas de 10 o más dígitos: pueden ser claves (13) o cédulas (10)."""
    return re.findall(r'\d{10,}', (txt or '').replace('.', '').replace('-', ''))


# El catastro RURAL usa claves de 13 dígitos y el URBANO de 23. Hay que probar
# las dos: si solo se buscan las de 13, los predios urbanos se descartan como
# "clave inválida" cuando en realidad existen.
LARGOS_CLAVE = (23, 13)


def separar(racha, claves_catastro):
    """Parte una racha larga en las claves catastrales que contenga.

    Los técnicos escriben la clave y la cédula pegadas, o dos claves seguidas,
    y quedan rachas de 20+ dígitos. Se prueban todas las ventanas de 23 y 13
    dígitos y se aceptan solo las que existen en el catastro: si no existe, no
    se inventa. Se prueba primero 23 para no partir una urbana en trozos.
    """
    if len(racha) in LARGOS_CLAVE and racha in claves_catastro:
        return [racha], False
    hallazgos, i = [], 0
    while i < len(racha):
        for n in LARGOS_CLAVE:
            v = racha[i:i + n]
            if len(v) == n and v in claves_catastro:
                hallazgos.append(v)
                i += n
                break
        else:
            i += 1
    return hallazgos, not hallazgos


def main():
    con = sqlite3.connect(GPKG)
    cur = con.cursor()

    # catastro: todas las claves que existen como polígono
    claves_catastro = set()
    for ruta, tabla, campo in CATASTROS:
        if not os.path.exists(ruta):
            print(f"  [aviso] falta {os.path.basename(ruta)}: no se validará contra el catastro")
            continue
        c2 = sqlite3.connect(ruta)
        c2.text_factory = bytes
        cur2 = c2.cursor()
        cur2.execute(f'SELECT "{campo}" FROM "{tabla}"')
        for (v,) in cur2.fetchall():
            if v:
                claves_catastro.add(v.decode('utf-8', 'ignore').strip()
                                    if isinstance(v, bytes) else str(v).strip())
        c2.close()
    print(f"  catastro: {len(claves_catastro):,} claves de referencia")

    cur.execute(f'''SELECT id, codigo_final, apellidos, nombres, cedula,
                           comunidad, clave_catastral, observaciones,
                           creado_por, es_ficha_hija, ficha_madre_id
                    FROM "{T_FICHAS}"
                    WHERE observaciones IS NOT NULL AND trim(observaciones) != ''
                 ''')
    filas = cur.fetchall()

    cur.execute(f'SELECT clave_catastral FROM "{T_FICHAS}" WHERE clave_catastral IS NOT NULL')
    con_ficha = Counter(str(r[0]).strip() for r in cur.fetchall())
    con.close()

    # cédula -> regante, para resolver las cédulas anotadas en observaciones
    cur2 = sqlite3.connect(GPKG).cursor()
    cur2.execute(f'''SELECT cedula, apellidos, nombres FROM "{T_FICHAS}"
                     WHERE cedula IS NOT NULL AND es_ficha_hija IS NOT 1''')
    por_cedula = {str(c).strip(): f"{a or ''} {n or ''}".strip()
                  for c, a, n in cur2.fetchall() if c}

    grupos = {'VINCULABLE': [], 'DUPLICADA': [], 'DUDOSA': [], 'INVALIDA': []}

    for (fid, cod, ape, nom, ced, com, clave_propia, obs,
         creado, es_hija, madre) in filas:
        rachas = [c for c in numeros(obs) if c != (clave_propia or '').strip()]
        if not rachas:
            continue

        regante = f"{ape or ''} {nom or ''}".strip()
        obs_low = (obs or '').lower()
        ruidosa = any(p in obs_low for p in RUIDO)

        # Una racha de 10 dígitos es una CÉDULA, no una clave: los técnicos la
        # anotaban para identificar al regante principal. Se resuelve aparte.
        cedulas = [r for r in rachas if len(r) == 10]
        pistas = []
        for c in cedulas:
            quien = por_cedula.get(c)
            pistas.append(f'CI {c}' + (f' = {quien}' if quien else ' (sin ficha)'))

        claves, sin_resolver = [], []
        for r in (x for x in rachas if len(x) != 10):
            hall, falla = separar(r, claves_catastro)
            claves += hall
            if falla:
                sin_resolver.append(r)

        claves = list(dict.fromkeys(claves))
        base = {
            'ficha_id': fid, 'codigo': cod, 'regante': regante,
            'cedula': ced, 'comunidad': com, 'clave_propia': clave_propia,
            'obs': ' '.join((obs or '').split()), 'creado_por': creado,
            'ya_es_hija': bool(es_hija), 'pistas': ' · '.join(pistas),
        }

        for racha in sin_resolver:
            grupos['INVALIDA'].append(dict(
                base, clave_obs=racha,
                motivo=f'{len(racha)} dígitos sin ninguna clave válida dentro'))

        for clave in claves:
            caso = dict(base, clave_obs=clave)
            if con_ficha.get(clave):
                caso['motivo'] = f'ya tiene {con_ficha[clave]} ficha(s) levantada(s)'
                grupos['DUPLICADA'].append(caso)
            elif len(claves) > 1 or ruidosa:
                caso['motivo'] = ('la observación menciona varias claves'
                                  if len(claves) > 1
                                  else 'el texto sugiere que no es un predio del mismo regante')
                grupos['DUDOSA'].append(caso)
            else:
                caso['motivo'] = 'clave válida, sin ficha, observación clara'
                grupos['VINCULABLE'].append(caso)

        # cédula anotada pero ninguna clave: igual sirve para vincular a mano
        if pistas and not claves and not sin_resolver:
            grupos['DUDOSA'].append(dict(
                base, clave_obs='—',
                motivo='solo se anotó la cédula del regante, sin clave del predio'))

    # ── informe ──
    L = []
    L.append('# Observaciones con clave catastral — revisión')
    L.append('')
    L.append('Fichas donde el técnico anotó una clave catastral en el campo de')
    L.append('observaciones, porque el formulario de QField todavía no tenía la casilla')
    L.append('para marcar un predio adicional. **Este informe no modifica nada**: sirve')
    L.append('para decidir cuáles se convierten en ficha adicional vinculada a su regante.')
    L.append('')
    L.append(f'Generado desde `data.gpkg` · {sum(len(v) for v in grupos.values())} claves '
             f'encontradas en {len(filas):,} fichas con observaciones.')
    L.append('')
    L.append('| Grupo | Claves | Qué hacer |')
    L.append('|---|---|---|')
    L.append(f'| Vinculables | {len(grupos["VINCULABLE"])} | crear la ficha adicional y vincularla |')
    L.append(f'| Ya existentes | {len(grupos["DUPLICADA"])} | no crear nada; revisar si hay que vincularla |')
    L.append(f'| Dudosas | {len(grupos["DUDOSA"])} | **decide el técnico** |')
    L.append(f'| Inválidas | {len(grupos["INVALIDA"])} | clave truncada o inexistente; volver a campo |')
    L.append('')

    titulos = {
        'VINCULABLE': ('Vinculables — listas para crear',
                       'La clave existe en el catastro, no tiene ficha propia y la '
                       'observación menciona una sola clave.'),
        'DUPLICADA': ('Ya tienen ficha levantada',
                      'El predio ya está registrado. No hay que crear nada: como mucho, '
                      'marcar esa ficha como adicional del regante que la declaró.'),
        'DUDOSA': ('Dudosas — requieren criterio del técnico',
                   'Varias claves en la misma observación, o el texto sugiere que se '
                   'habla de un vecino, un lindero o una aclaración, no de otro predio '
                   'del mismo regante.'),
        'INVALIDA': ('Inválidas — clave truncada o inexistente',
                     'No se puede resolver desde la oficina: hay que confirmar la clave '
                     'en campo.'),
    }

    for g in ('VINCULABLE', 'DUPLICADA', 'DUDOSA', 'INVALIDA'):
        titulo, ayuda = titulos[g]
        L.append(f'## {titulo} ({len(grupos[g])})')
        L.append('')
        L.append(ayuda)
        L.append('')
        if not grupos[g]:
            L.append('_Ninguna._')
            L.append('')
            continue
        L.append('| # | Regante | Comunidad | Clave en observaciones | Pista de cédula | Motivo | Observación |')
        L.append('|---|---|---|---|---|---|---|')
        for i, c in enumerate(sorted(grupos[g], key=lambda x: (x['comunidad'] or '', x['regante'])), 1):
            obs = c['obs'][:150].replace('|', '/')
            L.append('| {} | {} | {} | `{}` | {} | {} | {} |'.format(
                i, c['regante'][:34] or '—', (c['comunidad'] or '—')[:24],
                c['clave_obs'], c['pistas'] or '—', c['motivo'], obs))
        L.append('')

    os.makedirs(os.path.dirname(os.path.abspath(SALIDA)), exist_ok=True)
    with open(os.path.abspath(SALIDA), 'w', encoding='utf-8') as f:
        f.write('\n'.join(L))

    print(f"  claves encontradas: {sum(len(v) for v in grupos.values())}")
    for g in ('VINCULABLE', 'DUPLICADA', 'DUDOSA', 'INVALIDA'):
        print(f"     {g:<12} {len(grupos[g]):>4}")
    print(f"\n  informe: {os.path.abspath(SALIDA)}")


if __name__ == '__main__':
    main()
