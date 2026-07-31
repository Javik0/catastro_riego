# -*- coding: utf-8 -*-
"""
Arregla el desplegable de comunidad que en QField mostraba "Sector 3" repetido.

QUÉ PASÓ (2026-07-31, reportado por los técnicos con captura)
-------------------------------------------------------------
Puse una EXPRESIÓN en la opción `Value` del ValueRelation:

    concat(lpad(n, 2, '0'), '. ', comunidad)

QGIS de escritorio la evalúa, pero QFIELD NO: en ese campo espera el NOMBRE de
una columna. Al no encontrar una columna llamada así, cayó a la primera columna
de texto de la tabla — `sector_investigacion` — y el técnico veía
"Sector 3, Sector 3, Sector 3…" en vez de las comunidades.

(La clave del desplegable siguió siendo `comunidad`, así que no se guardó
basura: se verificó que ninguna ficha quedó con comunidad='Sector N'.)

LA SOLUCIÓN
-----------
La etiqueta "01. LARCACHACA" se materializa como COLUMNA REAL (`etiqueta`) en
Comunidades_Sectores, y `Value` pasa a ser simplemente ese nombre de columna.
Sin expresiones: no hay nada que QField pueda interpretar distinto que QGIS.

Simula por defecto. Escribe con --aplicar, con respaldo previo (fuera de la
carpeta de QFieldCloud).
"""

import os
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from respaldo_seguro import respaldar  # noqa: E402

QFIELD = r"C:\Users\HP\QField\cloud\porotog_levantamiento_offline"
GPKG = os.path.join(QFIELD, 'data.gpkg')
QGS = os.path.join(QFIELD, 'POROTOG LEVANTAMIENTO_qfield_cloud.qgs')

# La expresión que QField no entiende → el nombre de la columna real.
VALOR_VIEJO = ('<Option name="Value" type="QString" '
               "value=\"concat(lpad(n, 2, '0'), '. ', comunidad)\"/>")
VALOR_NUEVO = '<Option name="Value" type="QString" value="etiqueta"/>'


def main():
    aplicar = '--aplicar' in sys.argv
    print('=== Etiqueta de comunidad como columna real — {} ===\n'.format(
        'APLICANDO' if aplicar else 'SIMULACIÓN (usa --aplicar)'))

    con = sqlite3.connect(GPKG)
    cur = con.cursor()
    cols = [r[1] for r in cur.execute("PRAGMA table_info(Comunidades_Sectores)")]
    print(f"[data.gpkg] columnas: {cols}")
    print(f"   columna `etiqueta`: {'ya existe' if 'etiqueta' in cols else 'se agrega'}")

    cur.execute("SELECT n, comunidad FROM Comunidades_Sectores ORDER BY n")
    filas = cur.fetchall()
    print(f"   se etiquetan {len(filas)} comunidades: "
          f"'{filas[0][0]:02d}. {filas[0][1]}' … '{filas[-1][0]:02d}. {filas[-1][1]}'")

    s = open(QGS, encoding='utf-8').read()
    print("\n[.qgs] opción Value del desplegable")
    if VALOR_NUEVO in s:
        print("   ya apunta a la columna `etiqueta`")
    elif VALOR_VIEJO not in s:
        raise SystemExit(f"   ABORTADO: no encuentro la expresión esperada "
                         f"(aparece {s.count(VALOR_VIEJO)} veces)")
    else:
        print("   expresión → columna real `etiqueta`")

    if not aplicar:
        con.close()
        print("\nSIMULACIÓN — nada se escribió.")
        return

    print(f"\n   respaldo: {os.path.basename(respaldar(GPKG))}")
    if 'etiqueta' not in cols:
        cur.execute("ALTER TABLE Comunidades_Sectores ADD COLUMN etiqueta TEXT")
    cur.execute("UPDATE Comunidades_Sectores "
                "SET etiqueta = printf('%02d. %s', n, comunidad)")
    con.commit()
    cur.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    cur.execute("SELECT etiqueta FROM Comunidades_Sectores ORDER BY etiqueta LIMIT 3")
    print("   ✓ etiquetas escritas:", [r[0] for r in cur.fetchall()], "…")
    con.close()

    if VALOR_NUEVO not in s:
        respaldar(QGS)
        open(QGS, 'w', encoding='utf-8', newline='\r\n').write(
            s.replace(VALOR_VIEJO, VALOR_NUEVO, 1))
        print("   ✓ widget apuntando a la columna `etiqueta`")

    print("\n   Verificar: python-qgis scripts/verificar_desplegable_comunidad.py")
    print("   Después: subir a QFieldCloud y que los técnicos sincronicen.")


if __name__ == '__main__':
    main()
