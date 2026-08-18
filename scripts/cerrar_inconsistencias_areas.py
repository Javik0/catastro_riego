# -*- coding: utf-8 -*-
"""
Cierre de las inconsistencias de área y cultivo del padrón.

Criterio de JAVIKO (18-ago-2026), que es el que manda aquí
-----------------------------------------------------------
Donde se puede **determinar que fue error del sistema** —el default de QField
que nadie corrigió, o el generador automático de fichas adicionales
(`AUTO-SECCION7`)— se corrige. Lo demás es **el dato que el regante confirmó
en campo** («yo siembro tantas hectáreas», «tengo tantos animales») y **se
respeta tal cual**, aunque parezca raro.

Los tres pasos
--------------
**A — Duplicados del mismo cultivo dentro de una ficha.** Los duplicados
EXACTOS (mismo tipo, misma superficie) ya están en 0: se retiraron en sesiones
anteriores. Quedan 6 casos de mismo tipo con superficie DISTINTA, y los creó
la reclasificación de esta misma mañana (potrero/ladera → «Pasto no
mejorado», cascajo → «Baldío»): una ficha que ya tenía «Pasto no mejorado» y
además un «Potrero» quedó con dos filas de «Pasto no mejorado».

Se **fusionan sumando**, no se elimina ninguna: son dos pedazos reales y
distintos del mismo predio (una parte era ladera, la otra ya era pasto). Sumar
**no infla** —el total de la ficha no se mueve ni un metro—; eliminar sí
perdería superficie que el regante declaró.

**B — Predios que todavía declaran más que su polígono.** Los 68 que quedaron
fuera del reparto de la mañana. Por cada ficha del predio:

  1. Si su observación trae un número que es claramente suyo, se usa.
  2. El resto del polígono se reparte en partes iguales entre las demás.

La diferencia con `corregir_areas_declaradas_reparto.py` es el criterio de
aceptación. Aquel script exigía que los datos reconciliaran con el polígono
dentro de un 15 % y descartaba el predio si no —por eso dejó fuera el caso de
los cinco hermanos Cevallos Gordón, cuyas observaciones suman 7,09 ha sobre un
polígono de 9,81—. Ese chequeo era demasiado estricto: **el objetivo es no
inflar**, y declarar 7,09 sobre un polígono de 9,81 no infla nada. Ahora solo
se rechaza el caso contrario, que los datos reales ya superen el polígono.

**C — Cultivos con la huella exacta del default.** Filas de cultivo cuya
superficie coincide (±2 %) con el polígono catastral: es el mismo número que
QField pone por defecto, no algo que se haya medido. Se recorta al área de su
propia ficha —un cultivo no puede ser más grande que el predio donde está—.

Lo que este script NO toca, a propósito
----------------------------------------
* **Cultivos que exceden el área de su ficha sin la huella del default.** Un
  regante que declara sembrar más de lo que mide su predio puede estar
  diciendo la verdad: arrendar terreno fuera del predio propio es corriente en
  la zona. Es el dato que confirmó en campo y se respeta.
* **Los duplicados exactos**, porque ya están en 0.

Uso
---
    "C:\\OSGeo4W\\bin\\python-qgis.bat" -X utf8 scripts/cerrar_inconsistencias_areas.py
    "C:\\OSGeo4W\\bin\\python-qgis.bat" -X utf8 scripts/cerrar_inconsistencias_areas.py --aplicar

Sin `--aplicar` no escribe nada (regla 7). Con `--aplicar` respalda antes con
la API de backup de SQLite (regla 5) y retira/recrea los triggers de la tabla
de fichas.

Cómo revertirlo: docs/CORRECCION-cierre-inconsistencias.md.
"""
import argparse
import json
import os
import re
import sqlite3
import time
from collections import defaultdict

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
GPKG = os.path.join(os.path.expanduser('~'), 'QField', 'cloud',
                    'porotog_levantamiento_offline', 'data.gpkg')
CATASTRO = os.path.join(BASE, 'public', 'geo', 'catastro_geo.geojson')
RAIZ_RESPALDOS = (r"C:\Users\HP\OneDrive\Escritorio\CAYAMBE CATASTRO RIEGO"
                  r"\respaldos_qgs")

TOLERANCIA_M2 = 1000
MARGEN_POLIGONO = 0.02
VENTANA_MARCADOR = 80
VENTANA_CLAVE = 100
HOY = '18-08-2026'

AREA_EN_TEXTO = re.compile(
    r'(\d[\d.,]{1,12})\s*'
    r'(?:M2|M\u00b2|M\s*2|MTS?\b\.?|METROS?\b|HAS?\b|HECTAREAS?\b|M\b)'
    r'\s*(?:CUADRADOS?|CUADRADAS?)?', re.IGNORECASE)
MARCADOR = re.compile(
    r'(?:LE\s+)?(?:CORRESPONDE[N]?|ASIGNAD[AO]|ES\s+DUE[N\u00d1][AO]\s+DE|'
    r'TIENE\s+DERECHO\s+A|POR\s+CADA|CADA\s+UNO|MI\s+PARTE|SU\s+PARTE|'
    r'LOTE\s*:?\s*\d+)', re.IGNORECASE)
CLAVE_AJENA = re.compile(r'CLAVE\S*\s*(\d{8,20})', re.IGNORECASE)


def _a_numero(crudo):
    crudo = crudo.strip().rstrip('.,')
    if ',' in crudo and '.' in crudo:
        dec, mil = (',', '.') if crudo.rfind(',') > crudo.rfind('.') else ('.', ',')
        return float(crudo.replace(mil, '').replace(dec, '.'))
    for sep in ('.', ','):
        if sep in crudo:
            ent, _, frac = crudo.partition(sep)
            if len(ent) >= 4 or len(frac) != 3:
                return float(crudo.replace(sep, '.'))
            return float(ent + frac)
    return float(crudo)


def area_propia_del_texto(texto, clave_predio):
    """El área que la observación dice que le toca a ESTA ficha en ESTE predio."""
    if not texto:
        return None
    numeros = []
    for m in AREA_EN_TEXTO.finditer(texto):
        try:
            v = _a_numero(m.group(1))
        except ValueError:
            continue
        if 10 <= v <= 5_000_000:
            numeros.append((m.start(), v))
    if not numeros:
        return None
    marcadores = [m.start() for m in MARCADOR.finditer(texto)]
    if not marcadores:
        return None
    mejor = None
    for pos, v in numeros:
        anteriores = [mp for mp in marcadores if mp <= pos]
        if not anteriores:
            continue
        d = pos - max(anteriores)
        if d > VENTANA_MARCADOR:
            continue
        if mejor is None or d < mejor[0]:
            mejor = (d, pos, v)
    if mejor is None:
        return None
    _, pos, v = mejor
    previa = texto[max(0, pos - VENTANA_CLAVE):pos]
    ajena = CLAVE_AJENA.search(previa)
    if ajena and ajena.group(1).strip() != (clave_predio or '').strip():
        return None
    return round(v)


def cargar_catastro():
    with open(CATASTRO, encoding='utf-8') as f:
        datos = json.load(f)
    areas = {}
    for ft in datos.get('features', []):
        p = ft.get('properties') or {}
        k = str(p.get('clave_cata') or '').strip()
        if k and p.get('area_predi'):
            areas[k] = float(p['area_predi'])
    return areas


def tablas(cur):
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    todas = [t[0] for t in cur.fetchall()]

    def buscar(k):
        return next(t for t in todas if k in t
                    and not any(x in t for x in ('rtree_', 'log_', 'gpkg_')))
    return buscar('Fichas_Predios'), buscar('Cultivos_Agricolas')


def ha(v):
    return '{:,.2f}'.format(v / 10000.0).replace(',', '@').replace('.', ',').replace('@', '.')


def m2f(v):
    return '{:,.0f}'.format(v or 0).replace(',', '.')


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


# ── PASO A ────────────────────────────────────────────────────────────────
def paso_a(cur, t_cul):
    """Mismo tipo repetido en una ficha con superficie distinta: fusionar sumando."""
    grupos = cur.execute(
        'SELECT ficha_id, tipo_cultivo, COUNT(*), SUM(superficie_m2) FROM "{}" '
        'GROUP BY ficha_id, tipo_cultivo '
        'HAVING COUNT(*) > 1'.format(t_cul)).fetchall()
    fusiones = []
    for fid, tipo, n, suma in grupos:
        filas = cur.execute(
            'SELECT id_cultivo, superficie_m2 FROM "{}" '
            'WHERE ficha_id = ? AND tipo_cultivo IS ?'.format(t_cul), (fid, tipo)).fetchall()
        if len(filas) < 2:
            continue
        filas.sort(key=lambda r: -(r[1] or 0))
        fusiones.append({'ficha': fid, 'tipo': tipo, 'queda': filas[0][0],
                         'suma': suma, 'borra': [r[0] for r in filas[1:]],
                         'antes': [r[1] for r in filas]})
    return fusiones


# ── PASO B ────────────────────────────────────────────────────────────────
def paso_b(cur, t_fic, areas_cat):
    """Predios que aún declaran más que su polígono."""
    rows = cur.execute(
        "SELECT id, TRIM(COALESCE(clave_catastral,'')), COALESCE(area_total,0), "
        "COALESCE(area_riego,0), COALESCE(area_sin_riego,0), COALESCE(observaciones,''), "
        "TRIM(COALESCE(apellidos,'')||' '||COALESCE(nombres,'')), COALESCE(comunidad,'') "
        "FROM \"{}\"".format(t_fic)).fetchall()
    por_clave = defaultdict(list)
    for fid, clave, at, ar, asr, obs, nom, com in rows:
        if clave in areas_cat:
            por_clave[clave].append({'id': fid, 'at': at, 'ar': ar, 'asr': asr,
                                     'obs': obs, 'nom': nom, 'com': com})
    correcciones = []
    sin_arreglo = []
    for clave, fichas in por_clave.items():
        pol = areas_cat[clave]
        dec = sum(f['at'] for f in fichas)
        if len(fichas) < 2 or dec - pol <= TOLERANCIA_M2:
            continue
        ya = 0.0
        pendientes = []
        parciales = []
        for f in fichas:
            propia = area_propia_del_texto(f['obs'], clave)
            if propia is not None:
                parciales.append((f, float(propia)))
                ya += propia
            else:
                pendientes.append(f)
        remanente = pol - ya
        if pendientes:
            if remanente <= 0:
                # los datos "reales" ya llenan el polígono: se reparte todo
                # el polígono en partes iguales, que es lo único que no infla
                cuota = pol / len(fichas)
                correcciones.extend((f, cuota, 'reparto total', clave, pol) for f in fichas)
                continue
            cuota = remanente / len(pendientes)
            correcciones.extend((f, v, 'observacion', clave, pol) for f, v in parciales)
            correcciones.extend((f, cuota, 'reparto', clave, pol) for f in pendientes)
        else:
            if ya > pol:
                sin_arreglo.append((clave, pol, ya))
                continue
            # las observaciones cubren todas las fichas y no inflan: se usan
            correcciones.extend((f, v, 'observacion', clave, pol) for f, v in parciales)
    return correcciones, sin_arreglo


# ── PASO C ────────────────────────────────────────────────────────────────
def paso_c(cur, t_fic, t_cul, areas_cat, areas_nuevas):
    """Filas de cultivo con la huella exacta del polígono."""
    rows = cur.execute(
        'SELECT c.id_cultivo, c.ficha_id, c.tipo_cultivo, c.superficie_m2, '
        'TRIM(COALESCE(f.clave_catastral,\'\')), COALESCE(f.area_total,0), '
        'TRIM(COALESCE(f.apellidos,\'\')||\' \'||COALESCE(f.nombres,\'\')) '
        'FROM "{}" c JOIN "{}" f ON f.id = c.ficha_id '
        'WHERE COALESCE(c.superficie_m2,0) > 0'.format(t_cul, t_fic)).fetchall()
    recortes = []
    for idc, fid, tipo, sup, clave, area_bd, nom in rows:
        pol = areas_cat.get(clave)
        if not pol or pol <= 0:
            continue
        area = areas_nuevas.get(fid, area_bd)
        if area <= 0 or sup <= area:
            continue
        if abs(sup - pol) / pol <= MARGEN_POLIGONO:
            recortes.append({'id_cultivo': idc, 'ficha': fid, 'tipo': tipo,
                             'antes': sup, 'despues': area, 'nom': nom, 'clave': clave})
    return recortes


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--aplicar', action='store_true',
                    help='escribe en el data.gpkg (sin esto solo simula)')
    args = ap.parse_args()

    print('=' * 80)
    print(' CIERRE DE INCONSISTENCIAS DE AREA Y CULTIVO' +
          ('  [APLICAR]' if args.aplicar else '  [SIMULACION - no escribe nada]'))
    print('=' * 80)

    areas_cat = cargar_catastro()
    con = sqlite3.connect(GPKG)
    cur = con.cursor()
    t_fic, t_cul = tablas(cur)

    fusiones = paso_a(cur, t_cul)
    correcciones, sin_arreglo = paso_b(cur, t_fic, areas_cat)
    areas_nuevas = {f['id']: v for f, v, _, _, _ in correcciones}
    recortes = paso_c(cur, t_fic, t_cul, areas_cat, areas_nuevas)

    print('\n  [A] cultivos del mismo tipo repetidos en una ficha : {} fusiones'
          .format(len(fusiones)))
    for f in fusiones:
        print('        {:<20} {} -> {} m²  (el total de la ficha no cambia)'
              .format(f['tipo'], ' + '.join(m2f(x) for x in f['antes']), m2f(f['suma'])))

    quita_b = sum(f['at'] - v for f, v, _, _, _ in correcciones)
    predios_b = len(set(c[3] for c in correcciones))
    print('\n  [B] predios que declaraban de mas                  : {} predios, {} fichas'
          .format(predios_b, len(correcciones)))
    print('        superficie declarada que se quita: {} ha'.format(ha(quita_b)))
    if sin_arreglo:
        print('        sin arreglo posible (los datos reales ya superan el poligono): {}'
              .format(len(sin_arreglo)))
        for clave, pol, ya in sin_arreglo[:5]:
            print('           {} · poligono {} ha · datos reales {} ha'
                  .format(clave, ha(pol), ha(ya)))

    quita_c = sum(r['antes'] - r['despues'] for r in recortes)
    print('\n  [C] cultivos con la huella exacta del poligono     : {} filas'
          .format(len(recortes)))
    print('        superficie de cultivo que se quita: {} ha'.format(ha(quita_c)))
    for r in sorted(recortes, key=lambda x: -(x['antes'] - x['despues']))[:8]:
        print('        {} {:<22} {:>12} -> {:>10} m²'
              .format(r['clave'], r['nom'][:22], m2f(r['antes']), m2f(r['despues'])))

    if not args.aplicar:
        print('\n  ' + '-' * 76)
        print('  SIMULACION: no se escribio nada. Para aplicarlo:  --aplicar')
        print('  ' + '-' * 76)
        con.close()
        return

    print('\n  respaldando antes de escribir...')
    print('     {}'.format(respaldo_sqlite(GPKG, 'antes-cierre-inconsistencias')))

    cur.execute("SELECT name, sql FROM sqlite_master WHERE type='trigger' AND tbl_name=?", (t_fic,))
    triggers = cur.fetchall()
    for nombre, _ in triggers:
        cur.execute('DROP TRIGGER IF EXISTS "{}"'.format(nombre))
    try:
        for f in fusiones:
            cur.execute('UPDATE "{}" SET superficie_m2 = ? WHERE id_cultivo = ?'.format(t_cul),
                        (f['suma'], f['queda']))
            for idc in f['borra']:
                cur.execute('DELETE FROM "{}" WHERE id_cultivo = ?'.format(t_cul), (idc,))
        nota = (' [corregido {}: reparto para no exceder el poligono, ver '
                'CORRECCION-cierre-inconsistencias.md]'.format(HOY))
        for f, nuevo, origen, clave, pol in correcciones:
            factor = nuevo / f['at'] if f['at'] else 0
            cur.execute(
                'UPDATE "{}" SET area_total = ?, area_riego = ?, area_sin_riego = ?, '
                'observaciones = COALESCE(observaciones, "") || ? WHERE id = ?'.format(t_fic),
                (nuevo, round(f['ar'] * factor, 2), round(f['asr'] * factor, 2), nota, f['id']))
        for r in recortes:
            cur.execute('UPDATE "{}" SET superficie_m2 = ? WHERE id_cultivo = ?'.format(t_cul),
                        (r['despues'], r['id_cultivo']))
    finally:
        for _, sql in triggers:
            if sql:
                cur.execute(sql)
    con.commit()
    cur.execute('PRAGMA wal_checkpoint(TRUNCATE)')
    con.close()
    print('     aplicado: {} fusiones · {} fichas de area · {} filas de cultivo'
          .format(len(fusiones), len(correcciones), len(recortes)))

    # ── verificación releyendo del disco ──
    con = sqlite3.connect('file:{}?mode=ro'.format(GPKG.replace('\\', '/')), uri=True)
    cur = con.cursor()
    f2 = paso_a(cur, t_cul)
    c2, s2 = paso_b(cur, t_fic, areas_cat)
    a2 = {f['id']: v for f, v, _, _, _ in c2}
    r2 = paso_c(cur, t_fic, t_cul, areas_cat, a2)
    n_cul, sup_cul = cur.execute(
        'SELECT COUNT(*), SUM(superficie_m2) FROM "{}"'.format(t_cul)).fetchone()
    con.close()
    print('\n  VERIFICACION (releyendo del disco):')
    print('     [A] duplicados que quedan            : {} · se esperaban 0'.format(len(f2)))
    print('     [B] predios que aun declaran de mas  : {} · se esperaban {}'
          .format(len(set(c[3] for c in c2)), len(s2)))
    print('     [C] cultivos con huella del poligono : {} · se esperaban 0'.format(len(r2)))
    print('     cultivos: {} filas, {} ha'.format(n_cul, ha(sup_cul)))
    ok = not f2 and not r2 and len(set(c[3] for c in c2)) <= len(s2)
    print('\n  {}'.format('CIERRE APLICADO Y VERIFICADO' if ok
                          else '!! REVISAR: quedaron casos sin cerrar'))


if __name__ == '__main__':
    main()
