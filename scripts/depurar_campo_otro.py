# -*- coding: utf-8 -*-
"""
El cultivo que el técnico escribió a mano, escrito de una sola manera.

El hallazgo (18-ago-2026)
-------------------------
`depurar_cultivos_y_animales.py` unificó la escritura de `tipo_cultivo` (37 → 19)
y de `especie` (31 → 15). Pero cuando el técnico elige **«Otros»** en el
formulario y escribe el nombre a mano, ese texto va a otro campo —
`tipo_cultivo_otro` / `especie_otro` — que **nunca se depuró**.

Y ese campo no es interno: `generar_capitulo_produccion.py:118` lo publica tal
cual en el informe que se entrega al consorcio. La arveja está escrita de ocho
maneras (ARBEJA, ARVERJA, ALBERJA, ARVEJA, ALVERJA, ARBERJA, ARBEJAS, ATBEJA) y
sale como ocho cultivos distintos en `Produccion_Agropecuaria.xlsx`.

Peor que la lista sucia: el agrupador del informe busca la palabra `arveja`
dentro del nombre, así que **51 de las 57 filas de arveja caen hoy en «Otros
cultivos»** en vez de «Cereales y leguminosas». Lo mismo con la alfalfa mal
escrita, que no llega a «Pastos», y con los patrones, que no llegan a «Flores».

    nombres de cultivo distintos en el entregable   80  ->  58
    especies distintas                              38  ->  30
    grupo «Otros cultivos»                    78,90 ha  ->  62,24 ha

Qué hace, por bloques
---------------------
**A — escritura (por defecto).** Cada variante pasa a un nombre canónico, en
formato Título y sin espacios sobrantes. Solo toca el campo de texto: **no
cambia ninguna superficie, ninguna cantidad y ningún tipo**. El diccionario de
abajo es explícito a propósito — nada se adivina por parecido de letras.

**B — el texto ya es una categoría del catálogo** (`--con-catalogo`). Alguien
escribió a mano «CHOCHO» o «CEBADA» teniendo esas opciones en la lista. Se pasa
el registro a su categoría y se vacía el campo libre. En animales incluye el
criterio zootécnico: borrego es oveja y chivo es cabra, así que van a
«Ovejas / Cabras»; caballo y burro van a «Equinos».

**C — el campo libre repite lo ya elegido** (`--con-redundantes`). Especie
«Vacas en producción» con el texto «VACAS» al lado. Se vacía el campo libre.

Uso del suelo contado como cultivo (decisión de JAVIKO, 18-ago-2026)
---------------------------------------------------------------------
POTRERO, LADERA y PENDUENTE (16 filas, 13,79 ha) no son un cultivo: describen
la cobertura del terreno, igual que «Pasto no mejorado». Se reclasifican ahí.
CASCAJO y TERRENO PREPARADO (3 filas, 2,85 ha) se reclasifican a «Baldío», que
ya es una categoría del catálogo. Van en el bloque B (`--con-catalogo`), igual
que CHOCHO/CEBADA/TRIGO/HORTALIZAS.

**Sin decidir, quedan fuera a propósito:** RESERVORIO (3 filas, 0,40 ha) —no es
uso agrícola del suelo, es infraestructura— y HUERTO (1 fila) —si es huerto
familiar mixto, podría ser cultivo real—.

Lo que NO hace
--------------
* **No une ZAMBO con ZAPALLO** (143 y 101 filas): el técnico los distinguió y no
  hay base para decidir que son lo mismo.
* **No toca los registros donde el campo libre contradice al tipo** —
  `Pasto mejorado` + «CEBOLLA», `Pasto no mejorado` + «500», `Cebolla` +
  «HABAS,CEBOLLA Y PAPAS»—. Ahí no se sabe cuál de los dos datos vale; se
  listan al final para verificarlos en campo.

Ojo con la segunda pasada
-------------------------
Unificar la escritura puede dejar **dos registros del mismo cultivo dentro de una
misma ficha** («ARBEJA 100» + «ARVEJA 200» → dos «Arveja»). Este script los
detecta y los reporta, pero **no los fusiona**: eso lo hace
`depurar_cultivos_y_animales.py`, que ya tiene la regla del cliente (un registro
por cultivo, con la superficie sumada). Si el informe reporta casos, hay que
correrlo después.

Uso
---
    "C:\\OSGeo4W\\bin\\python-qgis.bat" -X utf8 scripts/depurar_campo_otro.py
    "C:\\OSGeo4W\\bin\\python-qgis.bat" -X utf8 scripts/depurar_campo_otro.py --aplicar

Sin `--aplicar` no escribe nada (regla 7). Con `--aplicar` respalda antes, con la
API de backup de SQLite y fuera de la carpeta de QFieldCloud (regla 5). Sobre
estas dos tablas solo hay triggers de INSERT y DELETE de `feature_count`: como
aquí solo se hacen UPDATE, no hay que retirarlos ni recrearlos.

Cómo revertirlo: `docs/CORRECCION-campo-otro.md`.

Después hay que regenerar: export → gpkg del cliente → informes → build → deploy.
"""
import argparse
import os
import sqlite3
import time
import unicodedata
from collections import defaultdict

GPKG = os.path.join(os.path.expanduser('~'), 'QField', 'cloud',
                    'porotog_levantamiento_offline', 'data.gpkg')
RAIZ_RESPALDOS = (r"C:\Users\HP\OneDrive\Escritorio\CAYAMBE CATASTRO RIEGO"
                  r"\respaldos_qgs")


def norm(s):
    """Para comparar: sin tildes, sin dobles espacios, en mayúsculas."""
    s = unicodedata.normalize('NFKD', str(s or '').strip().upper())
    s = ''.join(c for c in s if not unicodedata.combining(c))
    return ' '.join(s.split())


def variantes(destino, *vs):
    return {norm(v): destino for v in vs}


def cargar(pares):
    d = {}
    for destino, vs in pares:
        d.update(variantes(destino, *vs))
    return d


# ── A. Escritura: variante → nombre canónico ────────────────────────────────
# Cada línea es una decisión tomada mirando el dato, no una regla automática.
CANON_CULTIVO = cargar([
    ('Arveja',              ('arbeja', 'arbejas', 'arberja', 'arveja',
                             'arverja', 'alberja', 'alverja', 'atbeja')),
    ('Zambo',               ('zambo', 'sambos')),
    ('Avena',               ('avena', 'acena')),
    ('Alfalfa',             ('alfalfa', 'alfafa')),
    ('Oca',                 ('oca', 'ocas')),
    ('Tomate riñón',        ('tomate riñon', 'tomate riño', 'tomate riñón')),
    ('Patrones de flores',  ('patrones', 'patrones de flores',
                             'patrones de rosas', 'patrones rosas', 'potrones')),
    ('Aguacate',            ('aguacate', 'aguacates', 'aguate')),
    ('Mora',                ('mora', 'moras')),
    ('Frutilla',            ('frutilla', 'fresas')),
    ('Invernadero',         ('invernadero múltiple', 'inerndero')),
    ('Plantas medicinales', ('plantas medicinales', 'hierbas medicinales')),
    ('Albahaca',            ('albaca',)),
])

CANON_ANIMAL = cargar([
    ('Patos',             ('patos', 'pato')),
    ('Gansos',            ('gansos', 'ganzos')),
    ('Chivos',            ('chivos', 'chivo')),
    ('Pavos',             ('pavos', 'pavo')),
    ('Borregos',          ('borregos', 'borrego')),
    ('Llamingos',         ('llamingo', 'llamingos')),
    ('Caballos',          ('caballos', 'caballo')),
    ('Burros',            ('burros', 'burro')),
    ('Aves ornamentales', ('aves hornamentales',)),
])

# ── B. El texto libre ya es una categoría del catálogo del formulario ───────
CATALOGO_CULTIVO = cargar([
    ('Chocho',     ('chocho',)),
    ('Cebada',     ('cebada',)),
    ('Trigo',      ('trigo',)),
    ('Hortalizas', ('hortalizas',)),
    # Uso del suelo, no cultivo — decisión de JAVIKO, 18-ago-2026.
    ('Pasto no mejorado', ('potrero', 'ladera', 'penduente')),
    ('Baldío',            ('cascajo', 'terreno preparado',
                           'terreno preparado para arar')),
])

# Borrego es oveja y chivo es cabra: van a la categoría que ya existe.
# Caballo y burro son équidos.
# YUNTAS (1 registro, 1 cabeza) va a bovinos por decisión de JAVIKO del
# 18-ago-2026. Nota para quien lo revise: una yunta es un par de bueyes —machos
# castrados de trabajo—, así que «Toros» sería lo exacto; se dejó en «Vacas en
# producción» porque es lo que se pidió y el peso en el hato es de 1 cabeza.
CATALOGO_ANIMAL = cargar([
    ('Ovejas / Cabras',     ('borregos', 'borrego', 'chivos', 'chivo')),
    ('Equinos',             ('caballos', 'caballo', 'burros', 'burro')),
    ('Vacas en producción', ('yuntas', 'yunta')),
])


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
    for (t,) in cur.fetchall():
        if clave in t and not any(x in t for x in ('rtree_', 'log_', 'gpkg_')):
            return t
    raise SystemExit('No se encontró la tabla %s en el gpkg' % clave)


def raiz(s):
    """Quita el plural simple para comparar «VACA» con «VACAS»."""
    return s[:-1] if s.endswith('S') and len(s) > 3 else s


def redundante(tipo, otro):
    """El texto libre no aporta nada: repite el tipo ya elegido.

    «Vacas en producción» + «VACAS», «Vaconas» + «VACONA».
    """
    n, t = norm(otro), norm(tipo)
    return raiz(n) in (raiz(t), raiz(t.split(' ')[0]))


def analizar(cur, t, col_id, col_tipo, col_otro, col_val, canon, catalogo):
    """Devuelve (bloque_a, bloque_b, bloque_c, sin_coincidir) sin escribir nada.

    Cada elemento: (id, tipo_actual, texto_actual, tipo_nuevo, texto_nuevo,
    valor, ficha_id)
    """
    cur.execute('SELECT {}, {}, {}, {}, ficha_id FROM "{}" '
                'WHERE {} IS NOT NULL AND TRIM({}) <> ""'
                .format(col_id, col_tipo, col_otro, col_val, t, col_otro, col_otro))
    filas = cur.fetchall()
    a, b, c, sin_coincidir = [], [], [], []
    for rid, tipo, otro, val, ficha in filas:
        n = norm(otro)
        es_otros = norm(tipo) in ('OTRO', 'OTROS')
        if not es_otros:
            # el tipo ya está elegido y además hay texto libre
            if redundante(tipo, otro):
                c.append((rid, tipo, otro, tipo, None, val, ficha))
            else:
                sin_coincidir.append((rid, tipo, otro, val, ficha))
            continue
        destino_cat = catalogo.get(n)
        if destino_cat:
            b.append((rid, tipo, otro, destino_cat, None, val, ficha))
            continue
        nuevo = canon.get(n)
        if nuevo is None:
            # sin variante conocida: al menos se limpia el espaciado y la caja
            nuevo = ' '.join(otro.split())
            nuevo = nuevo[:1].upper() + nuevo[1:].lower() if nuevo else nuevo
        if nuevo != otro:
            a.append((rid, tipo, otro, tipo, nuevo, val, ficha))
    return a, b, c, sin_coincidir


def m2(v):
    return '{:,.2f}'.format(v).replace(',', '@').replace('.', ',').replace('@', '.')


def informe(titulo, a, b, c, sin_coincidir, unidad):
    print('\n' + '=' * 78)
    print(' ' + titulo)
    print('=' * 78)

    print('\n  [A] ESCRITURA UNIFICADA  —  %d registros' % len(a))
    agr = defaultdict(lambda: [0, 0.0, set()])
    for _rid, _tp, otro, _tn, nuevo, val, _f in a:
        g = agr[nuevo]
        g[0] += 1
        g[1] += float(val or 0)
        g[2].add(otro.strip())
    for nuevo, (n, val, origs) in sorted(agr.items(), key=lambda x: -x[1][0]):
        print('     %-22s %4d reg  %12s %s' % (nuevo, n, m2(val), unidad))
        print('        desde: %s' % ' | '.join(sorted(origs)))

    print('\n  [B] PASA A UNA CATEGORIA QUE YA EXISTE  —  %d registros  (--con-catalogo)'
          % len(b))
    agr = defaultdict(lambda: [0, 0.0, set()])
    for _rid, tipo, otro, destino, _tn, val, _f in b:
        g = agr[destino]
        g[0] += 1
        g[1] += float(val or 0)
        g[2].add(otro.strip())
    for destino, (n, val, origs) in sorted(agr.items(), key=lambda x: -x[1][0]):
        print('     «Otros» + %-24s ->  %-18s %3d reg  %10s %s'
              % ('/'.join(sorted(origs))[:24], destino, n, m2(val), unidad))

    print('\n  [C] EL TEXTO LIBRE REPITE EL TIPO YA ELEGIDO  —  %d registros'
          '  (--con-redundantes)' % len(c))
    for _rid, tipo, otro, _d, _tn, val, _f in c:
        print('     %-24s + «%s»  ->  se vacía el campo libre' % (tipo, otro.strip()))

    print('\n  [!] EL TEXTO LIBRE NO COINCIDE CON EL TIPO — NO SE TOCAN,'
          ' verificar en campo  —  %d registros' % len(sin_coincidir))
    for _rid, tipo, otro, val, _f in sin_coincidir:
        print('     %-24s + «%s»   (%s %s)' % (tipo, otro.strip(), m2(float(val or 0)), unidad))


def aplicar(con, cur, t, col_id, col_tipo, col_otro, cambios):
    for rid, _tp, _otro, tipo_nuevo, texto_nuevo, _val, _f in cambios:
        cur.execute('UPDATE "{}" SET {} = ?, {} = ? WHERE {} = ?'
                    .format(t, col_tipo, col_otro, col_id),
                    (tipo_nuevo, texto_nuevo, rid))
    return len(cambios)


def main():
    ap = argparse.ArgumentParser(
        description='Unifica la escritura del campo libre «Otros» de cultivos y animales')
    ap.add_argument('--aplicar', action='store_true',
                    help='escribe en el data.gpkg (sin esto solo simula)')
    ap.add_argument('--con-catalogo', action='store_true',
                    help='aplica también el bloque B (pasar a categoría existente)')
    ap.add_argument('--con-redundantes', action='store_true',
                    help='aplica también el bloque C (vaciar el texto que repite el tipo)')
    args = ap.parse_args()

    print('=' * 78)
    print(' CAMPO LIBRE «OTROS»: UNA SOLA ESCRITURA' +
          ('  [APLICAR]' if args.aplicar else '  [SIMULACION - no escribe nada]'))
    print('=' * 78)
    print(' gpkg: %s' % GPKG)

    con = sqlite3.connect(GPKG)
    cur = con.cursor()
    t_cult = tabla(cur, 'Cultivos_Agricolas')
    t_anim = tabla(cur, 'Animales_Especies')

    ac, bc, cc, xc = analizar(cur, t_cult, 'id_cultivo', 'tipo_cultivo',
                              'tipo_cultivo_otro', 'superficie_m2',
                              CANON_CULTIVO, CATALOGO_CULTIVO)
    aa, ba, ca, xa = analizar(cur, t_anim, 'id_animal', 'especie',
                              'especie_otro', 'cantidad',
                              CANON_ANIMAL, CATALOGO_ANIMAL)
    informe('CULTIVOS', ac, bc, cc, xc, 'm²')
    informe('ANIMALES', aa, ba, ca, xa, 'cabezas')

    # ¿Quedarían dos registros del mismo nombre dentro de una misma ficha?
    print('\n' + '=' * 78)
    print(' SEGUNDA PASADA NECESARIA')
    print('=' * 78)
    def choques(t, col_tipo, col_otro, cambios):
        """Fichas que quedarían con dos registros del mismo nombre."""
        nuevo_de = {r[0]: (r[3], r[4]) for r in cambios}
        col_id = 'id_cultivo' if 'Cultivos' in t else 'id_animal'
        cur.execute('SELECT {}, ficha_id, {}, {} FROM "{}"'
                    .format(col_id, col_tipo, col_otro, t))
        por_ficha = defaultdict(list)
        for rid, ficha, tipo, otro in cur.fetchall():
            if rid in nuevo_de:
                tipo, otro = nuevo_de[rid]
            nombre = otro if (norm(tipo) in ('OTRO', 'OTROS') and otro) else tipo
            if nombre:
                por_ficha[ficha].append(norm(nombre))
        return sum(1 for v in por_ficha.values() if len(v) != len(set(v)))

    for t, col_tipo, col_otro, a_, b_, etq in (
            (t_cult, 'tipo_cultivo', 'tipo_cultivo_otro', ac, bc, 'cultivos'),
            (t_anim, 'especie', 'especie_otro', aa, ba, 'animales')):
        solo_a = choques(t, col_tipo, col_otro, a_)
        con_b = choques(t, col_tipo, col_otro, a_ + b_)
        print('  %-9s fichas con el mismo nombre repetido:  solo [A] %d'
              '   ·   [A]+[B] %d' % (etq, solo_a, con_b))
    print('\n  Si sale distinto de 0, correr después «depurar_cultivos_y_animales.py»,'
          '\n  que fusiona el repetido sumando (regla del cliente).')

    total_a = len(ac) + len(aa)
    total_b = len(bc) + len(ba)
    total_c = len(cc) + len(ca)
    print('\n  RESUMEN')
    print('     [A] escritura unificada        %4d registros' % total_a)
    print('     [B] pasa a categoría existente %4d registros %s'
          % (total_b, '' if args.con_catalogo else '(NO se aplica: falta --con-catalogo)'))
    print('     [C] texto libre redundante     %4d registros %s'
          % (total_c, '' if args.con_redundantes else '(NO se aplica: falta --con-redundantes)'))
    print('     [!] texto que no coincide      %4d registros (nunca se tocan)'
          % (len(xc) + len(xa)))
    print('\n     Ninguna superficie ni cantidad cambia. El número de registros'
          '\n     tampoco: esto solo reescribe texto.')

    if not args.aplicar:
        print('\n  ' + '-' * 74)
        print('  SIMULACION: no se escribió nada. Para aplicarlo:  --aplicar')
        print('  ' + '-' * 74)
        con.close()
        return

    ruta = respaldo_sqlite(GPKG, 'antes-campo-otro')
    print('\n  Respaldo: %s' % ruta)

    n = 0
    n += aplicar(con, cur, t_cult, 'id_cultivo', 'tipo_cultivo', 'tipo_cultivo_otro', ac)
    n += aplicar(con, cur, t_anim, 'id_animal', 'especie', 'especie_otro', aa)
    if args.con_catalogo:
        n += aplicar(con, cur, t_cult, 'id_cultivo', 'tipo_cultivo', 'tipo_cultivo_otro', bc)
        n += aplicar(con, cur, t_anim, 'id_animal', 'especie', 'especie_otro', ba)
    if args.con_redundantes:
        n += aplicar(con, cur, t_cult, 'id_cultivo', 'tipo_cultivo', 'tipo_cultivo_otro', cc)
        n += aplicar(con, cur, t_anim, 'id_animal', 'especie', 'especie_otro', ca)
    con.commit()
    con.close()
    print('  Escritos %d registros.' % n)

    # ── verificación releyendo del disco ────────────────────────────────────
    con = sqlite3.connect('file:%s?mode=ro' % GPKG.replace('\\', '/'), uri=True)
    cur = con.cursor()
    print('\n  VERIFICACION (releyendo del disco)')
    for t, col_tipo, col_otro, etq in ((t_cult, 'tipo_cultivo', 'tipo_cultivo_otro', 'cultivos'),
                                       (t_anim, 'especie', 'especie_otro', 'animales')):
        cur.execute('SELECT COUNT(DISTINCT {}) FROM "{}" WHERE {} IS NOT NULL '
                    'AND TRIM({}) <> ""'.format(col_otro, t, col_otro, col_otro))
        print('     %-9s textos distintos en el campo libre: %d' % (etq, cur.fetchone()[0]))
    cur.execute('SELECT COUNT(*) FROM "{}"'.format(t_cult))
    nc = cur.fetchone()[0]
    cur.execute('SELECT ROUND(SUM(superficie_m2)/10000.0, 2) FROM "{}"'.format(t_cult))
    sc = cur.fetchone()[0]
    cur.execute('SELECT COUNT(*), SUM(cantidad) FROM "{}"'.format(t_anim))
    na, ca_ = cur.fetchone()
    print('     cultivos %d registros, %s ha   ·   animales %d registros, %s cabezas'
          % (nc, m2(sc), na, ca_))
    print('     (si estas cifras cambiaron respecto de antes, algo salió mal)')
    con.close()


if __name__ == '__main__':
    main()
