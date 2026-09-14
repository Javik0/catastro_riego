# -*- coding: utf-8 -*-
"""
Cuatro titulares duplicados por un error en la cédula.

EL HALLAZGO
-----------
Al asignar la codificación S01-C01-R001-F01 (que numera al titular por su
cédula dentro de cada comunidad) aparecieron 23 casos de un mismo nombre con
dos cédulas distintas en la misma comunidad: cada cédula recibía su propio
número de titular, como si fueran dos personas.

Validando el dígito verificador de la cédula ecuatoriana, esos 23 casos se
separan: en 15 las dos cédulas son válidas y son de verdad dos personas
distintas —parientes del mismo nombre, cosa corriente en la zona—, y no hay
nada que corregir. Los que sí son un error son los cuatro de aquí.

LOS DOS SEGUROS — un dígito mal escrito
---------------------------------------
En cada par, las dos cédulas difieren en UN dígito y solo una supera el
dígito verificador. La que no lo supera no puede existir:

  LARCACHACA · GUALAVISI IMBAQUINGO CRISTIAN JEFERSON
      1725933936  no valida   ->   1725963936  valida
  LARCACHACA · TIPANLUISA LANCHIMBA JOSE LINO
      1717276448  no valida   ->   1717275448  valida

LOS DOS DE ORGANIZACIONES — requieren confirmar el número
---------------------------------------------------------
Dos comunas están registradas dos veces: con un número de 10 dígitos y con
ese mismo número más el sufijo 001, que es la forma de un RUC. Que se trata
de la misma entidad no admite duda —el uno es prefijo del otro y comparten
nombre y comunidad—, pero **cuál de los dos números es el correcto no se
puede resolver aquí**: el de 10 dígitos no es una cédula válida (es la raíz
de un RUC, no una cédula) y el de 13 TAMPOCO supera el dígito verificador de
RUC de sociedad privada:

  COMUNA CANGAHUAPUNGO          1791797949 / 1791797949001
      RUC: suma 204, resto 6, verificador esperado 5, real 4
  COMUNA JURIDICA CHAUPIESTANCIA  1790713385 / 1790713385001
      RUC: suma 142, resto 10, verificador esperado 1, real 8

Por eso estos dos NO se corrigen por defecto. Unificarlos al RUC de 13
dígitos es lo razonable —el identificador de una persona jurídica es su
RUC—, pero conviene confirmar el número real (consulta al SRI o a la propia
comuna) antes de escribirlo. Con `--incluir-organizaciones` se aplican.

QUÉ HACE
--------
Cambia el campo `cedula` de las fichas que tienen la cédula equivocada, para
que queden bajo el mismo titular que sus otras fichas. No toca nombres,
áreas, claves, cultivos ni animales: el error es de identidad, no de dato
productivo.

EFECTO EN LA CODIFICACIÓN Y EN LAS FICHAS YA GENERADAS
------------------------------------------------------
Cada corrección funde dos titulares en uno, así que el número de titular (R)
del que desaparece queda sin uso. Al regenerar, las fichas afectadas pasan a
ser otra F del titular que queda:

  GUALAVISI   S01-C01-R026-F01  ->  pasa a ser otra ficha de R027
  TIPANLUISA  S01-C01-R133-F01  ->  pasa a ser otra ficha de R132
  CANGAHUAPUNGO      S03-C43-R043-F01  ->  pasa a R044
  CHAUPIESTANCIA     S03-C41-R057-F01  ->  pasa a R058

`public/geo/codificacion_fichas.json` conserva el código ya asignado a cada
ficha, así que para que tomen el nuevo hay que borrar sus entradas de ese
archivo, borrar sus PDF y volver a generarlos. Son 4 fichas de 6.830, y el
paquete todavía no se ha entregado: es el momento de hacerlo, no después.

USO
---
    python -X utf8 scripts/corregir_cedulas_homonimos.py
    python -X utf8 scripts/corregir_cedulas_homonimos.py --aplicar
    python -X utf8 scripts/corregir_cedulas_homonimos.py --aplicar --incluir-organizaciones

Sin `--aplicar` no escribe nada (regla 7). Con `--aplicar` respalda antes con
la API de backup de SQLite, fuera de la carpeta de QFieldCloud (regla 5).

ANTES DE CORRERLO CON --aplicar
--------------------------------
1. Que nadie esté sincronizando desde una tablet.
2. Cambiar el padrón se coordina antes: la base declarada al Consejo
   Provincial son 6.825 fichas y cualquier movimiento se avisa (regla 11).
   Esto no crea ni elimina fichas —solo corrige a quién pertenecen—, pero
   mueve el conteo de titulares.
3. Después hay que regenerar: export -> capas -> web -> informes -> gpkg
   cliente -> build -> deploy, y rehacer las 4 fichas PDF afectadas.
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

# (id de la ficha, cédula equivocada, cédula correcta, quién es, seguro?)
CASOS = [
    {'id': '{575c59c5-ccfe-4013-a274-cbca3aa23adc}',
     'de': '1725933936', 'a': '1725963936',
     'quien': 'GUALAVISI IMBAQUINGO CRISTIAN JEFERSON · LARCACHACA',
     'clave': '1702521470028', 'seguro': True,
     'motivo': 'un digito mal escrito; 1725933936 no supera el digito verificador'},
    {'id': '{b53f5c89-a193-4e7b-9bb2-2bacdd20c6dd}',
     'de': '1717276448', 'a': '1717275448',
     'quien': 'TIPANLUISA LANCHIMBA JOSE LINO · LARCACHACA',
     'clave': '1702521450002', 'seguro': True,
     'motivo': 'un digito mal escrito; 1717276448 no supera el digito verificador'},
    {'id': '{1352d31e-fcf1-4c64-bc43-721da83f9374}',
     'de': '1791797949', 'a': '1791797949001',
     'quien': 'COMUNA CANGAHUAPUNGO · CANGAHUA PUNGO',
     'clave': '1702550350026', 'seguro': False,
     'motivo': 'misma entidad con cedula y RUC; el RUC no valida, confirmar el numero'},
    {'id': '{5168406a-bfff-4884-90a1-477c6b180328}',
     'de': '1790713385', 'a': '1790713385001',
     'quien': 'COMUNA JURIDICA CHAUPIESTANCIA · CHAUPIESTANCIA',
     'clave': '1702540170100', 'seguro': False,
     'motivo': 'misma entidad con cedula y RUC; el RUC no valida, confirmar el numero'},
]

OBSERVACION = ('CEDULA CORREGIDA EN OFICINA (10-sep-2026): decia {de} y no superaba '
               'el digito verificador; el titular es el mismo de las otras fichas a '
               'su nombre en la comunidad, con cedula {a}.')


def cedula_valida(c):
    """Dígito verificador de la cédula ecuatoriana. None si no aplica."""
    c = (c or '').strip()
    if not c.isdigit() or len(c) != 10:
        return None
    if not (1 <= int(c[:2]) <= 24 or int(c[:2]) == 30) or int(c[2]) > 5:
        return False
    suma = 0
    for i, d in enumerate(c[:9]):
        v = int(d) * (2 if i % 2 == 0 else 1)
        suma += v - 9 if v > 9 else v
    return (10 - suma % 10) % 10 == int(c[9])


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


def main():
    ap = argparse.ArgumentParser(
        description='Corrige la cedula de titulares duplicados por error de digitacion')
    ap.add_argument('--aplicar', action='store_true',
                    help='escribe en el data.gpkg (sin esto solo simula)')
    ap.add_argument('--incluir-organizaciones', action='store_true',
                    help='corrige tambien las dos comunas con cedula y RUC (su numero '
                         'correcto no se pudo verificar: leer la cabecera del script)')
    args = ap.parse_args()

    casos = [c for c in CASOS if c['seguro'] or args.incluir_organizaciones]

    print('=' * 78)
    print(' CEDULAS DE TITULARES DUPLICADOS' +
          ('  [APLICAR]' if args.aplicar else '  [SIMULACION - no escribe nada]'))
    print('=' * 78)
    if not args.incluir_organizaciones:
        print('  (las dos comunas con cedula/RUC quedan fuera: --incluir-organizaciones)')

    if not os.path.exists(GPKG):
        print('ERROR: no se encuentra {}'.format(GPKG))
        return 1

    con = sqlite3.connect(GPKG)
    cur = con.cursor()
    t = tabla_fichas(cur)
    if not t:
        print('ERROR: no se encontro la tabla de fichas')
        con.close()
        return 1

    listos, problemas = [], []
    for c in casos:
        cur.execute('SELECT codigo_final, apellidos, nombres, cedula, clave_catastral, '
                    'comunidad FROM "{}" WHERE id = ?'.format(t), (c['id'],))
        row = cur.fetchone()
        print('\n  {}'.format(c['quien']))
        if not row:
            print('     NO EXISTE esa ficha en el gpkg — no se toca')
            problemas.append(c)
            continue
        cod, ape, nom, ced, clave, com = row
        ced = (ced or '').strip()
        print('     ficha {} · clave {}'.format(cod, clave))
        print('     cedula   {}  ({})  ->  {}  ({})'.format(
            ced, 'no valida' if cedula_valida(ced) is False else
                 ('valida' if cedula_valida(ced) else 'no es cedula de 10 digitos'),
            c['a'], 'valida' if cedula_valida(c['a']) else 'no verificable'))
        print('     motivo   {}'.format(c['motivo']))
        if ced == c['a']:
            print('     YA esta corregida — no se toca')
            continue
        if ced != c['de']:
            print('     ATENCION: la cedula actual no es la esperada ({}). No se toca.'
                  .format(c['de']))
            problemas.append(c)
            continue
        if str(clave or '').strip() != c['clave']:
            print('     ATENCION: la clave catastral no es la esperada ({}). No se toca.'
                  .format(c['clave']))
            problemas.append(c)
            continue
        # cuántas fichas quedarán bajo el titular destino
        cur.execute('SELECT COUNT(*) FROM "{}" WHERE TRIM(cedula) = ?'.format(t), (c['a'],))
        print('     el titular {} ya tiene {} ficha(s); esta se le suma'
              .format(c['a'], cur.fetchone()[0]))
        listos.append(c)

    con.close()

    print('\n  ' + '-' * 74)
    print('  a corregir: {} · sin tocar por revisar: {}'.format(len(listos), len(problemas)))
    if not listos:
        print('  No hay nada que aplicar.')
        return 0
    if not args.aplicar:
        print('  SIMULACION: no se escribio nada. Para aplicarlo:  --aplicar')
        print('  ' + '-' * 74)
        return 0

    print('\n  respaldando antes de tocar nada...')
    destino = respaldo_sqlite(GPKG, 'antes-cedulas-homonimos')
    print('     {}'.format(destino))

    con = sqlite3.connect(GPKG)
    cur = con.cursor()
    cur.execute("SELECT name, sql FROM sqlite_master WHERE type='trigger' AND tbl_name=?", (t,))
    triggers = cur.fetchall()
    for nombre, _ in triggers:
        cur.execute('DROP TRIGGER IF EXISTS "{}"'.format(nombre))
    n_upd = 0
    try:
        for c in listos:
            cur.execute('UPDATE "{}" SET cedula = ?, observaciones = ? WHERE id = ?'.format(t),
                        (c['a'], OBSERVACION.format(de=c['de'], a=c['a']), c['id']))
            n_upd += cur.rowcount
    finally:
        for _, sql in triggers:
            if sql:
                cur.execute(sql)
    con.commit()
    cur.execute('PRAGMA wal_checkpoint(TRUNCATE)')
    con.close()
    print('     fichas actualizadas: {} · triggers recreados: {}'.format(n_upd, len(triggers)))

    con = sqlite3.connect(GPKG)
    cur = con.cursor()
    print('\n  VERIFICADO releyendo del disco')
    ok = True
    for c in listos:
        cur.execute('SELECT cedula FROM "{}" WHERE id = ?'.format(t), (c['id'],))
        v = (cur.fetchone() or [''])[0]
        marca = 'ok' if (v or '').strip() == c['a'] else 'NO CUADRA'
        ok = ok and marca == 'ok'
        print('     {:52} {} {}'.format(c['quien'][:52], v, marca))
    con.close()

    print('\n  Falta, en este orden:')
    print('    1. export_geojson.py y el resto de la sincronizacion.')
    print('    2. Quitar de public/geo/codificacion_fichas.json las {} fichas corregidas'
          .format(len(listos)))
    print('       (para que tomen su codigo nuevo bajo el titular que queda).')
    print('    3. Borrar sus PDF y regenerarlos con generar_fichas_pdf.py.')
    print('=' * 78)
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
