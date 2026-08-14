# -*- coding: utf-8 -*-
"""
La ficha levantada sobre el PÁRAMO CHICO, que no es de nadie: es del Estado.

El hallazgo
-----------
La ficha S-C-P001 de AIGAJE QUINATOA SILVIA ESTELA quedó enganchada a la clave
catastral `1702606901`, que **no es su predio**. Según la ficha catastral del
GADM Cayambe esa clave es:

    PARAMO CHICO — «Polígono Especial de Colindancia»
    «REVERSIÓN DEL PARAMO CHICO AL ESTADO A PARTIR DE LA COTA 3680 M SNM
     OFICIO Nº 269-JACR-2018 INSPECCIÓN Nº 422 DEL 26/09/2018»

Con la clave se arrastró su superficie: la ficha declara **3.237.394 m²**
(323,74 ha) cuando el predio catastrado a su nombre —mismo nombre, misma
cédula— es `1702521020106`, de **3.073,78 m²**. Un predio 1.053 veces mayor que
el real, a 3.740 msnm, y contado entero como superficie bajo riego.

La prueba está en sus propios cultivos
--------------------------------------
Los cultivos de la ficha vienen duplicados, en dos versiones que se distinguen
por `ref_area_predio`:

    ref 3.073,78     Cebolla 1.000 m² + Pasto no mejorado 2.073,78 m²   ← suman
                                                          el predio real, exacto
    ref 3.237.394    Cebolla 3.237.394 m² + Pasto no mejorado 500 m²    ← el mismo
                                                          dato escalado al páramo

Esas 323,79 ha de cebolla son **el 35,4 % de toda la cebolla del padrón**.

Qué corrige
-----------
1. La ficha principal pasa a su predio real (clave y superficie del catastro).
   El riego mantiene la proporción que traía —declaraba todo su terreno regado,
   sigue todo regado— sobre la superficie que de verdad le corresponde.
2. Borra los dos registros de cultivo escalados al páramo. Los reales quedan.
3. Borra la ficha adicional (hija), que es **ese mismo predio**: al reasignar la
   principal, las dos apuntarían a `1702521020106` y la superficie se contaría
   dos veces.

Qué NO corrige
--------------
- Los animales de la ficha (2 ovejas, 30 cuyes, 1 chancho, 5 pollos): son datos
  reales de la titular y no dependen de la superficie.
- Su caudal (31,5 l/s). Es la moda de LA LIBERTAD —105 de 154 fichas— así que
  quitar o cambiar esta ficha no mueve el caudal del sistema (regla 3).
- El resto de fichas con superficie dudosa. La `1702520680109` declara 87,67 ha
  de cultivo sobre un predio de 0,88 ha: es otro caso, y es de campo, no de
  oficina.

Efecto en las cifras publicadas
-------------------------------
    superficie total    10.196,51 ha  →   9.872,77 ha
    con riego            7.633,76 ha  →   7.310,02 ha
    cebolla                913,43 ha  →     589,64 ha
    fichas                     6.831  →        6.830  (2.524 → 2.523 adicionales)
    caudal del sistema    950,16 l/s  →  sin cambio

Uso
---
    "C:\\OSGeo4W\\bin\\python-qgis.bat" -X utf8 scripts/corregir_ficha_paramo_chico.py
    "C:\\OSGeo4W\\bin\\python-qgis.bat" -X utf8 scripts/corregir_ficha_paramo_chico.py --aplicar

Sin `--aplicar` no escribe nada (regla 7). Con `--aplicar` respalda antes, con la
API de backup de SQLite y fuera de la carpeta de QFieldCloud (regla 5).

Antes de correrlo con --aplicar
-------------------------------
1. Que nadie esté sincronizando desde una tablet.
2. Aviso a Armando: **cambia el número de fichas** que declaró al Consejo
   Provincial y mueve la superficie publicada (regla 11).
3. Después hay que regenerar todo: export → capas → web → informes → Excel →
   gpkg del cliente, y volver a publicar.
"""
import argparse
import os
import sqlite3
import sys
import time

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
GPKG = os.path.join(os.path.expanduser('~'), 'QField', 'cloud',
                    'porotog_levantamiento_offline', 'data.gpkg')
RAIZ_RESPALDOS = (r"C:\Users\HP\OneDrive\Escritorio\CAYAMBE CATASTRO RIEGO"
                  r"\respaldos_qgs")

FICHA_MADRE = '{fa4970b3-bd19-428e-b47f-7cec734252d7}'
CLAVE_PARAMO = '1702606901'
CLAVE_REAL = '1702521020106'
AREA_REAL = 3073.78          # m², polígono del catastro a nombre de la titular

# Sin cifras a propósito: `corregir_areas_por_observacion.py` lee números de este
# campo para repartir superficies entre copropietarios, y no debe encontrar aquí
# nada que pueda confundir con un reparto.
OBSERVACION = ('PREDIO CORREGIDO EN OFICINA: la ficha se levanto sobre el poligono '
               'del PARAMO CHICO, revertido al Estado por oficio del GADM Cayambe; '
               'se reasigno al predio catastrado a nombre de la titular. '
               'Ver docs/CORRECCION-paramo-chico.md')


def ha(m2):
    return '{:,.2f}'.format((m2 or 0) / 10000.0).replace(',', 'X').replace('.', ',').replace('X', '.')


def respaldo_sqlite(origen, etiqueta):
    """Copia consistente con la API de backup de SQLite, fuera de QFieldCloud."""
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


def tablas(cur):
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    todas = [t[0] for t in cur.fetchall()]
    def buscar(clave):
        return next((t for t in todas if clave in t
                     and not any(x in t for x in ('rtree_', 'log_', 'gpkg_'))), None)
    return buscar('Fichas_Predios'), buscar('Cultivos_Agricolas'), buscar('Animales_Especies')


def main():
    ap = argparse.ArgumentParser(description='Corrige la ficha del PARAMO CHICO')
    ap.add_argument('--aplicar', action='store_true',
                    help='escribe en el data.gpkg (sin esto solo simula)')
    args = ap.parse_args()

    print('=' * 78)
    print(' FICHA LEVANTADA SOBRE EL PARAMO CHICO (predio del Estado)' +
          ('  [APLICAR]' if args.aplicar else '  [SIMULACION - no escribe nada]'))
    print('=' * 78)

    if not os.path.exists(GPKG):
        print('ERROR: no se encuentra {}'.format(GPKG))
        return 1

    con = sqlite3.connect(GPKG)
    cur = con.cursor()
    t_fichas, t_cult, t_anim = tablas(cur)
    if not (t_fichas and t_cult):
        print('ERROR: no se encontraron las tablas de fichas y cultivos')
        return 1

    # ── estado actual ──
    cur.execute('SELECT id, codigo_final, apellidos, nombres, cedula, clave_catastral, '
                'cod_poligono, area_total, area_riego, area_sin_riego, caudal_valor, '
                'cota_msnm, comunidad FROM "{}" WHERE id = ?'.format(t_fichas),
                (FICHA_MADRE,))
    madre = cur.fetchone()
    if not madre:
        print('ERROR: no existe la ficha {} en el gpkg'.format(FICHA_MADRE))
        con.close()
        return 1

    if str(madre[5] or '').strip() == CLAVE_REAL:
        print('\n  La ficha YA apunta al predio real ({}). No hay nada que hacer.'
              .format(CLAVE_REAL))
        con.close()
        return 0
    if str(madre[5] or '').strip() != CLAVE_PARAMO:
        print('\n  ATENCION: la ficha apunta a "{}", que no es la clave del paramo '
              'ni la real. No se toca nada.'.format(madre[5]))
        con.close()
        return 2

    print('\n  FICHA PRINCIPAL')
    print('     {}  {} {}  · cedula {}'.format(madre[1], madre[2], madre[3], madre[4]))
    print('     comunidad {} · cota {} msnm'.format(madre[12], madre[11]))
    print('     clave      {}  ->  {}'.format(madre[5], CLAVE_REAL))
    print('     area total {} ha  ->  {} ha'.format(ha(madre[7]), ha(AREA_REAL)))
    print('     con riego  {} ha  ->  {} ha'.format(ha(madre[8]), ha(AREA_REAL)))
    print('     caudal     {} l/s (no se toca: es la moda de su comunidad)'.format(madre[10]))

    # ── ficha hija ──
    cur.execute('SELECT id, codigo_final, clave_catastral, area_total, area_riego '
                'FROM "{}" WHERE ficha_madre_id = ?'.format(t_fichas), (FICHA_MADRE,))
    hijas = cur.fetchall()
    print('\n  FICHA(S) ADICIONAL(ES) COLGANDO DE ELLA: {}'.format(len(hijas)))
    for h in hijas:
        print('     {} · clave {} · {} ha  ->  se elimina (es el mismo predio)'
              .format(h[1], h[2], ha(h[3])))
    if len(hijas) != 1 or str(hijas[0][2] or '').strip() != CLAVE_REAL:
        print('\n  NO SE ESCRIBE NADA: se esperaba exactamente una ficha adicional '
              'sobre la clave {}. Revisar a mano.'.format(CLAVE_REAL))
        con.close()
        return 2
    id_hija = hijas[0][0]

    # Producción colgada de la hija: son copias de la de la madre —el mismo
    # cultivo, la misma superficie, con `ref_area_predio` en cero— porque la
    # recuperación de la Sección 7 la escribió en las dos fichas. Se va con ella
    # y la producción real queda registrada una sola vez.
    cur.execute('SELECT tipo_cultivo, superficie_m2 FROM "{}" WHERE ficha_id = ?'
                .format(t_cult), (id_hija,))
    cult_hija = cur.fetchall()
    if cult_hija:
        print('     lleva {} cultivo(s) propios, copia de los de la principal:'
              .format(len(cult_hija)))
        for c in cult_hija:
            print('        {:<20} {:>14} m²'.format(c[0] or '—', '{:,.2f}'.format(c[1] or 0)))
    if t_anim:
        cur.execute('SELECT COUNT(*) FROM "{}" WHERE ficha_id = ?'.format(t_anim), (id_hija,))
        n_anim_hija = cur.fetchone()[0]
        if n_anim_hija:
            print('     ATENCION: tiene {} animales propios; se eliminarian con ella'
                  .format(n_anim_hija))

    # ── cultivos escalados al páramo ──
    cur.execute('SELECT id_cultivo, tipo_cultivo, superficie_m2, ref_area_predio '
                'FROM "{}" WHERE ficha_id = ? ORDER BY superficie_m2 DESC'
                .format(t_cult), (FICHA_MADRE,))
    cultivos = cur.fetchall()
    sobran = [c for c in cultivos if (c[3] or 0) > 1000000]
    quedan = [c for c in cultivos if (c[3] or 0) <= 1000000]
    print('\n  CULTIVOS DE LA FICHA: {}'.format(len(cultivos)))
    for c in cultivos:
        print('     {:<20} {:>14} m²   ref predio {:>14} m²   {}'
              .format(c[1] or '—', '{:,.2f}'.format(c[2] or 0),
                      '{:,.2f}'.format(c[3] or 0),
                      'SE ELIMINA' if (c[3] or 0) > 1000000 else 'se conserva'))
    if not sobran or not quedan:
        print('\n  NO SE ESCRIBE NADA: se esperaban cultivos de las dos clases '
              '(los del predio real y los escalados al paramo).')
        con.close()
        return 2

    # ── efecto en el conjunto ──
    cur.execute('SELECT COUNT(*), SUM(COALESCE(area_total,0)), SUM(COALESCE(area_riego,0)) '
                'FROM "{}"'.format(t_fichas))
    n_fichas, tot, rie = cur.fetchone()
    cur.execute('SELECT COUNT(*), SUM(COALESCE(superficie_m2,0)) FROM "{}"'.format(t_cult))
    n_cult, sup_cult = cur.fetchone()
    baja_area = (madre[7] or 0) - AREA_REAL + (hijas[0][3] or 0)
    baja_riego = (madre[8] or 0) - AREA_REAL + (hijas[0][4] or 0)
    # se van los dos escalados al páramo y los duplicados que cuelgan de la hija
    baja_cult = sum(c[2] or 0 for c in sobran) + sum(c[1] or 0 for c in cult_hija)
    n_cult_fuera = len(sobran) + len(cult_hija)

    print('\n  EFECTO EN EL PADRON')
    print('     fichas               {:>12,}  ->  {:>12,}'.format(n_fichas, n_fichas - 1))
    print('     superficie total     {:>12} ha  ->  {:>12} ha'.format(ha(tot), ha(tot - baja_area)))
    print('     con riego            {:>12} ha  ->  {:>12} ha'.format(ha(rie), ha(rie - baja_riego)))
    print('     registros de cultivo {:>12,}  ->  {:>12,}'.format(n_cult, n_cult - n_cult_fuera))
    print('     superficie cultivada {:>12} ha  ->  {:>12} ha'
          .format(ha(sup_cult), ha(sup_cult - baja_cult)))

    if not args.aplicar:
        print('\n  ' + '-' * 74)
        print('  SIMULACION: no se escribio nada. Para aplicarlo:  --aplicar')
        print('  ' + '-' * 74)
        con.close()
        return 0

    con.close()

    # ── aplicar ──
    print('\n  respaldando antes de tocar nada...')
    destino = respaldo_sqlite(GPKG, 'antes-paramo-chico')
    print('     {}'.format(destino))

    con = sqlite3.connect(GPKG)
    cur = con.cursor()
    # Los triggers del índice espacial llaman a ST_IsEmpty, que SQLite puro no
    # trae. Se retiran mientras duran los UPDATE/DELETE y se recrean tal cual.
    cur.execute("SELECT name, sql FROM sqlite_master WHERE type='trigger' AND tbl_name=?",
                (t_fichas,))
    triggers = cur.fetchall()
    for nombre, _ in triggers:
        cur.execute('DROP TRIGGER IF EXISTS "{}"'.format(nombre))
    try:
        cur.execute('UPDATE "{}" SET clave_catastral = ?, cod_poligono = ?, '
                    'area_total = ?, area_riego = ?, area_sin_riego = 0, '
                    'observaciones = ? WHERE id = ?'.format(t_fichas),
                    (CLAVE_REAL, CLAVE_REAL, AREA_REAL, AREA_REAL, OBSERVACION, FICHA_MADRE))
        n_upd = cur.rowcount
        cur.execute('DELETE FROM "{}" WHERE id = ?'.format(t_fichas), (id_hija,))
        n_hija = cur.rowcount
    finally:
        for _, sql in triggers:
            if sql:
                cur.execute(sql)

    n_cult_del = 0
    for c in sobran:
        cur.execute('DELETE FROM "{}" WHERE id_cultivo = ?'.format(t_cult), (c[0],))
        n_cult_del += cur.rowcount
    for tabla in (t_cult, t_anim):
        if tabla:
            cur.execute('DELETE FROM "{}" WHERE ficha_id = ?'.format(tabla), (id_hija,))

    con.commit()
    cur.execute('PRAGMA wal_checkpoint(TRUNCATE)')
    con.close()
    print('     ficha corregida: {} · ficha adicional eliminada: {} · '
          'cultivos eliminados: {} · triggers recreados: {}'
          .format(n_upd, n_hija, n_cult_del, len(triggers)))

    # ── verificación releyendo del disco ──
    con = sqlite3.connect(GPKG)
    cur = con.cursor()
    cur.execute('SELECT clave_catastral, area_total, area_riego FROM "{}" WHERE id = ?'
                .format(t_fichas), (FICHA_MADRE,))
    v = cur.fetchone()
    cur.execute('SELECT COUNT(*), SUM(COALESCE(area_total,0)), SUM(COALESCE(area_riego,0)) '
                'FROM "{}"'.format(t_fichas))
    v_n, v_tot, v_rie = cur.fetchone()
    cur.execute('SELECT COUNT(*) FROM "{}" WHERE id = ?'.format(t_fichas), (id_hija,))
    v_hija = cur.fetchone()[0]
    cur.execute('SELECT COUNT(*), SUM(COALESCE(superficie_m2,0)) FROM "{}" WHERE ficha_id = ?'
                .format(t_cult), (FICHA_MADRE,))
    v_cn, v_cs = cur.fetchone()
    con.close()

    print('\n  VERIFICADO releyendo del disco')
    print('     ficha  -> clave {} · {} ha · riego {} ha'.format(v[0], ha(v[1]), ha(v[2])))
    print('     ficha adicional en la base: {} (debe ser 0)'.format(v_hija))
    print('     cultivos de la ficha: {} · {} ha'.format(v_cn, ha(v_cs)))
    print('     padron -> {:,} fichas · {} ha · {} ha con riego'.format(v_n, ha(v_tot), ha(v_rie)))
    print('\n  Falta regenerar: export -> capas -> web -> informes -> Excel -> gpkg cliente.')
    print('=' * 78)
    return 0


if __name__ == '__main__':
    sys.exit(main())
