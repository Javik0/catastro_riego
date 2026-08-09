# -*- coding: utf-8 -*-
"""
Extractor de geometría vectorial de los planos PDF del consorcio (represa Porotog).

Qué son estos PDF y por qué hace falta un extractor propio
----------------------------------------------------------
Los tres planos (`CARTOGRAFIA REPRESA/*.pdf`) salieron de AutoCAD Civil 3D 2026
vía pdfplot. NO son GeoPDF: no traen CRS ni georreferencia, pero SÍ traen todo
el dibujo como geometría vectorial real (no imagen).

GDAL abre estos PDF y expone capas, pero solo las que quedaron marcadas como
"optional content group" (OCG) — la topografía: curvas de nivel, río, canal,
camino, pantano, puentes, GPS. Justo lo que más interesa (el límite de proyecto
en rojo, los bancos de materiales en magenta, las obras) se dibujó SIN OCG, así
que GDAL no lo ve. De ahí este extractor: interpreta el content stream del PDF
directamente y guarda cada trazo con su capa CAD (si la tiene) Y su color, que
es lo que permite recuperar el resto.

Qué hace exactamente
--------------------
Recorre los operadores del PDF manteniendo el estado gráfico (pila q/Q, matriz
de transformación, color de trazo y de relleno, pila de marked content) y:

* arma los trazos: m, l, c, v, y, re, h  (las curvas Bézier se aplanan)
* les asigna la capa CAD leyendo los BDC /OC y resolviendo el OCG por nombre
* les asigna el color de trazo y de relleno en hexadecimal
* entra en los XObjects de formulario (/Do), donde pdfplot mete buena parte del
  dibujo, aplicando su /Matrix — sin esto se pierde casi todo

Las coordenadas de salida están en el espacio de usuario del PDF (puntos), NO
en UTM. Georreferenciar es el paso siguiente (`03_georreferenciar.py`).

El texto se extrae aparte con el visitor de pypdf, y se guarda como capa de
puntos: son las etiquetas del dibujo ("BANCO DE MATERIALES 1", "Fin Túnel", los
números de vértice del límite, las abscisas de la vía). OJO: las tablas de
coordenadas y el rótulo NO son texto — AutoCAD las vectorizó porque usan fuente
SHX. No se pueden leer por aquí; los vértices del límite se transcriben aparte
y se validan contra el área declarada en el plano.

Salida
------
CARTOGRAFIA REPRESA/procesado/<lamina>.gpkg  con dos capas:
    trazos  (líneas, en coordenadas de página)  campos: ocg, color, relleno, cerrado, pintado
    textos  (puntos, en coordenadas de página)  campos: texto
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.expanduser('~'), '.pylibs', 'carto'))

from osgeo import ogr
from pypdf import PdfReader
from pypdf.generic import ContentStream, NameObject

ogr.UseExceptions()

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
RAIZ = os.path.abspath(os.path.join(BASE, '..'))
CARTOGRAFIA = os.path.join(RAIZ, 'CARTOGRAFIA REPRESA')
PROCESADO = os.path.join(CARTOGRAFIA, 'procesado')

PLANOS = [
    'CCSPT-GEN-AMB-PL-DT-1000-R1.pdf',   # límite de proyecto, presa, bancos de materiales
    'CCSPT-GEN-AMB-PL-DT-1001-R1.pdf',   # vía de acceso (lámina 1)
    'CCSPT-GEN-AMB-PL-DT-1002-R1.pdf',   # vía de acceso (lámina 2)
]

PASOS_BEZIER = 16      # segmentos por curva; 16 es visualmente exacto a esta escala
MIN_PUNTOS = 2


# ─────────────────────────────────────────────────────────────────────────────
#  Álgebra de matrices PDF:  [a b c d e f]  →  x' = a·x + c·y + e
# ─────────────────────────────────────────────────────────────────────────────
def mat_mult(m, n):
    a, b, c, d, e, f = m
    A, B, C, D, E, F = n
    return (a * A + b * C, a * B + b * D,
            c * A + d * C, c * B + d * D,
            e * A + f * C + E, e * B + f * D + F)


def aplicar(m, x, y):
    a, b, c, d, e, f = m
    return (a * x + c * y + e, b * x + d * y + f)


def num(v, defecto=0.0):
    try:
        return float(v)
    except Exception:
        return defecto


def color_hex(comps, espacio):
    """Convierte los componentes de color actuales a #rrggbb."""
    try:
        if espacio == 'rgb' and len(comps) >= 3:
            r, g, b = comps[:3]
        elif espacio == 'gray' and len(comps) >= 1:
            r = g = b = comps[0]
        elif espacio == 'cmyk' and len(comps) >= 4:
            c, m, y, k = comps[:4]
            r, g, b = (1 - min(1, c + k)), (1 - min(1, m + k)), (1 - min(1, y + k))
        else:
            return None
        return '#{:02X}{:02X}{:02X}'.format(
            int(round(max(0.0, min(1.0, r)) * 255)),
            int(round(max(0.0, min(1.0, g)) * 255)),
            int(round(max(0.0, min(1.0, b)) * 255)))
    except Exception:
        return None


class Estado(object):
    """Estado gráfico del PDF (lo que salva/restaura q y Q)."""

    def __init__(self, ctm=(1, 0, 0, 1, 0, 0)):
        self.ctm = ctm
        self.trazo = [0.0]
        self.trazo_esp = 'gray'
        self.relleno = [0.0]
        self.relleno_esp = 'gray'

    def copia(self):
        e = Estado(self.ctm)
        e.trazo, e.trazo_esp = list(self.trazo), self.trazo_esp
        e.relleno, e.relleno_esp = list(self.relleno), self.relleno_esp
        return e


class Extractor(object):

    def __init__(self, reader):
        self.reader = reader
        self.trazos = []          # (ocg, color, relleno, cerrado, pintado, [subpaths])
        self._profundidad = 0

    # ── resolución de las capas CAD (optional content groups) ──
    def _nombre_ocg(self, recursos, etiqueta):
        try:
            props = recursos.get('/Properties')
            if props is None:
                return None
            obj = props.get(etiqueta)
            if obj is None:
                return None
            obj = obj.get_object()
            if '/Name' in obj:
                return str(obj['/Name'])
            if '/OCGs' in obj:                       # OCMD: apunta a uno o varios OCG
                ocgs = obj['/OCGs']
                ocgs = ocgs.get_object()
                if isinstance(ocgs, list):
                    nombres = [str(o.get_object().get('/Name', '')) for o in ocgs]
                    return ' + '.join(n for n in nombres if n) or None
                return str(ocgs.get('/Name', '')) or None
        except Exception:
            return None
        return None

    def ejecutar(self, contenido, recursos, ctm_inicial):
        if self._profundidad > 12:                   # anti-recursión infinita
            return
        self._profundidad += 1
        try:
            self._ejecutar(contenido, recursos, ctm_inicial)
        finally:
            self._profundidad -= 1

    def _ejecutar(self, contenido, recursos, ctm_inicial):
        est = Estado(ctm_inicial)
        pila = []
        capas = []                 # pila de marked content: nombre de OCG o None
        subpaths, actual = [], []
        x0 = y0 = xc = yc = 0.0    # inicio del subpath y punto actual (sin transformar)

        def pt(x, y):
            return aplicar(est.ctm, x, y)

        def cerrar_subpath():
            if len(actual) >= MIN_PUNTOS:
                subpaths.append(list(actual))
            del actual[:]

        def emitir(pintado, cerrado):
            cerrar_subpath()
            if subpaths:
                capa = next((c for c in reversed(capas) if c), None)
                self.trazos.append({
                    'ocg': capa,
                    'color': color_hex(est.trazo, est.trazo_esp),
                    'relleno': color_hex(est.relleno, est.relleno_esp),
                    'cerrado': cerrado,
                    'pintado': pintado,
                    'subpaths': list(subpaths),
                })
            del subpaths[:]

        for operandos, op in ContentStream(contenido, self.reader).operations:
            o = op.decode('latin-1') if isinstance(op, bytes) else str(op)

            # ── estado gráfico ──
            if o == 'q':
                pila.append(est.copia())
            elif o == 'Q':
                if pila:
                    est = pila.pop()
            elif o == 'cm' and len(operandos) >= 6:
                est.ctm = mat_mult(tuple(num(v) for v in operandos[:6]), est.ctm)

            # ── color ──
            elif o in ('RG', 'rg', 'G', 'g', 'K', 'k'):
                comps = [num(v) for v in operandos]
                esp = {'R': 'rgb', 'G': 'gray', 'K': 'cmyk'}[o.upper()[0]]
                if o.isupper():
                    est.trazo, est.trazo_esp = comps, esp
                else:
                    est.relleno, est.relleno_esp = comps, esp
            elif o in ('SC', 'SCN', 'sc', 'scn'):
                comps = [num(v) for v in operandos if not isinstance(v, NameObject)]
                esp = {1: 'gray', 3: 'rgb', 4: 'cmyk'}.get(len(comps))
                if esp:
                    if o.isupper():
                        est.trazo, est.trazo_esp = comps, esp
                    else:
                        est.relleno, est.relleno_esp = comps, esp

            # ── construcción del trazo ──
            elif o == 'm' and len(operandos) >= 2:
                cerrar_subpath()
                xc, yc = num(operandos[0]), num(operandos[1])
                x0, y0 = xc, yc
                actual.append(pt(xc, yc))
            elif o == 'l' and len(operandos) >= 2:
                xc, yc = num(operandos[0]), num(operandos[1])
                actual.append(pt(xc, yc))
            elif o in ('c', 'v', 'y') and len(operandos) >= 4:
                v = [num(x) for x in operandos]
                if o == 'c':
                    p1, p2, p3 = (v[0], v[1]), (v[2], v[3]), (v[4], v[5])
                elif o == 'v':
                    p1, p2, p3 = (xc, yc), (v[0], v[1]), (v[2], v[3])
                else:                                # 'y'
                    p1, p2, p3 = (v[0], v[1]), (v[2], v[3]), (v[2], v[3])
                px, py = xc, yc
                for i in range(1, PASOS_BEZIER + 1):
                    t = i / float(PASOS_BEZIER)
                    u = 1 - t
                    bx = (u ** 3 * px + 3 * u * u * t * p1[0]
                          + 3 * u * t * t * p2[0] + t ** 3 * p3[0])
                    by = (u ** 3 * py + 3 * u * u * t * p1[1]
                          + 3 * u * t * t * p2[1] + t ** 3 * p3[1])
                    actual.append(pt(bx, by))
                xc, yc = p3
            elif o == 're' and len(operandos) >= 4:
                cerrar_subpath()
                x, y, w, h = (num(v) for v in operandos[:4])
                actual.extend([pt(x, y), pt(x + w, y), pt(x + w, y + h),
                               pt(x, y + h), pt(x, y)])
                cerrar_subpath()
                xc, yc = x, y
                x0, y0 = x, y
            elif o == 'h':
                if actual:
                    actual.append(pt(x0, y0))
                    xc, yc = x0, y0

            # ── pintado (aquí se emite el trazo) ──
            elif o in ('S', 's', 'f', 'F', 'f*', 'B', 'B*', 'b', 'b*', 'n'):
                if o in ('s', 'b', 'b*') and actual:
                    actual.append(pt(x0, y0))
                relleno = o[0] in ('f', 'F', 'B', 'b')
                trazo = o[0] in ('S', 's', 'B', 'b')
                if o == 'n':
                    del subpaths[:]                  # solo recorte, no dibuja
                    del actual[:]
                else:
                    emitir('relleno+trazo' if (relleno and trazo)
                           else ('relleno' if relleno else 'trazo'),
                           o[0] in ('f', 'F', 'b', 's', 'B'))

            # ── capas CAD ──
            elif o == 'BDC':
                nombre = None
                if len(operandos) >= 2 and str(operandos[0]) == '/OC':
                    nombre = self._nombre_ocg(recursos, operandos[1])
                capas.append(nombre)
            elif o == 'BMC':
                capas.append(None)
            elif o == 'EMC':
                if capas:
                    capas.pop()

            # ── XObjects de formulario: aquí vive buena parte del dibujo ──
            elif o == 'Do' and operandos:
                try:
                    xo = recursos['/XObject'][operandos[0]].get_object()
                    if str(xo.get('/Subtype', '')) == '/Form':
                        m = xo.get('/Matrix')
                        ctm = est.ctm
                        if m:
                            ctm = mat_mult(tuple(num(v) for v in m), ctm)
                        self.ejecutar(xo, xo.get('/Resources', recursos), ctm)
                except Exception:
                    pass


# ─────────────────────────────────────────────────────────────────────────────
def escribir_gpkg(ruta, trazos, textos):
    drv = ogr.GetDriverByName('GPKG')
    if os.path.exists(ruta):
        drv.DeleteDataSource(ruta)
    ds = drv.CreateDataSource(ruta)

    cap = ds.CreateLayer('trazos', srs=None, geom_type=ogr.wkbMultiLineString)
    for nombre, tipo in [('ocg', ogr.OFTString), ('color', ogr.OFTString),
                         ('relleno', ogr.OFTString), ('pintado', ogr.OFTString),
                         ('cerrado', ogr.OFTInteger), ('vertices', ogr.OFTInteger),
                         ('largo', ogr.OFTReal)]:
        cap.CreateField(ogr.FieldDefn(nombre, tipo))
    defn = cap.GetLayerDefn()

    for t in trazos:
        geo = ogr.Geometry(ogr.wkbMultiLineString)
        nv = 0
        for sp in t['subpaths']:
            ln = ogr.Geometry(ogr.wkbLineString)
            for x, y in sp:
                ln.AddPoint_2D(x, y)
            geo.AddGeometry(ln)
            nv += len(sp)
        ft = ogr.Feature(defn)
        ft.SetField('ocg', t['ocg'] or '')
        ft.SetField('color', t['color'] or '')
        ft.SetField('relleno', t['relleno'] or '')
        ft.SetField('pintado', t['pintado'])
        ft.SetField('cerrado', 1 if t['cerrado'] else 0)
        ft.SetField('vertices', nv)
        ft.SetField('largo', geo.Length())
        ft.SetGeometry(geo)
        cap.CreateFeature(ft)
        ft = None

    cap = ds.CreateLayer('textos', srs=None, geom_type=ogr.wkbPoint)
    cap.CreateField(ogr.FieldDefn('texto', ogr.OFTString))
    defn = cap.GetLayerDefn()
    for x, y, txt in textos:
        ft = ogr.Feature(defn)
        ft.SetField('texto', txt)
        p = ogr.Geometry(ogr.wkbPoint)
        p.AddPoint_2D(x, y)
        ft.SetGeometry(p)
        cap.CreateFeature(ft)
        ft = None

    ds = None


def procesar(pdf):
    nombre = os.path.basename(pdf)
    lamina = nombre.split('-DT-')[1].split('-')[0] if '-DT-' in nombre else nombre
    print("\n" + "-" * 74)
    print(" lamina {}  ({})".format(lamina, nombre))
    print("-" * 74)

    reader = PdfReader(pdf)
    pagina = reader.pages[0]

    ext = Extractor(reader)
    ext.ejecutar(pagina.get_contents(), pagina['/Resources'], (1, 0, 0, 1, 0, 0))

    # El texto se ubica combinando la matriz de texto con la de transformación
    # vigente (Tm x CTM). Usar solo Tm deja el texto en OTRA escala que el
    # dibujo, porque pdfplot mete el contenido dentro de XObjects con su propia
    # matriz — y entonces textos y geometría no se pueden cruzar.
    textos = []

    def _texto(t, cm, tm, font_dict, font_size):
        t = (t or '').strip()
        if not t:
            return
        m = mat_mult(tuple(tm), tuple(cm))
        textos.append((m[4], m[5], t))

    pagina.extract_text(visitor_text=_texto)

    con_capa = sum(1 for t in ext.trazos if t['ocg'])
    print("  trazos extraidos : {:,}  ({:,} con capa CAD, {:,} sin capa)"
          .format(len(ext.trazos), con_capa, len(ext.trazos) - con_capa))
    print("  textos           : {:,}".format(len(textos)))

    # resumen por color de los trazos SIN capa: ahí están el límite y los bancos
    porcolor = {}
    for t in ext.trazos:
        if not t['ocg']:
            k = t['color'] or t['relleno'] or '(sin color)'
            porcolor[k] = porcolor.get(k, 0) + 1
    print("  colores sin capa (top 8):")
    for c, n in sorted(porcolor.items(), key=lambda kv: -kv[1])[:8]:
        print("      {:>9s}  {:,} trazos".format(c, n))

    salida = os.path.join(PROCESADO, 'plano_{}.gpkg'.format(lamina))
    escribir_gpkg(salida, ext.trazos, textos)
    print("  guardado: {}  ({:.1f} MB)".format(
        os.path.relpath(salida, RAIZ), os.path.getsize(salida) / 1e6))
    return lamina, len(ext.trazos)


def main():
    print("=" * 74)
    print(" EXTRACCION DE GEOMETRIA DE LOS PLANOS PDF DEL CONSORCIO")
    print("=" * 74)
    os.makedirs(PROCESADO, exist_ok=True)

    faltan = [p for p in PLANOS if not os.path.exists(os.path.join(CARTOGRAFIA, p))]
    if faltan:
        print("ERROR: faltan planos en {}:".format(CARTOGRAFIA))
        for f in faltan:
            print("   - {}".format(f))
        return 1

    for p in PLANOS:
        procesar(os.path.join(CARTOGRAFIA, p))

    print("\n" + "=" * 74)
    print(" Coordenadas en espacio de pagina (puntos PDF), sin georreferenciar.")
    print(" Siguiente paso: 03_georreferenciar.py")
    print("=" * 74)
    return 0


if __name__ == '__main__':
    sys.exit(main())
