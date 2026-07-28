# -*- coding: utf-8 -*-
"""
Verifica si las 492 fichas de ALPAKA conservan su clave catastral en el
GeoPackage de QField.

CUÁNDO USARLO: siempre DESPUÉS de sincronizar con QFieldCloud (descarga
nube -> local) y ANTES de correr sync.bat. Una descarga desde la nube puede
traer un data.gpkg sin las claves; si en ese estado se corre sync.bat, los
GeoJSON se regeneran sin los 490 polígonos de ALPAKA y el deploy publica el
mapa web sin ellos.

SI DA "FALTAN CLAVES": volver a ejecutar scratch/corregir_claves_alpaka_v2.py
(es idempotente: solo toca las claves vacías) y luego SUBIR a QFieldCloud para
que la nube quede con la corrección y esto deje de repetirse.

Uso:  python -X utf8 padron-app/scratch/verificar_claves_alpaka.py
"""
import sqlite3
import sys

DB = r"C:\Users\HP\QField\cloud\porotog_levantamiento_offline\data.gpkg"

con = sqlite3.connect("file:{}?mode=ro".format(DB), uri=True)
cur = con.cursor()

cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
tabs = [t[0] for t in cur.fetchall()]
ft = next((t for t in tabs if 'Fichas_Predios' in t
           and not any(x in t for x in ('rtree_', 'log_', 'gpkg_'))), None)
if not ft:
    print("ERROR: no se encontro la tabla de Fichas_Predios")
    sys.exit(2)

cur.execute('SELECT COUNT(*) FROM "{}"'.format(ft))
total = cur.fetchone()[0]
cur.execute('SELECT COUNT(*) FROM "{}" WHERE comunidad=?'.format(ft), ('ALPAKA',))
alpaka = cur.fetchone()[0]
cur.execute(
    'SELECT COUNT(*) FROM "{}" WHERE comunidad=? '
    'AND (clave_catastral IS NULL OR clave_catastral=?)'.format(ft),
    ('ALPAKA', ''))
sin_clave = cur.fetchone()[0]
con.close()

print("Fichas totales en el GeoPackage :", total)
print("Fichas de ALPAKA                :", alpaka)
print("ALPAKA sin clave catastral      :", sin_clave)
print()

if sin_clave == 0 and alpaka > 0:
    print("OK - las claves de ALPAKA estan intactas. Se puede correr sync.bat.")
    sys.exit(0)

print("FALTAN CLAVES ({}). NO corras sync.bat todavia.".format(sin_clave))
print("  1) python -X utf8 padron-app/scratch/corregir_claves_alpaka_v2.py")
print("  2) vuelve a correr esta verificacion")
print("  3) sube a QFieldCloud para que la nube quede corregida")
sys.exit(1)
