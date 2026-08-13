# -*- coding: utf-8 -*-
"""
Unifica cómo está escrito el nombre de la comunidad en el data.gpkg.

El problema
-----------
Los técnicos teclean el nombre a mano y una misma comunidad convive con dos
grafías. En varios casos **la mayoritaria es la equivocada**:

    PANBAMAQUITO      71 fichas   ·  PAMBAMARQUITO       1
    COMUNA INSACATA  127 fichas   ·  COMUNA IZACATA     10
    LOS ANDES IZACATA 104 fichas  ·  LOS ANDES INSACATA  4
    LARCACHACA       223 fichas   ·  LARCACOCHA          2

Hoy eso no se nota fuera: el export canoniza los nombres antes de publicar, así
que la web y los informes ya salen bien. Pero dentro del gpkg —que es lo que se
entrega en el GeoPackage y lo que ven los técnicos en QField— siguen las dos
formas, y cualquier consulta directa que agrupe por `comunidad` parte el dato en
dos sin avisar.

Cuál es el nombre bueno
-----------------------
No se inventa: se toma del catálogo oficial de comunidades
(`src/lib/constants.ts`, `CATALOGO_COMUNIDADES`), que es el mismo listado
numerado 1–50 que sale en los filtros de la web. Su campo `datos` dice
exactamente cómo debe estar escrito el nombre en el gpkg, y su propio
comentario avisa: «Nunca cambiarlo sin migrar las fichas». Esto es esa
migración.

El emparejamiento se hace canonizado con `comunidades_canon.py` (regla 4 del
proyecto), así que da igual la tildación o la errata: lo que decide es a qué
comunidad se refiere.

Uso
---
    "C:\\OSGeo4W\\bin\\python-qgis.bat" -X utf8 scripts/unificar_nombres_comunidad.py
    "C:\\OSGeo4W\\bin\\python-qgis.bat" -X utf8 scripts/unificar_nombres_comunidad.py --aplicar

Sin `--aplicar` no escribe nada (regla 7). No cambia ninguna cifra: solo unifica
cómo se escribe el nombre.
"""
import argparse
import os
import re
import sqlite3
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from comunidades_canon import canonica  # noqa: E402

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
GPKG = os.path.join(os.path.expanduser('~'), 'QField', 'cloud',
                    'porotog_levantamiento_offline', 'data.gpkg')
CONSTANTS = os.path.join(BASE, 'src', 'lib', 'constants.ts')
RAIZ_RESPALDOS = (r"C:\Users\HP\OneDrive\Escritorio\CAYAMBE CATASTRO RIEGO"
                  r"\respaldos_qgs")
TABLA = 'Fichas_Predios_880eb10d_d887_4fc6_99a2_8af3ac63877e'


def respaldo_sqlite(origen, etiqueta):
    carpeta = os.path.join(RAIZ_RESPALDOS, time.strftime('%Y-%m-%d'))
    os.makedirs(carpeta, exist_ok=True)
    destino = os.path.join(carpeta, '{}.{}-{}.bak'.format(
        os.path.basename(origen), time.strftime('%H%M'), etiqueta))
    src = sqlite3.connect(origen); dst = sqlite3.connect(destino)
    with dst:
        src.backup(dst)
    dst.close(); src.close()
    return destino


def catalogo():
    """Las comunidades del listado oficial, leídas de constants.ts.

    Se lee el archivo en vez de duplicar la lista aquí: si mañana se corrige
    una entrada del catálogo, este script la recoge sola.
    """
    txt = open(CONSTANTS, encoding='utf-8').read()
    bloque = re.search(r'CATALOGO_COMUNIDADES[^=]*=\s*\[(.*?)\n\];', txt, re.S)
    if not bloque:
        raise RuntimeError('no se encontró CATALOGO_COMUNIDADES en constants.ts')
    salida = []
    for m in re.finditer(
            r"\{\s*n:\s*(\d+).*?oficial:\s*'([^']*)'.*?datos:\s*'([^']*)'"
            r"(.*?)\}", bloque.group(1), re.S):
        n, oficial, datos, resto = m.groups()
        salida.append({'n': int(n), 'oficial': oficial, 'datos': datos,
                       'oculta': 'oculta: true' in resto})
    return salida


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--aplicar', action='store_true',
                    help='escribe en el data.gpkg (sin esto solo simula)')
    args = ap.parse_args()

    print("=" * 78)
    print(" NOMBRES DE COMUNIDAD" +
          ("  [APLICAR]" if args.aplicar else "  [SIMULACION - no escribe nada]"))
    print("=" * 78)

    cat = catalogo()
    print("\n  catálogo oficial: {} comunidades ({} ocultas)"
          .format(len(cat), sum(1 for c in cat if c['oculta'])))
    por_canon = {}
    for c in cat:
        por_canon.setdefault(canonica(c['datos']) or c['datos'], c)

    con = sqlite3.connect(GPKG)
    cur = con.cursor()
    t = '"{}"'.format(TABLA)
    cur.execute("SELECT TRIM(comunidad), COUNT(*) FROM {} WHERE comunidad IS NOT NULL "
                "AND TRIM(comunidad) <> '' GROUP BY 1 ORDER BY 2 DESC".format(t))
    en_datos = cur.fetchall()
    con.close()
    print("  en el gpkg      : {} formas distintas, {:,} fichas"
          .format(len(en_datos), sum(n for _, n in en_datos)))

    cambios, sin_catalogo, ya_ok = [], [], 0
    for nombre, n in en_datos:
        c = por_canon.get(canonica(nombre) or nombre)
        if not c:
            sin_catalogo.append((nombre, n))
        elif c['datos'] != nombre:
            cambios.append({'de': nombre, 'a': c['datos'], 'n': n,
                            'num': c['n'], 'oficial': c['oficial']})
        else:
            ya_ok += 1

    print("\n" + "-" * 78)
    print(" SE UNIFICAN")
    print("-" * 78)
    if not cambios:
        print("   nada: todos los nombres ya coinciden con el catálogo")
    for c in sorted(cambios, key=lambda x: -x['n']):
        print("   {:>3}. {:<26} «{}» -> «{}»   {} ficha{}"
              .format(c['num'], c['oficial'][:26], c['de'], c['a'],
                      c['n'], 's' if c['n'] != 1 else ''))
    print("\n   {} forma(s) ya correctas, {} ficha(s) a corregir"
          .format(ya_ok, sum(c['n'] for c in cambios)))

    if sin_catalogo:
        print("\n" + "-" * 78)
        print(" NO ESTAN EN EL CATALOGO — no se tocan")
        print("-" * 78)
        for nombre, n in sin_catalogo:
            print("   {:<34} {} ficha(s)".format(nombre[:34], n))

    if not args.aplicar:
        print("\n  SIMULACION: no se escribió nada.")
        print("  No cambia ninguna cifra: solo unifica cómo se escribe el nombre.")
        print("=" * 78)
        return 0

    if not cambios:
        print("\n  Nada que aplicar.")
        return 0

    print("\n  respaldando antes de tocar nada...")
    print("     {}".format(respaldo_sqlite(GPKG, 'antes-nombres-comunidad')))

    con = sqlite3.connect(GPKG)
    cur = con.cursor()
    cur.execute("SELECT name, sql FROM sqlite_master "
                "WHERE type='trigger' AND tbl_name=?", (TABLA,))
    triggers = cur.fetchall()
    for nombre, _ in triggers:
        cur.execute('DROP TRIGGER IF EXISTS "{}"'.format(nombre))
    try:
        tocadas = 0
        for c in cambios:
            cur.execute("UPDATE {} SET comunidad = ? WHERE TRIM(comunidad) = ?"
                        .format(t), (c['a'], c['de']))
            tocadas += cur.rowcount
    finally:
        for _, sql in triggers:
            if sql:
                cur.execute(sql)
    con.commit()
    cur.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    con.close()
    print("     {} fichas actualizadas · {} triggers recreados"
          .format(tocadas, len(triggers)))

    # verificación releyendo del disco
    con = sqlite3.connect(GPKG)
    cur = con.cursor()
    cur.execute("SELECT TRIM(comunidad), COUNT(*) FROM {} WHERE comunidad IS NOT NULL "
                "AND TRIM(comunidad) <> '' GROUP BY 1".format(t))
    quedan = [(nom, n) for nom, n in cur.fetchall()
              if (c := por_canon.get(canonica(nom) or nom)) and c['datos'] != nom]
    con.close()
    print("\n  VERIFICACION (releyendo del disco):")
    print("     formas que aún no coinciden con el catálogo: {}".format(len(quedan)))
    for nom, n in quedan:
        print("        {} ({})".format(nom, n))
    print("\n  {}".format('NOMBRES UNIFICADOS Y VERIFICADO' if not quedan
                          else '!! REVISAR: quedaron formas sin unificar'))
    print("\n  Siguiente: regenerar capas e informes.")
    print("=" * 78)
    return 0 if not quedan else 1


if __name__ == '__main__':
    sys.exit(main())
