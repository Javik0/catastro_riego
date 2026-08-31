# -*- coding: utf-8 -*-
"""
Dos personas distintas comparten el mismo `id` de QField (colisión de UUID).

El hallazgo
-----------
En el `data.gpkg` hay UN solo `id` duplicado en todo el padrón,
`{f06e1d27-3c64-4cdf-9f5f-79c10efd1a4a}`, compartido por dos regantes
distintos sobre el mismo predio (clave catastral 1702520200008, comunidad
Santa Marianita de Pingulmí):

  · JOSE RAFAEL COYAGO CHICAIZA   cédula 1709566549   (fid_1 2717)
  · MARCO RAFAEL COYAGO ALQUINGA  cédula 1726802000   (fid_1 7152)

No es error de digitación: son dos cédulas reales, probablemente familiares
que llenaron cada uno su ficha para el mismo predio y QField les asignó el
mismo identificador al sincronizar. Detectado el 4-ago-2026 porque
`generar_excel_consolidado.py` crasheaba al indexar por `id`.

Qué corrige
-----------
Un solo campo, en una sola fila: el `id` de MARCO RAFAEL pasa a un UUID
nuevo. JOSE RAFAEL conserva el identificador original. Ninguna ficha se
elimina — las dos personas siguen en el padrón.

Por qué JOSE conserva el id (decisión de JAVIKO, 30-ago-2026)
-------------------------------------------------------------
Porque su ficha hija —el predio adicional de 10.761,42 m², clave
1702521720007— ya apunta a ese id como madre. Si el id se lo quedara MARCO,
habría que reapuntar además esa hija, que es un cambio más y más superficie
en riesgo si algo sale mal. Conservándolo JOSE, la hija queda correctamente
enganchada sin tocarla.

Consecuencia asumida: el cultivo (558,07 m² de pasto no mejorado) y los 4
registros de animales (51 cabezas) cuelgan de ese id, así que quedan a
nombre de JOSE RAFAEL. No hay forma técnica de saber de quién son en
realidad; si campo aclara que son de MARCO, se reasignan aparte.

Efecto en las cifras publicadas
--------------------------------
NINGUNO — medido el 30-ago-2026 antes de aplicar. El padrón sigue en 6.830
(se cuenta por filas, no por id), las personas siguen siendo dos (se
identifican por cédula), la superficie catastral no se mueve (por polígono,
el predio se cuenta una vez), el riego tampoco (las dos declaran 0) y el
caudal va por moda de comunidad. Cultivos y animales no se duplican: hay un
solo juego y sigue colgando del mismo id.

Lo que sí arregla: hoy el dueño al que se atribuyen esos hijos cambia según
el documento (el Excel consolidado usa la primera fila -> JOSE; los
capítulos indexan por id y gana la última -> MARCO). Tras la corrección los
dos criterios coinciden. Y desaparece el riesgo latente de que un script
nuevo que cruce por `id` con `pd.merge` duplique registros.

Uso
---
    python -X utf8 scripts/corregir_colision_id_coyago.py
    python -X utf8 scripts/corregir_colision_id_coyago.py --aplicar

Sin `--aplicar` no escribe nada (regla 7). Con `--aplicar` respalda antes,
con la API de backup de SQLite y fuera de la carpeta de QFieldCloud (regla 5).

Antes de correrlo con --aplicar
--------------------------------
1. Que nadie esté sincronizando desde una tablet.
2. Después conviene regenerar el Excel consolidado y los capítulos, para que
   la atribución del cultivo y los animales quede igual en todos lados.
"""
import argparse
import os
import sqlite3
import sys
import time

GPKG = os.path.join(os.path.expanduser('~'), 'QField', 'cloud',
                    'porotog_levantamiento_offline', 'data.gpkg')
RAIZ_RESPALDOS = (r"C:\Users\HP\OneDrive\Escritorio\CAYAMBE CATASTRO RIEGO"
                  r"\respaldos_qgs")

ID_COMPARTIDO = '{f06e1d27-3c64-4cdf-9f5f-79c10efd1a4a}'
# Fijo en el código (no aleatorio por corrida) para que la simulación y la
# aplicación muestren el mismo valor y quede auditable qué id se asignó.
ID_NUEVO = '{13786bd3-531c-4ef2-9823-0889f7ec76ca}'

CEDULA_CONSERVA = '1709566549'   # JOSE RAFAEL COYAGO CHICAIZA  — se queda el id
CEDULA_CAMBIA = '1726802000'     # MARCO RAFAEL COYAGO ALQUINGA — recibe el nuevo
FID1_CAMBIA = 7152               # fila exacta a modificar
CLAVE_ESPERADA = '1702520200008'

NOTA = ('CORREGIDO EN OFICINA 30-ago-2026: esta ficha compartia el id de QField '
        '{f06e1d27-...} con la de JOSE RAFAEL COYAGO CHICAIZA (colision de UUID al '
        'sincronizar, dos personas distintas sobre el mismo predio). Se le asigno un '
        'id propio. Los cultivos y animales quedaron con la otra ficha; si campo '
        'aclara que son de este titular, hay que reasignarlos.')


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


def tabla_fichas(cur):
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    todas = [t[0] for t in cur.fetchall()]
    return next((t for t in todas if 'Fichas_Predios' in t
                 and not any(x in t for x in ('rtree_', 'log_', 'gpkg_'))), None)


def tablas_hijas(cur, t_fichas):
    """Tablas con columna ficha_id (cultivos, animales, ...)."""
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    salida = []
    for (t,) in cur.fetchall():
        if t == t_fichas or any(x in t for x in ('rtree_', 'gpkg_', 'sqlite_')):
            continue
        try:
            cols = [r[1] for r in cur.execute('PRAGMA table_info("{}")'.format(t))]
        except sqlite3.DatabaseError:
            continue
        if 'ficha_id' in cols:
            salida.append(t)
    return salida


def main():
    ap = argparse.ArgumentParser(
        description='Separa el id de QField compartido por dos regantes (caso Coyago)')
    ap.add_argument('--aplicar', action='store_true',
                    help='escribe en el data.gpkg (sin esto solo simula)')
    args = ap.parse_args()

    print('=' * 78)
    print(' COLISION DE ID DE QFIELD — caso Coyago' +
          ('  [APLICAR]' if args.aplicar else '  [SIMULACION - no escribe nada]'))
    print('=' * 78)

    if not os.path.exists(GPKG):
        print('ERROR: no se encuentra {}'.format(GPKG))
        return 1

    con = sqlite3.connect(GPKG)
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    t_fichas = tabla_fichas(cur)
    if not t_fichas:
        print('ERROR: no se encontro la tabla de fichas')
        con.close()
        return 1

    filas = list(cur.execute(
        'SELECT fid_1, id, cedula, nombres, apellidos, clave_catastral, area_total, '
        'observaciones FROM "{}" WHERE id = ?'.format(t_fichas), (ID_COMPARTIDO,)))

    # ── comprobaciones de seguridad: si algo no es como se midio, no se toca ──
    if len(filas) != 2:
        print('\n  ATENCION: se esperaban 2 fichas con ese id y hay {}. No se toca nada.'
              .format(len(filas)))
        con.close()
        return 2
    ceds = {str(f['cedula'] or '').strip() for f in filas}
    if ceds != {CEDULA_CONSERVA, CEDULA_CAMBIA}:
        print('\n  ATENCION: las cedulas no son las esperadas ({}). No se toca nada.'
              .format(sorted(ceds)))
        con.close()
        return 2
    if cur.execute('SELECT COUNT(*) FROM "{}" WHERE id = ?'.format(t_fichas),
                   (ID_NUEVO,)).fetchone()[0]:
        print('\n  ATENCION: el id nuevo YA existe en la tabla. No se toca nada.')
        con.close()
        return 2

    print('\n  LAS DOS FICHAS QUE COMPARTEN EL ID')
    for f in filas:
        marca = 'conserva el id' if str(f['cedula']).strip() == CEDULA_CONSERVA \
                else '-> id NUEVO'
        print('     [{}] {} {}  ced {}  clave {}  {} m²   {}'.format(
            f['fid_1'], f['nombres'], f['apellidos'], f['cedula'],
            f['clave_catastral'], '{:,.2f}'.format(f['area_total'] or 0), marca))
        if str(f['clave_catastral'] or '').strip() != CLAVE_ESPERADA:
            print('\n  ATENCION: clave catastral inesperada. No se toca nada.')
            con.close()
            return 2

    # ── qué se queda colgando del id que conserva JOSE ──
    print('\n  REGISTROS QUE SIGUEN COLGANDO DEL ID ORIGINAL (quedan con {})'
          .format(CEDULA_CONSERVA))
    for t in tablas_hijas(cur, t_fichas):
        n = cur.execute('SELECT COUNT(*) FROM "{}" WHERE ficha_id = ?'.format(t),
                        (ID_COMPARTIDO,)).fetchone()[0]
        if n:
            print('     {:<28} {} registro(s)'.format(t, n))
    n_hijas = cur.execute('SELECT COUNT(*) FROM "{}" WHERE ficha_madre_id = ?'
                          .format(t_fichas), (ID_COMPARTIDO,)).fetchone()[0]
    print('     fichas hijas (predio adicional)  {}'.format(n_hijas))
    for h in cur.execute('SELECT cedula, nombres, apellidos, area_total FROM "{}" '
                         'WHERE ficha_madre_id = ?'.format(t_fichas), (ID_COMPARTIDO,)):
        ok = 'OK, es de quien conserva el id' \
            if str(h['cedula']).strip() == CEDULA_CONSERVA else 'REVISAR'
        print('        {} {} ({} m²)  ced {}  -> {}'.format(
            h['nombres'], h['apellidos'], '{:,.2f}'.format(h['area_total'] or 0),
            h['cedula'], ok))

    total_antes = cur.execute('SELECT COUNT(*) FROM "{}"'.format(t_fichas)).fetchone()[0]
    dups_antes = cur.execute(
        'SELECT COUNT(*) FROM (SELECT id FROM "{}" GROUP BY id HAVING COUNT(*)>1)'
        .format(t_fichas)).fetchone()[0]
    print('\n  ANTES:  fichas {} · ids duplicados {}'.format(total_antes, dups_antes))
    print('  DESPUES esperado: fichas {} (igual) · ids duplicados 0'.format(total_antes))

    if not args.aplicar:
        print('\n  ' + '-' * 74)
        print('  SIMULACION: no se escribio nada. Para aplicarlo:  --aplicar')
        print('  ' + '-' * 74)
        con.close()
        return 0

    con.close()

    print('\n  respaldando antes de tocar nada...')
    destino = respaldo_sqlite(GPKG, 'antes-colision-id-coyago')
    print('     {}'.format(destino))

    con = sqlite3.connect(GPKG)
    cur = con.cursor()
    cur.execute("SELECT name, sql FROM sqlite_master WHERE type='trigger' AND tbl_name=?",
                (t_fichas,))
    triggers = cur.fetchall()
    for nombre, _ in triggers:
        cur.execute('DROP TRIGGER IF EXISTS "{}"'.format(nombre))
    try:
        # se identifica la fila por fid_1 (clave de fila) Y por cedula, para no
        # depender de un solo criterio al escribir
        cur.execute('UPDATE "{}" SET id = ?, observaciones = '
                    'TRIM(COALESCE(observaciones, "") || " | " || ?) '
                    'WHERE fid_1 = ? AND cedula = ? AND id = ?'.format(t_fichas),
                    (ID_NUEVO, NOTA, FID1_CAMBIA, CEDULA_CAMBIA, ID_COMPARTIDO))
        n_upd = cur.rowcount
    finally:
        for _, sql in triggers:
            if sql:
                cur.execute(sql)

    if n_upd != 1:
        con.rollback()
        con.close()
        print('     ERROR: se iban a modificar {} filas (se esperaba 1). '
              'Se deshizo el cambio.'.format(n_upd))
        return 1

    con.commit()
    cur.execute('PRAGMA wal_checkpoint(TRUNCATE)')
    con.close()
    print('     fichas actualizadas: {} · triggers recreados: {}'.format(n_upd, len(triggers)))

    # ── verificacion releyendo del disco ──
    con = sqlite3.connect(GPKG)
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    total = cur.execute('SELECT COUNT(*) FROM "{}"'.format(t_fichas)).fetchone()[0]
    dups = cur.execute(
        'SELECT COUNT(*) FROM (SELECT id FROM "{}" GROUP BY id HAVING COUNT(*)>1)'
        .format(t_fichas)).fetchone()[0]
    print('\n  VERIFICADO releyendo del disco')
    print('     fichas totales   {}  (antes {})'.format(total, total_antes))
    print('     ids duplicados   {}  (antes {})'.format(dups, dups_antes))
    for ced in (CEDULA_CONSERVA, CEDULA_CAMBIA):
        for r in cur.execute('SELECT id, nombres, apellidos FROM "{}" WHERE cedula = ? '
                             'AND clave_catastral = ?'.format(t_fichas),
                             (ced, CLAVE_ESPERADA)):
            print('     {} {}  ->  {}'.format(r['nombres'], r['apellidos'], r['id']))
    n_h = cur.execute('SELECT COUNT(*) FROM "{}" WHERE ficha_madre_id = ?'
                      .format(t_fichas), (ID_COMPARTIDO,)).fetchone()[0]
    print('     hijas que siguen colgando del id original: {}'.format(n_h))
    for t in tablas_hijas(cur, t_fichas):
        n = cur.execute('SELECT COUNT(*) FROM "{}" WHERE ficha_id = ?'.format(t),
                        (ID_COMPARTIDO,)).fetchone()[0]
        if n:
            print('     {:<28} {} registro(s) intactos'.format(t, n))
    con.close()

    print('\n  Conviene regenerar el Excel consolidado y los capitulos para que la')
    print('  atribucion del cultivo y los animales quede igual en todos los documentos.')
    print('=' * 78)
    return 0


if __name__ == '__main__':
    sys.exit(main())
