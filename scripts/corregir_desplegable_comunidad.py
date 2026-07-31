# -*- coding: utf-8 -*-
"""
Quita la causa de que QField borre la comunidad, y numera el desplegable según
el listado oficial de Armando.

EL PROBLEMA
-----------
El desplegable de `comunidad` filtraba con:

    "sector_investigacion" = current_value('sector_investigacion')

`current_value()` lee lo que el técnico tiene en pantalla en ese momento. Cuando
QField no logra resolverlo al guardar, en vez de conservar el valor escribe
NULL. Acumulado: 553 fichas adicionales se quedaron sin comunidad, y el mismo
patrón borró 375 fichas en su día.

LA SOLUCIÓN
-----------
Se retira el filtro dinámico y en su lugar el desplegable muestra las 50
comunidades numeradas como en el documento "SECTORES Y COMUNIDADES":

    01. LARCACHACA
    ...
    36. OTONCITO
    37. PAMBAMARQUITO

Quedan agrupadas por sector igual que en el listado (01-22 Sector 1,
23-35 Sector 2, 36-50 Sector 3) y el técnico las filtra escribiendo el número o
el nombre. Sin `current_value()` no hay nada que QField pueda dejar sin resolver.

El número va con DOS DÍGITOS para que el orden alfabético coincida con el
numérico ('09' antes que '10'); si no, QField pondría la 10 antes que la 2.

QUÉ TOCA
--------
1. data.gpkg → Comunidades_Sectores: añade la columna `n` y alinea el contenido
   con el listado oficial (quita ASOCIACIÓN ROSALÍA del Sector 2 y SR. COLOMA,
   corrige PANBAMAQUITO y renombra MONTESERÍN BAJO).
2. .qgs → el ValueRelation de `comunidad`: sin FilterExpression y mostrando
   `n. comunidad`.

Simula por defecto. Escribe con --aplicar, con respaldo previo.
"""

import os
import re
import shutil
import sqlite3
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from respaldo_seguro import respaldar  # noqa: E402

QFIELD = r"C:\Users\HP\QField\cloud\porotog_levantamiento_offline"
GPKG = os.path.join(QFIELD, 'data.gpkg')
QGS = os.path.join(QFIELD, 'POROTOG LEVANTAMIENTO_qfield_cloud.qgs')

# Listado oficial: número → (sector, nombre tal como debe quedar en el gpkg).
# Los nombres son los que usan las fichas, no los abreviados del documento.
OFICIAL = [
    (1, 'Sector 1', 'LARCACHACA'), (2, 'Sector 1', 'LA LIBERTAD'),
    (3, 'Sector 1', 'SAN ANTONIO'), (4, 'Sector 1', 'SAN JOSÉ'),
    (5, 'Sector 1', 'MILAGRO'), (6, 'Sector 1', 'CHAMBITOLA'),
    (7, 'Sector 1', 'LA CANDELARIA'), (8, 'Sector 1', 'CARRERA'),
    (9, 'Sector 1', 'COCHAPAMBA'), (10, 'Sector 1', 'JESÚS GRAN PODER'),
    (11, 'Sector 1', 'SANTA BÁRBARA'), (12, 'Sector 1', 'ASOCIACIÓN POROTOG'),
    (13, 'Sector 1', 'COMUNA POROTOG'), (14, 'Sector 1', 'ASOCIACIÓN 17 DE JUNIO'),
    (15, 'Sector 1', 'AVELLANEDA'), (16, 'Sector 1', 'CORDILLERAS DE LOS ANDES'),
    (17, 'Sector 1', 'COMUNA IZACATA'), (18, 'Sector 1', 'IZACATA GRANDE'),
    (19, 'Sector 1', 'LOS ANDES IZACATA'), (20, 'Sector 1', 'LOMA GORDA'),
    (21, 'Sector 1', 'SAN JACINTO'), (22, 'Sector 1', 'MATÍAS IMBAGO'),
    (23, 'Sector 2', 'CUARTO LOTE'), (24, 'Sector 2', 'ASOC. SAN VICENTE BAJO'),
    (25, 'Sector 2', 'SANTA ROSA DE PACCHA'), (26, 'Sector 2', 'ASOC. SAN VICENTE ALTO'),
    (27, 'Sector 2', 'PUCARÁ'), (28, 'Sector 2', 'ASOCIACIÓN SAN PEDRO'),
    (29, 'Sector 2', 'PITANA ALTO'), (30, 'Sector 2', 'ALPAKA'),
    (31, 'Sector 2', 'ASOC. PITANA BAJO'), (32, 'Sector 2', 'PROMEJ. PITANA BAJO'),
    (33, 'Sector 2', 'SANTA ROSA DE PINGULMI'), (34, 'Sector 2', 'SANTA MARIANITA DE PINGULMI'),
    (35, 'Sector 2', 'PAMBAMARCA'),
    (36, 'Sector 3', 'OTONCITO'), (37, 'Sector 3', 'PAMBAMARQUITO'),
    (38, 'Sector 3', 'SR. HERNÁN TIMPE'), (39, 'Sector 3', 'HDA. SAN FRANSISCO'),
    (40, 'Sector 3', 'MONTESERRÍN ALTO'), (41, 'Sector 3', 'CHAUPIESTANCIA'),
    (42, 'Sector 3', 'PUEBLO DE OTÓN'), (43, 'Sector 3', 'CANGAHUA PUNGO'),
    (44, 'Sector 3', 'CHINCHINLOMA'), (45, 'Sector 3', 'ASOCIACIÓN ROSALÍA'),
    (46, 'Sector 3', 'SR. COLOMA MONTESERRIN BAJO'), (47, 'Sector 3', 'HDA. GUANGUILQUI'),
    (48, 'Sector 3', 'PUEBLO DE ASCÁZUBI'), (49, 'Sector 3', 'EL MANZANO'),
    (50, 'Sector 3', 'JUNTA SAN LUIS'),
    # 51 SAN VICENTE DE GUAYLLABAMBA queda fuera: no se investiga.
]

# En el .qgs las comillas simples van literales; solo se escapan las dobles.
FILTRO_VIEJO = ('<Option name="FilterExpression" type="QString" '
                'value="&quot;sector_investigacion&quot; = '
                "current_value('sector_investigacion')\"/>")
FILTRO_NUEVO = '<Option name="FilterExpression" type="QString" value=""/>'
VALOR_VIEJO = '<Option name="Value" type="QString" value="comunidad"/>'
VALOR_NUEVO = ('<Option name="Value" type="QString" '
               "value=\"concat(lpad(n, 2, '0'), '. ', comunidad)\"/>")


def main():
    aplicar = '--aplicar' in sys.argv
    print('=== Desplegable de comunidad — {} ===\n'.format(
        'APLICANDO' if aplicar else 'SIMULACIÓN (usa --aplicar)'))

    # ── 1. la tabla de referencia ──
    con = sqlite3.connect(GPKG)
    cur = con.cursor()
    cur.execute("SELECT sector_investigacion, comunidad FROM Comunidades_Sectores")
    actual = {(s, c) for s, c in cur.fetchall()}
    deseado = {(s, c) for _, s, c in OFICIAL}

    sobran = sorted(actual - deseado)
    faltan = sorted(deseado - actual)
    print(f"[data.gpkg] Comunidades_Sectores: {len(actual)} filas → {len(deseado)}")
    if sobran:
        print(f"   se quitan {len(sobran)}:")
        for s, c in sobran:
            print(f"      {s} · {c}")
    if faltan:
        print(f"   se agregan {len(faltan)}:")
        for s, c in faltan:
            print(f"      {s} · {c}")
    tiene_n = any(r[1] == 'n' for r in
                  cur.execute("PRAGMA table_info(Comunidades_Sectores)").fetchall())
    print(f"   columna `n` (número oficial): {'ya existe' if tiene_n else 'se agrega'}")

    # ── 2. el .qgs ──
    s = open(QGS, encoding='utf-8').read()
    print("\n[.qgs] widget de `comunidad`")
    ok_filtro = FILTRO_VIEJO in s
    ok_valor = VALOR_VIEJO in s
    print(f"   quitar el filtro con current_value : "
          f"{'sí' if ok_filtro else 'ya estaba quitado' }")
    print(f"   mostrar `01. LARCACHACA`           : "
          f"{'sí' if ok_valor else 'ya estaba puesto'}")
    if not aplicar:
        con.close()
        print("\nSIMULACIÓN — nada se escribió.")
        return

    # ── escribir gpkg ──
    copia = respaldar(GPKG)
    print(f"\n   respaldo: {os.path.basename(copia)}")
    if not tiene_n:
        cur.execute("ALTER TABLE Comunidades_Sectores ADD COLUMN n INTEGER")
    cur.execute("DELETE FROM Comunidades_Sectores")
    cur.executemany(
        "INSERT INTO Comunidades_Sectores (n, sector_investigacion, comunidad) VALUES (?,?,?)",
        OFICIAL)
    con.commit()
    cur.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    cur.execute("SELECT COUNT(*) FROM Comunidades_Sectores")
    print(f"   ✓ tabla reescrita con {cur.fetchone()[0]} comunidades numeradas")
    con.close()

    # ── escribir qgs ──
    if ok_filtro or ok_valor:
        respaldar(QGS)
        s = s.replace(FILTRO_VIEJO, FILTRO_NUEVO, 1).replace(VALOR_VIEJO, VALOR_NUEVO, 1)
        open(QGS, 'w', encoding='utf-8', newline='\r\n').write(s)
        print("   ✓ widget actualizado en el proyecto")

    print("\n   Verificar con: python-qgis scripts/verificar_formulario_adicional.py")


if __name__ == '__main__':
    main()
