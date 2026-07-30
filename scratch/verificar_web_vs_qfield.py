# -*- coding: utf-8 -*-
"""
Verifica que el sitio PUBLICADO refleje exactamente el GeoPackage de QField.

Por que existe: firebase.json publica la carpeta dist/, y Vite solo copia
public/geo/ -> dist/geo/ durante `npm run build`. Un deploy sin build previo
sirve datos viejos. Comprobar los archivos locales NO prueba nada sobre
produccion: hay que descargar lo que Firebase esta sirviendo y contarlo.

Uso:  python -X utf8 padron-app/scratch/verificar_web_vs_qfield.py
"""
import json
import sqlite3
import sys
import tempfile
import time
import os
from urllib.request import urlopen

DB = r"C:\Users\HP\QField\cloud\porotog_levantamiento_offline\data.gpkg"
BASE_URL = "https://invs-riego-comunitario.web.app/geo"


def del_gpkg():
    con = sqlite3.connect("file:{}?mode=ro".format(DB), uri=True)
    cur = con.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tabs = [t[0] for t in cur.fetchall()]
    ft = next(t for t in tabs if 'Fichas_Predios' in t
              and not any(x in t for x in ('rtree_', 'log_', 'gpkg_')))
    cur.execute('SELECT COUNT(*) FROM "{}"'.format(ft))
    total = cur.fetchone()[0]
    cur.execute('SELECT COUNT(*) FROM "{}" WHERE es_ficha_hija IN (1)'.format(ft))
    hijas = cur.fetchone()[0]
    cur.execute('SELECT COUNT(*) FROM "{}" WHERE es_ficha_hija IN (1) '
                'AND estado_investigacion=?'.format(ft), ('completada',))
    compl = cur.fetchone()[0]
    cur.execute('SELECT COUNT(*) FROM "{}" WHERE comunidad=?'.format(ft), ('ALPAKA',))
    alpaka = cur.fetchone()[0]
    con.close()
    return {"total": total, "hijas": hijas, "compl": compl, "alpaka": alpaka}


def bajar(nombre):
    url = "{}/{}?t={}".format(BASE_URL, nombre, int(time.time() * 1000))
    destino = os.path.join(tempfile.gettempdir(), "verif_" + nombre)
    with urlopen(url, timeout=300) as r, open(destino, "wb") as f:
        f.write(r.read())
    with open(destino, encoding="utf-8") as f:
        return json.load(f)


print("Descargando lo que Firebase esta sirviendo...")
fic = bajar("fichas_predios.geojson")["features"]
cat = bajar("catastro_geo.geojson")["features"]

props = [f["properties"] for f in fic]
hijas = [p for p in props if p.get("es_ficha_hija") in (1, True)]
compl = [p for p in hijas if p.get("estado_investigacion") == 'completada']
alp = [p for p in props if str(p.get("comunidad") or "").upper().strip() == "ALPAKA"]
claves = {str((f.get("properties") or {}).get("clave_cata") or "").strip()
          for f in cat if f.get("geometry")}
alp_con_pol = sum(1 for p in alp if str(p.get("clave_catastral") or "").strip() in claves)
# Una hija sin ficha_madre_id solo es un problema si su madre EXISTE en el
# padron (vinculo perdido, p.ej. por un widget que lo borra al guardar). Si la
# madre fue eliminada en campo, el vinculo vacio refleja la realidad.
ids_fichas = {p.get("id") for p in props}
madres_ref = {p.get("ficha_madre_id") for p in hijas if p.get("ficha_madre_id")}
sin_madre = sum(1 for p in hijas if not p.get("ficha_madre_id"))
# recuperable = alguna declaracion de Seccion 7 apunta a esta hija
adic = bajar("predios_adicionales.json")
mapa_pa = {a.get("ficha_hija_generada_id"): a.get("ficha_id")
           for a in adic if a.get("ficha_hija_generada_id")}
sin_madre_recuperable = sum(
    1 for p in hijas
    if not p.get("ficha_madre_id")
    and mapa_pa.get(p.get("id")) in ids_fichas)

g = del_gpkg()
print()
print("{:<28}{:>10}{:>14}".format("", "QField", "Publicado"))
filas = [
    ("Fichas totales", g["total"], len(props)),
    ("Fichas adicionales", g["hijas"], len(hijas)),
    ("Adicionales completadas", g["compl"], len(compl)),
    ("Fichas de ALPAKA", g["alpaka"], len(alp)),
]
fallos = []
for nom, a, b in filas:
    marca = "  OK" if a == b else "  <-- DIFIERE"
    if a != b:
        fallos.append(nom)
    print("{:<28}{:>10}{:>14}{}".format(nom, a, b, marca))

print()
print("Poligonos servidos             :", len(cat))
print("ALPAKA con poligono en el mapa : {} de {}".format(alp_con_pol, len(alp)))
print("Adicionales sin ficha madre    : {} ({} recuperables — el resto tiene "
      "la madre eliminada en campo)".format(sin_madre, sin_madre_recuperable))

if alp_con_pol != len(alp):
    fallos.append("poligonos de ALPAKA")
if sin_madre_recuperable:
    fallos.append("vinculo madre-hija (correr scratch/restaurar_ficha_madre.py)")

print()
if fallos:
    print("REVISAR -> no coincide:", ", ".join(fallos))
    print("Si faltan poligonos de ALPAKA: corre corregir_claves_alpaka_v2.py,")
    print("regenera con scripts/export_geojson.py, y repite build + deploy.")
    sys.exit(1)

print("OK - el sitio publicado refleja exactamente el GeoPackage de QField.")
