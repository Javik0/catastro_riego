# -*- coding: utf-8 -*-
"""
Informe por Sector de Investigación — material del sociólogo del proyecto.

QUÉ ES
------
El hermano del informe por comunidad (`generar_informe_sociologo.py`): UN solo
documento que reproduce LOS GRÁFICOS DEL DASHBOARD de la aplicación web —«los
gráficos del Dashboard van muy bien en el informe», dijo el cliente— tal como
se ven con el filtro de sector puesto, para el sistema completo y para cada
sector de investigación (Sector 1, 2 y 3). Encargo de JAVIKO, 31-ago-2026.

Los 10 gráficos reproducidos (mismos títulos, colores, universos y redondeos
que `src/components/dashboard/DashboardHome.tsx`):

  1. Uso del Suelo: Con Riego vs Sin Riego (ha)
  2. Especies Pecuarias Principales (Cabezas)
  3. Destino de la Producción Agrícola
  4. Nivel de Instrucción
  5. Hijos por Familia
  6. Represa y Capacitación
  7. Método de Riego (promedio %)
  8. Cultivos Más Frecuentes
  9. Tenencia del Predio
 10. Fichas por Parroquia

«Fichas por Técnico» y «Fichas Investigadas por Día» NO van: son seguimiento
interno del equipo (el Dashboard ya los restringe a admin/tecnico) y el
contratante ve el padrón, no cómo se repartió el trabajo.

DECISIONES DE JAVIKO (31-ago-2026) QUE ESTE SCRIPT APLICA
---------------------------------------------------------
· «Uso del Suelo» usa la medición CATASTRAL de las comunidades del sector,
  igual que la web con el filtro puesto, y lo etiqueta así. La superficie
  DECLARADA sigue siendo el universo de la narrativa (regla 12: las dos
  familias se citan, nunca se suman ni se mezclan sin nombre).
· La granja avícola de Asociación Rosalía (registros de ≥10.000 aves por
  titular sobre el mismo predio) se EXCLUYE del gráfico pecuario, con nota.
  El Dashboard web no la excluye: en el sector de Rosalía el gráfico difiere
  de la web a propósito, y la nota lo dice.
· El documento lleva un capítulo «Todo el sistema» (los mismos gráficos sin
  filtro) antes de los tres sectores.
· ASOCIACIÓN ROSALÍA cuenta en el SECTOR 3, como la web y como el catálogo de
  `constants.ts` («en campo son del Sector 3»). El bloque `sectores` de
  superficie_por_comunidad.json todavía la cuenta en el Sector 2 — bug
  heredado de la lista duplicada de generar_capas_sectores_comunidades.py,
  REPORTADO y pendiente de corregir allí; este script NO lo replica y avisa
  en consola de la diferencia esperada (47 fichas / 36,97 ha entre S2 y S3).

REGLAS DURAS DEL PROYECTO QUE ESTE SCRIPT RESPETA
-------------------------------------------------
· Regla 3: el caudal NO se suma ficha a ficha (fuente única
  caudal_por_comunidad.json; los heredados se muestran y no se suman).
· Regla 4: el nombre de comunidad se canoniza SOLO con comunidades_canon.py.
· Regla 6: personas ≠ predios. Instrucción, hijos, represa/capacitación y
  TENENCIA salen SOLO de fichas principales. (El gráfico de tenencia del
  Dashboard cuenta todas las fichas; aquí manda la regla 6 y la nota al pie
  documenta la diferencia con la web.)
· Regla 9: «sin riego», nunca «secano».
· Regla 12: superficie catastral y declarada no se mezclan; cada gráfico y
  cada cifra nombra su familia.
· Las fichas hijas PENDIENTES se excluyen (hoy 0; se filtran igual).
· NO se toca el data.gpkg: todo se lee de los GeoJSON de public/geo/.
· FECHA_CORTE editorial compartida: «19 de agosto de 2026».

SALIDAS
-------
  docs/INFORME-SOCIOLOGO-por-sector.html       documento imprimible (estilo casa)
  docs/INFORME-SOCIOLOGO-por-sector.md         fuente Markdown (para md_a_docx.py)
  docs/graficos-sociologo/*.png|.jpg           gráficos y mapas para el Word
  build_entrega/Informe_Sociologo_Sectores.xlsx  matrices crudas por gráfico

USO
---
  python -X utf8 scripts/generar_informe_sociologo_sector.py
  python scripts/md_a_docx.py docs/INFORME-SOCIOLOGO-por-sector.md

Se corre con el Python del PATH (C:\\Python314): nada de aquí lee el data.gpkg.
"""

import base64
import os
import statistics as st
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import informe_estilo as E  # noqa: E402
# El motor de agregación y los mapas satelitales son los del informe por
# comunidad: aquí no se recalcula nada que ya exista allá.
from generar_informe_sociologo import (  # noqa: E402
    BASE, DIR_MAPAS, FECHA_CORTE, GRANJA_AVICOLA_MIN,
    agregar_todo, f0, f1, f2, generar_mapas, lleno, num, pct,
)

HTML_OUT = os.path.join(BASE, 'docs', 'INFORME-SOCIOLOGO-por-sector.html')
MD_OUT = os.path.join(BASE, 'docs', 'INFORME-SOCIOLOGO-por-sector.md')
XLSX_OUT = os.path.join(BASE, 'build_entrega', 'Informe_Sociologo_Sectores.xlsx')
# Carpeta (relativa a docs/) con los PNG de los gráficos y los JPG de los
# mapas: el HTML los lleva embebidos en base64, pero el Markdown —y por tanto
# el Word— necesita archivos a los que apuntar.
DIR_GRAF = 'graficos-sociologo'

SECTORES = ('Sector 1', 'Sector 2', 'Sector 3')

# Los mismos cortes del informe por comunidad y del reporte «Terrenos por
# rango de superficie»: se importan para que las tres salidas no se separen.
from generar_informe_sociologo import RANGOS_PREDIO  # noqa: E402

# La paleta del Dashboard y la escala de instrucción viven en
# informe_graficos.py (compartidas con los capítulos).
from informe_graficos import (  # noqa: E402
    COLORES_INSTRUCCION, NIVELES_INSTRUCCION, PIE_COLORS,
)

NOTA_UNIV_TODAS = 'Todas las fichas del corte (cada ficha es un predio).'
NOTA_UNIV_PRI = 'Fichas principales (una por titular entrevistado).'


def es_hija(p):
    return p.get('es_ficha_hija') == 1


def fnum(n):
    """Números al estilo es-EC de la web: punto de miles, coma decimal."""
    return f0(n)


# ─── Los datos de cada gráfico, calcados de DashboardHome.tsx ────────────────

# Superficie catastral por clave de predio, para el gráfico de tamaños que
# pidió el sociólogo (2-sep-2026). Se carga una vez; el predio se asigna a la
# comunidad de SU FICHA, no a la etiqueta del catastro municipal (ese campo
# trae 767 valores propios del GADM y agrupar por él vacía comunidades).
_AREA_POR_CLAVE = None


def area_por_clave():
    global _AREA_POR_CLAVE
    if _AREA_POR_CLAVE is None:
        import json as _json
        ruta = os.path.join(BASE, 'public', 'geo', 'catastro_geo.geojson')
        with open(ruta, encoding='utf-8') as f:
            _AREA_POR_CLAVE = {
                str(x['properties'].get('clave_cata') or '').strip():
                    x['properties'].get('area_predi') or 0
                for x in _json.load(f)['features']
                if str(x['properties'].get('clave_cata') or '').strip()}
    return _AREA_POR_CLAVE


def datos_graficos(todas, pri, cultivos, animales, coms_sup):
    """`todas`/`pri`: fichas del corte (sector o sistema); `cultivos`/
    `animales`: sus registros; `coms_sup`: filas de superficie_por_comunidad
    de sus comunidades. Devuelve un dict con la matriz de cada gráfico."""
    d = {}

    # 1 — Uso del Suelo (medición CATASTRAL de las comunidades del corte,
    #     como la web con filtro: riego ajustado + resto del polígono)
    d['uso_suelo'] = {
        'riego': sum(c.get('riego_ajustado_ha') or 0 for c in coms_sup),
        'sin_riego': sum(c.get('sin_riego_catastral_ha') or 0 for c in coms_sup),
        'catastral': sum(c.get('superficie_catastral_ha') or 0 for c in coms_sup),
        'n_com': len(coms_sup),
    }

    # 2 — Especies Pecuarias Principales (especie cruda, top 5 por cabezas;
    #     granja avícola excluida con nota — la web NO la excluye)
    cab = defaultdict(int)
    granja = 0
    for a in animales:
        n = int(a.get('cantidad') or 0)
        if n <= 0:
            continue
        if n >= GRANJA_AVICOLA_MIN:
            granja += n
            continue
        cab[(a.get('especie') or 'Sin clasificar').strip()] += n
    d['pecuario'] = sorted(cab.items(), key=lambda kv: -kv[1])[:5]
    d['pecuario_granja_excluida'] = granja
    d['pecuario_total'] = sum(cab.values())
    d['pecuario_registros'] = sum(1 for a in animales
                                  if 0 < int(a.get('cantidad') or 0) < GRANJA_AVICOLA_MIN)

    # 3 — Destino de la Producción Agrícola (registros de cultivo que declaran
    #     cada destino; un registro puede declarar varios)
    # El campo trae '1', '0' o vacío: solo el '1' declara el destino. Hasta el
    # 4-sep-2026 se contaba «truthy» y los '0' pasaban por sí (el tablero web
    # arrastra el mismo error en JavaScript, reportado a JAVIKO ese día).
    d['destino'] = [(nom, sum(1 for c in cultivos
                              if str(c.get(campo) or '').strip() in ('1', 'True')),
                     color)
                    for nom, campo, color in
                    (('Autoconsumo', 'es_autoconsumo', '#10b981'),
                     ('Mercado / Venta', 'es_mercado', '#3b82f6'),
                     ('Agroindustria', 'es_agroindustria', '#8b5cf6'),
                     ('Exportación', 'es_exportacion', '#ec4899'))]
    d['destino'] = [x for x in d['destino'] if x[1] > 0]

    # 4 — Nivel de Instrucción (principales; escala pedagógica y las erratas
    #     fuera de escala al final, como la web)
    ins = Counter()
    for p in pri:
        v = str(p.get('nivel_instruccion') or '').strip()
        if v:
            ins[v] += 1
    d['instruccion'] = ([(nv, ins[nv]) for nv in NIVELES_INSTRUCCION if ins[nv] > 0] +
                        [(nv, c) for nv, c in ins.items()
                         if nv not in NIVELES_INSTRUCCION])
    d['instruccion_con_dato'] = sum(ins.values())
    d['n_pri'] = len(pri)

    # 5 — Hijos por Familia (principales; basta un campo lleno para contar a
    #     la familia — dos hijos hombres y ninguna mujer es 2 y vacío)
    hh = hm = fam = 0
    for p in pri:
        th, tm = p.get('hijos_hombres'), p.get('hijos_mujeres')
        if th is None and tm is None:
            continue
        fam += 1
        hh += int(num(p, 'hijos_hombres'))
        hm += int(num(p, 'hijos_mujeres'))
    d['hijos'] = {'hombres': hh, 'mujeres': hm, 'familias': fam,
                  'promedio': (hh + hm) / fam if fam else 0.0}

    # 6 — Represa y Capacitación (principales; el campo llega como texto, con
    #     y sin tilde según el dispositivo: S.../N... como la web)
    def si_no(campo):
        si = no = 0
        for p in pri:
            v = str(p.get(campo) or '').strip().upper()
            if not v:
                continue
            if v.startswith('S'):
                si += 1
            elif v.startswith('N'):
                no += 1
        return si, no
    d['comunitaria'] = [(nom,) + si_no(campo) for nom, campo in
                        (('Conoce la represa', 'conoce_presa'),
                         ('Recibió capacitación', 'recibio_capacitacion'),
                         ('Quiere capacitarse', 'le_gustaria_cap'))]
    d['comunitaria'] = [x for x in d['comunitaria'] if x[1] + x[2] > 0]

    # 7 — Método de Riego (promedio % sobre TODAS las fichas del corte,
    #     incluidas las que no declaran método, redondeado a enteros — es
    #     exactamente lo que muestra el tablero web)
    nf = len(todas) or 1
    d['metodo'] = [(nom, round(sum(num(p, campo) for p in todas) / nf), color)
                   for nom, campo, color in
                   (('Aspersión', 'metodo_aspersion_pct', '#3b82f6'),
                    ('Gravedad', 'metodo_gravedad_pct', '#10b981'),
                    ('Goteo', 'metodo_goteo_pct', '#f59e0b'))]
    d['metodo'] = [x for x in d['metodo'] if x[1] > 0]

    # 8 — Cultivos Más Frecuentes (top 12 por número de registros, con la
    #     escritura unificada por mayúsculas como la web)
    etiquetas, conteo = {}, Counter()
    for c in cultivos:
        bruto = ' '.join(str(c.get('tipo_cultivo') or 'Sin dato').split())
        clave = bruto.upper()
        if clave not in etiquetas or etiquetas[clave] == etiquetas[clave].upper():
            etiquetas[clave] = bruto
        conteo[clave] += 1
    d['cultivos_frec'] = [(etiquetas[k], v) for k, v in conteo.most_common(12)]
    d['cultivos_registros'] = len(cultivos)

    # 9 — Tenencia del Predio. Regla 6: SOLO fichas principales (el tablero
    #     web cuenta todas las fichas; la nota al pie documenta la diferencia).
    ten = Counter((str(p.get('tenencia_predio') or '').strip() or 'Sin dato')
                  for p in pri)
    d['tenencia'] = ten.most_common()
    # el valor de la web (todas las fichas), solo para la verificación
    d['tenencia_web'] = Counter((str(p.get('tenencia_predio') or '').strip()
                                 or 'Sin dato') for p in todas).most_common()

    # 10 — Fichas por Parroquia (todas las fichas del corte)
    parr = Counter((str(p.get('parroquia') or '').strip() or 'Sin parroquia')
                   for p in todas)
    d['parroquias'] = parr.most_common()

    d['n_todas'] = len(todas)
    # 11 — Tamaño de los predios del corte. Por predio catastral, no por
    # ficha: los predios familiares tienen varias fichas y contarlos por
    # ficha multiplicaría los grandes (regla del reporte «Terrenos por rango
    # de superficie»). La clave se resuelve con clave_catastral y
    # cod_poligono de respaldo (regla 14).
    areas = area_por_clave()
    vistas, tam = set(), {et: 0 for _, _, et in RANGOS_PREDIO}
    for p in todas:
        clave = (str(p.get('clave_catastral') or '').strip() or
                 str(p.get('cod_poligono') or '').strip())
        if not clave or clave in vistas or clave not in areas:
            continue
        vistas.add(clave)
        a_ = areas[clave]
        for lo, hi, et in RANGOS_PREDIO:
            if lo <= a_ < hi:
                tam[et] += 1
                break
    d['tamanos'] = [(et, tam[et]) for _, _, et in RANGOS_PREDIO]
    d['tamanos_total'] = sum(tam.values())

    return d


# ─── Dibujo: las piezas compartidas de informe_graficos.py ─────────────────
# (vivieron aquí hasta el 4-sep-2026; ahora las usan también los capítulos)
from informe_graficos import (  # noqa: E402
    ARCHIVOS as _ARCHIVOS, g_barras_h, g_barras_v, g_donut, g_si_no,
)


def dibujar_graficos(slug, d):
    """Los 10 gráficos de un corte. Devuelve {n: (b64, clave)} en el orden
    del Dashboard."""
    g = {}
    g[1] = g_donut(f'{slug}-uso-suelo',
                   [('Con riego', d['uso_suelo']['riego'], '#3b82f6'),
                    ('Sin riego', d['uso_suelo']['sin_riego'], '#f59e0b')],
                   lambda v: f'{f2(v)} ha',
                   centro=f"{f2(d['uso_suelo']['catastral'])} ha")
    if d['pecuario']:
        g[2] = g_barras_h(f'{slug}-pecuario', d['pecuario'],
                          lambda i, n: PIE_COLORS[i % len(PIE_COLORS)])
    if d['destino']:
        g[3] = g_barras_v(f'{slug}-destino',
                          [(n, v) for n, v, _ in d['destino']],
                          [c for _, _, c in d['destino']])
    if d['instruccion']:
        g[4] = g_barras_h(f'{slug}-instruccion', d['instruccion'],
                          lambda i, n: COLORES_INSTRUCCION.get(
                              n, PIE_COLORS[i % len(PIE_COLORS)]))
    if d['hijos']['hombres'] + d['hijos']['mujeres'] > 0:
        g[5] = g_barras_v(f'{slug}-hijos',
                          [('Hombres', d['hijos']['hombres']),
                           ('Mujeres', d['hijos']['mujeres'])],
                          ['#3b82f6', '#ec4899'])
    if d['comunitaria']:
        g[6] = g_si_no(f'{slug}-comunitaria', d['comunitaria'])
    if d['metodo']:
        g[7] = g_donut(f'{slug}-metodo',
                       [(n, v, c) for n, v, c in d['metodo']],
                       lambda v: f'{v} %')
    if d['cultivos_frec']:
        g[8] = g_barras_v(f'{slug}-cultivos', d['cultivos_frec'],
                          lambda i, n: PIE_COLORS[i % len(PIE_COLORS)], rot=45)
    if d['tenencia']:
        g[9] = g_donut(f'{slug}-tenencia',
                       [(n, v, PIE_COLORS[i % len(PIE_COLORS)])
                        for i, (n, v) in enumerate(d['tenencia'])],
                       fnum, centro=fnum(sum(v for _, v in d['tenencia'])))
    if d['parroquias']:
        g[10] = g_barras_v(f'{slug}-parroquias', d['parroquias'],
                           lambda i, n: '#8b5cf6')
    if d['tamanos_total']:
        g[11] = g_barras_h(f'{slug}-tamanos', d['tamanos'],
                           lambda i, n: '#0ea5e9', alto=3.4)
    return g


# ─── Los títulos y notas de cada gráfico ─────────────────────────────────────

def titulos_y_notas(d, nombre_corte):
    """Título y pie de cada gráfico. El pie es UNA línea que nombra el
    universo y la cifra base; las explicaciones de método van en la
    presentación del documento, no bajo cada figura (acento aprobado por
    JAVIKO el 4-sep-2026)."""
    granja = d['pecuario_granja_excluida']
    todas = f"{NOTA_UNIV_TODAS} {fnum(d['n_todas'])} fichas."
    pri = f"{NOTA_UNIV_PRI} {fnum(d['n_pri'])} fichas."
    return {
        1: ('Uso del Suelo: Con Riego vs Sin Riego (ha)',
            [f"Medición catastral de las {d['uso_suelo']['n_com']} comunidades "
             f"de {nombre_corte}: {f2(d['uso_suelo']['catastral'])} ha, cada "
             'predio contado una sola vez.']),
        2: ('Especies Pecuarias Principales (Cabezas)',
            [todas + ' Las cinco especies con más cabezas.' +
             (f' No incluye la explotación avícola industrial de {fnum(granja)} '
              'aves de Asociación Rosalía.' if granja else '')]),
        3: ('Destino de la Producción Agrícola',
            [todas + ' Registros de cultivo por destino; un cultivo puede '
             'declarar más de uno.']),
        4: ('Nivel de Instrucción',
            [f"{NOTA_UNIV_PRI} {fnum(d['instruccion_con_dato'])} de "
             f"{fnum(d['n_pri'])} con el dato."]),
        5: ('Hijos por Familia',
            [f"{NOTA_UNIV_PRI} "
             f"{fnum(d['hijos']['hombres'] + d['hijos']['mujeres'])} hijos en "
             f"{fnum(d['hijos']['familias'])} familias, "
             f"{d['hijos']['promedio']:.1f} por familia."]),
        6: ('Represa y Capacitación',
            [pri + ' Verde Sí, rojo No.']),
        7: ('Método de Riego (promedio %)',
            [todas + ' Promedio simple del porcentaje declarado en cada '
             'ficha, redondeado a enteros.']),
        8: ('Cultivos Más Frecuentes',
            [todas + f" Los doce cultivos con más registros, de "
             f"{fnum(d['cultivos_registros'])}."]),
        9: ('Tenencia del Predio',
            [pri]),
        10: ('Fichas por Parroquia',
             [todas]),
        11: ('Tamaño de los Predios',
             [f"{fnum(d['tamanos_total'])} predios catastrales, cada uno "
              'contado una sola vez; superficie del catastro municipal.']),
    }


# ─── Documento ───────────────────────────────────────────────────────────────

def figura(b64, clave, titulo, notas):
    h = [f'<h3>{titulo}</h3>',
         '<div class="evitar-corte" style="margin:8px 0">',
         f'<img src="data:image/png;base64,{b64}" alt="{titulo}" '
         'style="max-width:100%;border:1px solid #dbe3ee;border-radius:7px;'
         'background:#fff;padding:6px">',
         '</div>']
    m = [f'### {titulo}', '', f'![{titulo}]({_ARCHIVOS[clave]})', '']
    for nde in notas:
        if nde:
            h.append(f'<p class="sub" style="margin-top:2px">{nde}</p>')
            m += [f'*{nde}*', '']
    return '\n'.join(h), '\n'.join(m)


def lectura_corte(nombre, d, coms, caudal_ls, es_sistema=False,
                  caudal_totales=None):
    """Párrafos de lectura del corte, con el universo de cada cifra nombrado."""
    uso = d['uso_suelo']
    decl = sum(c['sup_declarada'] for c in coms)
    decl_riego = sum(c['sup_riego_decl'] for c in coms)
    top_cult = d['cultivos_frec'][0][0] if d['cultivos_frec'] else '—'
    top_esp = d['pecuario'][0][0] if d['pecuario'] else '—'
    ins_top = max(d['instruccion'], key=lambda kv: kv[1])[0] if d['instruccion'] else '—'
    presa = next((x for x in d['comunitaria'] if x[0] == 'Conoce la represa'),
                 None)
    if es_sistema and caudal_totales:
        frase_caudal = (f'El caudal del sistema es de '
                        f'{f2(caudal_totales["caudal_sistema_ls"])} l/s: '
                        f'{f2(caudal_totales["caudal_comunidades_ls"])} l/s '
                        'que reciben las comunidades (un caudal por '
                        'comunidad) más '
                        f'{f2(caudal_totales["caudal_individual_ls"])} l/s de '
                        'tomas individuales.')
    else:
        frase_caudal = (f'Sus comunidades reciben {f1(caudal_ls)} l/s, un '
                        'caudal por comunidad.')
    p1 = (f'{"El sistema" if es_sistema else nombre} agrupa '
          f'{fnum(len(coms))} comunidades con {fnum(d["n_todas"])} fichas '
          f'catastrales ({fnum(d["n_pri"])} principales y '
          f'{fnum(d["n_todas"] - d["n_pri"])} adicionales). Los comuneros '
          f'declaran {f2(decl)} hectáreas, de las cuales {f2(decl_riego)} '
          f'({pct(decl_riego, decl):,.1f} %) con riego; la medición catastral '
          f'de sus comunidades es de {f2(uso["catastral"])} hectáreas. '
          + frase_caudal).replace('.0 %', ' %')
    p2 = (f'En producción, el cultivo más registrado es {top_cult} y la '
          f'especie pecuaria con más cabezas, {top_esp}. Entre los titulares '
          f'entrevistados predomina la instrucción {ins_top.lower()}' +
          (f'; {fnum(presa[1])} conocen el proyecto de la represa y '
           f'{fnum(presa[2])} no' if presa else '') + '.')
    return [p1, p2]


def construir_documento(comunidades, sup, caudal, datos_por_corte, mapas):
    titulo = 'Informe por Sector de Investigación'
    subtitulo = ('Los gráficos del tablero del padrón, para el sistema y por '
                 'sector de investigación · Cada gráfico nombra su universo')
    corte_linea = f'Datos al {FECHA_CORTE}'

    H = [E.cabecera(titulo, subtitulo)]
    M = [f'# {titulo}', '', f'*{subtitulo}*', '', f'*{corte_linea}.*', '']

    total = sup['total']
    H.append(E.kpis([
        (f0(total['fichas']), 'fichas catastrales'),
        (f0(total['regantes']), 'fichas principales'),
        (f2(total['superficie_declarada_ha']) + ' ha', 'superficie declarada'),
        (f2(caudal['totales']['caudal_sistema_ls']) + ' l/s',
         'caudal del sistema'),
    ]))

    H.append('<h2>Presentación</h2>')
    M += ['## Presentación', '']
    intro = [
        'Este informe reproduce, para el sistema completo y para cada sector '
        'de investigación, los diez gráficos del tablero de la aplicación '
        'web del padrón, tal como se ven en pantalla con el filtro de sector '
        'puesto. Es el complemento gráfico del Informe por Comunidad: aquella '
        'entrega responde cada pregunta de la ficha comunidad por comunidad; '
        'esta muestra el retrato de cada sector de un vistazo.',
        'Cada gráfico nombra al pie su universo. Los datos de tierra y '
        'producción salen de todas las fichas, porque cada ficha es un predio; '
        'los datos de las personas —instrucción, hijos, represa y capacitación, '
        'tenencia— salen solo de las fichas principales, una por titular '
        'entrevistado. El inventario pecuario no incluye una explotación '
        'avícola industrial de 60.000 aves registrada en Asociación Rosalía, '
        'ajena a la producción familiar que describe este material.',
        'Dos mediciones de superficie conviven y no se suman entre sí: la '
        'declarada por los comuneros en la entrevista y la catastral de los '
        'polígonos municipales, que es la que usa el gráfico de uso del suelo. '
        'El método de riego es el promedio simple del porcentaje declarado en '
        'cada ficha; la tenencia se cuenta sobre fichas principales.',
        f'Las cifras corresponden al padrón al {FECHA_CORTE}, la misma fecha '
        'de referencia de los demás documentos entregados al consorcio. El '
        'levantamiento de campo está cerrado.',
    ]
    for p in intro:
        H.append(f'<p>{p}</p>')
        M += [p, '']

    caudal_de = {c['key']: c for c in comunidades}

    def caudal_corte(coms):
        return sum(c['caudal_ls'] or 0 for c in coms
                   if not c['caudal_heredado_de'])

    cortes = [('Todo el sistema', 'sistema', None)] + \
             [(s, s.lower().replace(' ', '-'), s) for s in SECTORES]

    for nombre, slug, sector in cortes:
        d = datos_por_corte[nombre]
        coms = [c for c in comunidades
                if sector is None or c['sector_informe'] == sector]
        H.append(f'<h2>{nombre}' +
                 (f' — {len(coms)} comunidades</h2>' if sector else '</h2>'))
        M += [f'## {nombre}' + (f' — {len(coms)} comunidades' if sector else ''), '']
        if sector is None:
            # el capítulo del sistema cita las fuentes únicas tal cual, no la
            # suma de comunidades (difieren en centavos de redondeo y el
            # caudal del sistema incluye las tomas individuales)
            H.append(E.kpis([
                (f0(total['fichas']), 'fichas catastrales'),
                (f0(total['regantes']), 'fichas principales'),
                (f2(total['superficie_declarada_ha']) + ' ha',
                 'superficie declarada'),
                (f2(caudal['totales']['caudal_sistema_ls']) + ' l/s',
                 'caudal del sistema'),
            ]))
        else:
            H.append(E.kpis([
                (f0(d['n_todas']), 'fichas catastrales'),
                (f0(d['n_pri']), 'fichas principales'),
                (f2(sum(c['sup_declarada'] for c in coms)) + ' ha',
                 'superficie declarada'),
                (f1(caudal_corte(coms)) + ' l/s', 'caudal de sus comunidades'),
            ]))
        mapa_clave = 'general' if sector is None else sector
        if mapa_clave in mapas:
            pie_mapa = ('El área de estudio sobre imagen satelital (Esri '
                        'World Imagery): límites oficiales de comunas del '
                        'GADM Cayambe, recortados al sistema y coloreados '
                        'por sector de investigación; la numeración 1–50 es '
                        'la del listado oficial de organizaciones de riego.'
                        if sector is None else
                        f'Las comunas oficiales del {sector} (límites del '
                        'GADM Cayambe, asignadas por cruce espacial); la '
                        'numeración es la del listado oficial de '
                        'organizaciones del consorcio.')
            H.append('<div class="evitar-corte" style="margin:10px 0">'
                     f'<img src="data:image/jpeg;base64,{mapas[mapa_clave]}" '
                     f'alt="{pie_mapa}" style="width:100%;border:1px solid '
                     '#dbe3ee;border-radius:7px">'
                     f'<p class="sub" style="margin-top:4px">{pie_mapa}</p></div>')
            M += [f'![{pie_mapa}]({DIR_GRAF}/mapa-{slug}.jpg)', '']
        for p in lectura_corte(nombre, d, coms, caudal_corte(coms),
                               es_sistema=(sector is None),
                               caudal_totales=caudal['totales']):
            H.append(f'<p>{p}</p>')
            M += [p, '']
        tyn = titulos_y_notas(d, nombre if sector else 'todo el sistema')
        for i in sorted(d['_graficos']):
            b64 = d['_graficos'][i]
            tit, notas = tyn[i]
            h, m = figura(b64, f'{slug}-' + CLAVES_GRAFICO[i], tit, notas)
            H.append(h)
            M += [m]

    H.append(E.pie(corte_linea.lower()))
    M += ['---', '',
          f'*{E.PIE_INSTITUCION} · {corte_linea}. Documento generado por '
          'scripts/generar_informe_sociologo_sector.py a partir de los '
          'gráficos del tablero web; encargo del cliente, 31-ago-2026.*', '']

    html = E.documento(f'{titulo} — Padrón Guanguilquí–Porotog', '\n'.join(H))
    return html, '\n'.join(M)


CLAVES_GRAFICO = {1: 'uso-suelo', 2: 'pecuario', 3: 'destino',
                  4: 'instruccion', 5: 'hijos', 6: 'comunitaria',
                  7: 'metodo', 8: 'cultivos', 9: 'tenencia', 10: 'parroquias',
                  11: 'tamanos'}


# ─── Excel de matrices crudas ────────────────────────────────────────────────

def escribir_xlsx(datos_por_corte, ruta):
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill

    wb = Workbook()
    wb.remove(wb.active)
    cab_font = Font(bold=True, color='FFFFFF')
    cab_fill = PatternFill('solid', fgColor='1E4D8C')

    def hoja(nombre, columnas, filas):
        ws = wb.create_sheet(nombre[:31])
        ws.append(columnas)
        for cel in ws[1]:
            cel.font = cab_font
            cel.fill = cab_fill
            cel.alignment = Alignment(vertical='center', wrap_text=True)
        for fila in filas:
            ws.append(fila)
        ws.freeze_panes = 'A2'
        for col in ws.columns:
            ancho = max(len(str(c.value or '')) for c in col[:40])
            ws.column_dimensions[col[0].column_letter].width = \
                min(max(ancho + 2, 10), 42)

    cortes = list(datos_por_corte.items())

    hoja('Uso del suelo (catastral)',
         ['Corte', 'Comunidades', 'Con riego ajustado (ha)',
          'Sin riego catastral (ha)', 'Catastral total (ha)'],
         [[n, d['uso_suelo']['n_com'], round(d['uso_suelo']['riego'], 2),
           round(d['uso_suelo']['sin_riego'], 2),
           round(d['uso_suelo']['catastral'], 2)] for n, d in cortes])

    hoja('Pecuario top 5',
         ['Corte', 'Especie', 'Cabezas', 'Aves granja excluidas (corte)'],
         [[n, esp, v, d['pecuario_granja_excluida']]
          for n, d in cortes for esp, v in d['pecuario']])

    hoja('Destino produccion',
         ['Corte', 'Destino', 'Registros de cultivo'],
         [[n, dest, v] for n, d in cortes for dest, v, _ in d['destino']])

    hoja('Instruccion',
         ['Corte', 'Nivel', 'Titulares', 'Con dato', 'Principales'],
         [[n, nv, v, d['instruccion_con_dato'], d['n_pri']]
          for n, d in cortes for nv, v in d['instruccion']])

    hoja('Hijos',
         ['Corte', 'Hijos hombres', 'Hijas mujeres', 'Familias con dato',
          'Promedio por familia'],
         [[n, d['hijos']['hombres'], d['hijos']['mujeres'],
           d['hijos']['familias'], round(d['hijos']['promedio'], 2)]
          for n, d in cortes])

    hoja('Represa y capacitacion',
         ['Corte', 'Pregunta', 'Si', 'No'],
         [[n, preg, si, no] for n, d in cortes
          for preg, si, no in d['comunitaria']])

    hoja('Metodo de riego',
         ['Corte', 'Metodo', 'Promedio % (redondeado)'],
         [[n, met, v] for n, d in cortes for met, v, _ in d['metodo']])

    hoja('Cultivos frecuentes',
         ['Corte', 'Cultivo', 'Registros'],
         [[n, cu, v] for n, d in cortes for cu, v in d['cultivos_frec']])

    hoja('Tenencia (principales)',
         ['Corte', 'Tenencia', 'Fichas principales'],
         [[n, t, v] for n, d in cortes for t, v in d['tenencia']])

    hoja('Tamano de predios',
         ['Corte'] + [et for _, _, et in RANGOS_PREDIO] + ['Predios'],
         [[nombre] + [dict(d['tamanos']).get(et, 0)
                      for _, _, et in RANGOS_PREDIO] + [d['tamanos_total']]
          for nombre, d in datos_por_corte.items()])

    hoja('Parroquias',
         ['Corte', 'Parroquia', 'Fichas'],
         [[n, pa, v] for n, d in cortes for pa, v in d['parroquias']])

    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    wb.save(ruta)


# ─── Autoverificación contra las fuentes únicas ──────────────────────────────

def verificar(datos_por_corte, comunidades, sup, caudal):
    """Los totales del documento contra las fuentes únicas. No corrige: avisa."""
    avisos = []
    tot = sup['total']
    d_sis = datos_por_corte['Todo el sistema']

    if d_sis['n_todas'] != tot['fichas']:
        avisos.append(f"fichas del sistema: {d_sis['n_todas']} ≠ fuente "
                      f"{tot['fichas']}")
    if d_sis['n_pri'] != tot['regantes']:
        avisos.append(f"principales: {d_sis['n_pri']} ≠ fuente {tot['regantes']}")

    suma_f = sum(datos_por_corte[s]['n_todas'] for s in SECTORES)
    if suma_f != d_sis['n_todas']:
        avisos.append(f'fichas por sector no suman el sistema: {suma_f} ≠ '
                      f"{d_sis['n_todas']}")

    decl = sum(c['sup_declarada'] for c in comunidades)
    if abs(decl - tot['superficie_declarada_ha']) > 0.5:
        avisos.append(f"declarada: {decl:,.2f} ≠ fuente "
                      f"{tot['superficie_declarada_ha']:,.2f}")

    cat_sis = d_sis['uso_suelo']['catastral']
    if abs(cat_sis - tot['superficie_catastral_ha']) > 0.5:
        avisos.append(f"catastral: {cat_sis:,.2f} ≠ fuente "
                      f"{tot['superficie_catastral_ha']:,.2f}")

    q = sum(c['caudal_ls'] or 0 for c in comunidades
            if not c['caudal_heredado_de'])
    q_ref = caudal['totales']['caudal_comunidades_ls']
    if abs(q - q_ref) > 0.1:
        avisos.append(f'caudal de comunidades: {q:,.2f} ≠ fuente {q_ref:,.2f}')

    # La discrepancia CONOCIDA del bloque `sectores` del JSON: cuenta a
    # ASOCIACIÓN ROSALÍA en el Sector 2 (lista duplicada en
    # generar_capas_sectores_comunidades.py) mientras el catálogo oficial, la
    # web y este informe la cuentan en el Sector 3. Se avisa siempre para que
    # nadie compare a ciegas contra ese bloque.
    js = sup.get('sectores', {})
    for s in SECTORES:
        f_doc = datos_por_corte[s]['n_todas']
        f_json = int(js.get(s, {}).get('fichas') or 0)
        if f_doc != f_json:
            print(f'ℹ {s}: el informe cuenta {f_doc} fichas y el bloque '
                  f'`sectores` del JSON dice {f_json} — diferencia esperada: '
                  'Asociación Rosalía (47 fichas) va en el Sector 3, como la '
                  'web; el JSON aún la cuenta en el Sector 2 (bug reportado).')

    for a in avisos:
        print(f'⚠ NO CUADRA — {a}')
    if not avisos:
        print(f"✔ Cuadre contra fuentes únicas: {tot['fichas']:,} fichas "
              f"({tot['regantes']:,} principales) · declarada "
              f"{tot['superficie_declarada_ha']:,.2f} ha · catastral "
              f"{tot['superficie_catastral_ha']:,.2f} ha · caudal "
              f"{caudal['totales']['caudal_sistema_ls']:,.2f} l/s")
        for s in SECTORES:
            ds = datos_por_corte[s]
            coms_s = [c for c in comunidades if c['sector_informe'] == s]
            print(f"   {s}: {ds['n_todas']:,} fichas · declarada "
                  f"{sum(c['sup_declarada'] for c in coms_s):,.2f} ha · "
                  f"catastral {ds['uso_suelo']['catastral']:,.2f} ha")
    return avisos


# ─── main ────────────────────────────────────────────────────────────────────

def calcular_datos_por_corte(dibujar=False):
    """Las matrices de los gráficos, para el sistema y cada sector. Es el
    ÚNICO sitio donde se calculan: el informe por sector las dibuja y los
    capítulos del informe técnico las reutilizan (informe_graficos.
    datos_dashboard) para coincidir con la pantalla."""
    comunidades, sup, caudal, corte_txt, fichas = agregar_todo()

    # El sector del INFORME es el del catálogo oficial (constants.ts), el
    # mismo que usa la web — con Asociación Rosalía en el Sector 3.
    for c in comunidades:
        c['sector_informe'] = c['sector']

    # Datos por ficha para los gráficos, con la misma limpieza del motor:
    # hijas pendientes fuera (hoy 0), clave canónica ya puesta en '_key'.
    todas = [p for p in fichas
             if not (es_hija(p) and
                     (p.get('estado_investigacion') or '') != 'completada')]
    pri = [p for p in fichas if not es_hija(p)]

    import json
    GEO = os.path.join(BASE, 'public', 'geo')
    with open(os.path.join(GEO, 'cultivos.json'), encoding='utf-8') as f:
        cultivos = json.load(f)
    with open(os.path.join(GEO, 'animales.json'), encoding='utf-8') as f:
        animales = json.load(f)

    sector_de_key = {c['key']: c['sector_informe'] for c in comunidades}
    id_a_sector = {p.get('id'): sector_de_key.get(p['_key'])
                   for p in todas}
    ids_todas = {p.get('id') for p in todas}
    cultivos = [c for c in cultivos if c.get('ficha_id') in ids_todas]
    animales = [a for a in animales if a.get('ficha_id') in ids_todas]

    from comunidades_canon import canonica
    sup_por_key = {canonica(c['comunidad']): c for c in sup['comunidades']}

    datos_por_corte = {}
    for nombre, sector in [('Todo el sistema', None)] + \
                          [(s, s) for s in SECTORES]:
        if sector is None:
            t, p_ = todas, pri
            cu, an = cultivos, animales
            coms_sup = [sup_por_key[c['key']] for c in comunidades
                        if c['key'] in sup_por_key]
        else:
            keys = {c['key'] for c in comunidades
                    if c['sector_informe'] == sector}
            t = [p for p in todas if p['_key'] in keys]
            p_ = [p for p in pri if p['_key'] in keys]
            ids = {p.get('id') for p in t}
            cu = [c for c in cultivos if c.get('ficha_id') in ids]
            an = [a for a in animales if a.get('ficha_id') in ids]
            coms_sup = [sup_por_key[k] for k in keys if k in sup_por_key]
        d = datos_graficos(t, p_, cu, an, coms_sup)
        if sector is None:
            # Sin filtro, la web usa la fila `total` del JSON, no la suma de
            # comunidades: las filas por comunidad no cierran exactas entre sí
            # (su «sin riego» suma 8,01 ha más que el total) y con la suma el
            # gráfico del sistema no coincidiría con la pantalla.
            d['uso_suelo'] = {
                'riego': sup['total']['riego_ajustado_ha'],
                'sin_riego': sup['total']['sin_riego_catastral_ha'],
                'catastral': sup['total']['superficie_catastral_ha'],
                'n_com': len(coms_sup),
            }
        if dibujar:
            slug = 'sistema' if sector is None else sector.lower().replace(' ', '-')
            d['_graficos'] = dibujar_graficos(slug, d)
        datos_por_corte[nombre] = d
    return {'datos': datos_por_corte, 'comunidades': comunidades, 'sup': sup,
            'caudal': caudal, 'fichas': fichas, 'todas': todas, 'pri': pri,
            'cultivos': cultivos, 'animales': animales,
            'sector_de_key': sector_de_key}


def main():
    import informe_graficos as G
    G.preparar()
    G.configurar(os.path.join(BASE, 'docs'), DIR_GRAF)
    r = calcular_datos_por_corte(dibujar=True)
    datos_por_corte, comunidades, sup, caudal = (r['datos'], r['comunidades'],
                                                 r['sup'], r['caudal'])


    verificar(datos_por_corte, comunidades, sup, caudal)

    # Mapas satelitales: los mismos del informe por comunidad, generados en
    # memoria (pdf_ruta=None para no tocar el anexo PDF de aquel documento) y
    # escritos como archivo propio para el Markdown/Word.
    mapas = generar_mapas(comunidades, pdf_ruta=None)
    carpeta = os.path.join(BASE, 'docs', DIR_GRAF)
    os.makedirs(carpeta, exist_ok=True)
    for clave, slug in [('general', 'sistema'), ('Sector 1', 'sector-1'),
                        ('Sector 2', 'sector-2'), ('Sector 3', 'sector-3')]:
        with open(os.path.join(carpeta, f'mapa-{slug}.jpg'), 'wb') as f:
            f.write(base64.b64decode(mapas[clave]))

    html, md = construir_documento(comunidades, sup, caudal,
                                   datos_por_corte, mapas)
    with open(HTML_OUT, 'w', encoding='utf-8') as f:
        f.write(html)
    with open(MD_OUT, 'w', encoding='utf-8') as f:
        f.write(md)
    escribir_xlsx(datos_por_corte, XLSX_OUT)
    print(f'✔ {os.path.relpath(HTML_OUT, BASE)}')
    print(f'✔ {os.path.relpath(MD_OUT, BASE)}')
    print(f'✔ {os.path.relpath(XLSX_OUT, BASE)}')
    print('  Word: python scripts/md_a_docx.py docs/INFORME-SOCIOLOGO-por-sector.md')


if __name__ == '__main__':
    main()
