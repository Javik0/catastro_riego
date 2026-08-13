# -*- coding: utf-8 -*-
"""
Recupera el área que el técnico escribió en las observaciones.

El hallazgo
-----------
En muchos predios compartidos las fichas declaran **el predio entero cada una**,
y por eso la superficie del padrón sale inflada. Pero al leer las observaciones
aparece que el técnico **sí anotó cuánto le corresponde a cada regante** — solo
que en el campo equivocado:

    predio 1702550220015, polígono de 98.056 m²
        cinco hermanos Cevallos Gordón declaran 98.056 m² cada uno
        y sus observaciones dicen 12.500, 15.266, 14.420, 12.623 y 16.053

El dato correcto existe, está escrito, y no hace falta ir a campo a buscarlo.

Qué corrige y qué no
--------------------
Solo los predios donde **las áreas de las observaciones suman el polígono**
(dentro del margen de `--margen`). Ese cuadre es la prueba de que el reparto
está completo y bien entendido: si las partes suman el todo, no hay
interpretación que hacer.

Donde las observaciones existen pero no cuadran —falta alguna ficha, o el
reparto no llega al polígono— no se toca nada y se lista aparte. Ahí sí hace
falta una persona.

Qué pasa con el área de riego
-----------------------------
Al cambiar el área total hay que decidir qué ocurre con las de riego y sin
riego. Se mantiene la **proporción** que traía la ficha: si declaraba todo su
terreno bajo riego, sigue todo bajo riego, pero sobre la superficie que de
verdad le corresponde. Es lo único que se puede afirmar sin inventar dato.

Uso
---
    "C:\\OSGeo4W\\bin\\python-qgis.bat" -X utf8 scripts/corregir_areas_por_observacion.py
    "C:\\OSGeo4W\\bin\\python-qgis.bat" -X utf8 scripts/corregir_areas_por_observacion.py --aplicar

Sin `--aplicar` no escribe nada (regla 7).

⚠ Esto **cambia la superficie del padrón**, que es cifra publicada. Requiere el
visto bueno de la coordinación antes de aplicarse.
"""
import argparse
import json
import os
import sqlite3
import sys
import time
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from generar_auditoria_areas import num_del_texto  # noqa: E402

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
GPKG = os.path.join(os.path.expanduser('~'), 'QField', 'cloud',
                    'porotog_levantamiento_offline', 'data.gpkg')
CATASTRO = os.path.join(BASE, 'public', 'geo', 'catastro_geo.geojson')
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


def ha(v):
    return '{:,.2f}'.format(v / 10000.0).replace(',', 'X').replace('.', ',').replace('X', '.')


def analizar(margen=0.15):
    """Predios cuyas observaciones traen el reparto completo del área."""
    cat = {}
    with open(CATASTRO, encoding='utf-8') as f:
        for ft in json.load(f).get('features', []):
            p = ft.get('properties') or {}
            c = str(p.get('clave_cata') or '').strip()
            if c and p.get('area_predi'):
                cat[c] = float(p['area_predi'])

    con = sqlite3.connect(GPKG)
    cur = con.cursor()
    cur.execute(
        "SELECT COALESCE(id,''), TRIM(COALESCE(clave_catastral,'')), "
        "TRIM(COALESCE(apellidos,'') || ' ' || COALESCE(nombres,'')), "
        "COALESCE(area_total,0), COALESCE(area_riego,0), "
        "COALESCE(area_sin_riego,0), COALESCE(observaciones,''), "
        "COALESCE(comunidad,'') FROM \"{}\"".format(TABLA))
    filas = cur.fetchall()
    con.close()

    por_clave = defaultdict(list)
    for uid, clave, nom, at, ar, asr, obs, com in filas:
        if clave in cat:
            por_clave[clave].append({
                'uid': uid, 'nom': nom, 'at': at, 'ar': ar, 'asr': asr,
                'obs': (obs or '').strip(), 'com': com,
                'oa': num_del_texto(obs) if obs else None})

    cuadran, no_cuadran = [], []
    for clave, fichas in por_clave.items():
        pol = cat[clave]
        if len(fichas) < 2:
            continue
        dec = sum(f['at'] for f in fichas)
        if dec - pol <= 1000:            # este predio no está inflado
            continue
        con_oa = [f for f in fichas if f['oa']]
        if not con_oa:
            continue
        caso = {'clave': clave, 'pol': pol, 'dec': dec,
                'com': fichas[0]['com'], 'fichas': fichas,
                'n_oa': len(con_oa), 'suma_oa': sum(f['oa'] for f in con_oa)}
        completo = len(con_oa) == len(fichas)
        cuadra = pol > 0 and abs(caso['suma_oa'] - pol) / pol <= margen
        if completo and cuadra:
            cuadran.append(caso)
        else:
            caso['motivo'] = ('{} de {} fichas tienen área en la observación'
                              .format(len(con_oa), len(fichas)) if not completo
                              else 'las observaciones suman {} ha sobre un polígono de {} ha'
                              .format(ha(caso['suma_oa']), ha(pol)))
            no_cuadran.append(caso)
    cuadran.sort(key=lambda c: -(c['dec'] - c['pol']))
    no_cuadran.sort(key=lambda c: -(c['dec'] - c['pol']))
    return cuadran, no_cuadran


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--aplicar', action='store_true',
                    help='escribe en el data.gpkg (sin esto solo simula)')
    ap.add_argument('--margen', type=float, default=0.15,
                    help='holgura al comparar la suma con el polígono (0-1)')
    args = ap.parse_args()

    print("=" * 80)
    print(" AREA ESCRITA EN LAS OBSERVACIONES" +
          ("  [APLICAR]" if args.aplicar else "  [SIMULACION - no escribe nada]"))
    print("=" * 80)

    cuadran, no_cuadran = analizar(args.margen)

    print("\n" + "-" * 80)
    print(" SE CORRIGEN — las observaciones reparten el predio entero")
    print("-" * 80)
    ahorro = 0.0
    for c in cuadran:
        ahorro += c['dec'] - c['suma_oa']
        print("\n   {} · {} · polígono {} ha".format(c['clave'], c['com'][:26], ha(c['pol'])))
        print("      declaran {} ha entre {} fichas; las observaciones dicen {} ha"
              .format(ha(c['dec']), len(c['fichas']), ha(c['suma_oa'])))
        for f in c['fichas']:
            print("         {:<32} {:>9,.0f} -> {:>9,.0f} m²"
                  .format(f['nom'][:32], f['at'], f['oa']))

    print("\n" + "-" * 80)
    print(" NO SE TOCAN — las observaciones no completan el reparto")
    print("-" * 80)
    for c in no_cuadran[:12]:
        print("   {} · {:<24} sobran {:>8} ha · {}"
              .format(c['clave'], c['com'][:24], ha(c['dec'] - c['pol']), c['motivo']))
    if len(no_cuadran) > 12:
        print("   … y {} predios más".format(len(no_cuadran) - 12))

    print("\n" + "=" * 80)
    print("  predios que se corrigen : {:>4}  ({} fichas)"
          .format(len(cuadran), sum(len(c['fichas']) for c in cuadran)))
    print("  superficie que se quita : {:>9} ha".format(ha(ahorro)))
    print("  predios que quedan      : {:>4}".format(len(no_cuadran)))

    if not args.aplicar:
        print("\n  SIMULACION: no se escribió nada.")
        print("  Cambia la superficie del padrón: requiere visto bueno antes de aplicar.")
        print("=" * 80)
        return 0

    if not cuadran:
        print("\n  Nada que aplicar.")
        return 0

    print("\n  respaldando antes de tocar nada...")
    print("     {}".format(respaldo_sqlite(GPKG, 'antes-areas-por-observacion')))

    t = '"{}"'.format(TABLA)
    con = sqlite3.connect(GPKG)
    cur = con.cursor()
    cur.execute("SELECT name, sql FROM sqlite_master "
                "WHERE type='trigger' AND tbl_name=?", (TABLA,))
    triggers = cur.fetchall()
    for nombre, _ in triggers:
        cur.execute('DROP TRIGGER IF EXISTS "{}"'.format(nombre))
    try:
        n = 0
        for c in cuadran:
            for f in c['fichas']:
                nuevo = float(f['oa'])
                # se conserva la proporción de riego que traía la ficha
                factor = nuevo / f['at'] if f['at'] else 0
                cur.execute(
                    "UPDATE {} SET area_total = ?, area_riego = ?, "
                    "area_sin_riego = ? WHERE id = ?".format(t),
                    (nuevo, round(f['ar'] * factor, 2),
                     round(f['asr'] * factor, 2), f['uid']))
                n += cur.rowcount
    finally:
        for _, sql in triggers:
            if sql:
                cur.execute(sql)
    con.commit()
    cur.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    con.close()
    print("     {} fichas actualizadas · {} triggers recreados".format(n, len(triggers)))

    c2, n2 = analizar(args.margen)
    print("\n  VERIFICACION (releyendo del disco):")
    print("     predios que aún se corregirían: {} · se esperaban 0".format(len(c2)))
    print("\n  {}".format('CORRECCION APLICADA Y VERIFICADA' if not c2
                          else '!! REVISAR: quedaron casos sin corregir'))
    print("=" * 80)
    return 0 if not c2 else 1


if __name__ == '__main__':
    sys.exit(main())
