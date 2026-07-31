# -*- coding: utf-8 -*-
"""
Correcciones al proyecto de campo — VENTANA COORDINADA (2026-07-31).

Se aplica SOLO cuando los técnicos ya sincronizaron y antes de subir el
proyecto a QFieldCloud. QFieldSync reemplaza archivos completos: si alguien
sincroniza entre medias, se pierde su trabajo.

QUÉ CORRIGE
-----------
Contra el listado oficial "GUANGUILQUI - POROTOG · SECTORES Y COMUNIDADES"
que envió Armando:

1. data.gpkg → tabla Comunidades_Sectores (la que filtra el desplegable de
   comunidad por sector en el formulario):
     · ASOCIACIÓN ROSALÍA sale del Sector 2 — Armando la ubica en el 3 (#45)
       y sus 47 fichas son de campo del Sector 3
     · SR. COLOMA se elimina — no figura en el listado y no tiene fichas
     · PANBAMAQUITO → PAMBAMARQUITO (#37), estaba mal escrito
     · MONTESERÍN BAJO → SR. COLOMA MONTESERRIN BAJO (#46)

2. data.gpkg → campo `comunidad` de las fichas: se renombra Monteserrín Bajo
   para que coincida con el listado y con lo que ya muestra la web.

3. .qgs → texto del desplegable "ID de Ficha Madre": se añade la clave
   catastral, para poder buscar al regante también por su predio y no solo
   por apellidos o cédula.

Simula por defecto. Escribe con --aplicar, haciendo respaldo antes.
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
T_FICHAS = 'Fichas_Predios_880eb10d_d887_4fc6_99a2_8af3ac63877e'

VIEJO_MB, NUEVO_MB = 'MONTESERÍN BAJO', 'SR. COLOMA MONTESERRIN BAJO'

VALOR_VIEJO = ("concat(&quot;apellidos&quot;, ' ', &quot;nombres&quot;, ' — CI ', "
               "coalesce(&quot;cedula&quot;, 's/n'))")
VALOR_NUEVO = ("concat(&quot;apellidos&quot;, ' ', &quot;nombres&quot;, ' — CI ', "
               "coalesce(&quot;cedula&quot;, 's/n'), ' — ', "
               "coalesce(&quot;clave_catastral&quot;, 'sin clave'))")


def main():
    aplicar = '--aplicar' in sys.argv
    modo = 'APLICANDO' if aplicar else 'SIMULACIÓN (usa --aplicar para escribir)'
    print(f"=== Correcciones al proyecto de campo — {modo} ===\n")

    # ── 1 y 2: data.gpkg ──
    con = sqlite3.connect(GPKG)
    cur = con.cursor()

    print("[data.gpkg] Comunidades_Sectores")
    cur.execute("SELECT COUNT(*) FROM Comunidades_Sectores")
    print(f"    {cur.fetchone()[0]} filas antes")

    acciones = [
        ("ASOCIACIÓN ROSALÍA fuera del Sector 2",
         "DELETE FROM Comunidades_Sectores "
         "WHERE comunidad = 'ASOCIACIÓN ROSALÍA' AND sector_investigacion = 'Sector 2'"),
        ("SR. COLOMA eliminada (no está en el listado oficial)",
         "DELETE FROM Comunidades_Sectores WHERE comunidad = 'SR. COLOMA'"),
        ("PANBAMAQUITO → PAMBAMARQUITO",
         "UPDATE Comunidades_Sectores SET comunidad = 'PAMBAMARQUITO' "
         "WHERE comunidad = 'PANBAMAQUITO'"),
        (f"{VIEJO_MB} → {NUEVO_MB}",
         f"UPDATE Comunidades_Sectores SET comunidad = '{NUEVO_MB}' "
         f"WHERE comunidad = '{VIEJO_MB}'"),
    ]
    for etiqueta, sql in acciones:
        cur.execute(sql.replace('DELETE FROM', 'SELECT COUNT(*) FROM', 1)
                    if sql.startswith('DELETE')
                    else re.sub(r'UPDATE (\S+) SET .*? WHERE', r'SELECT COUNT(*) FROM \1 WHERE', sql, flags=re.S))
        n = cur.fetchone()[0]
        print(f"    {n:>3} fila(s) · {etiqueta}")
        if aplicar and n:
            cur.execute(sql)

    print(f"\n[data.gpkg] campo `comunidad` de las fichas")
    cur.execute(f'SELECT COUNT(*) FROM "{T_FICHAS}" WHERE comunidad = ?', (VIEJO_MB,))
    n_fichas = cur.fetchone()[0]
    print(f"    {n_fichas:>3} ficha(s) · {VIEJO_MB} → {NUEVO_MB}")
    if aplicar and n_fichas:
        # Los triggers del índice espacial llaman a ST_IsEmpty, que SQLite puro
        # no trae. Se retiran mientras dura el UPDATE y se recrean tal cual.
        cur.execute("SELECT name, sql FROM sqlite_master "
                    "WHERE type='trigger' AND tbl_name=?", (T_FICHAS,))
        triggers = cur.fetchall()
        for nombre, _ in triggers:
            cur.execute(f'DROP TRIGGER IF EXISTS "{nombre}"')
        try:
            cur.execute(f'UPDATE "{T_FICHAS}" SET comunidad = ? WHERE comunidad = ?',
                        (NUEVO_MB, VIEJO_MB))
        finally:
            for _, sql in triggers:
                if sql:
                    cur.execute(sql)
            print(f"    ({len(triggers)} triggers espaciales retirados y recreados)")

    if aplicar:
        con.commit()
        cur.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        con.close()
        print(f"    ✓ respaldo: {os.path.basename(respaldar(GPKG))}")
        # verificación releyendo del disco
        c2 = sqlite3.connect(GPKG); k = c2.cursor()
        k.execute("SELECT sector_investigacion, COUNT(*) FROM Comunidades_Sectores GROUP BY 1")
        print("    tras aplicar:", dict(k.fetchall()))
        k.execute(f'SELECT COUNT(*) FROM "{T_FICHAS}" WHERE comunidad = ?', (NUEVO_MB,))
        print(f"    fichas con el nombre nuevo: {k.fetchone()[0]}")
        c2.close()
    else:
        con.close()

    # ── 3: .qgs ──
    print(f"\n[.qgs] texto del desplegable 'ID de Ficha Madre'")
    s = open(QGS, encoding='utf-8').read()
    if VALOR_NUEVO in s:
        print("    ya incluye la clave catastral; nada que hacer")
    elif s.count(VALOR_VIEJO) != 1:
        print(f"    ⚠ ABORTADO: la expresión aparece {s.count(VALOR_VIEJO)} veces (se esperaba 1)")
    else:
        print("    se añade la clave catastral para poder buscar también por predio")
        if aplicar:
            respaldar(QGS)
            open(QGS, 'w', encoding='utf-8', newline='\r\n').write(
                s.replace(VALOR_VIEJO, VALOR_NUEVO, 1))
            print("    ✓ escrito")

    print("\nSiguiente paso:" + (
        "\n  1. python-qgis scripts/verificar_formulario_adicional.py"
        "\n  2. subir el proyecto a QFieldCloud"
        "\n  3. avisar a los técnicos que sincronicen"
        if aplicar else "\n  ejecutar con --aplicar cuando los técnicos hayan sincronizado"))


if __name__ == '__main__':
    main()
