# -*- coding: utf-8 -*-
"""
Aplica al padrón las comunidades decididas a mano en la pantalla.

De dónde salen las decisiones
-----------------------------
De «Asignar comunidad a mano» (`/auditoria-areas` → botón del grupo «Datos por
completar»). Esa pantalla enseña, por cada ficha sin comunidad, dónde cae el
punto y qué comunidades tiene alrededor —a cuántos metros y con cuántas fichas
vecinas de cada una—; quien la usa elige mirando el mapa y al final pulsa
«Copiar decisiones».

Lo copiado es una línea por ficha, separada por tabuladores:

    {uid}\t{clave}\t{nombre}\t{COMUNIDAD ELEGIDA}

Se pega en un archivo de texto y se le pasa a este script:

    "C:\\OSGeo4W\\bin\\python-qgis.bat" -X utf8 scripts/aplicar_comunidad_manual.py decisiones.txt
    "C:\\OSGeo4W\\bin\\python-qgis.bat" -X utf8 scripts/aplicar_comunidad_manual.py decisiones.txt --aplicar

Por qué en dos pasos y no directo desde la web
-----------------------------------------------
La web es estática: lee JSON, no escribe en el `data.gpkg`. Y aunque pudiera,
conviene que no lo haga — toda escritura al padrón pasa por un script que
simula primero, respalda con la API de backup de SQLite y verifica releyendo
del disco (reglas 5 y 7). Esta separación mantiene esa garantía.

Comprobaciones antes de escribir
--------------------------------
* que la ficha exista y siga sin comunidad —si alguien ya se la puso, se avisa
  y no se pisa—;
* que el nombre elegido sea una comunidad que ya existe en el padrón, comparado
  en su forma canónica (`comunidades_canon.py`, regla 4), y se escribe con la
  grafía que más se usa, no con la que venga en el archivo.

Sin `--aplicar` no escribe nada.
"""
import argparse
import os
import sqlite3
import sys
import time
from collections import Counter

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from comunidades_canon import canonica  # noqa: E402

GPKG = os.path.join(os.path.expanduser('~'), 'QField', 'cloud',
                    'porotog_levantamiento_offline', 'data.gpkg')
RAIZ_RESPALDOS = (r"C:\Users\HP\OneDrive\Escritorio\CAYAMBE CATASTRO RIEGO"
                  r"\respaldos_qgs")
TABLA = 'Fichas_Predios_880eb10d_d887_4fc6_99a2_8af3ac63877e'
VACIA = ("(comunidad IS NULL OR TRIM(comunidad) = '' "
         "OR UPPER(TRIM(comunidad)) IN ('NULL','NONE','(SIN COMUNIDAD)'))")


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


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('archivo', help='el texto copiado de la pantalla')
    ap.add_argument('--aplicar', action='store_true',
                    help='escribe en el data.gpkg (sin esto solo simula)')
    args = ap.parse_args()

    print('=' * 78)
    print(' COMUNIDADES DECIDIDAS A MANO' +
          ('  [APLICAR]' if args.aplicar else '  [SIMULACION - no escribe nada]'))
    print('=' * 78)

    if not os.path.exists(args.archivo):
        print('ERROR: no existe {}'.format(args.archivo))
        return 1
    with open(args.archivo, encoding='utf-8') as f:
        lineas = [l.rstrip('\n') for l in f if l.strip()]

    decisiones = []
    for n, linea in enumerate(lineas, 1):
        partes = linea.split('\t')
        if len(partes) < 4:
            print('  aviso: línea {} mal formada, se omite: {!r}'.format(n, linea[:60]))
            continue
        decisiones.append((partes[0].strip(), partes[1].strip(),
                           partes[2].strip(), partes[3].strip()))
    print('  decisiones leídas: {}'.format(len(decisiones)))
    if not decisiones:
        return 1

    con = sqlite3.connect(GPKG)
    cur = con.cursor()

    cur.execute('SELECT TRIM(comunidad), COUNT(*) FROM "{}" WHERE NOT {} GROUP BY 1'
                .format(TABLA, VACIA))
    variantes = {}
    for nom, n in cur.fetchall():
        variantes.setdefault(canonica(nom) or nom, []).append((n, nom))
    forma_usual = {k: max(v)[1] for k, v in variantes.items()}

    listas, problemas = [], []
    for uid, clave, nombre, comunidad in decisiones:
        cur.execute('SELECT TRIM(COALESCE(comunidad,\'\')), '
                    'TRIM(COALESCE(apellidos,\'\')||\' \'||COALESCE(nombres,\'\')) '
                    'FROM "{}" WHERE id = ?'.format(TABLA), (uid,))
        fila = cur.fetchone()
        if not fila:
            problemas.append((clave, nombre, 'la ficha no existe en el padrón'))
            continue
        actual, nom_bd = fila
        if actual:
            problemas.append((clave, nom_bd,
                              'ya tiene comunidad «{}», no se pisa'.format(actual)))
            continue
        k = canonica(comunidad) or comunidad
        if k not in forma_usual:
            problemas.append((clave, nom_bd,
                              '«{}» no es una comunidad del padrón'.format(comunidad)))
            continue
        listas.append((uid, clave, nom_bd, forma_usual[k]))

    print('\n  SE APLICAN: {}'.format(len(listas)))
    for _uid, clave, nom, com in listas:
        print('     {:<16} {:<34} -> {}'.format(clave, nom[:34], com))
    if problemas:
        print('\n  NO SE APLICAN: {}'.format(len(problemas)))
        for clave, nom, motivo in problemas:
            print('     {:<16} {:<34} {}'.format(clave, nom[:34], motivo))

    reparto = Counter(c for *_x, c in listas)
    if reparto:
        print('\n  a qué comunidad van:')
        for com, n in reparto.most_common():
            print('     {:<34} {}'.format(com, n))

    if not args.aplicar:
        print('\n  ' + '-' * 74)
        print('  SIMULACION: no se escribió nada. Para aplicarlo:  --aplicar')
        print('  ' + '-' * 74)
        con.close()
        return 0

    if not listas:
        print('\n  Nada que aplicar.')
        con.close()
        return 0

    print('\n  respaldando antes de tocar nada...')
    print('     {}'.format(respaldo_sqlite(GPKG, 'antes-comunidad-manual')))

    cur.execute("SELECT name, sql FROM sqlite_master WHERE type='trigger' AND tbl_name=?",
                (TABLA,))
    triggers = cur.fetchall()
    for nombre, _ in triggers:
        cur.execute('DROP TRIGGER IF EXISTS "{}"'.format(nombre))
    n = 0
    try:
        for uid, _clave, _nom, com in listas:
            cur.execute('UPDATE "{}" SET comunidad = ? WHERE id = ?'.format(TABLA),
                        (com, uid))
            n += cur.rowcount
    finally:
        for _, sql in triggers:
            if sql:
                cur.execute(sql)
    con.commit()
    cur.execute('PRAGMA wal_checkpoint(TRUNCATE)')
    con.close()
    print('     {} fichas actualizadas · {} triggers recreados'.format(n, len(triggers)))

    con = sqlite3.connect('file:{}?mode=ro'.format(GPKG.replace('\\', '/')), uri=True)
    cur = con.cursor()
    cur.execute('SELECT COUNT(*) FROM "{}" WHERE {}'.format(TABLA, VACIA))
    quedan = cur.fetchone()[0]
    con.close()
    print('\n  VERIFICACION (releyendo del disco): quedan {} fichas sin comunidad'
          .format(quedan))
    print('\n  Siguiente: regenerar capas e informes para que recojan el cambio.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
