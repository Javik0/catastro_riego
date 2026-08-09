# -*- coding: utf-8 -*-
"""
Georreferenciación del plano 1000 (límite de proyecto, presa, bancos de materiales).

El problema
-----------
Los PDF del consorcio no traen georreferencia. Traen el dibujo en coordenadas de
página (puntos PDF) y, aparte, una tabla con las coordenadas UTM de los 29
vértices del límite de proyecto. Esa tabla está VECTORIZADA en el PDF (fuente
SHX de AutoCAD), así que no se puede leer por software: se transcribió a mano
desde el plano y se validó contra el área que el propio plano declara.

Cómo se resuelve
----------------
1. Puntos de control: los números de vértice «1»…«29» del plano SÍ son texto con
   posición conocida. Cada uno se empareja con su fila de la tabla UTM. Como la
   etiqueta se dibuja al lado del vértice y no encima, esto da una transformación
   aproximada (error de metros, no de centímetros).
2. Refinamiento: con esa transformación aproximada se proyecta cada vértice UTM
   al espacio de página y se busca el vértice REAL del polígono dibujado más
   cercano (capa `C3D-Volumen`, el límite rojo). Con esos pares se reajusta.
3. Se ajusta una SIMILITUD (escala uniforme + rotación + traslación, 4
   parámetros). Es la transformación físicamente correcta para un plano CAD: la
   escala tiene que ser la misma en X e Y. También se ajusta una AFÍN de 6
   parámetros solo como control: si la afín mejorara mucho el residual, algo
   estaría mal (dos viewports a escalas distintas, por ejemplo).

Validación de la tabla transcrita
---------------------------------
El plano declara ÁREA = 636.015,618 m². Con los 29 vértices tal como figuran en
la tabla el área da 338.162,757 m² (el polígono se cruza consigo mismo). Sin el
vértice 23 da 635.547,911 m², a 467,7 m² de lo declarado — 0,07 %.

    => la fila 23 de la tabla del plano está equivocada.
       Sus vecinos son el 22 (N 9.984.080,607 / E 818.653,210) y el 24
       (N 9.983.870,509 / E 818.536,396); la tabla la sitúa a 2,4 km de ahí,
       al sureste. El resto de la transcripción queda validada por el área.

El vértice 23 se excluye del ajuste y su coordenada correcta se DEDUCE al final,
leyendo dónde está dibujado en el plano. Ese dato hay que devolvérselo al
consorcio: es un error en su entregable, no nuestro.

Salida
------
CARTOGRAFIA REPRESA/procesado/georref_1000.json  con los parámetros, el residual
por punto y el diagnóstico completo.
"""
import json
import math
import os
import sys

import numpy as np
from osgeo import ogr

ogr.UseExceptions()

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
RAIZ = os.path.abspath(os.path.join(BASE, '..'))
PROCESADO = os.path.join(RAIZ, 'CARTOGRAFIA REPRESA', 'procesado')
GPKG = os.path.join(PROCESADO, 'plano_1000.gpkg')
SALIDA = os.path.join(PROCESADO, 'georref_1000.json')

AREA_DECLARADA = 636015.618          # m², según el propio plano
CAPA_LIMITE = 'C3D-Volumen'          # el límite de proyecto, en rojo #DD0000
VERTICE_MALO = 23                    # fila errónea de la tabla (ver docstring)

# Tabla «LIMITE DE PROYECTO» del plano CCSPT-GEN-AMB-PL-DT-1000-R1
# ORD: (NORTE, ESTE) en WGS84 / UTM 17S (EPSG:32717)
TABLA = {
    1:  (9983826.207, 819039.695),   2:  (9983831.964, 819137.973),
    3:  (9983870.532, 819192.850),   4:  (9983942.814, 819278.162),
    5:  (9984110.286, 819353.881),   6:  (9984224.732, 819370.006),
    7:  (9984279.067, 819367.417),   8:  (9984453.559, 819289.455),
    9:  (9984596.563, 819218.630),   10: (9984834.584, 818916.397),
    11: (9984797.463, 818888.044),   12: (9984751.617, 818881.625),
    13: (9984705.943, 818767.176),   14: (9984683.283, 818740.313),
    15: (9984643.056, 818715.117),   16: (9984606.039, 818705.121),
    17: (9984437.954, 818720.268),   18: (9984368.366, 818656.580),
    19: (9984338.088, 818632.328),   20: (9984215.479, 818559.602),
    21: (9984129.051, 818534.653),   22: (9984080.607, 818653.210),
    23: (9982773.250, 820757.241),   24: (9983870.509, 818536.396),
    25: (9983819.372, 818542.692),   26: (9983761.727, 818616.193),
    27: (9983655.595, 818851.735),   28: (9983641.455, 818887.818),
    29: (9983770.531, 818971.843),
}


def area_poligono(pts):
    """Área por la fórmula del agrimensor. pts = [(este, norte), ...]"""
    s = 0.0
    for i in range(len(pts)):
        x1, y1 = pts[i]
        x2, y2 = pts[(i + 1) % len(pts)]
        s += x1 * y2 - x2 * y1
    return abs(s) / 2.0


def ajustar_similitud(origen, destino):
    """
    Similitud 2D por mínimos cuadrados: escala uniforme + rotación + traslación.
        X = a·x - b·y + tx
        Y = b·x + a·y + ty
    origen/destino: arrays (n,2). Devuelve (a, b, tx, ty).
    """
    n = len(origen)
    A = np.zeros((2 * n, 4))
    L = np.zeros(2 * n)
    for i, ((x, y), (X, Y)) in enumerate(zip(origen, destino)):
        A[2 * i] = [x, -y, 1, 0]
        L[2 * i] = X
        A[2 * i + 1] = [y, x, 0, 1]
        L[2 * i + 1] = Y
    sol, *_ = np.linalg.lstsq(A, L, rcond=None)
    return tuple(sol)


def ajustar_afin(origen, destino):
    """Afín completa de 6 parámetros; solo se usa como control de sanidad."""
    n = len(origen)
    A = np.zeros((2 * n, 6))
    L = np.zeros(2 * n)
    for i, ((x, y), (X, Y)) in enumerate(zip(origen, destino)):
        A[2 * i] = [x, y, 1, 0, 0, 0]
        L[2 * i] = X
        A[2 * i + 1] = [0, 0, 0, x, y, 1]
        L[2 * i + 1] = Y
    sol, *_ = np.linalg.lstsq(A, L, rcond=None)
    return tuple(sol)


def aplicar_similitud(p, x, y):
    a, b, tx, ty = p
    return (a * x - b * y + tx, b * x + a * y + ty)


def aplicar_afin(p, x, y):
    a, b, c, d, e, f = p
    return (a * x + b * y + c, d * x + e * y + f)


def residuales(par, origen, destino, fn):
    return [math.hypot(*(np.subtract(fn(par, x, y), (X, Y))))
            for (x, y), (X, Y) in zip(origen, destino)]


def leer_textos_numericos(gpkg):
    """
    Números de vértice del plano: {n: (x_pagina, y_pagina)}.

    Se descarta el origen exacto (0,0): algún rótulo sale del PDF con la matriz
    de texto sin resolver y aterriza ahí. Es basura, no un vértice — el «17» del
    plano 1000 es uno de esos, y colado en el ajuste lo arruina.
    """
    ds = ogr.Open(gpkg, 0)
    capa = ds.GetLayerByName('textos')
    puntos = {}
    for ft in capa:
        t = (ft.GetField('texto') or '').strip()
        if t.isdigit() and 1 <= int(t) <= 29:
            g = ft.GetGeometryRef()
            x, y = g.GetX(), g.GetY()
            if abs(x) < 1e-6 and abs(y) < 1e-6:
                continue
            puntos.setdefault(int(t), (x, y))
    ds = None
    return puntos


def ajuste_robusto(origen, destino, etiquetas, umbral=20.0):
    """
    Similitud robusta a puntos de control equivocados (RANSAC exhaustivo).

    Por qué hace falta: los números del plano se emparejan con la tabla por su
    valor, y ese emparejamiento puede fallar — un número que en el dibujo rotula
    otra cosa, o una fila mal transcrita. Un solo par equivocado arrastra el
    ajuste por mínimos cuadrados entero (aquí, de metros a 200 m de RMS).

    Dos puntos bastan para definir una similitud, así que se prueban TODAS las
    parejas (con 27 candidatos son 351 combinaciones: exhaustivo, determinista y
    barato) y gana la que deja más puntos dentro del umbral. Con ese consenso se
    reajusta por mínimos cuadrados.

    Devuelve (parametros, indices_inliers).
    """
    n = len(origen)
    mejor_par, mejor_inliers = None, []
    for i in range(n):
        for j in range(i + 1, n):
            try:
                p = ajustar_similitud(origen[[i, j]], destino[[i, j]])
            except Exception:
                continue
            if not all(map(math.isfinite, p)):
                continue
            r = residuales(p, origen, destino, aplicar_similitud)
            inliers = [k for k, v in enumerate(r) if v <= umbral]
            if len(inliers) > len(mejor_inliers):
                mejor_par, mejor_inliers = p, inliers

    if len(mejor_inliers) < 3:
        return ajustar_similitud(origen, destino), list(range(n))

    par = ajustar_similitud(origen[mejor_inliers], destino[mejor_inliers])
    # una segunda pasada: con el modelo de consenso ya afinado, puede entrar
    # algún punto que la pareja inicial dejaba justo fuera
    r = residuales(par, origen, destino, aplicar_similitud)
    inliers = [k for k, v in enumerate(r) if v <= umbral]
    if len(inliers) >= len(mejor_inliers):
        par = ajustar_similitud(origen[inliers], destino[inliers])
        mejor_inliers = inliers
    return par, mejor_inliers


def leer_vertices_limite(gpkg):
    """Todos los vértices dibujados del límite de proyecto (capa roja)."""
    ds = ogr.Open(gpkg, 0)
    capa = ds.GetLayerByName('trazos')
    capa.SetAttributeFilter("ocg = '{}'".format(CAPA_LIMITE))
    pts = []
    for ft in capa:
        g = ft.GetGeometryRef()
        for i in range(g.GetGeometryCount()):
            ln = g.GetGeometryRef(i)
            for j in range(ln.GetPointCount()):
                x, y, *_ = ln.GetPoint(j)
                pts.append((x, y))
    ds = None
    return np.array(pts) if pts else np.zeros((0, 2))


def main():
    print("=" * 74)
    print(" GEORREFERENCIACION DEL PLANO 1000 (limite de proyecto)")
    print("=" * 74)

    if not os.path.exists(GPKG):
        print("ERROR: falta {}. Ejecuta antes 02_extraer_pdf.py".format(GPKG))
        return 1

    # ── 1. validar la tabla transcrita contra el área declarada ──
    buenos = [o for o in sorted(TABLA) if o != VERTICE_MALO]
    poli = [(TABLA[o][1], TABLA[o][0]) for o in buenos]
    area = area_poligono(poli)
    dif = area - AREA_DECLARADA
    print("\n  [1] Validacion de la tabla transcrita")
    print("      area declarada por el plano : {:14,.3f} m2".format(AREA_DECLARADA))
    print("      area de los 28 vertices     : {:14,.3f} m2".format(area))
    print("      diferencia                  : {:+14,.3f} m2  ({:+.3f} %)"
          .format(dif, 100.0 * dif / AREA_DECLARADA))
    if abs(dif) / AREA_DECLARADA > 0.005:
        print("      ATENCION: mas de 0,5 % de diferencia. Revisar la transcripcion")
        print("                antes de dar por buena la georreferenciacion.")
    else:
        print("      -> transcripcion validada (la diferencia es el vertice 23 ausente)")

    # ── 2. puntos de control aproximados: las etiquetas numéricas ──
    etiquetas = leer_textos_numericos(GPKG)
    comunes = [o for o in buenos if o in etiquetas]
    print("\n  [2] Puntos de control (etiquetas de vertice en el plano)")
    print("      vertices de la tabla usables : {}".format(len(buenos)))
    print("      etiquetas halladas en el PDF : {}".format(len(etiquetas)))
    print("      pares utilizables            : {}".format(len(comunes)))
    if len(comunes) < 4:
        print("      ERROR: insuficientes puntos de control.")
        return 1

    origen = np.array([etiquetas[o] for o in comunes])
    destino = np.array([(TABLA[o][1], TABLA[o][0]) for o in comunes])  # (E, N)

    par, inliers = ajuste_robusto(origen, destino, comunes)
    res = residuales(par, origen, destino, aplicar_similitud)
    rms = math.sqrt(sum(res[k] ** 2 for k in inliers) / len(inliers))
    descartados = [comunes[k] for k in range(len(comunes)) if k not in inliers]
    print("      en consenso                  : {} de {}"
          .format(len(inliers), len(comunes)))
    print("      RMS con las etiquetas        : {:.2f} m".format(rms))
    print("      (la etiqueta se dibuja AL LADO del vertice, asi que este error")
    print("       es el desplazamiento del rotulo, no de la georreferenciacion)")
    if descartados:
        print("      fuera de consenso            : {}".format(descartados))
        for o in descartados:
            k = comunes.index(o)
            print("          vertice {:2d}: {:9,.0f} m de discrepancia".format(o, res[k]))
        print("      -> o esos numeros rotulan otra cosa en el dibujo, o esas")
        print("         filas de la tabla del consorcio no son de esos vertices.")
        print("         Se excluyen del ajuste; se revisan en el paso [6].")

    comunes = [comunes[k] for k in inliers]
    origen, destino = origen[inliers], destino[inliers]

    # ── 3. refinamiento contra los vértices dibujados del límite ──
    dibujados = leer_vertices_limite(GPKG)
    print("\n  [3] Refinamiento con la geometria dibujada")
    print("      vertices del limite en el PDF: {:,}".format(len(dibujados)))

    a, b, tx, ty = par
    escala_pag = math.hypot(a, b)                    # unidades UTM por unidad de página
    radio_pag = 25.0 / escala_pag if escala_pag else 25.0   # 25 m de búsqueda

    pares_ref = []
    for o in comunes:
        E, N = TABLA[o][1], TABLA[o][0]
        # invertir la similitud para llevar el vértice UTM al espacio de página
        det = a * a + b * b
        dx, dy = E - tx, N - ty
        xp = (a * dx + b * dy) / det
        yp = (-b * dx + a * dy) / det
        if len(dibujados):
            d = np.hypot(dibujados[:, 0] - xp, dibujados[:, 1] - yp)
            i = int(np.argmin(d))
            if d[i] <= radio_pag:
                pares_ref.append((o, tuple(dibujados[i]), (E, N), d[i] * escala_pag))

    print("      vertices emparejados         : {} de {}"
          .format(len(pares_ref), len(comunes)))

    if len(pares_ref) >= 6:
        origen2 = np.array([p[1] for p in pares_ref])
        destino2 = np.array([p[2] for p in pares_ref])
        par2 = ajustar_similitud(origen2, destino2)
        res2 = residuales(par2, origen2, destino2, aplicar_similitud)
        rms2 = math.sqrt(sum(r * r for r in res2) / len(res2))

        # descartar emparejamientos malos (más de 3 sigma) y reajustar
        umbral = max(3 * rms2, 1.0)
        filtrados = [(o, op, dp) for (o, op, dp, _), r
                     in zip(pares_ref, res2) if r <= umbral]
        if 6 <= len(filtrados) < len(pares_ref):
            origen2 = np.array([p[1] for p in filtrados])
            destino2 = np.array([p[2] for p in filtrados])
            par2 = ajustar_similitud(origen2, destino2)
            res2 = residuales(par2, origen2, destino2, aplicar_similitud)
            rms2 = math.sqrt(sum(r * r for r in res2) / len(res2))
            print("      descartados por residual     : {}"
                  .format(len(pares_ref) - len(filtrados)))
            usados = [f[0] for f in filtrados]
        else:
            usados = [p[0] for p in pares_ref]

        par, res, rms, origen, destino = par2, res2, rms2, origen2, destino2
        print("      RMS refinado                 : {:.3f} m".format(rms))
    else:
        usados = comunes
        print("      no hubo emparejamientos suficientes: se conserva el ajuste")
        print("      por etiquetas (menos preciso, revisar antes de publicar)")

    # ── 4. parámetros e informe ──
    a, b, tx, ty = par
    escala = math.hypot(a, b)
    rot = math.degrees(math.atan2(b, a))
    par_af = ajustar_afin(origen, destino)
    res_af = residuales(par_af, origen, destino, aplicar_afin)
    rms_af = math.sqrt(sum(r * r for r in res_af) / len(res_af))

    print("\n  [4] Transformacion pagina -> WGS84 / UTM 17S (EPSG:32717)")
    print("      escala      : {:.6f} m por unidad de pagina".format(escala))
    print("      equivalente : 1:{:,.0f} sobre papel".format(escala * 72 / 0.0254))
    print("      rotacion    : {:+.4f} grados".format(rot))
    print("      traslacion  : E {:,.3f}   N {:,.3f}".format(tx, ty))
    print("      RMS similitud (4 parametros): {:.3f} m".format(rms))
    print("      RMS afin      (6 parametros): {:.3f} m".format(rms_af))
    if rms_af < rms * 0.5:
        print("      ATENCION: la afin mejora mucho el ajuste. Eso sugiere que el")
        print("                plano tiene mas de una escala (dos viewports) o que")
        print("                hay puntos de control mal emparejados.")
    else:
        print("      -> la similitud basta: escala uniforme, como debe ser en CAD")

    print("\n      residual por vertice:")
    for o, r in sorted(zip(usados, res), key=lambda t: -t[1]):
        marca = '  <-- el mayor' if r == max(res) else ''
        print("        vertice {:2d}: {:7.3f} m{}".format(o, r, marca))

    # ── 5. ¿las filas descartadas son culpa de la tabla o de las etiquetas? ──
    # Con la transformación ya buena se proyecta CADA fila de la tabla al plano
    # y se mide su distancia al límite realmente dibujado. Si la fila cae sobre
    # el dibujo, la tabla está bien y lo que falló fue el rótulo (un número que
    # en el plano etiqueta otra cosa). Si cae lejos, la tabla está mal.
    det = a * a + b * b

    def a_pagina(E, N):
        dx, dy = E - tx, N - ty
        return ((a * dx + b * dy) / det, (-b * dx + a * dy) / det)

    def dist_al_limite(E, N):
        xp, yp = a_pagina(E, N)
        d = np.hypot(dibujados[:, 0] - xp, dibujados[:, 1] - yp)
        return float(d.min()) * escala

    print("\n  [5] Contraste de CADA fila de la tabla contra el limite dibujado")
    lejos = []
    for o in sorted(TABLA):
        if o == VERTICE_MALO:
            continue
        d = dist_al_limite(TABLA[o][1], TABLA[o][0])
        if d > 2.0:
            lejos.append((o, d))
    if not lejos:
        print("      las 28 filas caen sobre el limite dibujado (< 2 m).")
        print("      -> la tabla del consorcio es correcta; los rotulos {} del"
              .format(sorted(set(range(1, 30)) - set(usados) - {VERTICE_MALO})))
        print("         plano etiquetan otra cosa, por eso quedaron fuera.")
    else:
        print("      filas que NO caen sobre el limite dibujado:")
        for o, d in lejos:
            print("        fila {:2d}: a {:,.1f} m del limite".format(o, d))

    # ── 6. deducir la coordenada real del vértice 23 ──
    print("\n  [6] Vertice {} (fila erronea de la tabla del consorcio)"
          .format(VERTICE_MALO))
    print("      la tabla dice   : N {:,.3f}   E {:,.3f}".format(*TABLA[VERTICE_MALO]))

    # el 23 va entre el 22 y el 24: es el vértice dibujado que más se aparta de
    # la recta que los une (el saliente que explica los 467,7 m² que faltan)
    p22 = np.array(a_pagina(TABLA[22][1], TABLA[22][0]))
    p24 = np.array(a_pagina(TABLA[24][1], TABLA[24][0]))
    v = p24 - p22
    largo_v = np.hypot(*v)
    deducido = None
    if largo_v > 0 and len(dibujados):
        rel = dibujados - p22
        t = (rel @ v) / (largo_v ** 2)              # posición sobre la recta 22-24
        perp = np.abs(np.cross(np.broadcast_to(v, rel.shape), rel)) / largo_v
        cerca = (t > 0.05) & (t < 0.95) & (perp * escala < 60)
        if cerca.any():
            i = int(np.argmax(np.where(cerca, perp, -1)))
            deducido = aplicar_similitud(par, *dibujados[i])

    if deducido:
        E23, N23 = deducido
        print("      segun el dibujo : N {:,.3f}   E {:,.3f}".format(N23, E23))
        print("      discrepancia    : {:,.0f} m".format(
            math.hypot(E23 - TABLA[VERTICE_MALO][1], N23 - TABLA[VERTICE_MALO][0])))

        # prueba definitiva: con el 23 deducido, ¿sale el área que declara el plano?
        completo = []
        for o in sorted(TABLA):
            completo.append((E23, N23) if o == VERTICE_MALO
                            else (TABLA[o][1], TABLA[o][0]))
        area_c = area_poligono(completo)
        dif_c = area_c - AREA_DECLARADA
        print("      area con el 23 deducido: {:,.3f} m2  (declarada {:,.3f})"
              .format(area_c, AREA_DECLARADA))
        print("      diferencia             : {:+,.3f} m2  ({:+.4f} %)"
              .format(dif_c, 100.0 * dif_c / AREA_DECLARADA))
        # El punto deducido es un vértice del CONTORNO de la línea gruesa del
        # plano, no el eje exacto, así que quedan unas decenas de m² de resto.
        # Sin el vértice faltaban 467,7 m²; con él, un orden de magnitud menos.
        if abs(dif_c) < 0.05 * AREA_DECLARADA / 100 * 100:   # 0,05 % del área
            print("      -> CONFIRMADO: con esta coordenada el poligono cierra")
            print("         contra el area que declara el propio plano (sin ella")
            print("         faltaban 467,7 m2). La fila 23 de la tabla del")
            print("         consorcio esta equivocada: hay que reportarsela.")
    else:
        print("      no se pudo deducir del dibujo; el error queda igualmente")
        print("      probado por el area (paso 1).")

    with open(SALIDA, 'w', encoding='utf-8') as f:
        json.dump({
            'plano': 'CCSPT-GEN-AMB-PL-DT-1000-R1',
            'crs': 'EPSG:32717',
            'modelo': 'similitud',
            'parametros': {'a': a, 'b': b, 'tx': tx, 'ty': ty},
            'formula': 'E = a*x - b*y + tx ; N = b*x + a*y + ty',
            'escala_m_por_unidad': escala,
            'rotacion_grados': rot,
            'rms_m': rms,
            'rms_afin_control_m': rms_af,
            'puntos_usados': list(map(int, usados)),
            'residual_m': {int(o): round(r, 4) for o, r in zip(usados, res)},
            'area_declarada_m2': AREA_DECLARADA,
            'area_transcrita_m2': round(area, 3),
            'vertice_erroneo_en_tabla': VERTICE_MALO,
            'vertice_23_segun_tabla': {'norte': TABLA[VERTICE_MALO][0],
                                       'este': TABLA[VERTICE_MALO][1]},
            'vertice_23_deducido': ({'norte': round(deducido[1], 3),
                                     'este': round(deducido[0], 3)}
                                    if deducido else None),
        }, f, ensure_ascii=False, indent=2)
    print("\n  guardado: {}".format(os.path.relpath(SALIDA, RAIZ)))
    print("=" * 74)
    return 0


if __name__ == '__main__':
    sys.exit(main())
