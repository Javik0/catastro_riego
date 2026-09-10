# -*- coding: utf-8 -*-
"""
Gráficos de los informes: las mismas piezas de dibujo para todos los documentos.

POR QUÉ EXISTE
--------------
Nacieron dentro de `generar_informe_sociologo_sector.py` (31-ago-2026) para
reproducir los gráficos del tablero web con matplotlib. Cuando los capítulos
del informe técnico también ganaron gráficos (encargo de JAVIKO, 2-sep-2026),
se sacaron aquí para que ambos documentos dibujen igual sin copiar código:
mismos colores del Dashboard, mismas proporciones, misma tipografía.

Cada función devuelve el PNG en base64 (para incrustarlo en el HTML) y además
escribe el archivo en disco (para los Markdown/Word que apuntan a archivos).

RESOLUCIÓN
----------
Un solo PNG a 200 ppp sirve al HTML y al Word: JAVIKO pidió (4-sep-2026)
que las imágenes lleguen con resolución fiel, sin recomprimir. PNG es sin
pérdida; `html_a_docx.py` incrusta el mismo archivo y marca el documento con
«no comprimir imágenes».

USO
---
    import informe_graficos as G
    G.configurar(os.path.join(BASE, 'docs'), 'graficos-capitulos')
    b64 = G.g_barras_h('perfil-instruccion', [('Primaria', 2600), ...],
                       lambda i, n: G.PIE_COLORS[i])
    ruta_relativa = G.ARCHIVOS['perfil-instruccion']
"""

import base64
import io
import os

# La paleta del Dashboard (PIE_COLORS de DashboardHome.tsx), en el mismo orden.
PIE_COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444',
              '#8b5cf6', '#ec4899', '#06b6d4', '#84cc16']
COLORES_INSTRUCCION = {'Ninguno': '#94a3b8', 'Alfabetizado': '#22d3ee',
                       'Primaria': '#3b82f6', 'Secundaria': '#6366f1',
                       'Superior': '#8b5cf6'}
NIVELES_INSTRUCCION = ['Ninguno', 'Alfabetizado', 'Primaria',
                       'Secundaria', 'Superior']

DPI = 200

# clave → ruta relativa a la carpeta base (p. ej. 'graficos-sociologo/x.png')
ARCHIVOS = {}
_CARPETA_ABS = None
_CARPETA_REL = None


def configurar(base_abs, carpeta_rel):
    """Dónde se escriben los PNG: `base_abs/carpeta_rel/<clave>.png`."""
    global _CARPETA_ABS, _CARPETA_REL
    _CARPETA_REL = carpeta_rel
    _CARPETA_ABS = os.path.join(base_abs, carpeta_rel)
    os.makedirs(_CARPETA_ABS, exist_ok=True)


def preparar():
    """Backend sin pantalla y tipografía de la casa. Llamar una vez."""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.family': ['Segoe UI', 'DejaVu Sans'],
                         'axes.edgecolor': '#dbe3ee',
                         'figure.facecolor': 'white'})


def fnum(n):
    return f'{n:,.0f}'


def guardar(fig, clave):
    """PNG en base64 para el HTML y el mismo archivo en disco para el Word."""
    import matplotlib.pyplot as plt
    if _CARPETA_ABS is None:
        raise RuntimeError('informe_graficos.configurar() no se ha llamado')
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=DPI, facecolor='white',
                bbox_inches='tight')
    datos = buf.getvalue()
    ruta = os.path.join(_CARPETA_ABS, clave + '.png')
    with open(ruta, 'wb') as f:
        f.write(datos)
    ARCHIVOS[clave] = f'{_CARPETA_REL}/{clave}.png'
    plt.close(fig)
    return base64.b64encode(datos).decode('ascii')


def _ejes(fig, ax):
    ax.spines[:].set_visible(False)
    ax.tick_params(length=0, labelsize=8.5, colors='#556070')
    ax.set_axisbelow(True)


def g_donut(clave, series, fmt, centro=None):
    """Anillo como los Pie de recharts: (nombre, valor, color) con la leyenda
    de cifras debajo, no como etiquetas radiales."""
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(5.4, 3.4))
    vals = [v for _, v, _ in series]
    cols = [c for _, _, c in series]
    ax.pie(vals, colors=cols, startangle=90, counterclock=False,
           wedgeprops=dict(width=0.38, edgecolor='white', linewidth=2))
    if centro:
        ax.text(0, 0, centro, ha='center', va='center', fontsize=10,
                fontweight='bold', color='#24405e')
    ax.set(aspect='equal')
    leyenda = '    '.join(f'{n}: {fmt(v)}' for n, v, _ in series)
    fig.text(0.5, 0.02, leyenda, ha='center', fontsize=8.5, color='#374151')
    return guardar(fig, clave)


def g_barras_h(clave, items, colores, fmt=fnum, alto=None):
    """Barras horizontales con la cifra al final, como los BarChart layout=
    vertical de recharts. `items`: [(nombre, valor)] de mayor a menor."""
    import matplotlib.pyplot as plt
    n = len(items)
    fig, ax = plt.subplots(figsize=(6.4, alto or max(1.6, 0.5 * n + 0.6)))
    nombres = [x[0] for x in items][::-1]
    vals = [x[1] for x in items][::-1]
    cols = ([colores(i, nom) for i, (nom, _) in enumerate(items)][::-1]
            if callable(colores) else list(colores)[::-1])
    barras = ax.barh(range(n), vals, color=cols, height=0.62)
    ax.set_yticks(range(n), nombres)
    ax.xaxis.grid(True, linestyle=(0, (3, 3)), color='#dbe3ee', linewidth=0.8)
    _ejes(fig, ax)
    vmax = max(vals) if vals else 1
    for b, v in zip(barras, vals):
        dentro = v > vmax * 0.18
        ax.text(v - vmax * 0.015 if dentro else v + vmax * 0.015,
                b.get_y() + b.get_height() / 2, fmt(v),
                ha='right' if dentro else 'left', va='center', fontsize=8,
                fontweight='bold', color='white' if dentro else '#556070')
    ax.margins(x=0.06)
    return guardar(fig, clave)


def g_barras_v(clave, items, colores, fmt=fnum, rot=0):
    """Barras verticales con la cifra dentro, como los BarChart de recharts."""
    import matplotlib.pyplot as plt
    n = len(items)
    fig, ax = plt.subplots(figsize=(max(4.6, 0.62 * n + 1.6), 3.2))
    nombres = [x[0] for x in items]
    vals = [x[1] for x in items]
    cols = ([colores(i, nom) for i, (nom, _) in enumerate(items)]
            if callable(colores) else list(colores))
    barras = ax.bar(range(n), vals, color=cols, width=0.62)
    ax.set_xticks(range(n), nombres, rotation=rot,
                  ha='right' if rot else 'center', fontsize=8)
    ax.yaxis.grid(True, linestyle=(0, (3, 3)), color='#dbe3ee', linewidth=0.8)
    _ejes(fig, ax)
    vmax = max(vals) if vals else 1
    for b, v in zip(barras, vals):
        dentro = v > vmax * 0.12
        ax.text(b.get_x() + b.get_width() / 2,
                v - vmax * 0.02 if dentro else v + vmax * 0.02, fmt(v),
                ha='center', va='top' if dentro else 'bottom', fontsize=8,
                fontweight='bold', color='white' if dentro else '#556070')
    ax.margins(y=0.08)
    return guardar(fig, clave)


def g_si_no(clave, filas):
    """Pares Sí/No en horizontal (verde Sí, rojo No), como «Represa y
    Capacitación». `filas`: [(nombre, sí, no)]."""
    import matplotlib.pyplot as plt
    n = len(filas)
    fig, ax = plt.subplots(figsize=(6.4, 0.9 * n + 0.7))
    ys = range(n)
    si = [f[1] for f in filas][::-1]
    no = [f[2] for f in filas][::-1]
    nombres = [f[0] for f in filas][::-1]
    b1 = ax.barh([y + 0.19 for y in ys], si, height=0.34, color='#10b981',
                 label='Sí')
    b2 = ax.barh([y - 0.19 for y in ys], no, height=0.34, color='#ef4444',
                 label='No')
    ax.set_yticks(list(ys), nombres, fontsize=8.5)
    ax.xaxis.grid(True, linestyle=(0, (3, 3)), color='#dbe3ee', linewidth=0.8)
    _ejes(fig, ax)
    vmax = max(si + no) or 1
    for barras, vals in ((b1, si), (b2, no)):
        for b, v in zip(barras, vals):
            ax.text(v + vmax * 0.015, b.get_y() + b.get_height() / 2, fnum(v),
                    va='center', fontsize=8, fontweight='bold', color='#556070')
    ax.margins(x=0.09)
    ax.legend(loc='lower right', fontsize=8, frameon=False)
    return guardar(fig, clave)


def g_barras_agrupadas(clave, categorias, series, fmt=fnum, rot=0):
    """Barras agrupadas: una barra por serie dentro de cada categoría. Es el
    gráfico del capítulo «Los tres sectores de un vistazo»: `categorias` son
    los indicadores y `series` = [(nombre_serie, color, [valores])], una por
    sector, en el orden de `categorias`."""
    import matplotlib.pyplot as plt
    n, k = len(categorias), len(series)
    fig, ax = plt.subplots(figsize=(max(5.2, 0.9 * n + 1.8), 3.3))
    ancho = 0.8 / k
    vmax = max((v for _, _, vals in series for v in vals), default=1) or 1
    for j, (nombre, color, vals) in enumerate(series):
        xs = [i - 0.4 + ancho * (j + 0.5) for i in range(n)]
        barras = ax.bar(xs, vals, width=ancho * 0.92, color=color, label=nombre)
        for b, v in zip(barras, vals):
            ax.text(b.get_x() + b.get_width() / 2, v + vmax * 0.015, fmt(v),
                    ha='center', va='bottom', fontsize=7,
                    fontweight='bold', color='#556070')
    ax.set_xticks(range(n), categorias, rotation=rot,
                  ha='right' if rot else 'center', fontsize=8)
    ax.yaxis.grid(True, linestyle=(0, (3, 3)), color='#dbe3ee', linewidth=0.8)
    _ejes(fig, ax)
    ax.margins(y=0.12)
    # la leyenda va ENCIMA del área de dibujo: dentro tapaba la cifra de la
    # barra más alta (visto en «Nivel de instrucción por sector», 4-sep-2026)
    ax.legend(loc='lower center', bbox_to_anchor=(0.5, 1.01), fontsize=8,
              frameon=False, ncol=k)
    return guardar(fig, clave)


_DASHBOARD = None


def datos_dashboard():
    """Las matrices de los gráficos del tablero web, para el sistema y por
    sector, calculadas UNA sola vez por `generar_informe_sociologo_sector.py`
    (el mismo código que produce el informe por sector). Los capítulos las
    usan para que sus gráficos coincidan con la pantalla y con ese informe.

    Devuelve el dict de `calcular_datos_por_corte()`: 'datos' (por corte:
    'Todo el sistema', 'Sector 1'…), 'comunidades', 'sup', 'caudal',
    'fichas'. Import diferido para no cargar los GeoJSON si no hace falta.
    """
    global _DASHBOARD
    if _DASHBOARD is None:
        from generar_informe_sociologo_sector import calcular_datos_por_corte
        _DASHBOARD = calcular_datos_por_corte()
    return _DASHBOARD


def sistema():
    """Atajo: las matrices del corte «Todo el sistema»."""
    return datos_dashboard()['datos']['Todo el sistema']


def figura_html(b64, titulo, notas=(), nivel='h3'):
    """Bloque de figura con el estilo de la casa: título, imagen y notas al
    pie (`p.sub`). Es lo que insertan los capítulos y el informe por sector."""
    h = [f'<{nivel}>{titulo}</{nivel}>' if titulo else '',
         '<div class="evitar-corte" style="margin:8px 0">',
         f'<img src="data:image/png;base64,{b64}" alt="{titulo}" '
         'style="max-width:100%;border:1px solid #dbe3ee;border-radius:7px;'
         'background:#fff;padding:6px">',
         '</div>']
    for nde in notas:
        if nde:
            h.append(f'<p class="sub" style="margin-top:2px">{nde}</p>')
    return '\n'.join(x for x in h if x)
