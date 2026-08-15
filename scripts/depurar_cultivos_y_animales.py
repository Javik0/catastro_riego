# -*- coding: utf-8 -*-
"""
Un cultivo por ficha, escrito de una sola manera.

Los dos problemas
-----------------
1. **El mismo cultivo escrito de dos formas.** 18 de los 20 tipos de cultivo y
   15 de las 16 especies conviven en dos escrituras: «Cebolla» 1.913 veces y
   «CEBOLLA» 157. Los informes ya los suman —normalizan antes de agrupar— pero
   el Dashboard de la web no, y ahí salen como dos filas distintas.

2. **El mismo ítem repetido dentro de una ficha.** La instrucción a los técnicos
   era clara: si el mismo cultivo está en varias zonas del predio, va en **un
   solo registro con la superficie sumada**. No siempre se hizo, y además hay
   registros duplicados por error de captura.

Qué hace con cada caso
----------------------
* **Escritura** — cada tipo pasa a su variante más frecuente, que es la del
  catálogo del formulario. No cambia ninguna superficie ni cantidad.

* **Repetido con valores DISTINTOS** → se fusiona en un registro con la suma,
  que es la regla del cliente. Los totales del padrón no se mueven: lo que
  cambia es el número de registros, no la superficie.

* **Repetido con el MISMO valor y decimales** (`OTROS ×2 de 24.399,98 m²`) →
  copia. Nadie mide dos parcelas iguales al centímetro. Se deja un registro.

* **Repetido con el MISMO valor redondo** (`CEBOLLA ×2 de 5.000 m²`) → **no se
  toca**. Puede ser copia o dos lotes iguales de verdad, y el riesgo es
  simétrico: sumar infla, borrar pierde. Se listan al final para decidirlos.
  Lo mismo con los animales, donde las cantidades son enteras y no hay
  decimales que delaten la copia.

Uso
---
    "C:\\OSGeo4W\\bin\\python-qgis.bat" -X utf8 scripts/depurar_cultivos_y_animales.py
    "C:\\OSGeo4W\\bin\\python-qgis.bat" -X utf8 scripts/depurar_cultivos_y_animales.py --aplicar

Sin `--aplicar` no escribe nada (regla 7). Con `--aplicar` respalda antes, con la
API de backup de SQLite y fuera de la carpeta de QFieldCloud (regla 5).

Después hay que regenerar: export → gpkg del cliente → informes → build → deploy.
"""
import argparse
import os
import sqlite3
import sys
import time
import unicodedata
from collections import defaultdict

GPKG = os.path.join(os.path.expanduser('~'), 'QField', 'cloud',
                    'porotog_levantamiento_offline', 'data.gpkg')
RAIZ_RESPALDOS = (r"C:\Users\HP\OneDrive\Escritorio\CAYAMBE CATASTRO RIEGO"
                  r"\respaldos_qgs")

# Los flags se conservan con un OR: si una de las partes iba al mercado, el
# registro fusionado también.
FLAGS_CULT = ('es_principal', 'es_autoconsumo', 'es_agroindustria',
              'es_exportacion', 'es_mercado')
FLAGS_ANIM = ('es_autoconsumo', 'es_mercado', 'es_agroindustria', 'es_exportacion')


def norm(s):
    """Para comparar: sin tildes, sin dobles espacios, en mayúsculas."""
    s = unicodedata.normalize('NFKD', str(s or '').strip().upper())
    s = ''.join(c for c in s if not unicodedata.combining(c))
    return ' '.join(s.split())


def m2(v):
    return '{:,.2f}'.format(v or 0).replace(',', 'X').replace('.', ',').replace('X', '.')


def respaldo_sqlite(origen, etiqueta):
    carpeta = os.path.join(RAIZ_RESPALDOS, time.strftime('%Y-%m-%d'))
    os.makedirs(carpeta, exist_ok=True)
    destino = os.path.join(carpeta, '{}.{}-{}.bak'.format(
        os.path.basename(origen), time.strftime('%H%M'), etiqueta))
    src = sqlite3.connect(origen)
    dst = sqlite3.connect(destino)
    with dst:
        src.backup(dst)
    dst.close()
    src.close()
    return destino


def tabla(cur, clave):
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    return next((t[0] for t in cur.fetchall() if clave in t[0]
                 and not any(x in t[0] for x in ('rtree_', 'log_', 'gpkg_'))), None)


def analizar(cur, t, col_id, col_tipo, col_valor, flags, entero):
    """Devuelve (renombres, fusiones, copias, ambiguos) sin tocar nada."""
    cur.execute('SELECT {}, ficha_id, {}, COALESCE({},0), {} FROM "{}"'
                .format(col_id, col_tipo, col_valor,
                        ', '.join('COALESCE({},0)'.format(f) for f in flags), t))
    filas = cur.fetchall()

    # ── escritura: gana la variante más frecuente de cada tipo ──
    formas = defaultdict(lambda: defaultdict(int))
    for r in filas:
        formas[norm(r[2])][r[2]] += 1
    canonico = {k: max(v.items(), key=lambda x: x[1])[0] for k, v in formas.items()}
    renombres = [(r[0], r[2], canonico[norm(r[2])]) for r in filas
                 if r[2] != canonico[norm(r[2])]]

    # ── repetidos dentro de la misma ficha ──
    por_ficha = defaultdict(lambda: defaultdict(list))
    for r in filas:
        por_ficha[r[1]][norm(r[2])].append(r)

    fusiones, copias, ambiguos = [], [], []
    for _, tipos in por_ficha.items():
        for clave, rs in tipos.items():
            if len(rs) < 2:
                continue
            vals = [round(float(r[3]), 2) for r in rs]
            if len(set(vals)) > 1:
                fusiones.append((clave, rs, sum(vals)))       # regla del cliente
            elif not entero and abs(vals[0] - round(vals[0])) > 0.001:
                copias.append((clave, rs, vals[0]))           # copia evidente
            else:
                ambiguos.append((clave, rs, vals[0]))         # decide una persona
    return renombres, fusiones, copias, ambiguos


def informe(etiqueta, renombres, fusiones, copias, ambiguos, unidad):
    print('\n  {}'.format(etiqueta))
    print('     escritura a unificar        : {:>5} registros'.format(len(renombres)))
    print('     repetidos con valor distinto: {:>5} casos  -> se fusionan sumando'
          .format(len(fusiones)))
    print('        (no cambia ningun total: solo deja de haber dos filas del mismo item)')
    print('     copias evidentes            : {:>5} casos  -> se deja una'
          .format(len(copias)))
    quita = sum(v * (len(rs) - 1) for _, rs, v in copias)
    print('        se retiran {} {}'.format(m2(quita) if unidad == 'm²' else int(quita), unidad))
    print('     iguales sin decimales       : {:>5} casos  -> SIN TOCAR, hay que decidirlos'
          .format(len(ambiguos)))
    if ambiguos:
        print('        en juego: {} {}'.format(
            m2(sum(v * (len(rs) - 1) for _, rs, v in ambiguos)) if unidad == 'm²'
            else int(sum(v * (len(rs) - 1) for _, rs, v in ambiguos)), unidad))
        for clave, rs, v in sorted(ambiguos, key=lambda x: -x[2])[:6]:
            print('           {:<24} x{} de {}'.format(clave[:24], len(rs),
                                                       m2(v) if unidad == 'm²' else int(v)))
    return quita


def aplicar(cur, t, col_id, col_tipo, col_valor, flags, renombres, fusiones, copias):
    for id_r, _, nuevo in renombres:
        cur.execute('UPDATE "{}" SET {} = ? WHERE {} = ?'.format(t, col_tipo, col_id),
                    (nuevo, id_r))
    n_fus = n_del = 0
    for _, rs, suma in fusiones:
        # se conserva el registro con más superficie; el resto se retira
        rs = sorted(rs, key=lambda r: -float(r[3]))
        principal, sobran = rs[0], rs[1:]
        sets = ['{} = ?'.format(col_valor)]
        vals = [round(suma, 2)]
        for i, f in enumerate(flags):
            if any(r[4 + i] for r in rs):
                sets.append('{} = 1'.format(f))
        cur.execute('UPDATE "{}" SET {} WHERE {} = ?'
                    .format(t, ', '.join(sets), col_id), vals + [principal[0]])
        n_fus += 1
        for r in sobran:
            cur.execute('DELETE FROM "{}" WHERE {} = ?'.format(t, col_id), (r[0],))
            n_del += 1
    for _, rs, _ in copias:
        for r in sorted(rs, key=lambda r: r[0])[1:]:
            cur.execute('DELETE FROM "{}" WHERE {} = ?'.format(t, col_id), (r[0],))
            n_del += 1
    return len(renombres), n_fus, n_del


def main():
    ap = argparse.ArgumentParser(description='Unifica escritura y consolida repetidos')
    ap.add_argument('--aplicar', action='store_true',
                    help='escribe en el data.gpkg (sin esto solo simula)')
    args = ap.parse_args()

    print('=' * 78)
    print(' CULTIVOS Y ANIMALES: UNA ESCRITURA Y UN REGISTRO POR ITEM' +
          ('  [APLICAR]' if args.aplicar else '  [SIMULACION - no escribe nada]'))
    print('=' * 78)

    con = sqlite3.connect(GPKG)
    cur = con.cursor()
    t_cult, t_anim = tabla(cur, 'Cultivos_Agricolas'), tabla(cur, 'Animales_Especies')

    c = analizar(cur, t_cult, 'id_cultivo', 'tipo_cultivo', 'superficie_m2',
                 FLAGS_CULT, entero=False)
    a = analizar(cur, t_anim, 'id_animal', 'especie', 'cantidad',
                 FLAGS_ANIM, entero=True)
    quita_c = informe('CULTIVOS', *c, unidad='m²')
    quita_a = informe('ANIMALES', *a, unidad='cabezas')

    cur.execute('SELECT COUNT(*), SUM(COALESCE(superficie_m2,0)) FROM "{}"'.format(t_cult))
    n_c, sup = cur.fetchone()
    cur.execute('SELECT COUNT(*), SUM(COALESCE(cantidad,0)) FROM "{}"'.format(t_anim))
    n_a, cab = cur.fetchone()
    print('\n  EFECTO EN EL PADRON')
    print('     registros de cultivo  {:>7,}  ->  {:>7,}'
          .format(n_c, n_c - sum(len(rs) - 1 for _, rs, _ in c[1] + c[2])))
    print('     superficie cultivada  {:>12} ha  ->  {:>12} ha'
          .format(m2(sup / 10000), m2((sup - quita_c) / 10000)))
    print('     registros de animales {:>7,}  ->  {:>7,}'
          .format(n_a, n_a - sum(len(rs) - 1 for _, rs, _ in a[1] + a[2])))
    print('     cabezas               {:>12,}  ->  {:>12,}'
          .format(int(cab), int(cab - quita_a)))

    if not args.aplicar:
        print('\n  ' + '-' * 74)
        print('  SIMULACION: no se escribio nada. Para aplicarlo:  --aplicar')
        print('  ' + '-' * 74)
        con.close()
        return 0
    con.close()

    print('\n  respaldando antes de tocar nada...')
    print('     {}'.format(respaldo_sqlite(GPKG, 'antes-depurar-cultivos')))

    con = sqlite3.connect(GPKG)
    cur = con.cursor()
    r1 = aplicar(cur, t_cult, 'id_cultivo', 'tipo_cultivo', 'superficie_m2',
                 FLAGS_CULT, c[0], c[1], c[2])
    r2 = aplicar(cur, t_anim, 'id_animal', 'especie', 'cantidad',
                 FLAGS_ANIM, a[0], a[1], a[2])
    con.commit()
    cur.execute('PRAGMA wal_checkpoint(TRUNCATE)')
    con.close()
    print('     cultivos : {} renombrados · {} fusionados · {} eliminados'.format(*r1))
    print('     animales : {} renombrados · {} fusionados · {} eliminados'.format(*r2))

    # ── verificación releyendo del disco ──
    con = sqlite3.connect(GPKG)
    cur = con.cursor()
    cur.execute('SELECT COUNT(*), COUNT(DISTINCT tipo_cultivo), '
                'SUM(COALESCE(superficie_m2,0)) FROM "{}"'.format(t_cult))
    v_n, v_t, v_s = cur.fetchone()
    cur.execute('SELECT COUNT(*), COUNT(DISTINCT especie), SUM(COALESCE(cantidad,0)) '
                'FROM "{}"'.format(t_anim))
    a_n, a_t, a_s = cur.fetchone()
    con.close()
    print('\n  VERIFICADO releyendo del disco')
    print('     cultivos : {:,} registros · {} tipos distintos · {} ha'
          .format(v_n, v_t, m2(v_s / 10000)))
    print('     animales : {:,} registros · {} especies distintas · {:,} cabezas'
          .format(a_n, a_t, int(a_s)))
    print('\n  Falta regenerar: export -> gpkg cliente -> informes -> build -> deploy.')
    print('=' * 78)
    return 0


if __name__ == '__main__':
    sys.exit(main())
