# -*- coding: utf-8 -*-
"""
Generador masivo de fichas del padrón en PDF — una ficha A4 por PDF.

QUÉ HACE
--------
Reproduce la ficha de impresión de la web (src/components/fichas/
FichaImpresion.tsx: 7 secciones, cabecera con logos, bloque de auditoría)
como PDF vectorial con reportlab, y escribe los archivos organizados en
carpetas por sector de investigación y comunidad:

    <salida>/Sector N/<COMUNIDAD>/<clave> - <TITULAR> - <codigo_final>.pdf

Decisiones de JAVIKO (4-sep-2026): universo completo (6.830 fichas,
principales + adicionales), ALPAKA en su carpeta normal, con los dos mapas
satelitales por ficha (ubicación regional + emplazamiento del predio) y un
índice Excel al final con la ruta de cada archivo.

REGLAS DEL PROYECTO QUE ESTE SCRIPT RESPETA
-------------------------------------------
· NO toca el data.gpkg: lee SOLO los GeoJSON/JSON de public/geo/.
· Regla 15: el sector de una ficha es el de su comunidad según el catálogo
  COM_A_SECTOR (generar_capas_sectores_comunidades.py), NUNCA el campo
  sector_investigacion de la ficha.
· Regla 4: el nombre de carpeta de comunidad sale de comunidades_canon.py
  (canonica()), saneado para Windows.
· Regla 14: el polígono del predio se resuelve por clave_catastral y
  cod_poligono es el respaldo.
· Regla 3: el caudal que muestra la ficha es el que publica el export
  (fichas_predios.geojson ya trae el caudal imputado por comunidad).
· Regla 18: agua/luz se muestran Sí solo con `1`, No con `0`, «Sin dato»
  si el campo viene vacío.
· Convención de conteo: la sección 3 dice «del Titular», no «del Regante».
· Las observaciones que se imprimen son `observaciones_cliente` (la vista
  externa de la web); el campo `observaciones` crudo es texto interno.
· La fecha de corte del paquete es informe_estilo.FECHA_CORTE.
· La ficha NO lleva fotografía: el campo `foto_predio` guarda el retrato del
  titular, no el predio (decisión de JAVIKO, 10-sep-2026). Ver `--con-foto`.

CÓMO SE CORRE
-------------
    python -X utf8 scripts/generar_fichas_pdf.py --comunidad "MATIAS IMBAGO"
    python -X utf8 scripts/generar_fichas_pdf.py            # las 6.830
    python -X utf8 scripts/generar_fichas_pdf.py --sin-mapa # medición
    python -X utf8 scripts/generar_fichas_pdf.py --indice   # solo el Excel

Es REANUDABLE: si el PDF ya existe se salta (--rehacer lo fuerza). Los
mosaicos satelitales Esri se cachean en <salida>\.tiles\ y no se vuelven a
descargar (mismo know-how que generar_informe_sociologo.generar_mapas).
"""

import argparse
import io
import json
import math
import os
import re
import sys
import time
import unicodedata
import urllib.request
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor

if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf-8', buffering=1)
    sys.stderr = open(sys.stderr.fileno(), mode='w', encoding='utf-8', buffering=1)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

from comunidades_canon import canonica, normalizar  # noqa: E402
from generar_capas_sectores_comunidades import COM_A_SECTOR  # noqa: E402
from informe_estilo import FECHA_CORTE  # noqa: E402

from PIL import Image, ImageDraw, ImageFont, ImageOps  # noqa: E402
from reportlab.lib import colors  # noqa: E402
from reportlab.lib.pagesizes import A4  # noqa: E402
from reportlab.lib.styles import ParagraphStyle  # noqa: E402
from reportlab.lib.units import mm  # noqa: E402
from reportlab.lib.utils import ImageReader  # noqa: E402
from reportlab.platypus import (  # noqa: E402
    BaseDocTemplate, Frame, PageBreak, PageTemplate, Paragraph, Spacer,
    Table, TableStyle, Image as RLImage,
)

# ─── Rutas y constantes ──────────────────────────────────────────────────────

APP_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, '..'))
GEO = os.path.join(APP_DIR, 'public', 'geo')
PUB = os.path.join(APP_DIR, 'public')
QFIELD_DIR = r'C:\Users\HP\QField\cloud\porotog_levantamiento_offline'
SALIDA_DEF = r'C:\Users\HP\OneDrive\Escritorio\FICHAS PDF POROTOG'

# Identidad del proyecto — copiada de src/lib/constants.ts (mantener en sincronía)
PROJECT_TITLE = 'ESTUDIO DEFINITIVO DE PRESA EN EL RIO POROTOG'
PROJECT_SUBTITLE = 'PADRÓN DE USUARIOS: SISTEMA DE RIEGO COMUNITARIO GUANGUILQUÍ–POROTOG'
PROJECT_SUBTITLE_ALCANCE = 'Ficha de empadronamiento predial y productivo – línea base censal'
PROJECT_LOCATION = 'Provincia Pichincha — Cantón Cayambe'

# Técnicos investigadores — copiado de src/lib/constants.ts (mantener en sincronía)
TECNICOS = {
    'u0_a314': 'Melany Jara', 'u0_a319': 'Melany Jara', 'jvk-editor': 'Melany Jara',
    'u0_a504': 'Adriana Cuascota', 'jvk-editor6': 'Adriana Cuascota',
    'u0_a279': 'Huguito Ipial', 'jvk-editor2': 'Huguito Ipial',
    'u0_a70': 'Pablo Barrionuevo', 'jvk-editor5': 'Pablo Barrionuevo',
    'u0_a330': 'Mayra Benavides', 'mayralisseth201': 'Mayra Benavides',
    'u0_a362': 'Martha Simbaña', 'u0_a335': 'Martha Simbaña', 'jvk-editor4': 'Martha Simbaña',
    'u0_a2': 'JVK-DIGITALIZACION', 'jvk-digitalizacion': 'JVK-DIGITALIZACION',
    'u0_a302': 'Dylan Chavez', 'jvk-editor3': 'Dylan Chavez',
    'jvk-corp': 'Melany Recalde', 'u0_a200': 'Melany Recalde',
}

AZUL = colors.HexColor('#1e3a8a')
BORDE = colors.HexColor('#cbd5e1')
FONDO = colors.HexColor('#f8fafc')
GRIS_LBL = colors.HexColor('#475569')
TINTA = colors.HexColor('#0f172a')

DIAS = ['lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado', 'domingo']
MESES = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio',
         'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre']

R_MERC = 6378137.0
MUNDO = 2 * math.pi * R_MERC

# ─── Utilidades de formato ───────────────────────────────────────────────────


def fmt_num(v, dec=0):
    """Número al estilo es-EC: miles con punto, decimales con coma."""
    if v is None or v == '':
        return '—'
    try:
        n = float(v)
    except (TypeError, ValueError):
        return str(v)
    if dec == 0 and n == int(n):
        s = f'{int(n):,}'
    else:
        s = f'{n:,.{dec}f}'
    return s.replace(',', '§').replace('.', ',').replace('§', '.')


def parse_fecha(txt):
    """'2026-05-21T15:13:02...' → (aaaa, mm, dd) o None."""
    if not txt:
        return None
    m = re.match(r'(\d{4})-(\d{2})-(\d{2})', str(txt))
    return (int(m.group(1)), int(m.group(2)), int(m.group(3))) if m else None


def fecha_corta(txt):
    f = parse_fecha(txt)
    return f'{f[2]:02d}/{f[1]:02d}/{f[0]}' if f else '—'


def fecha_larga(txt):
    f = parse_fecha(txt)
    if not f:
        return '—'
    import datetime
    d = datetime.date(*f)
    return f'{DIAS[d.weekday()]}, {f[2]} de {MESES[f[1] - 1]} de {f[0]}'


def texto(v, vacio='—'):
    if v is None or str(v).strip() == '':
        return vacio
    return str(v).strip()


def es_uno(v):
    """Regla 18: un campo 1/0/vacío solo es Sí con `1`."""
    return str(v).strip() in ('1', '1.0', 'True', 'true')


def si_no_sindato(v):
    s = '' if v is None else str(v).strip()
    if s in ('1', '1.0', 'True', 'true'):
        return 'Sí'
    if s in ('0', '0.0', 'False', 'false'):
        return 'No'
    return 'Sin dato'


def esc(s):
    return (str(s).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;'))


# Observación de lote con cocina interna (UUID de ficha, técnico y timestamp de
# la unificación física): decisión de JAVIKO del 4-sep-2026 — NO va al PDF.
# Las observaciones de campo reales («no posee escrituras…») sí se muestran.
_RE_OBS_INTERNA = re.compile(r'\{[0-9a-fA-F-]{8,}\}|^\s*Unificaci[oó]n f[ií]sica',
                             re.IGNORECASE)


def obs_lote(txt):
    if not txt or _RE_OBS_INTERNA.search(str(txt)):
        return '—'
    return str(txt).strip()


def sanear_nombre(nombre):
    """Nombre válido para carpeta/archivo Windows."""
    s = re.sub(r'[\\/:*?"<>|]', ' ', str(nombre))
    s = re.sub(r'\s+', ' ', s).strip().rstrip('.')
    return s or 'SIN NOMBRE'


def wgs84_a_utm17s(lat, lon):
    """Conversión WGS84 → UTM zona 17S (respaldo si la ficha no trae UTM)."""
    a, f = 6378137.0, 1 / 298.257223563
    k0, e2 = 0.9996, f * (2 - f)
    ep2 = e2 / (1 - e2)
    lon0 = math.radians(-81.0)
    lat_r, lon_r = math.radians(lat), math.radians(lon)
    n = a / math.sqrt(1 - e2 * math.sin(lat_r) ** 2)
    t = math.tan(lat_r) ** 2
    c = ep2 * math.cos(lat_r) ** 2
    A = math.cos(lat_r) * (lon_r - lon0)
    m = a * ((1 - e2 / 4 - 3 * e2 ** 2 / 64 - 5 * e2 ** 3 / 256) * lat_r
             - (3 * e2 / 8 + 3 * e2 ** 2 / 32 + 45 * e2 ** 3 / 1024) * math.sin(2 * lat_r)
             + (15 * e2 ** 2 / 256 + 45 * e2 ** 3 / 1024) * math.sin(4 * lat_r)
             - (35 * e2 ** 3 / 3072) * math.sin(6 * lat_r))
    este = k0 * n * (A + (1 - t + c) * A ** 3 / 6
                     + (5 - 18 * t + t ** 2 + 72 * c - 58 * ep2) * A ** 5 / 120) + 500000
    norte = k0 * (m + n * math.tan(lat_r) * (A ** 2 / 2 + (5 - t + 9 * c + 4 * c ** 2) * A ** 4 / 24
                  + (61 - 58 * t + t ** 2 + 600 * c - 330 * ep2) * A ** 6 / 720)) + 10000000
    return este, norte


# ─── Codificación S01-C01-R001-F01 (aprobada por JAVIKO el 4-sep-2026) ───────
# S = sector por catálogo (regla 15) · C = número OFICIAL GLOBAL de la
# comunidad (CATALOGO_COMUNIDADES de constants.ts, el del listado del
# consorcio y el QField: C01-C22=S1, C23-C35=S2, C36-C50=S3) · R = titular
# dentro de su comunidad (por cédula; sin cédula, por apellidos+nombres),
# en orden alfabético de apellidos · F = fichas del titular: la principal
# F01 y las adicionales después, por clave catastral.
#
# La asignación se PERSISTE en public/geo/codificacion_fichas.json (fuente
# única): una vez impresa en los PDF no puede cambiar. En corridas futuras
# los códigos existentes se respetan y las fichas nuevas numeran al final.

CODIFICACION_JSON = os.path.join(GEO, 'codificacion_fichas.json')


def cargar_catalogo_numerado():
    """comunidad canónica → (n oficial 1-50, sector) desde constants.ts."""
    with open(os.path.join(APP_DIR, 'src', 'lib', 'constants.ts'), encoding='utf-8') as f:
        ts = f.read()
    patron = re.compile(
        r"\{\s*n:\s*(\d+),\s*sector:\s*'([^']+)',\s*oficial:\s*'([^']+)',"
        r"\s*datos:\s*'([^']+)'(,\s*oculta:\s*true)?\s*\}")
    cat = {}
    for m in patron.finditer(ts):
        if m.group(5):
            continue
        cat[canonica(m.group(4))] = (int(m.group(1)), m.group(2))
    if len(cat) != 50:
        print(f'⚠ Catálogo numerado: se esperaban 50 comunidades, salieron {len(cat)}')
    return cat


def _titular_id(p):
    ced = (p.get('cedula') or '').strip()
    if ced:
        return ced
    return 'NOM:' + normalizar(f"{p.get('apellidos') or ''} {p.get('nombres') or ''}")


def asignar_codigos(fichas):
    """Asigna (o relee) el código S-C-R-F de cada ficha y persiste el JSON.
    Deja el código en p['_codigo']."""
    catalogo = cargar_catalogo_numerado()
    if os.path.exists(CODIFICACION_JSON):
        with open(CODIFICACION_JSON, encoding='utf-8') as f:
            reg = json.load(f)
    else:
        reg = {'nota': 'Codificación S01-C01-R001-F01 del padrón, aprobada el '
                       '4-sep-2026. R por titular (cédula) en orden alfabético '
                       'dentro de su comunidad; F01 la principal, adicionales '
                       'por clave. NO renumerar: los códigos ya impresos en '
                       'PDF se conservan y lo nuevo numera al final.',
               'titulares': {}, 'fichas': {}}
    titulares, codigos = reg['titulares'], reg['fichas']
    nuevos_r = nuevos_f = 0

    por_com = defaultdict(list)
    for p in fichas:
        por_com[p['_com']].append(p)

    for com, lista in sorted(por_com.items()):
        if com not in catalogo:
            print(f'⚠ Comunidad sin número oficial en el catálogo: {com} '
                  f'({len(lista)} fichas SIN código)')
            continue
        n_com, sector = catalogo[com]
        s_num = int(sector.split()[-1])

        por_tit = defaultdict(list)
        for p in lista:
            por_tit[_titular_id(p)].append(p)

        def clave_alfabetica(tid):
            fichas_t = por_tit[tid]
            principales = [p for p in fichas_t if str(p.get('es_ficha_hija') or '') not in ('1', 'True', 'true')]
            ref = min(principales or fichas_t,
                      key=lambda p: (p.get('clave_catastral') or '', p.get('id') or ''))
            return (normalizar(ref.get('apellidos') or ''),
                    normalizar(ref.get('nombres') or ''), tid)

        r_max = max([v for k, v in titulares.items() if k.startswith(com + '|')] + [0])
        for tid in sorted(por_tit, key=clave_alfabetica):
            k_tit = f'{com}|{tid}'
            if k_tit not in titulares:
                r_max += 1
                titulares[k_tit] = r_max
                nuevos_r += 1
            r = titulares[k_tit]

            fichas_t = por_tit[tid]
            def orden_f(p):
                hija = str(p.get('es_ficha_hija') or '') in ('1', 'True', 'true')
                return (1 if hija else 0, p.get('clave_catastral') or '', p.get('id') or '')
            usados_f = [int(codigos[p['id']].rsplit('-F', 1)[1])
                        for p in fichas_t if p.get('id') in codigos]
            f_max = max(usados_f + [0])
            for p in sorted(fichas_t, key=orden_f):
                fid = p.get('id') or ''
                if fid not in codigos:
                    f_max += 1
                    codigos[fid] = f'S{s_num:02d}-C{n_com:02d}-R{r:03d}-F{f_max:02d}'
                    nuevos_f += 1
                p['_codigo'] = codigos[fid]

    if nuevos_f or not os.path.exists(CODIFICACION_JSON):
        reg['actualizado'] = time.strftime('%Y-%m-%d')
        with open(CODIFICACION_JSON, 'w', encoding='utf-8') as f:
            json.dump(reg, f, ensure_ascii=False, indent=1)
        print(f'✔ Codificación: {nuevos_f} códigos nuevos ({nuevos_r} titulares), '
              f'{len(codigos)} en total → {CODIFICACION_JSON}')
    else:
        print(f'✔ Codificación releída sin cambios ({len(codigos)} códigos)')
    dup = len(codigos) - len(set(codigos.values()))
    if dup:
        print(f'✖ ¡{dup} códigos DUPLICADOS en la codificación! Revisar antes de generar.')
        sys.exit(1)


# ─── Mosaicos satelitales Esri con caché en disco ────────────────────────────

TILES_DIR = None          # se fija en main() según --salida
TILES_FALLIDOS = 0


def _merc(lon, lat):
    return (math.radians(lon) * R_MERC,
            math.log(math.tan(math.pi / 4 + math.radians(lat) / 2)) * R_MERC)


def _tile(z, x, y):
    """Mosaico Esri World Imagery, del caché en disco o descargado (3 intentos)."""
    global TILES_FALLIDOS
    ruta = os.path.join(TILES_DIR, str(z), str(x), f'{y}.jpg')
    if os.path.exists(ruta) and os.path.getsize(ruta) > 0:
        try:
            return Image.open(ruta).convert('RGB')
        except Exception:
            pass
    url = ('https://server.arcgisonline.com/ArcGIS/rest/services/'
           f'World_Imagery/MapServer/tile/{z}/{y}/{x}')
    req = urllib.request.Request(url, headers={'User-Agent': 'padron-app'})
    for _ in range(3):
        try:
            with urllib.request.urlopen(req, timeout=25) as r:
                datos = r.read()
            img = Image.open(io.BytesIO(datos)).convert('RGB')
            os.makedirs(os.path.dirname(ruta), exist_ok=True)
            with open(ruta, 'wb') as fh:
                fh.write(datos)
            return img
        except Exception:
            continue
    TILES_FALLIDOS += 1
    return Image.new('RGB', (256, 256), (226, 232, 240))


def base_satelital(x0, x1, y0, y1, w_px, h_px):
    """Imagen (w_px × h_px) del extent mercator dado, compuesta de mosaicos."""
    res = (x1 - x0) / w_px
    z = max(3, min(18, int(round(math.log2(MUNDO / 256 / res)))))
    n = 2 ** z
    tx0 = int((x0 + MUNDO / 2) / MUNDO * n)
    tx1 = int((x1 + MUNDO / 2) / MUNDO * n)
    ty0 = int((MUNDO / 2 - y1) / MUNDO * n)
    ty1 = int((MUNDO / 2 - y0) / MUNDO * n)
    faltan = [(z, tx, ty) for ty in range(ty0, ty1 + 1) for tx in range(tx0, tx1 + 1)
              if not os.path.exists(os.path.join(TILES_DIR, str(z), str(tx), f'{ty}.jpg'))]
    if len(faltan) > 3:
        with ThreadPoolExecutor(max_workers=8) as ex:
            list(ex.map(lambda t: _tile(*t), faltan))
    mosaico = Image.new('RGB', ((tx1 - tx0 + 1) * 256, (ty1 - ty0 + 1) * 256))
    for ty in range(ty0, ty1 + 1):
        for tx in range(tx0, tx1 + 1):
            mosaico.paste(_tile(z, tx, ty), ((tx - tx0) * 256, (ty - ty0) * 256))
    # recorte sub-mosaico del extent pedido y reescalado al tamaño final
    mx0 = tx0 / n * MUNDO - MUNDO / 2
    my1 = MUNDO / 2 - ty0 / n * MUNDO
    res_z = MUNDO / 256 / n
    px0 = (x0 - mx0) / res_z
    py0 = (my1 - y1) / res_z
    px1 = (x1 - mx0) / res_z
    py1 = (my1 - y0) / res_z
    rec = mosaico.crop((int(px0), int(py0), max(int(px1), int(px0) + 1),
                        max(int(py1), int(py0) + 1)))
    return rec.resize((w_px, h_px), Image.LANCZOS)


def _linea_discontinua(draw, puntos, color, ancho, patron=(14, 8)):
    """PIL no trae líneas discontinuas: se trocea a mano."""
    on, off = patron
    resto, dibujando = on, True
    for (x1, y1), (x2, y2) in zip(puntos, puntos[1:]):
        seg = math.hypot(x2 - x1, y2 - y1)
        if seg == 0:
            continue
        ux, uy = (x2 - x1) / seg, (y2 - y1) / seg
        pos = 0.0
        cx, cy = x1, y1
        while pos < seg:
            paso = min(resto, seg - pos)
            nx, ny = cx + ux * paso, cy + uy * paso
            if dibujando:
                draw.line([(cx, cy), (nx, ny)], fill=color, width=ancho)
            cx, cy, pos = nx, ny, pos + paso
            resto -= paso
            if resto <= 0:
                dibujando = not dibujando
                resto = on if dibujando else off


def _anillos_geom(geom):
    """Todos los anillos exteriores+interiores de un Polygon/MultiPolygon."""
    if not geom:
        return []
    if geom['type'] == 'Polygon':
        return list(geom['coordinates'])
    if geom['type'] == 'MultiPolygon':
        return [a for poli in geom['coordinates'] for a in poli]
    return []


_FUENTE_MAPA = None


def _fuente_mapa(tam):
    global _FUENTE_MAPA
    try:
        return ImageFont.truetype(r'C:\Windows\Fonts\arialbd.ttf', tam)
    except Exception:
        return ImageFont.load_default()


def mapa_regional(ficha, ctx):
    """Mapa 1: satelital zoom amplio con parroquias, recuadro localizador y
    punto del predio — calcado del bloque 'Ubicación Regional' de la web."""
    lat, lon = ficha['_lat'], ficha['_lon']
    W, H, S = 690, 470, 2
    ancho_m = 26000.0
    cx, cy = _merc(lon, lat)
    alto_m = ancho_m * H / W
    x0, x1 = cx - ancho_m / 2, cx + ancho_m / 2
    y0, y1 = cy - alto_m / 2, cy + alto_m / 2
    img = base_satelital(x0, x1, y0, y1, W * S, H * S)

    def px(mx, my):
        return ((mx - x0) / (x1 - x0) * W * S, (y1 - my) / (y1 - y0) * H * S)

    capa = Image.new('RGBA', img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(capa)
    for anillo in ctx['parroquias_anillos']:
        pts = [px(*p) for p in anillo]
        _linea_discontinua(d, pts, (255, 255, 255, 235), 3, (16, 9))
    # recuadro localizador amarillo (mismas proporciones que la web: ±0.012/±0.015°)
    e1 = _merc(lon - 0.015, lat - 0.012)
    e2 = _merc(lon + 0.015, lat + 0.012)
    ra, rb = px(*e1), px(*e2)
    rect = [(ra[0], ra[1]), (rb[0], ra[1]), (rb[0], rb[1]), (ra[0], rb[1]), (ra[0], ra[1])]
    _linea_discontinua(d, rect, (250, 204, 21, 255), 5, (20, 10))
    pc = px(cx, cy)
    d.ellipse([pc[0] - 9, pc[1] - 9, pc[0] + 9, pc[1] + 9],
              fill=(239, 68, 68, 255), outline=(255, 255, 255, 255), width=3)
    img = Image.alpha_composite(img.convert('RGBA'), capa)

    # etiqueta de ubicación (Provincia › Cantón › Parroquia › Comunidad)
    etiqueta = (f"PICHINCHA › CAYAMBE › {texto(ficha.get('parroquia'), 'SIN PARROQUIA')} › "
                f"{texto(ficha.get('sector_comunidad') or ficha.get('comunidad'), 'SIN COMUNIDAD')}")
    d2 = ImageDraw.Draw(img)
    fnt = _fuente_mapa(22)
    caja = d2.textbbox((0, 0), etiqueta, font=fnt)
    d2.rectangle([8, 8, min(caja[2] + 28, W * S - 8), caja[3] + 24],
                 fill=(15, 23, 42, 195))
    d2.text((18, 14), etiqueta, font=fnt, fill=(248, 250, 252, 255))
    return img.convert('RGB').resize((W, H), Image.LANCZOS)


def mapa_emplazamiento(ficha, ctx):
    """Mapa 2: satelital cerrado con el polígono del predio en rojo, los
    vecinos en gris y el punto GPS en azul — el 'Emplazamiento Predial'."""
    lat, lon = ficha['_lat'], ficha['_lon']
    W, H, S = 690, 470, 2
    feat = ficha.get('_poligono')
    if feat:
        xs, ys = [], []
        for anillo in _anillos_geom(feat['geometry']):
            for p in anillo:
                mx, my = _merc(p[0], p[1])
                xs.append(mx)
                ys.append(my)
        cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
        ancho_m = max((max(xs) - min(xs)) * 1.6, (max(ys) - min(ys)) * 1.6 * W / H, 320.0)
    else:
        cx, cy = _merc(lon, lat)
        ancho_m = 500.0
    alto_m = ancho_m * H / W
    x0, x1 = cx - ancho_m / 2, cx + ancho_m / 2
    y0, y1 = cy - alto_m / 2, cy + alto_m / 2
    img = base_satelital(x0, x1, y0, y1, W * S, H * S)

    def px(mx, my):
        return ((mx - x0) / (x1 - x0) * W * S, (y1 - my) / (y1 - y0) * H * S)

    capa = Image.new('RGBA', img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(capa)
    for vecino in ficha.get('_vecinos', []):
        for anillo in _anillos_geom(vecino['geometry']):
            pts = [px(*_merc(p[0], p[1])) for p in anillo]
            d.line(pts, fill=(148, 163, 184, 220), width=2)
    if feat:
        for anillo in _anillos_geom(feat['geometry']):
            pts = [px(*_merc(p[0], p[1])) for p in anillo]
            d.polygon(pts, fill=(239, 68, 68, 60))
            d.line(pts + [pts[0]], fill=(239, 68, 68, 255), width=6)
    pgps = px(*_merc(lon, lat))
    d.ellipse([pgps[0] - 10, pgps[1] - 10, pgps[0] + 10, pgps[1] + 10],
              fill=(59, 130, 246, 255), outline=(255, 255, 255, 255), width=3)
    img = Image.alpha_composite(img.convert('RGBA'), capa)
    return img.convert('RGB').resize((W, H), Image.LANCZOS)


def imagen_a_flowable(img_pil, ancho_mm, alto_mm, calidad=74):
    buf = io.BytesIO()
    img_pil.save(buf, 'JPEG', quality=calidad)
    buf.seek(0)
    return RLImage(buf, width=ancho_mm * mm, height=alto_mm * mm)


# ─── Estilos reportlab ───────────────────────────────────────────────────────

ST_LBL = ParagraphStyle('lbl', fontName='Helvetica-Bold', fontSize=5.3,
                        leading=6.3, textColor=GRIS_LBL)
ST_VAL = ParagraphStyle('val', fontName='Helvetica', fontSize=7.6,
                        leading=8.8, textColor=TINTA)
ST_VAL_B = ParagraphStyle('valb', parent=ST_VAL, fontName='Helvetica-Bold')
ST_SEC = ParagraphStyle('sec', fontName='Helvetica-Bold', fontSize=8.2,
                        leading=10, textColor=colors.white)
ST_TH = ParagraphStyle('th', fontName='Helvetica-Bold', fontSize=6.4,
                       leading=7.6, textColor=colors.HexColor('#1e293b'))
ST_TD = ParagraphStyle('td', fontName='Helvetica', fontSize=7.0,
                       leading=8.2, textColor=TINTA)
ST_NOTA = ParagraphStyle('nota', fontName='Helvetica-Oblique', fontSize=7.2,
                         leading=8.6, textColor=colors.HexColor('#64748b'))

ANCHO_UTIL = 190 * mm
COL4 = [ANCHO_UTIL / 4.0] * 4


def titulo_seccion(txt):
    t = Table([[Paragraph(txt.upper(), ST_SEC)]], colWidths=[ANCHO_UTIL])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), AZUL),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 2.5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2.5),
    ]))
    return [Spacer(0, 3 * mm), t, Spacer(0, 1.5 * mm)]


def grid(filas):
    """Rejilla de casillas etiqueta+valor (como .grid-details de la web).
    filas = lista de filas; cada fila, lista de (label, value, span)."""
    data, spans = [], []
    for r, fila in enumerate(filas):
        celdas, c = [], 0
        for label, value, span in fila:
            contenido = [Paragraph(esc(label).upper(), ST_LBL),
                         Paragraph(esc(value), ST_VAL)]
            celdas.append(contenido)
            if span > 1:
                spans.append(('SPAN', (c, r), (c + span - 1, r)))
                celdas.extend([''] * (span - 1))
            c += span
        while c < 4:
            celdas.append('')
            c += 1
        data.append(celdas)
    t = Table(data, colWidths=COL4)
    estilo = [
        ('GRID', (0, 0), (-1, -1), 0.5, BORDE),
        ('BACKGROUND', (0, 0), (-1, -1), FONDO),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ] + spans
    t.setStyle(TableStyle(estilo))
    return t


def tabla_datos(cabeceras, filas, anchos):
    data = [[Paragraph(esc(h).upper(), ST_TH) for h in cabeceras]]
    for fila in filas:
        data.append([Paragraph(esc(v), ST_TD) for v in fila])
    t = Table(data, colWidths=anchos, repeatRows=1)
    t.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.5, BORDE),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e2e8f0')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, FONDO]),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ]))
    return t


def destino(item):
    partes = []
    if es_uno(item.get('es_autoconsumo')):
        partes.append('Autoconsumo')
    if es_uno(item.get('es_mercado')):
        partes.append('Mercado')
    if es_uno(item.get('es_agroindustria')):
        partes.append('Agroindustria')
    if es_uno(item.get('es_exportacion')):
        partes.append('Exportación')
    return ', '.join(partes) if partes else '—'


# ─── Composición del PDF de una ficha ────────────────────────────────────────


def cabecera_pie(canv, doc, ficha):
    canv.saveState()
    w, h = A4
    # cabecera: logos + títulos
    y_top = h - 8 * mm
    for ruta, x in ((os.path.join(PUB, 'logo-izq.png'), 10 * mm),
                    (os.path.join(PUB, 'logo-der.png'), w - 32 * mm)):
        try:
            canv.drawImage(ImageReader(ruta), x, y_top - 14 * mm, width=22 * mm,
                           height=14 * mm, preserveAspectRatio=True, mask='auto')
        except Exception:
            pass
    canv.setFillColor(colors.HexColor('#64748b'))
    canv.setFont('Helvetica-Bold', 6.3)
    canv.drawCentredString(w / 2, y_top - 3.2 * mm, PROJECT_TITLE)
    canv.setFillColor(TINTA)
    canv.setFont('Helvetica-Bold', 8.6)
    canv.drawCentredString(w / 2, y_top - 7.4 * mm, PROJECT_SUBTITLE)
    canv.setFillColor(colors.HexColor('#64748b'))
    canv.setFont('Helvetica', 6.3)
    canv.drawCentredString(w / 2, y_top - 10.8 * mm, PROJECT_SUBTITLE_ALCANCE)
    canv.drawCentredString(w / 2, y_top - 13.6 * mm, PROJECT_LOCATION)
    canv.setStrokeColor(AZUL)
    canv.setLineWidth(1.6)
    canv.line(10 * mm, y_top - 16 * mm, w - 10 * mm, y_top - 16 * mm)
    # pie
    canv.setStrokeColor(BORDE)
    canv.setLineWidth(0.5)
    canv.line(10 * mm, 11 * mm, w - 10 * mm, 11 * mm)
    canv.setFillColor(colors.HexColor('#64748b'))
    canv.setFont('Helvetica', 6.2)
    inv = ficha.get('_investigador') or '—'
    canv.drawString(10 * mm, 7.5 * mm, f'Investigador: {inv} · AP&CATASTROS')
    canv.drawRightString(w - 10 * mm, 7.5 * mm,
                         f'CONSORCIO CAYAMBE SPT · Datos al {FECHA_CORTE} · pág. {canv.getPageNumber()}')
    canv.restoreState()


def construir_historia(ficha, ctx, con_mapa, con_foto=False):
    p = ficha
    historia = []

    # barra de identificación — el CÓDIGO es la codificación S-C-R-F del
    # padrón (el codigo_final del gpkg, «S-C-P001», se repite y no identifica)
    ident = (f"<b>CÓDIGO:</b> {esc(texto(p.get('_codigo')))}   |   "
             f"<b>CLAVE:</b> {esc(texto(p.get('clave_catastral'), 'S/N'))}   |   "
             f"<b>REGISTRO:</b> {fecha_corta(p.get('fecha_creacion'))}")
    st_id = ParagraphStyle('ident', fontName='Helvetica', fontSize=7.6,
                           leading=9, alignment=1, textColor=TINTA)
    t = Table([[Paragraph(ident, st_id)]], colWidths=[ANCHO_UTIL])
    t.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 0.5, BORDE),
        ('BACKGROUND', (0, 0), (-1, -1), FONDO),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    historia.append(t)
    if str(p.get('es_ficha_hija') or '') in ('1', 'True', 'true'):
        madre = ctx['fichas_por_id'].get(p.get('ficha_madre_id') or '')
        ref = (f" — vinculada a la ficha principal {texto(madre.get('_codigo'))} "
               f"(clave {texto(madre.get('clave_catastral'))})" if madre else '')
        historia.append(Spacer(0, 1 * mm))
        historia.append(Paragraph(f'<b>FICHA ADICIONAL</b>{esc(ref)}',
                                  ParagraphStyle('hija', parent=ST_NOTA, alignment=1)))

    # ── 1. Datos del propietario ──
    historia += titulo_seccion('1. Datos del Propietario / Titular')
    nombre = texto(p.get('propietario')) if p.get('propietario') else \
        f"{texto(p.get('apellidos'), '')} {texto(p.get('nombres'), '')}".strip() or '—'
    historia.append(grid([
        [('Apellidos y Nombres', nombre, 2),
         ('Cédula Identidad', texto(p.get('cedula')), 1),
         ('Teléfono Celular', texto(p.get('telefono_celular')), 1)],
        [('Parroquia', texto(p.get('parroquia')), 1),
         ('Sector', texto(p.get('sector')), 1),
         ('Comunidad', texto(p.get('comunidad')), 1),
         ('Sector Comunidad', texto(p.get('sector_comunidad')), 1)],
        [('Hijos Varones', texto(p.get('hijos_hombres'), '0'), 1),
         ('Hijas Mujeres', texto(p.get('hijos_mujeres'), '0'), 1),
         ('Tenencia del Predio', texto(p.get('tenencia_predio')), 1),
         ('Instrucción', texto(p.get('nivel_instruccion')), 1)],
    ]))

    # ── 2. Predio y riego ──
    historia += titulo_seccion('2. Información del Predio y de Riego')
    metodo = ' · '.join(filter(None, [
        f"Aspersión ({fmt_num(p.get('metodo_aspersion_pct'))}%)" if p.get('metodo_aspersion_pct') else '',
        f"Gravedad ({fmt_num(p.get('metodo_gravedad_pct'))}%)" if p.get('metodo_gravedad_pct') else '',
        f"Goteo ({fmt_num(p.get('metodo_goteo_pct'))}%)" if p.get('metodo_goteo_pct') else '',
    ])) or '—'
    caudal = (f"{fmt_num(p.get('caudal_valor'), 2)} l/s ({texto(p.get('caudal_tipo'), '')})".replace(' ()', '')
              if p.get('caudal_valor') else '—')
    turno = (f"{fmt_num(p.get('dias_riego'))} días / {fmt_num(p.get('horas_turno') or 0)} horas"
             if p.get('dias_riego') else '—')
    tarifa = (f"${fmt_num(p.get('valor_tarifa'), 2)} ({texto(p.get('tipo_tarifa'), '')})".replace(' ()', '')
              if p.get('valor_tarifa') else '—')
    historia.append(grid([
        [('Área Total (declarada)', f"{fmt_num(p.get('area_total'), 2)} m²", 1),
         ('Área con Riego', f"{fmt_num(p.get('area_riego'), 2)} m²", 1),
         ('Área sin Riego', f"{fmt_num(p.get('area_sin_riego'), 2)} m²", 1),
         ('Reservorio', texto(p.get('tiene_reservorio')), 1)],
        [('Organización de Riego', texto(p.get('org_riego')), 2),
         ('Canal', texto(p.get('canal')), 1),
         ('Caudal', caudal, 1)],
        [('Método Riego', metodo, 2),
         ('Frecuencia', texto(p.get('frecuencia_riego')), 1),
         ('Turno Riego', turno, 1)],
        [('Tarifa de Riego', tarifa, 4)],
    ]))

    # ── 3. Otros predios del titular ──
    historia += titulo_seccion('3. Otros Predios del Titular en la Comunidad')
    adicionales = ctx['adicionales'].get(p.get('id') or '', [])
    if not adicionales:
        historia.append(Paragraph(
            'No se registraron predios adicionales asociados a este titular.', ST_NOTA))
    else:
        filas = [[texto(a.get('clave_catastral_otro')),
                  f"{fmt_num(a.get('area_total_otro'), 2)} m²",
                  f"{fmt_num(a.get('area_lote_asignado_otro'), 2)} m²",
                  f"{fmt_num(a.get('area_riego_otro'), 2)} m²",
                  f"{fmt_num(a.get('area_sin_riego_otro'), 2)} m²",
                  obs_lote(a.get('observaciones_otro'))]
                 for a in adicionales]
        historia.append(tabla_datos(
            ['Clave Catastral Adicional', 'Área Total', 'Área Lote Asignado',
             'Área Riego', 'Área sin Riego', 'Observaciones del Lote'],
            filas, [36 * mm, 24 * mm, 27 * mm, 24 * mm, 24 * mm, 55 * mm]))

    # ── 4. Servicios y ubicación ──
    historia += titulo_seccion('4. Servicios Básicos e Infraestructura')
    material = (texto(p.get('material_constr_otro'))
                if (p.get('material_construccion') or '') == 'Otros'
                else texto(p.get('material_construccion')))
    utm_e, utm_n = p.get('coord_x_utm'), p.get('coord_y_utm')
    if (not utm_e or not utm_n) and p.get('_lat') is not None:
        utm_e, utm_n = wgs84_a_utm17s(p['_lat'], p['_lon'])
    historia.append(grid([
        [('Agua Consumo', si_no_sindato(p.get('agua_consumo')), 1),
         ('Energía Eléctrica', si_no_sindato(p.get('energia_electrica')), 1),
         ('Material de Construcción', material, 2)],
        [('Cota Altura', f"{fmt_num(p.get('cota_msnm'))} msnm" if p.get('cota_msnm') else '—', 1),
         ('Este (X)', f'{fmt_num(utm_e, 1)} m' if utm_e else '—', 1),
         ('Norte (Y)', f'{fmt_num(utm_n, 1)} m' if utm_n else '—', 1),
         ('Zona UTM', '17S', 1)],
        [('Referencia Cartográfica',
          'Polígono del predio referenciado a la capa Catastro Rural – GADM Cayambe '
          '(insumo municipal). Datum WGS 84 · Zona 17S.', 4)],
    ]))

    # ── 5. Actividad agropecuaria ──
    historia += titulo_seccion('5. Producción y Actividad Agropecuaria')
    historia.append(grid([
        [('Actividad Productiva Principal', texto(p.get('actividad_productiva')), 2),
         ('Soberanía Alimentaria',
          f"{fmt_num(p.get('soberania_aliment_pct'))}%" if p.get('soberania_aliment_pct') else '—', 1),
         ('Comercialización',
          f"{fmt_num(p.get('act_productivas_pct'))}%" if p.get('act_productivas_pct') else '—', 1)],
    ]))
    historia.append(Spacer(0, 1.5 * mm))

    cultivos = ctx['cultivos'].get(p.get('id') or '', [])
    animales = ctx['animales'].get(p.get('id') or '', [])
    f_cult = [[(texto(c.get('tipo_cultivo_otro')) if (c.get('tipo_cultivo') or '') == 'Otros'
                else texto(c.get('tipo_cultivo'))) + (' (P)' if es_uno(c.get('es_principal')) else ''),
               f"{fmt_num(c.get('superficie_m2'), 2)} m²" if c.get('superficie_m2') else '—',
               destino(c)] for c in cultivos]
    f_anim = [[texto(a.get('especie_otro')) if (a.get('especie') or '') == 'Otros'
               else texto(a.get('especie')),
               fmt_num(a.get('cantidad')), destino(a)] for a in animales]
    mitad = (ANCHO_UTIL - 4 * mm) / 2
    sub = [Paragraph('CULTIVOS AGRÍCOLAS', ST_TH),
           Paragraph('PRODUCCIÓN PECUARIA', ST_TH)]
    caja_c = (tabla_datos(['Cultivo', 'Área', 'Destino'], f_cult,
                          [mitad * 0.42, mitad * 0.3, mitad * 0.28])
              if f_cult else Paragraph('Sin cultivos registrados.', ST_NOTA))
    caja_a = (tabla_datos(['Especie', 'Cantidad', 'Destino'], f_anim,
                          [mitad * 0.42, mitad * 0.24, mitad * 0.34])
              if f_anim else Paragraph('Sin animales registrados.', ST_NOTA))
    if max(len(f_cult), len(f_anim)) <= 12:
        t = Table([sub, [caja_c, caja_a]], colWidths=[mitad, mitad])
        t.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'TOP'),
                               ('LEFTPADDING', (0, 0), (0, -1), 0),
                               ('RIGHTPADDING', (1, 0), (1, -1), 0),
                               ('BOTTOMPADDING', (0, 0), (-1, 0), 1.5)]))
        historia.append(t)
    else:  # tablas largas: apiladas para que puedan partirse entre páginas
        historia += [sub[0], Spacer(0, 1 * mm), caja_c, Spacer(0, 2 * mm),
                     sub[1], Spacer(0, 1 * mm), caja_a]

    # ── página 2: organización, mapas, foto y auditoría ──
    historia.append(PageBreak())
    historia += titulo_seccion('6. Organización Comunitaria y Auditoría')
    eleccion = (texto(p.get('como_elige_dir_otro'))
                if (p.get('como_elige_dir') or '') == 'Otros'
                else texto(p.get('como_elige_dir')))
    historia.append(grid([
        [('¿Conoce el Proyecto Presa?', texto(p.get('conoce_presa')), 2),
         ('Elección de Directivas', eleccion, 2)],
        [('Presidente Junta', texto(p.get('nom_presidente')), 1),
         ('Operador Sector', texto(p.get('operador_sector')), 1),
         ('Años Canal', texto(p.get('anios_sistema')), 1),
         ('Canal Longitud', f"{fmt_num(p.get('km_canal'), 1)} km" if p.get('km_canal') else '—', 1)],
        [('Capacitación (¿Recibió? / ¿Desea?)',
          f"Recibió: {texto(p.get('recibio_capacitacion'), 'No')} | "
          f"Desea: {texto(p.get('le_gustaria_cap'), 'No')}", 2),
         ('Temas Solicitados', texto(p.get('temas_capacitacion')), 2)],
    ]))

    # ── 7. Ubicación regional, emplazamiento y foto ──
    if con_mapa and p.get('_lat') is not None:
        historia.append(Spacer(0, 2.5 * mm))
        mitad = (ANCHO_UTIL - 4 * mm) / 2
        img_reg = imagen_a_flowable(mapa_regional(p, ctx), 92, 62)
        img_emp = imagen_a_flowable(mapa_emplazamiento(p, ctx), 92, 62)
        t = Table([[Paragraph('UBICACIÓN REGIONAL', ST_TH),
                    Paragraph('EMPLAZAMIENTO PREDIAL', ST_TH)],
                   [img_reg, img_emp]], colWidths=[mitad + 2 * mm, mitad + 2 * mm])
        t.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 0.5, BORDE),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e2e8f0')),
            ('ALIGN', (0, 1), (-1, 1), 'CENTER'),
            ('TOPPADDING', (0, 1), (-1, 1), 2),
            ('BOTTOMPADDING', (0, 1), (-1, 1), 2),
        ]))
        historia.append(t)
    elif con_mapa:
        historia.append(Spacer(0, 2 * mm))
        historia.append(Paragraph('Coordenadas geográficas no disponibles — '
                                  'la ficha no registra ubicación en campo.', ST_NOTA))

    # FOTOGRAFÍA: apagada por defecto (decisión de JAVIKO, 10-sep-2026). El
    # campo se llama `foto_predio` pero lo que los técnicos capturaron en campo
    # es el RETRATO DEL TITULAR (revisadas 40 de las 894: todas son personas en
    # asambleas, varias sosteniendo su cédula). No aporta dato catastral y son
    # datos personales que no deben viajar en el paquete del consorcio. Se
    # conserva el código tras `--con-foto` por si algún día hacen falta.
    foto_rel = p.get('foto_predio') if con_foto else None
    if foto_rel:
        ruta_foto = os.path.join(QFIELD_DIR, foto_rel.replace('/', os.sep))
        if os.path.exists(ruta_foto):
            try:
                imf = Image.open(ruta_foto)
                imf = ImageOps.exif_transpose(imf).convert('RGB')
                imf.thumbnail((1300, 1300), Image.LANCZOS)
                ratio = imf.height / imf.width
                w_mm = min(110.0, 62.0 / ratio)
                foto = imagen_a_flowable(imf, w_mm, w_mm * ratio, calidad=76)
                t = Table([[Paragraph('FOTOGRAFÍA DEL PREDIO', ST_TH)], [foto]],
                          colWidths=[ANCHO_UTIL])
                t.setStyle(TableStyle([
                    ('GRID', (0, 0), (-1, -1), 0.5, BORDE),
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e2e8f0')),
                    ('ALIGN', (0, 1), (-1, 1), 'CENTER'),
                    ('TOPPADDING', (0, 1), (-1, 1), 2),
                    ('BOTTOMPADDING', (0, 1), (-1, 1), 2),
                ]))
                historia += [Spacer(0, 2.5 * mm), t]
            except Exception:
                pass

    # consentimiento informado
    otorgado = str(p.get('consentimiento_inform')).strip() not in ('0', '0.0', 'False', 'false')
    st_cons = ParagraphStyle('cons', fontName='Helvetica', fontSize=7.2,
                             leading=8.6, textColor=colors.HexColor('#166534'))
    t = Table([[Paragraph(f"<b>{'OTORGADO' if otorgado else 'NO OTORGADO'}</b>", ParagraphStyle(
                    'chip', fontName='Helvetica-Bold', fontSize=6.4,
                    textColor=colors.HexColor('#15803d'), alignment=1)),
                Paragraph('<b>Consentimiento Informado:</b> El/la informante autoriza el uso '
                          'institucional de los datos recopilados en esta ficha para el Catastro '
                          'de Riego de Cayambe, conforme a la normativa de protección de datos '
                          'personales.', st_cons)]],
              colWidths=[26 * mm, ANCHO_UTIL - 26 * mm])
    t.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#bbf7d0')),
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f0fdf4')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    historia += [Spacer(0, 2.5 * mm), t]

    # bloque de responsables (4 columnas)
    inv = p.get('_investigador') or '—'
    def _resp(label, valor, sub):
        return [Paragraph(esc(label).upper(), ParagraphStyle(
                    'al', parent=ST_LBL, textColor=AZUL)),
                Paragraph(esc(valor), ST_VAL_B),
                Paragraph(esc(sub), ParagraphStyle(
                    'as', fontName='Helvetica', fontSize=5.4, leading=6.4,
                    textColor=colors.HexColor('#94a3b8')))]
    t = Table([[
        _resp('Informante', texto(p.get('informante')) if p.get('informante') else nombre,
              'Propietario / Titular'),
        _resp('Investigador (Técnico)', inv, 'Responsable del Levantamiento · AP&CATASTROS'),
        _resp('Supervisor', texto(p.get('supervisor')) if p.get('supervisor') else 'Téc. Steven Proaño',
              'AP CATASTROS'),
        _resp('Fecha de Registro', fecha_larga(p.get('fecha_creacion')), 'Registro en campo'),
    ]], colWidths=COL4)
    t.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 1, AZUL),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, BORDE),
        ('BACKGROUND', (0, 0), (-1, -1), FONDO),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    historia += [Spacer(0, 2.5 * mm), t]

    # observaciones — SOLO la vista externa (observaciones_cliente), como ve
    # el rol cliente en la web; el campo crudo es texto interno del catastro.
    if p.get('observaciones_cliente'):
        historia += [Spacer(0, 2 * mm),
                     Paragraph('OBSERVACIONES GENERALES', ST_LBL),
                     Paragraph(esc(p['observaciones_cliente']), ST_NOTA)]

    return historia


def generar_pdf(ficha, ctx, ruta, con_mapa, con_foto=False):
    doc = BaseDocTemplate(
        ruta, pagesize=A4,
        leftMargin=10 * mm, rightMargin=10 * mm,
        topMargin=27 * mm, bottomMargin=13 * mm,
        title=f"Ficha {texto(ficha.get('codigo_final'))} — {texto(ficha.get('clave_catastral'))}",
        author='AP&CATASTROS — Padrón Guanguilquí–Porotog')
    marco = Frame(10 * mm, 13 * mm, 190 * mm, A4[1] - 40 * mm, id='cuerpo')
    doc.addPageTemplates([PageTemplate(
        id='pagina', frames=[marco],
        onPage=lambda c, d: cabecera_pie(c, d, ficha))])
    doc.build(construir_historia(ficha, ctx, con_mapa, con_foto))


# ─── Carga de datos ──────────────────────────────────────────────────────────


def cargar_contexto(con_mapa):
    print('Cargando datos de public/geo/ ...')
    with open(os.path.join(GEO, 'fichas_predios.geojson'), encoding='utf-8') as f:
        feats = json.load(f)['features']
    fichas = []
    for ft in feats:
        p = dict(ft['properties'])
        g = ft.get('geometry')
        if g and g.get('type') == 'Point':
            p['_lon'], p['_lat'] = g['coordinates'][0], g['coordinates'][1]
        else:
            p['_lon'] = p['_lat'] = None
        p['_com'] = canonica(p.get('comunidad') or '')
        p['_sector'] = COM_A_SECTOR.get(normalizar(p['_com']))
        fichas.append(p)

    def agrupar(nombre):
        with open(os.path.join(GEO, nombre), encoding='utf-8') as f:
            datos = json.load(f)
        d = defaultdict(list)
        for r in datos:
            d[r.get('ficha_id') or ''].append(r)
        return d

    ctx = {
        'cultivos': agrupar('cultivos.json'),
        'animales': agrupar('animales.json'),
        'adicionales': agrupar('predios_adicionales.json'),
        'fichas_por_id': {p.get('id') or '': p for p in fichas},
    }

    # Investigador a mostrar. En las hijas generadas en bloque (creado_por
    # AUTO-SECCION7, sin mapeo en TECNICOS) se muestra el técnico de su ficha
    # madre — el levantamiento real es suyo (decisión de JAVIKO, 4-sep-2026).
    for p in fichas:
        creado = p.get('creado_por') or ''
        nombre = TECNICOS.get(creado)
        if not nombre:
            madre = ctx['fichas_por_id'].get(p.get('ficha_madre_id') or '')
            if madre:
                nombre = TECNICOS.get(madre.get('creado_por') or '')
        p['_investigador'] = nombre or creado or '—'

    if con_mapa:
        with open(os.path.join(GEO, 'catastro_geo.geojson'), encoding='utf-8') as f:
            cat = json.load(f)['features']
        por_clave, rejilla = {}, defaultdict(list)
        for ft in cat:
            clave = (ft.get('properties', {}).get('clave_cata') or '').strip()
            if clave:
                por_clave.setdefault(clave, ft)
            anillos = _anillos_geom(ft.get('geometry'))
            if anillos and anillos[0]:
                p0 = anillos[0][0]
                ft['_p0'] = p0
                rejilla[(int(p0[0] / 0.008), int(p0[1] / 0.008))].append(ft)
        ctx['catastro_por_clave'] = por_clave
        ctx['catastro_rejilla'] = rejilla

        with open(os.path.join(GEO, 'parroquias.geojson'), encoding='utf-8') as f:
            parr = json.load(f)['features']
        ctx['parroquias_anillos'] = [
            [_merc(pt[0], pt[1]) for pt in anillo]
            for ft in parr for anillo in _anillos_geom(ft.get('geometry'))]

        # resolver polígono (regla 14: clave manda, cod_poligono respaldo),
        # centroide de respaldo y vecinos (±0.008°, como la web)
        for p in fichas:
            clave = (p.get('clave_catastral') or '').strip()
            feat = por_clave.get(clave) or por_clave.get((p.get('cod_poligono') or '').strip())
            p['_poligono'] = feat
            if p['_lat'] is None and feat:
                xs = [q[0] for a in _anillos_geom(feat['geometry']) for q in a]
                ys = [q[1] for a in _anillos_geom(feat['geometry']) for q in a]
                if xs:
                    p['_lon'], p['_lat'] = sum(xs) / len(xs), sum(ys) / len(ys)
            if p['_lat'] is not None:
                cx, cy = int(p['_lon'] / 0.008), int(p['_lat'] / 0.008)
                vecinos = []
                for dx in (-1, 0, 1):
                    for dy in (-1, 0, 1):
                        for ft in rejilla.get((cx + dx, cy + dy), []):
                            p0 = ft['_p0']
                            if (abs(p0[1] - p['_lat']) < 0.008 and abs(p0[0] - p['_lon']) < 0.008
                                    and (ft.get('properties', {}).get('clave_cata') or '').strip() != clave):
                                vecinos.append(ft)
                p['_vecinos'] = vecinos[:400]

    return fichas, ctx


# ─── Índice Excel ────────────────────────────────────────────────────────────


def escribir_indice(filas, salida):
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill
    wb = Workbook()
    ws = wb.active
    ws.title = 'Índice de fichas'
    cab = ['Sector', 'Comunidad (carpeta)', 'Código', 'Clave catastral',
           'Titular', 'Cédula', 'Tipo de ficha', 'Archivo PDF (ruta relativa)']
    ws.append(cab)
    for c in ws[1]:
        c.font = Font(bold=True, color='FFFFFF')
        c.fill = PatternFill('solid', fgColor='1E3A8A')
    for fila in filas:
        ws.append(fila)
    anchos = [10, 30, 18, 22, 38, 13, 12, 80]
    for i, a in enumerate(anchos, 1):
        ws.column_dimensions[chr(64 + i)].width = a
    ws.freeze_panes = 'A2'
    ws.auto_filter.ref = ws.dimensions
    ruta = os.path.join(salida, 'INDICE DE FICHAS.xlsx')
    wb.save(ruta)
    print(f'✔ Índice: {ruta} ({len(filas)} filas)')


# ─── Main ────────────────────────────────────────────────────────────────────


def main():
    global TILES_DIR
    ap = argparse.ArgumentParser(description='Fichas del padrón en PDF, por sector y comunidad')
    ap.add_argument('--comunidad', action='append', default=[],
                    help='limitar a esta(s) comunidad(es) — nombre canónico')
    ap.add_argument('--clave', action='append', default=[], help='limitar a esta(s) clave(s)')
    ap.add_argument('--limite', type=int, default=0, help='generar solo N fichas (medición)')
    ap.add_argument('--sin-mapa', action='store_true', help='fichas sin mapas satelitales')
    ap.add_argument('--con-foto', action='store_true',
                    help='incrustar la foto de campo (retrato del titular): NO se usa '
                         'en la entrega al consorcio, ver la nota en construir_historia')
    ap.add_argument('--rehacer', action='store_true', help='regenerar aunque el PDF exista')
    ap.add_argument('--indice', action='store_true', help='solo escribir el índice Excel')
    ap.add_argument('--salida', default=SALIDA_DEF)
    args = ap.parse_args()

    con_mapa = not args.sin_mapa
    os.makedirs(args.salida, exist_ok=True)
    TILES_DIR = os.path.join(args.salida, '.tiles')

    fichas, ctx = cargar_contexto(con_mapa and not args.indice)
    # la codificación se asigna SIEMPRE sobre el padrón completo (aunque se
    # genere un lote filtrado): los números no dependen del filtro de hoy
    asignar_codigos(fichas)

    filtro_com = {normalizar(canonica(c)) for c in args.comunidad}
    filtro_clave = {c.strip() for c in args.clave}
    lote = [p for p in fichas
            if (not filtro_com or normalizar(p['_com']) in filtro_com)
            and (not filtro_clave or (p.get('clave_catastral') or '').strip() in filtro_clave)]
    lote.sort(key=lambda p: (p['_sector'] or 'Z', p['_com'],
                             p.get('_codigo') or 'Z', p.get('clave_catastral') or ''))
    if args.limite:
        lote = lote[:args.limite]

    sin_sector = [p for p in lote if not p['_sector']]
    if sin_sector:
        print(f'⚠ {len(sin_sector)} fichas sin sector en el catálogo — NO se generan:')
        for p in sin_sector[:10]:
            print(f"   {p.get('codigo_final')} · comunidad «{p.get('comunidad')}»")
        lote = [p for p in lote if p['_sector']]

    # rutas de salida y filas del índice. codigo_final NO es único en el padrón
    # (S-C-P001 se repite), así que ante colisión de nombre se numera (2), (3)…
    trabajos, indice, usados = [], [], set()
    for p in lote:
        carpeta = os.path.join(args.salida, sanear_nombre(p['_sector']),
                               sanear_nombre(p['_com']))
        titular = texto(p.get('propietario')) if p.get('propietario') else \
            f"{texto(p.get('apellidos'), '')} {texto(p.get('nombres'), '')}".strip() or 'SIN NOMBRE'
        base = sanear_nombre(f"{texto(p.get('_codigo'), 'SIN-CODIGO')} - "
                             f"{texto(p.get('clave_catastral'), 'SIN-CLAVE')} - "
                             f"{titular[:60]}")
        nombre, n = base + '.pdf', 1
        while os.path.join(carpeta, nombre).lower() in usados:
            n += 1
            nombre = f'{base} ({n}).pdf'
        ruta = os.path.join(carpeta, nombre)
        usados.add(ruta.lower())
        trabajos.append((p, ruta))
        indice.append([p['_sector'], p['_com'],
                       texto(p.get('_codigo'), ''), texto(p.get('clave_catastral'), ''),
                       titular, texto(p.get('cedula'), ''),
                       'Adicional' if str(p.get('es_ficha_hija') or '') in ('1', 'True', 'true') else 'Principal',
                       os.path.relpath(ruta, args.salida)])

    if args.indice:
        escribir_indice(indice, args.salida)
        return

    print(f'A generar: {len(trabajos)} fichas '
          f"({'con' if con_mapa else 'sin'} mapas) → {args.salida}")
    t0, hechos, saltados, errores = time.time(), 0, 0, []
    for i, (p, ruta) in enumerate(trabajos, 1):
        if not args.rehacer and os.path.exists(ruta) and os.path.getsize(ruta) > 0:
            saltados += 1
            continue
        os.makedirs(os.path.dirname(ruta), exist_ok=True)
        try:
            generar_pdf(p, ctx, ruta, con_mapa, args.con_foto)
            hechos += 1
        except Exception as e:
            errores.append((p.get('codigo_final'), str(e)))
            if os.path.exists(ruta):
                os.remove(ruta)
        if hechos and hechos % 100 == 0:
            ritmo = hechos / (time.time() - t0)
            faltan = len(trabajos) - i
            print(f'  {i}/{len(trabajos)} · {ritmo:.1f} fichas/s · '
                  f'ETA {faltan / max(ritmo, 0.01) / 60:.0f} min')

    dur = time.time() - t0
    print(f'✔ Generadas {hechos} · saltadas (ya existían) {saltados} · '
          f'errores {len(errores)} · {dur / 60:.1f} min')
    if TILES_FALLIDOS:
        print(f'⚠ {TILES_FALLIDOS} mosaicos satelitales no se pudieron descargar '
              '(quedan en gris); reintentar con red estable regenera solo esos mapas '
              'si se borra el PDF afectado')
    for cod, err in errores[:15]:
        print(f'   ✖ {cod}: {err}')

    # verificación: conteo de PDFs por sector/comunidad contra lo esperado
    print('\nVerificación de carpetas (PDF en disco / fichas esperadas):')
    esperado = defaultdict(int)
    for p, ruta in trabajos:
        esperado[p['_sector']] += 1
    for sector in sorted(esperado):
        n_disco = 0
        d = os.path.join(args.salida, sanear_nombre(sector))
        for raiz, _, archivos in os.walk(d):
            n_disco += sum(1 for a in archivos if a.lower().endswith('.pdf'))
        marca = '✔' if n_disco == esperado[sector] else '✖'
        print(f'  {marca} {sector}: {n_disco} / {esperado[sector]}')

    if not args.comunidad and not args.clave and not args.limite:
        escribir_indice(indice, args.salida)


if __name__ == '__main__':
    main()
