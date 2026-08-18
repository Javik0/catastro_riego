# -*- coding: utf-8 -*-
"""
Correcciones que mandó el técnico por WhatsApp (vía Armando, 18-ago-2026).

Qué llegó
---------
Una lista de fichas revisadas en campo con lo que había que arreglar en cada
una. Al buscarlas en el padrón, **la mitad ya estaba correcta** —el sembrío
que decían que faltaba ya constaba— así que aquí solo van las que de verdad
cambian algo:

1. **María Caridad Vallejo Villavicencio** (`1702521730053`) — «no hay
   construcción, la hacen constar como Tapia». Se vacía
   `material_construccion`.
2. **Pablo Lenin Robalino Muñoz** (`1702520920041`) — «es comunero, está
   comunera». Su observación dice «LA COMUNERA … A NOMBRE DEL ESPOSA»: se
   corrige el género y la concordancia.
3. **Mauricio Rafael Vallejo Zaldumbide** (`1702520730114`) — «sí tiene
   escritura, el impuesto sale a su nombre; en el Excel consta que no tiene
   escrituras y está a nombre del esposo». Su observación es falsa de principio
   a fin (además él es varón y hablaba de «el esposo»): se retira. La tenencia
   ya decía «Escritura / Título de Propiedad» y se deja.
4. **María Guadalupe Basurto Solís** (`1702521730025`) — «sí tiene escritura,
   pero el impuesto predial está a nombre del esposo». Su tenencia decía
   «Posesión sin Título»: pasa a «Escritura / Título de Propiedad». La
   observación se conserva porque describe bien la situación —la escritura
   existe, a nombre del esposo— y su género ya es correcto.

Lo que se dejó como estaba, y por qué
--------------------------------------
* **El sembrío de Manuel Isauro, Sara Lourdes y el predio adicional de Manuel
  Elías**: el técnico pedía añadir pasto, cebada y cebolla, y **ya constaban**.
  Decisión de JAVIKO: si ya está, se deja.
* **Los cultivos de Mauricio Rafael**: el técnico dice «papas y habas» y el
  padrón tiene papas y cebada. No se toca hasta que lo confirme —el mismo
  mensaje traía otro dato cruzado (ver abajo)—.
* **Las cédulas**: el mensaje atribuía a Pablo Robalino la cédula 1713315016,
  que en realidad es de Sara Lourdes Vallejo (su esposa, con quien comparte
  predio). El padrón ya las tiene bien; el cruce estaba en el mensaje.
* **El «40.005,33 m²»** que el mensaje asociaba a María Caridad no es de ella
  —su predio mide 53.940,93 y coincide con el polígono—: es la suma de las dos
  fichas del predio vecino `1702521730029` (Manuel Isauro y Lorena Marcela,
  20.002,665 cada una). Dos asuntos distintos en el mismo mensaje.

El género de las observaciones
-------------------------------
El aviso «es comunero, está comunera» destapó que el técnico usó una plantilla
en femenino sin ajustarla. Se corrige **solo donde el molde es inequívoco**:
la observación empieza hablando del titular («LA COMUNERA REGANTE …», «EL
COMUNERO REGANTE …») y su género no coincide con el nombre.

**No** se tocan las observaciones donde el género cruzado es correcto porque
hablan de otra persona —«el regante actual es el esposo», «actualiza datos la
hija»—. Ahí cambiar el artículo destrozaría la frase. De 76 observaciones con
género cruzado, la mayoría son de ese tipo.

Uso
---
    "C:\\OSGeo4W\\bin\\python-qgis.bat" -X utf8 scripts/corregir_fichas_tecnico_18ago.py
    "C:\\OSGeo4W\\bin\\python-qgis.bat" -X utf8 scripts/corregir_fichas_tecnico_18ago.py --aplicar

Sin `--aplicar` no escribe nada (regla 7).
"""
import argparse
import os
import re
import sqlite3
import time
import unicodedata

GPKG = os.path.join(os.path.expanduser('~'), 'QField', 'cloud',
                    'porotog_levantamiento_offline', 'data.gpkg')
RAIZ_RESPALDOS = (r"C:\Users\HP\OneDrive\Escritorio\CAYAMBE CATASTRO RIEGO"
                  r"\respaldos_qgs")
TABLA = 'Fichas_Predios_880eb10d_d887_4fc6_99a2_8af3ac63877e'

# ── 1. Las cuatro fichas puntuales ─────────────────────────────────────────
# (clave, campo, valor nuevo, por qué)
PUNTUALES = [
    ('1702521730053', 'material_construccion', None,
     'no hay construcción; constaba TAPIA'),
    ('1702521730025', 'tenencia_predio', 'Escritura / Título de Propiedad',
     'sí tiene escritura, aunque el impuesto salga a nombre del esposo'),
    ('1702520730114', 'observaciones', '',
     'la observación decía que no tiene escrituras y que el predio es del '
     'esposo; ambas cosas son falsas según el técnico'),
]

# ── 2. Género en el molde de la plantilla ──────────────────────────────────
VARON = {
    'JOSE', 'JUAN', 'LUIS', 'CARLOS', 'MANUEL', 'SEGUNDO', 'PEDRO', 'PABLO',
    'MIGUEL', 'ANGEL', 'VICTOR', 'JORGE', 'MARIO', 'RAFAEL', 'FRANCISCO',
    'ANTONIO', 'ALBERTO', 'FERNANDO', 'RICARDO', 'ROBERTO', 'EDGAR', 'MARCO',
    'CESAR', 'HECTOR', 'HUGO', 'RAUL', 'JAIME', 'DIEGO', 'DAVID', 'ANDRES',
    'MAURICIO', 'PATRICIO', 'WILSON', 'BYRON', 'MARCELO', 'GERARDO', 'HERNAN',
    'VICENTE', 'DANIEL', 'GABRIEL', 'ALEJANDRO', 'FABIAN', 'HENRY', 'EDWIN',
    'DARWIN', 'FREDDY', 'NELSON', 'RAMON', 'GUILLERMO', 'HUMBERTO', 'ISIDRO',
    'LEONARDO', 'VIRGILIO', 'MELCHOR', 'TEODORO', 'ELIAS', 'CIPRIANO', 'LENIN',
    'ISAURO', 'AMILCAR', 'ROLANDO', 'GONZALO', 'ARMANDO', 'ERNESTO', 'ROGELIO',
    'SANTIAGO', 'CRISTIAN', 'JEFFERSON', 'BLADIMIR', 'WILLIAN', 'STALYN',
    'RUBEN', 'OSCAR', 'TELMO', 'HOMERO', 'POLIVIO', 'VINICIO', 'SIXTO',
    'CLEMENTE', 'LINO', 'JACINTO', 'FELIPE', 'MARTIN', 'AURELIO', 'JOAQUIN',
}
MUJER = {
    'MARIA', 'ROSA', 'ANA', 'CARMEN', 'BLANCA', 'MARTHA', 'LAURA', 'TERESA',
    'ELENA', 'SUSANA', 'PATRICIA', 'MERCEDES', 'ISABEL', 'JUANA', 'DOLORES',
    'BEATRIZ', 'SILVIA', 'GLORIA', 'ESTHER', 'PIEDAD', 'ZOILA', 'MAIRA',
    'LORENA', 'SARA', 'CARIDAD', 'GUADALUPE', 'NORMA', 'DELIA', 'OLGA',
    'YOLANDA', 'MARIANA', 'VERONICA', 'ADRIANA', 'PAOLA', 'JESSICA', 'MONICA',
    'SANDRA', 'GLADYS', 'NANCY', 'ELSA', 'LUCIA', 'INES', 'AMPARO', 'JOSEFINA',
    'ERMELINDA', 'ERLINDA', 'ASUCENA', 'ORFELINA', 'PASTORA', 'CECILIA',
    'MARLENE', 'PAULINA', 'RICARDINA', 'ELBIA', 'ELOISA', 'FANNY', 'LEONOR',
    'CRISTINA', 'ESTELA', 'NAYELI', 'LEYDI', 'ELIZABETH', 'MARGARITA',
    'ALICIA', 'MANUELA', 'VICENTA', 'REGINA', 'NARCISA', 'ADELA', 'HORTENCIA',
    'URSULA', 'MARUJA', 'EVA', 'CANDELARIA', 'AMERICA', 'ANITA', 'LOURDES',
    'MARCELA', 'JUDITH', 'TRANSITO', 'LUISA', 'ENCARNACION', 'EMILIA',
}

# El molde: la frase ARRANCA hablando del titular. Si la observación empieza
# así, el sujeto es la persona de la ficha y el género debe concordar con su
# nombre. Lo que viene después («… A NOMBRE DEL PAPÁ») no se toca.
MOLDE = re.compile(
    r'^\s*(LA\s+COMUNERA\s+REGANTE|EL\s+COMUNERO\s+REGANTE|'
    r'LA\s+REGANTE\s+COMUNERA|EL\s+REGANTE\s+COMUNERO)\b', re.IGNORECASE)

A_MASCULINO = [
    (re.compile(r'^(\s*)LA\s+COMUNERA\s+REGANTE\b', re.I), r'\1EL COMUNERO REGANTE'),
    (re.compile(r'^(\s*)LA\s+REGANTE\s+COMUNERA\b', re.I), r'\1EL REGANTE COMUNERO'),
    # Si la plantilla venía en femenino, el cónyuge también quedó cambiado:
    # un varón cuyo predio está «a nombre del esposo» es la misma errata, solo
    # que en la otra mitad de la frase. Corregir una sin la otra deja el texto
    # peor que como estaba.
    (re.compile(r'\bA\s+NOMBRE\s+DEL\s+ESPOSO\b', re.I), 'A NOMBRE DE LA ESPOSA'),
]
A_FEMENINO = [
    (re.compile(r'^(\s*)EL\s+COMUNERO\s+REGANTE\b', re.I), r'\1LA COMUNERA REGANTE'),
    (re.compile(r'^(\s*)EL\s+REGANTE\s+COMUNERO\b', re.I), r'\1LA REGANTE COMUNERA'),
    (re.compile(r'\bA\s+NOMBRE\s+DE\s+LA\s+ESPOSA\b', re.I), 'A NOMBRE DEL ESPOSO'),
]
# concordancia suelta que trae la misma plantilla
GRAMATICA = [(re.compile(r'\bA\s+NOMBRE\s+DEL\s+ESPOSA\b', re.I), 'A NOMBRE DE LA ESPOSA')]


def sinac(s):
    s = unicodedata.normalize('NFKD', str(s or '').strip().upper())
    return ''.join(c for c in s if not unicodedata.combining(c))


def sexo(nombres):
    for tok in sinac(nombres).split():
        if tok in VARON:
            return 'H'
        if tok in MUJER:
            return 'M'
    return None


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
    print(' CORRECCIONES DEL TECNICO (18-ago)' +
          ('  [APLICAR]' if args.aplicar else '  [SIMULACION - no escribe nada]'))
    print('=' * 80)

    con = sqlite3.connect(GPKG)
    cur = con.cursor()

    print('\n  [1] LAS CUATRO FICHAS PUNTUALES')
    puntuales = []
    for clave, campo, valor, motivo in PUNTUALES:
        cur.execute('SELECT id, TRIM(COALESCE(apellidos,\'\')||\' \'||COALESCE(nombres,\'\')), '
                    '{} FROM "{}" WHERE clave_catastral = ?'.format(campo, TABLA), (clave,))
        fila = cur.fetchone()
        if not fila:
            print('     {} · NO ENCONTRADA'.format(clave))
            continue
        uid, quien, actual = fila
        if (actual or '') == (valor or ''):
            print('     {} · {} · ya estaba'.format(clave, quien[:32]))
            continue
        print('     {} · {}'.format(clave, quien[:34]))
        print('        {}: {!r} -> {!r}'.format(campo, actual, valor))
        print('        motivo: {}'.format(motivo))
        puntuales.append((uid, campo, valor))

    print('\n  [2] GENERO EN EL MOLDE DE LA PLANTILLA')
    cur.execute('SELECT id, TRIM(COALESCE(apellidos,\'\')), TRIM(COALESCE(nombres,\'\')), '
                'clave_catastral, observaciones FROM "{}" '
                'WHERE TRIM(COALESCE(observaciones,\'\')) <> \'\''.format(TABLA))
    generos = []
    for uid, ape, nom, clave, obs in cur.fetchall():
        if not MOLDE.match(obs or ''):
            continue
        s = sexo(nom)
        if s is None:
            continue
        nuevo = obs
        for rx, rep in (A_MASCULINO if s == 'H' else A_FEMENINO):
            nuevo = rx.sub(rep, nuevo)
        for rx, rep in GRAMATICA:
            nuevo = rx.sub(rep, nuevo)
        if nuevo != obs:
            generos.append((uid, clave, '{} {}'.format(ape, nom).strip(), s, obs, nuevo))

    print('     fichas con el molde y el genero cruzado: {}'.format(len(generos)))
    for _uid, clave, quien, s, obs, nuevo in generos:
        print('\n        {} · {} · {}'.format(clave, quien[:34],
                                              'VARON' if s == 'H' else 'MUJER'))
        print('           antes  : {}'.format(obs.strip()[:110]))
        print('           despues: {}'.format(nuevo.strip()[:110]))

    # Pablo Robalino: su observación no arranca con el molde exacto, va aparte
    print('\n  [3] PABLO LENIN ROBALINO — el caso que destapo todo')
    cur.execute('SELECT id, observaciones FROM "{}" WHERE cedula = ?'.format(TABLA),
                ('1713466942',))
    fila = cur.fetchone()
    pablo = None
    if fila:
        uid, obs = fila
        nuevo = obs or ''
        for rx, rep in A_MASCULINO:
            nuevo = rx.sub(rep, nuevo)
        for rx, rep in GRAMATICA:
            nuevo = rx.sub(rep, nuevo)
        if nuevo != (obs or ''):
            pablo = (uid, nuevo)
            print('        antes  : {}'.format((obs or '').strip()[:130]))
            print('        despues: {}'.format(nuevo.strip()[:130]))
        else:
            print('        ya estaba correcta')

    total = len(puntuales) + len(generos) + (1 if pablo else 0)
    print('\n' + '=' * 80)
    print('  fichas a corregir: {}'.format(total))

    if not args.aplicar:
        print('\n  SIMULACION: no se escribio nada. Para aplicarlo:  --aplicar')
        print('=' * 80)
        con.close()
        return

    if not total:
        print('  Nada que aplicar.')
        con.close()
        return

    print('\n  respaldando antes de tocar nada...')
    print('     {}'.format(respaldo_sqlite(GPKG, 'antes-correcciones-tecnico')))

    cur.execute("SELECT name, sql FROM sqlite_master WHERE type='trigger' AND tbl_name=?",
                (TABLA,))
    triggers = cur.fetchall()
    for nombre, _ in triggers:
        cur.execute('DROP TRIGGER IF EXISTS "{}"'.format(nombre))
    n = 0
    try:
        for uid, campo, valor in puntuales:
            cur.execute('UPDATE "{}" SET {} = ? WHERE id = ?'.format(TABLA, campo),
                        (valor, uid))
            n += cur.rowcount
        for uid, _clave, _quien, _s, _obs, nuevo in generos:
            cur.execute('UPDATE "{}" SET observaciones = ? WHERE id = ?'.format(TABLA),
                        (nuevo, uid))
            n += cur.rowcount
        if pablo:
            cur.execute('UPDATE "{}" SET observaciones = ? WHERE id = ?'.format(TABLA),
                        (pablo[1], pablo[0]))
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
    cur.execute('SELECT material_construccion FROM "{}" WHERE clave_catastral=?'.format(TABLA),
                ('1702521730053',))
    print('\n  VERIFICACION (releyendo del disco):')
    print('     Maria Caridad · material_construccion = {!r}'.format(cur.fetchone()[0]))
    cur.execute('SELECT tenencia_predio FROM "{}" WHERE clave_catastral=?'.format(TABLA),
                ('1702521730025',))
    print('     Maria Guadalupe · tenencia = {!r}'.format(cur.fetchone()[0]))
    cur.execute('SELECT observaciones FROM "{}" WHERE cedula=?'.format(TABLA), ('1713466942',))
    print('     Pablo Robalino · obs = {!r}'.format((cur.fetchone()[0] or '')[:90]))
    con.close()
    print('\n  Siguiente: regenerar capas e informes.')


if __name__ == '__main__':
    main()
