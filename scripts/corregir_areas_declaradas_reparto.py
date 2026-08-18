# -*- coding: utf-8 -*-
"""
El área que cada regante declara, cuando el técnico dejó el default de QField.

El hallazgo (18-ago-2026)
--------------------------
298 predios tienen varias fichas que, sumadas, declaran más de lo que mide su
polígono. `corregir_areas_por_observacion.py` (15-ago) ya resuelve los que
tienen el reparto completo escrito en las observaciones — quedan 297.

Al mirarlos de cerca aparecen **tres grupos distintos**, no uno:

    A — puro        112 predios · 197,79 ha · TODAS las fichas declaran
                     el polígono completo, NINGUNA tiene observación.
    B — casi puro    132 predios · 1.209,79 ha · la MAYORÍA declara el
                     polígono completo, pero alguna ficha ya trae un valor
                     distinto o una observación con un número propio.
    C — mixto         54 predios ·   358,59 ha · NO hay un patrón de
                     "todos declaran el polígono". Ver más abajo.

(197,79 + 1.209,79 + 358,59 = 1.766,17 ha: cuadra con el total de la pantalla.)

A y B son el mismo error, confirmado por JAVIKO viendo casos concretos en el
mapa: QField pone por defecto **el área del polígono entero** cuando el
técnico marca el punto sobre un predio compartido, y si no se corrige a mano,
cada ficha se queda con el 100% del predio — no con la parte que le toca.
Revisado con Armando: no se va a volver a campo por esto. La mayoría son
errores de técnico, no reparto real entre coherederos.

**El grupo C es un problema distinto y no lo toca este script.** Ahí varias
fichas declaran valores que no son ni el polígono ni una fracción razonable de
él —una ficha con 3.159% del predio, por ejemplo—, y su observación aclara que
esa persona tiene su terreno en **otra clave catastral**: quedó enganchada al
predio equivocado (error de punto GPS o de digitación), no mal dividida. Eso se
arregla reasignando la clave, no repartiendo el área. Se lista aparte al
final de la ejecución.

La regla, para A y B
---------------------
Por cada predio, para cada ficha:

1. **Si su área ya es distinta del polígono** (no ronda el 100%), se asume que
   es un dato real —aunque no se sepa la historia— y no se toca.
2. **Si su área es ≈ el polígono** (el default sin corregir) y su observación
   trae un número que es claramente el suyo, se usa ese número.
3. **Si no hay número propio recuperable**, la ficha entra al reparto: lo que
   sobra del polígono —descontando lo ya identificado en 1 y 2— se divide en
   partes iguales entre las fichas de este grupo.

Cada ficha corregida por el paso 3 queda marcada en las observaciones
(«[corregido 18-ago-2026: reparto igualitario, ver CORRECCION-...]») para que
quien lea el dato sepa que es una estimación, no algo que dijo el regante.

Por qué la extracción de números es propia de este script
-----------------------------------------------------------
`generar_auditoria_areas.num_del_texto` sirve para el aviso de la pantalla,
pero falla en textos con más de una mención de pertenencia. El caso real que
lo destapó:

    "el predio global PERTENECE a catorce propietarios [...] Área de Lote
     ASIGNADA al Regante: 5.000 m², Lote 3"

`num_del_texto` se engancha con el primer «pertenece» —genérico, habla de los
14 propietarios— y como es anterior a los dos números del texto, elige el
primero que encuentra después: el «50.000 m²» del lote sin fraccionar, no los
«5.000 m²» que sí son del regante. (Y por un bug aparte con espacios como
separador de miles, ese primer número ni siquiera se lee bien: da 0.)

Aquí se busca el marcador de pertenencia **más cercano** a cada número, no el
primero del texto entero, y se exige que esté a menos de `VENTANA_MARCADOR`
caracteres. Verificado con los dos casos reales que motivaron el cambio:

    Pilca Lanchimba Luis Germán → 5.000  (antes: None)
    Quilumbaquin Farinango Rosa → excluido (su número es de OTRA clave)

El segundo caso es la otra guarda: si entre el marcador y el número aparece
«clave» seguida de otra clave catastral, el número no es de este predio y se
descarta —la ficha cae en el reparto igualitario en vez de robarle el dato a
otro predio—.

Qué NO hace
-----------
* No toca el grupo C (54 predios, 358,59 ha): necesitan revisar la clave
  catastral, no el área. Ver el informe al final de la ejecución.
* No inventa una historia para el reparto igualitario: lo marca como tal.
* No cambia ninguna cifra publicada del sistema (esa se mide por polígono
  catastral). Si cambia `riego_ajustado_ha` al regenerar, que sí es cifra
  publicada — ver aviso al final.

Uso
---
    "C:\\OSGeo4W\\bin\\python-qgis.bat" -X utf8 scripts/corregir_areas_declaradas_reparto.py
    "C:\\OSGeo4W\\bin\\python-qgis.bat" -X utf8 scripts/corregir_areas_declaradas_reparto.py --aplicar

Sin `--aplicar` no escribe nada (regla 7). Con `--aplicar` respalda antes con
la API de backup de SQLite (regla 5) y retira/recrea los triggers de la tabla
de fichas (regla 7: usan ST_IsEmpty, que SQLite puro no trae).

Cómo revertirlo: `docs/CORRECCION-areas-declaradas-reparto.md`.
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

TOLERANCIA_M2 = 1000       # igual que generar_auditoria_areas.py
AL_POLIGONO_PCT = 0.02     # +-2% del poligono cuenta como "es el default"
GRUPO_AB_MIN_PROPORCION = 0.8   # >=80% de fichas al poligono => es A o B
VENTANA_MARCADOR = 80      # caracteres antes del numero para aceptar un marcador
VENTANA_CLAVE = 100        # caracteres antes del numero para buscar una clave ajena

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
    """Igual que generar_auditoria_areas._a_numero: miles de tres en tres,
    decimal por posición del último separador."""
    crudo = crudo.strip().rstrip('.,')
    if ',' in crudo and '.' in crudo:
        dec, mil = (',', '.') if crudo.rfind(',') > crudo.rfind('.') else ('.', ',')
        crudo = crudo.replace(mil, '').replace(dec, '.')
        return float(crudo)
    for sep in ('.', ','):
        if sep in crudo:
            ent, _, frac = crudo.partition(sep)
            if len(ent) >= 4 or len(frac) != 3:
                return float(crudo.replace(sep, '.'))
            return float(ent + frac)
    return float(crudo)


def area_propia_del_texto(texto, clave_predio):
    """El área que la observación dice que le toca A ESTA FICHA en ESTE predio.

    None si no hay un número con un marcador de pertenencia cerca, o si el
    número más cercano a un marcador está precedido por una clave catastral
    distinta a la de este predio (habla de otro terreno).
    """
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

    # el numero cuyo marcador de pertenencia mas cercano (por delante) es el
    # mas chico gana; empatan solo si ninguno tiene marcador cerca
    mejor = None
    for pos, v in numeros:
        anteriores = [mp for mp in marcadores if mp <= pos]
        if not anteriores:
            continue
        distancia = pos - max(anteriores)
        if distancia > VENTANA_MARCADOR:
            continue
        if mejor is None or distancia < mejor[0]:
            mejor = (distancia, pos, v)
    if mejor is None:
        return None

    _, pos, v = mejor
    ventana_previa = texto[max(0, pos - VENTANA_CLAVE):pos]
    ajena = CLAVE_AJENA.search(ventana_previa)
    if ajena and ajena.group(1).strip() != clave_predio.strip():
        return None
    return round(v)


def cargar_catastro():
    with open(CATASTRO, encoding='utf-8') as f:
        datos = json.load(f)
    areas = {}
    for ft in datos.get('features', []):
        p = ft.get('properties') or {}
        clave = str(p.get('clave_cata') or '').strip()
        if clave and p.get('area_predi'):
            areas[clave] = float(p['area_predi'])
    return areas


def tabla(cur):
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    return next(t[0] for t in cur.fetchall() if 'Fichas_Predios' in t[0]
                and not any(x in t[0] for x in ('rtree_', 'log_', 'gpkg_')))


def ha(v):
    return '{:,.2f}'.format(v / 10000.0).replace(',', '@').replace('.', ',').replace('@', '.')


def m2(v):
    return '{:,.0f}'.format(v).replace(',', '.')


def clasificar(areas_cat, filas):
    """Agrupa por predio y separa A/B (se corrige) de C (no se toca)."""
    por_clave = defaultdict(list)
    for uid, clave, at, ar, asr, obs, nom, com in filas:
        clave = (clave or '').strip()
        if clave in areas_cat:
            por_clave[clave].append({
                'uid': uid, 'at': at or 0, 'ar': ar or 0, 'asr': asr or 0,
                'obs': (obs or '').strip(), 'nom': nom, 'com': com})

    grupo_ab, grupo_c = [], []
    for clave, fichas in por_clave.items():
        pol = areas_cat[clave]
        n = len(fichas)
        dec = sum(f['at'] for f in fichas)
        exceso = dec - pol
        if not (n > 1 and exceso > TOLERANCIA_M2):
            continue
        al_pol = sum(1 for f in fichas
                     if pol > 0 and abs(f['at'] - pol) / pol <= AL_POLIGONO_PCT)
        caso = {'clave': clave, 'pol': pol, 'com': fichas[0]['com'],
                'fichas': fichas, 'n': n, 'dec': dec, 'exceso': exceso}
        if al_pol >= max(2, int(n * GRUPO_AB_MIN_PROPORCION)):
            grupo_ab.append(caso)
        else:
            grupo_c.append(caso)
    return grupo_ab, grupo_c


MARGEN_RECONCILIA = 0.15   # igual que MARGEN_DIVIDIDO en generar_auditoria_areas.py


def resolver(caso):
    """Decide, ficha por ficha, si se toca y con qué valor.

    Devuelve (correcciones, ok, motivo). ok es False y correcciones viene
    vacía en dos casos: el remanente a repartir salió negativo (los "valores
    reales" ya superan el polígono), o no quedó ninguna ficha para el reparto
    y aun así los números reales no reconcilian con el polígono dentro de
    `MARGEN_RECONCILIA` — como el predio de Asociación Rosalía, donde los 5
    hermanos tienen su parte anotada pero **suman 7,09 ha sobre un polígono de
    9,81**: si se aplicara tal cual, el predio pasaría de sobrar a faltar.
    Sin fichas de reparto que absorban esa diferencia, no hay forma honesta de
    cerrarlo aquí: se descarta y queda para revisar a mano.
    """
    pol, clave = caso['pol'], caso['clave']
    correcciones = []
    ya_asignado = 0.0
    pendientes = []
    for f in caso['fichas']:
        al_poligono = pol > 0 and abs(f['at'] - pol) / pol <= AL_POLIGONO_PCT
        if not al_poligono:
            ya_asignado += f['at']          # valor real, se conserva tal cual
            continue
        propia = area_propia_del_texto(f['obs'], clave)
        if propia is not None:
            correcciones.append((f, propia, 'observacion'))
            ya_asignado += propia
        else:
            pendientes.append(f)

    remanente = pol - ya_asignado
    if pendientes:
        if remanente <= 0:
            return [], False, 'los valores reales ya superan el poligono'
        cuota = remanente / len(pendientes)
        for f in pendientes:
            correcciones.append((f, cuota, 'reparto'))
        return correcciones, True, None

    # nadie quedo pendiente: todo salio de valores reales o ya-distintos.
    # eso solo es honesto si, sumados, reconcilian con el poligono.
    if pol > 0 and abs(remanente) / pol > MARGEN_RECONCILIA:
        detalle = ('las observaciones suman {} ha sobre un poligono de {} ha, '
                   'sin fichas de reparto que absorban la diferencia'
                   .format(ha(ya_asignado), ha(pol)))
        return [], False, detalle
    return correcciones, True, None


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
    ap.add_argument('--aplicar', action='store_true',
                    help='escribe en el data.gpkg (sin esto solo simula)')
    args = ap.parse_args()

    print('=' * 80)
    print(' AREAS DECLARADAS: DEFAULT DE QFIELD SIN CORREGIR' +
          ('  [APLICAR]' if args.aplicar else '  [SIMULACION - no escribe nada]'))
    print('=' * 80)

    areas_cat = cargar_catastro()
    con = sqlite3.connect(GPKG)
    cur = con.cursor()
    t = tabla(cur)
    cur.execute(
        "SELECT COALESCE(id,''), TRIM(COALESCE(clave_catastral,'')), "
        "COALESCE(area_total,0), COALESCE(area_riego,0), "
        "COALESCE(area_sin_riego,0), COALESCE(observaciones,''), "
        "TRIM(COALESCE(apellidos,'')||' '||COALESCE(nombres,'')), "
        "COALESCE(comunidad,'') FROM \"{}\"".format(t))
    filas = cur.fetchall()
    con.close()

    grupo_ab, grupo_c = clasificar(areas_cat, filas)
    grupo_ab.sort(key=lambda c: -c['exceso'])

    print('\n  predios grupo A/B (se procesan): {}'.format(len(grupo_ab)))
    print('  predios grupo C (NO se tocan)  : {}'.format(len(grupo_c)))

    todas_correcciones = []
    descartados = []
    reales_sin_tocar = 0
    por_observacion = 0
    por_reparto = 0
    for caso in grupo_ab:
        correcciones, ok, motivo = resolver(caso)
        if not ok:
            descartados.append((caso, motivo))
            continue
        for f, nuevo, origen in correcciones:
            todas_correcciones.append((caso, f, nuevo, origen))
            if origen == 'observacion':
                por_observacion += 1
            else:
                por_reparto += 1
        reales_sin_tocar += len(caso['fichas']) - len(correcciones)

    print('\n  fichas con valor real, sin tocar          : {}'.format(reales_sin_tocar))
    print('  fichas corregidas con dato de observacion  : {}'.format(por_observacion))
    print('  fichas corregidas por reparto igualitario  : {}'.format(por_reparto))
    print('  predios descartados (no reconcilian)       : {}'.format(len(descartados)))
    if descartados:
        for c, motivo in descartados[:10]:
            print('     {} · {:<26} · {}'.format(c['clave'], c['com'][:26], motivo))
        if len(descartados) > 10:
            print('     … y {} predios mas'.format(len(descartados) - 10))

    print('\n' + '-' * 80)
    print(' MUESTRA — 8 predios con mas exceso, tal como quedarian')
    print('-' * 80)
    mostrados = 0
    for caso in grupo_ab:
        correcciones, ok, _ = resolver(caso)
        if not ok or not correcciones:
            continue
        print('\n   {} · {} · poligono {} ha · exceso actual {} ha'.format(
            caso['clave'], caso['com'][:28], ha(caso['pol']), ha(caso['exceso'])))
        for f, nuevo, origen in correcciones:
            etiqueta = 'obs' if origen == 'observacion' else 'reparto'
            print('      {:<32} {:>10} -> {:>10} m²  [{}]'.format(
                f['nom'][:32], m2(f['at']), m2(nuevo), etiqueta))
        mostrados += 1
        if mostrados >= 8:
            break

    total_quitado = sum(f['at'] - nuevo for _, f, nuevo, _ in todas_correcciones)
    print('\n' + '=' * 80)
    print('  fichas que se corrigen  : {}'.format(len(todas_correcciones)))
    print('  superficie que se quita : {} ha'.format(ha(total_quitado)))

    print('\n  GRUPO C — no tocado por este script, necesita revisar clave catastral:')
    for c in sorted(grupo_c, key=lambda x: -x['exceso'])[:10]:
        print('     {} · {:<26} exceso {} ha · {} fichas'.format(
            c['clave'], c['com'][:26], ha(c['exceso']), c['n']))
    if len(grupo_c) > 10:
        print('     … y {} predios mas (ver docs/CORRECCION-areas-declaradas-reparto.md)'
              .format(len(grupo_c) - 10))

    if not args.aplicar:
        print('\n  ' + '-' * 76)
        print('  SIMULACION: no se escribio nada. Para aplicarlo:  --aplicar')
        print('  Ojo: esto puede mover riego_ajustado_ha al regenerar, que es cifra')
        print('  publicada (aunque la catastral, 8.092,45 ha, no se mueve).')
        print('  ' + '-' * 76)
        return

    if not todas_correcciones:
        print('\n  Nada que aplicar.')
        return

    print('\n  respaldando antes de escribir...')
    print('     {}'.format(respaldo_sqlite(GPKG, 'antes-reparto-areas')))

    con = sqlite3.connect(GPKG)
    cur = con.cursor()
    cur.execute("SELECT name, sql FROM sqlite_master WHERE type='trigger' AND tbl_name=?", (t,))
    triggers = cur.fetchall()
    for nombre, _ in triggers:
        cur.execute('DROP TRIGGER IF EXISTS "{}"'.format(nombre))

    hoy = time.strftime('%d-%m-%Y')
    n = 0
    try:
        for caso, f, nuevo, origen in todas_correcciones:
            factor = nuevo / f['at'] if f['at'] else 0
            nueva_ar = round(f['ar'] * factor, 2)
            nueva_asr = round(f['asr'] * factor, 2)
            nota = (' [corregido {}: {}, ver CORRECCION-areas-declaradas-reparto.md]'
                    .format(hoy, 'dato de observacion' if origen == 'observacion'
                            else 'reparto igualitario del predio'))
            cur.execute(
                'UPDATE "{}" SET area_total = ?, area_riego = ?, area_sin_riego = ?, '
                'observaciones = COALESCE(observaciones, "") || ? WHERE id = ?'.format(t),
                (nuevo, nueva_ar, nueva_asr, nota, f['uid']))
            n += cur.rowcount
    finally:
        for _, sql in triggers:
            if sql:
                cur.execute(sql)
    con.commit()
    cur.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    con.close()
    print('     {} fichas actualizadas · {} triggers recreados'.format(n, len(triggers)))

    con = sqlite3.connect('file:{}?mode=ro'.format(GPKG.replace('\\', '/')), uri=True)
    cur = con.cursor()
    cur.execute(
        "SELECT COALESCE(id,''), TRIM(COALESCE(clave_catastral,'')), "
        "COALESCE(area_total,0), COALESCE(area_riego,0), "
        "COALESCE(area_sin_riego,0), COALESCE(observaciones,''), "
        "TRIM(COALESCE(apellidos,'')||' '||COALESCE(nombres,'')), "
        "COALESCE(comunidad,'') FROM \"{}\"".format(t))
    filas2 = cur.fetchall()
    con.close()
    ab2, _ = clasificar(areas_cat, filas2)
    quedan = 0
    for caso in ab2:
        correcciones, ok, _ = resolver(caso)
        if ok and correcciones:
            quedan += 1
    print('\n  VERIFICACION (releyendo del disco):')
    print('     predios A/B que aun tendrian correccion pendiente: {} · se esperaban 0'
          .format(quedan))
    print('\n  {}'.format('CORRECCION APLICADA Y VERIFICADA' if quedan == 0
                          else '!! REVISAR: quedaron casos sin aplicar'))


if __name__ == '__main__':
    main()
