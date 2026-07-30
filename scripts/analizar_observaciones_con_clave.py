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

  VINCULABLE  la clave existe en el catastro, NO tiene ya una ficha propia, y
              la observación menciona una sola clave
  MARCABLE    el predio ya tiene ficha Y es del MISMO regante que lo declaró:
              basta marcar esa ficha como adicional, sin crear nada
  DE_TERCERO  el predio ya tiene ficha pero es de OTRA persona (o de la comuna).
              NO se marca: el regante suele estar señalando el predio comunal
              donde tiene su lote, no un predio suyo. Atribuírselo sería un error
  DUDOSA      varias claves en la misma observación, o texto ambiguo: necesita
              criterio humano
  INVALIDA    la clave está truncada o no existe en el catastro

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

    # Quién es el dueño de cada predio ya levantado: hace falta para saber si el
    # regante está declarando un predio SUYO o señalando el de un tercero.
    cur.execute(f'''SELECT clave_catastral, apellidos, nombres, cedula
                    FROM "{T_FICHAS}" WHERE clave_catastral IS NOT NULL''')
    duenos = {}
    con_ficha = Counter()
    for clave, ape, nom, ced in cur.fetchall():
        k = str(clave).strip()
        con_ficha[k] += 1
        duenos.setdefault(k, []).append((f"{ape or ''} {nom or ''}".strip(), (ced or '').strip()))
    con.close()

    def mismo_regante(clave, regante, cedula):
        """¿El predio ya levantado es de quien lo declaró en observaciones?"""
        r = ' '.join((regante or '').upper().split())
        for dueno, ced in duenos.get(clave, []):
            if (cedula and ced and ced == cedula) or ' '.join(dueno.upper().split()) == r:
                return True, dueno
        return False, (duenos.get(clave, [('—', '')])[0][0])

    # cédula -> regante, para resolver las cédulas anotadas en observaciones
    cur2 = sqlite3.connect(GPKG).cursor()
    cur2.execute(f'''SELECT cedula, apellidos, nombres FROM "{T_FICHAS}"
                     WHERE cedula IS NOT NULL AND es_ficha_hija IS NOT 1''')
    por_cedula = {str(c).strip(): f"{a or ''} {n or ''}".strip()
                  for c, a, n in cur2.fetchall() if c}

    grupos = {'VINCULABLE': [], 'MARCABLE': [], 'DE_TERCERO': [],
              'DUDOSA': [], 'INVALIDA': []}

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
                propio, dueno = mismo_regante(clave, regante, (ced or '').strip())
                caso['dueno'] = dueno
                if propio:
                    caso['motivo'] = 'ya levantado y ES del mismo regante'
                    grupos['MARCABLE'].append(caso)
                else:
                    caso['motivo'] = f'ya levantado, pero es de: {dueno[:34]}'
                    grupos['DE_TERCERO'].append(caso)
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
    ORDEN = ('VINCULABLE', 'MARCABLE', 'DUDOSA', 'DE_TERCERO', 'INVALIDA')
    total = sum(len(v) for v in grupos.values())
    tecnicos = sorted({c['creado_por'] for g in grupos.values() for c in g if c['creado_por']})

    L = []
    L.append('# Predios anotados en observaciones — revisión de campo')
    L.append('')
    L.append('## Por qué existe esta lista')
    L.append('')
    L.append('Cuando un regante mencionaba **otro predio suyo**, el formulario de QField')
    L.append('todavía no tenía la casilla para registrarlo como predio adicional. Los')
    L.append('técnicos hicieron lo correcto: anotaron la clave catastral (y a veces la')
    L.append('cédula) en el campo de **observaciones** para no perder el dato.')
    L.append('')
    L.append('Ahora el formulario ya tiene la pestaña **➕ PREDIO ADICIONAL**, así que esos')
    L.append('casos se pueden regularizar. Esta lista dice qué hacer con cada uno.')
    L.append('')
    L.append(f'`{total}` claves encontradas en `{len(filas):,}` fichas con observaciones · '
             f'{len(tecnicos)} técnicos involucrados.')
    L.append('')
    L.append('## Resumen')
    L.append('')
    L.append('| Grupo | Casos | Quién lo resuelve | Acción |')
    L.append('|---|---|---|---|')
    L.append(f'| 1. Crear la ficha | {len(grupos["VINCULABLE"])} | **técnico en campo** | levantar el predio y vincularlo al regante |')
    L.append(f'| 2. Solo marcar | {len(grupos["MARCABLE"])} | oficina | la ficha ya existe y es del mismo regante |')
    L.append(f'| 3. Revisar | {len(grupos["DUDOSA"])} | **técnico en campo** | el texto no deja claro qué es |')
    L.append(f'| 4. No tocar | {len(grupos["DE_TERCERO"])} | — | el predio es de otra persona o de la comuna |')
    L.append(f'| 5. Confirmar clave | {len(grupos["INVALIDA"])} | **técnico en campo** | la clave está mal escrita |')
    L.append('')
    L.append('> **Importante para el grupo 4:** cuando el regante señala un predio que ya')
    L.append('> está a nombre de otra persona o de la comuna, casi siempre está indicando')
    L.append('> *dónde está su lote dentro de ese predio*, no que el predio sea suyo. No')
    L.append('> hay que marcarlo como predio adicional: se le atribuiría el predio entero.')
    L.append('')
    L.append('## Cómo registrar un predio adicional')
    L.append('')
    L.append('1. Crear la ficha **sobre el predio nuevo**, no sobre el del regante principal.')
    L.append('2. Abrir la pestaña **➕ PREDIO ADICIONAL** y marcar **¿Es Ficha Hija?**.')
    L.append('3. En **ID de Ficha Madre**, elegir al regante (se busca por apellido o cédula).')
    L.append('4. Dejar el estado en **⚪ Pendiente Producción (S4)** si los cultivos se levantan después.')
    L.append('')
    L.append('El instructivo completo está en `instructivo-ficha-adicional.html`.')
    L.append('')

    titulos = {
        'VINCULABLE': ('1. Crear la ficha del predio',
                       'La clave existe en el catastro, nadie la ha levantado y la '
                       'observación menciona un solo predio. **Hay que ir a campo**, '
                       'levantar la ficha y vincularla al regante que aparece aquí.'),
        'MARCABLE': ('2. Solo marcar — ya está levantado y es del mismo regante',
                     'El predio ya tiene ficha y está a nombre de la misma persona que lo '
                     'declaró. No hay que ir a campo: basta marcar esa ficha como adicional '
                     'y vincularla. Lo hace la oficina.'),
        'DUDOSA': ('3. Revisar con el regante',
                   'La observación menciona varias claves, o el texto habla de herederos, '
                   'linderos o vecinos. **El técnico decide** si corresponde crear un predio '
                   'adicional y a nombre de quién.'),
        'DE_TERCERO': ('4. No tocar — el predio es de otra persona',
                       'El predio ya está levantado a nombre de alguien más (a menudo la '
                       'comuna). El regante lo anotó como referencia de dónde está su lote. '
                       '**No marcar como predio adicional.** Se listan solo para dejar '
                       'constancia de que se revisaron.'),
        'INVALIDA': ('5. Confirmar la clave en campo',
                     'La clave anotada no existe en el catastro o está incompleta. No se '
                     'puede resolver desde la oficina: hay que verificarla con el regante.'),
    }

    for g in ORDEN:
        titulo, ayuda = titulos[g]
        L.append(f'## {titulo}  ({len(grupos[g])})')
        L.append('')
        L.append(ayuda)
        L.append('')
        if not grupos[g]:
            L.append('_Ninguno._')
            L.append('')
            continue

        # Agrupado por comunidad: así el técnico recorre una comunidad a la vez
        por_com = {}
        for c in grupos[g]:
            por_com.setdefault(c['comunidad'] or '(sin comunidad)', []).append(c)

        for com in sorted(por_com):
            casos = sorted(por_com[com], key=lambda x: x['regante'])
            L.append(f'### {com}  ({len(casos)})')
            L.append('')
            if g == 'DE_TERCERO':
                L.append('| # | Regante que lo anotó | Clave | Está a nombre de | Observación |')
                L.append('|---|---|---|---|---|')
                for i, c in enumerate(casos, 1):
                    L.append('| {} | {} | `{}` | {} | {} |'.format(
                        i, c['regante'][:32] or '—', c['clave_obs'],
                        (c.get('dueno') or '—')[:32], c['obs'][:110].replace('|', '/')))
            else:
                L.append('| # | Regante principal | Cédula | Clave del predio | Pista | Observación del técnico | ✔ |')
                L.append('|---|---|---|---|---|---|---|')
                for i, c in enumerate(casos, 1):
                    L.append('| {} | {} | {} | `{}` | {} | {} | ☐ |'.format(
                        i, c['regante'][:32] or '—', c['cedula'] or '—',
                        c['clave_obs'], c['pistas'] or '—',
                        c['obs'][:130].replace('|', '/')))
            L.append('')

    L.append('---')
    L.append('')
    L.append('_Padrón de Usuarios · Sistema de Riego Comunitario Guanguilquí–Porotog_  ')
    L.append('_Marca la casilla ☐ de cada fila cuando la resuelvas._')

    os.makedirs(os.path.dirname(os.path.abspath(SALIDA)), exist_ok=True)
    with open(os.path.abspath(SALIDA), 'w', encoding='utf-8') as f:
        f.write('\n'.join(L))

    print(f"  claves encontradas: {sum(len(v) for v in grupos.values())}")
    for g in ORDEN:
        print(f"     {g:<12} {len(grupos[g]):>4}")
    print(f"\n  informe: {os.path.abspath(SALIDA)}")


if __name__ == '__main__':
    main()
