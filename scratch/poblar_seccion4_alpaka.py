# -*- coding: utf-8 -*-
"""
Poblar la Seccion 4 (cultivos y animales) de los 490 lotes de ALPAKA y corregir
sus areas de riego y caudal.

Origen de los criterios: chat con Armando Proano (28-07-2026).
  - Cultivos ALPAKA / Sector 2: cebada, trigo, maiz, papas, habas, zambo, zapallo
  - "el 20% de los lotes estan con animales, los mas cercanos a las comunidades"
  - "2 vacas, 6 ovejas, 1 chancho y 12 cuyes"

Decisiones acordadas con el cliente:
  - Area cultivada = 80% del area del lote (20% para vivienda, caminos, linderos)
  - 2 cultivos si el lote esta bajo el area MEDIANA, 3 si esta encima (rotacion).
    Se usa la mediana y no la media porque unos pocos lotes enormes (hasta 95 ha)
    inflan la media y dejarian al 84% de los lotes con solo 2 cultivos.
  - El cultivo principal lleva el 50% del area cultivable; el resto se divide
  - Animales: los 98 lotes (20%) mas cercanos a una comunidad VECINA
  - area_riego = area real del lote; caudal repartido proporcional al area

MODO SEGURO: por defecto solo SIMULA. Para escribir hay que pasar --aplicar.

Uso:
  python -X utf8 padron-app/scratch/poblar_seccion4_alpaka.py            (simula)
  python -X utf8 padron-app/scratch/poblar_seccion4_alpaka.py --aplicar  (escribe)
"""
import json
import os
import sqlite3
import statistics
import struct
import sys
import uuid

from shapely.geometry import Point, shape
from shapely.ops import transform
from pyproj import Transformer

APLICAR = "--aplicar" in sys.argv

QDIR = r"C:\Users\HP\QField\cloud\porotog_levantamiento_offline"
DB = QDIR + r"\data.gpkg"
GEO = r"C:\Users\HP\OneDrive\Escritorio\CAYAMBE CATASTRO RIEGO\padron-app\public\geo"

CULTIVOS = [
    ("Cebada", None), ("Trigo", None), ("Maíz", None), ("Papas", None),
    ("Habas", None), ("Otros", "Zambo"), ("Otros", "Zapallo"),
]
ANIMALES = [
    ("Vacas en producción", 2), ("Ovejas / Cabras", 6),
    ("Porcino (Chanchos)", 1), ("Cuyes / Conejos", 12),
]
FRAC_CULTIVABLE = 0.80
FRAC_PRINCIPAL = 0.50
PCT_CON_ANIMALES = 0.20

to_utm = Transformer.from_crs("EPSG:4326", "EPSG:32717", always_xy=True)


def parse_header(blob):
    if not blob or blob[:2] != b'GP':
        return 0
    return 8 + {0: 0, 1: 32, 2: 48, 3: 48, 4: 64}.get((blob[3] >> 1) & 0x07, 0)


def tabla(cur, kw):
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tabs = [t[0] for t in cur.fetchall()]
    return next(t for t in tabs if kw in t and not any(x in t for x in ('gpkg_', 'rtree_', 'log_')))


con = sqlite3.connect(DB)
cur = con.cursor()
ft, ct, at = tabla(cur, 'Fichas_Predios'), tabla(cur, 'Cultivos_Agricolas'), tabla(cur, 'Animales_Especies')

cur.execute('SELECT id, codigo_final, area_total, area_riego, caudal_valor, geom FROM "{}" '
            'WHERE comunidad=? AND codigo_final LIKE ?'.format(ft), ('ALPAKA', 'LOTE%'))
lotes = []
for fid, cod, area, ariego, caudal, blob in cur.fetchall():
    wkb = blob[parse_header(blob):]
    fmt = '<' if wkb[0] == 1 else '>'
    x, y = struct.unpack('{}dd'.format(fmt), wkb[5:21])
    lotes.append({"id": fid, "cod": cod, "area": area or 0.0,
                  "area_riego_old": ariego or 0.0, "caudal_old": caudal or 0.0,
                  "pt": Point(*to_utm.transform(x, y))})

lotes.sort(key=lambda L: L["cod"])
area_total_conj = sum(L["area"] for L in lotes)
area_media = area_total_conj / len(lotes)
area_corte = statistics.median([L["area"] for L in lotes])  # mediana: reparto 50/50
CAUDAL_SISTEMA = lotes[0]["caudal_old"]  # 18.5 l/s declarados en cada lote

# ── distancia a comunidades vecinas ──
d = json.load(open(GEO + r"\comunidades.geojson", encoding="utf-8"))
vecinas = []
for f in d["features"]:
    nom = str((f.get("properties") or {}).get("comunidad") or "").upper().strip()
    if nom == "ALPAKA" or not f.get("geometry"):
        continue
    try:
        vecinas.append(transform(lambda x, y, z=None: to_utm.transform(x, y), shape(f["geometry"])))
    except Exception:
        pass
for L in lotes:
    L["d"] = min(L["pt"].distance(g) for g in vecinas)

n_animales = round(len(lotes) * PCT_CON_ANIMALES)
con_animales = set(L["id"] for L in sorted(lotes, key=lambda L: L["d"])[:n_animales])
corte = sorted(L["d"] for L in lotes)[n_animales - 1]

# ── construir los registros ──
cultivos_new, animales_new, updates = [], [], []
for i, L in enumerate(lotes):
    n_cult = 2 if L["area"] < area_corte else 3
    sel = [CULTIVOS[(i + k) % len(CULTIVOS)] for k in range(n_cult)]
    cultivable = L["area"] * FRAC_CULTIVABLE
    princ = cultivable * FRAC_PRINCIPAL
    resto = (cultivable - princ) / (n_cult - 1)
    for k, (tipo, otro) in enumerate(sel):
        cultivos_new.append({
            "id_cultivo": "{" + str(uuid.uuid4()) + "}", "ficha_id": L["id"],
            "tipo_cultivo": tipo, "tipo_cultivo_otro": otro,
            "superficie_m2": round(princ if k == 0 else resto, 2),
            "es_principal": 1 if k == 0 else 0, "es_autoconsumo": 1,
        })
    if L["id"] in con_animales:
        for esp, cant in ANIMALES:
            animales_new.append({
                "id_animal": "{" + str(uuid.uuid4()) + "}", "ficha_id": L["id"],
                "especie": esp, "cantidad": cant, "es_autoconsumo": 1,
            })
    updates.append({
        "id": L["id"], "area_riego": round(L["area"], 2), "area_sin_riego": 0.0,
        "caudal": round(CAUDAL_SISTEMA * L["area"] / area_total_conj, 4),
    })

# ── informe ──
print("=" * 74)
print(" {} — SECCION 4 DE ALPAKA".format("APLICANDO" if APLICAR else "SIMULACION (no escribe)"))
print("=" * 74)
print("\nLotes: {}   area total {:,.0f} m2 ({:.1f} ha)".format(
    len(lotes), area_total_conj, area_total_conj / 10000))
print("Corte 2 vs 3 cultivos: MEDIANA {:,.0f} m2 (media {:,.0f} m2, no usada)".format(
    area_corte, area_media))

print("\n--- CORRECCION DE AREAS Y CAUDAL ---")
print("  area_riego  : {:>15,.0f} ha  ->  {:>10,.1f} ha".format(
    sum(L["area_riego_old"] for L in lotes) / 10000, sum(u["area_riego"] for u in updates) / 10000))
print("  caudal total: {:>15,.1f} l/s ->  {:>10,.1f} l/s".format(
    sum(L["caudal_old"] for L in lotes), sum(u["caudal"] for u in updates)))

print("\n--- CULTIVOS ---")
print("  registros a crear:", len(cultivos_new))
print("  superficie sembrada: {:,.0f} m2 ({:.1f} ha) = {:.0f}% del area".format(
    sum(c["superficie_m2"] for c in cultivos_new),
    sum(c["superficie_m2"] for c in cultivos_new) / 10000, FRAC_CULTIVABLE * 100))
import collections
rep = collections.Counter((c["tipo_cultivo_otro"] or c["tipo_cultivo"]) for c in cultivos_new)
for k, v in rep.most_common():
    sup = sum(c["superficie_m2"] for c in cultivos_new
              if (c["tipo_cultivo_otro"] or c["tipo_cultivo"]) == k)
    print("     {:<10} {:>4} lotes   {:>10,.0f} m2".format(k, v, sup))
print("  lotes con 2 cultivos: {} | con 3: {}".format(
    sum(1 for L in lotes if L["area"] < area_corte),
    sum(1 for L in lotes if L["area"] >= area_corte)))

print("\n--- ANIMALES ---")
print("  lotes seleccionados: {} ({:.0f}%) — corte a {:.0f} m de una comunidad vecina".format(
    n_animales, 100 * n_animales / len(lotes), corte))
print("  registros a crear:", len(animales_new))
for esp, cant in ANIMALES:
    print("     {:<22} {:>4} x {:>3} = {:>6} cabezas".format(esp, n_animales, cant, n_animales * cant))

if not APLICAR:
    print("\n" + "=" * 74)
    print(" SIMULACION — no se escribio nada. Ejecutar con --aplicar para grabar.")
    print("=" * 74)
    con.close()
    sys.exit(0)

# ── escritura ──
print("\nEscribiendo...")
cur.execute("SELECT name, sql FROM sqlite_master WHERE type='trigger'")
trg = [(n, s) for n, s in cur.fetchall() if ft.lower() in (s or '').lower()]
for n, _ in trg:
    cur.execute('DROP TRIGGER IF EXISTS "{}"'.format(n))

cur.execute('DELETE FROM "{}" WHERE ficha_id IN (SELECT id FROM "{}" '
            'WHERE comunidad=? AND codigo_final LIKE ?)'.format(ct, ft), ('ALPAKA', 'LOTE%'))
print("  cultivos previos borrados:", cur.rowcount)
cur.execute('DELETE FROM "{}" WHERE ficha_id IN (SELECT id FROM "{}" '
            'WHERE comunidad=? AND codigo_final LIKE ?)'.format(at, ft), ('ALPAKA', 'LOTE%'))
print("  animales previos borrados:", cur.rowcount)

for c in cultivos_new:
    cur.execute('INSERT INTO "{}" (id_cultivo, ficha_id, tipo_cultivo, tipo_cultivo_otro, '
                'superficie_m2, es_principal, es_autoconsumo) VALUES (?,?,?,?,?,?,?)'.format(ct),
                (c["id_cultivo"], c["ficha_id"], c["tipo_cultivo"], c["tipo_cultivo_otro"],
                 c["superficie_m2"], c["es_principal"], c["es_autoconsumo"]))
for a in animales_new:
    cur.execute('INSERT INTO "{}" (id_animal, ficha_id, especie, cantidad, es_autoconsumo) '
                'VALUES (?,?,?,?,?)'.format(at),
                (a["id_animal"], a["ficha_id"], a["especie"], a["cantidad"], a["es_autoconsumo"]))
for u in updates:
    cur.execute('UPDATE "{}" SET area_riego=?, area_sin_riego=?, caudal_valor=? '
                'WHERE id=?'.format(ft), (u["area_riego"], u["area_sin_riego"], u["caudal"], u["id"]))

for n, s in trg:
    try:
        cur.execute(s)
    except Exception as e:
        print("  [AVISO] trigger {} no restaurado: {}".format(n, e))
con.commit()
cur.execute("PRAGMA wal_checkpoint(TRUNCATE)")
print("  checkpoint:", cur.fetchone())
con.close()

# ── log de auditoria: queda constancia de que se asigno y con que criterio ──
por_ficha = {L["id"]: L for L in lotes}
log = {
    "generado_por": "scratch/poblar_seccion4_alpaka.py",
    "fuente_criterios": "chat con Armando Proano, 28-07-2026",
    "criterios": {
        "cultivos": [c[1] or c[0] for c in CULTIVOS],
        "area_cultivada_pct": FRAC_CULTIVABLE * 100,
        "area_cultivo_principal_pct": FRAC_PRINCIPAL * 100,
        "corte_2_vs_3_cultivos_m2": round(area_corte, 2),
        "animales_por_lote": {e: c for e, c in ANIMALES},
        "pct_lotes_con_animales": PCT_CON_ANIMALES * 100,
        "criterio_animales": "los {} lotes mas cercanos a una comunidad VECINA "
                             "(comunidades.geojson, excluyendo ALPAKA); corte a "
                             "{:.0f} m".format(n_animales, corte),
        "correccion_areas": "area_riego = area real del lote; caudal del sistema "
                            "({} l/s) repartido proporcional al area".format(CAUDAL_SISTEMA),
    },
    "como_identificarlos": "comunidad='ALPAKA' AND codigo_final LIKE 'LOTE %'",
    "totales": {
        "lotes": len(lotes), "cultivos": len(cultivos_new), "animales": len(animales_new),
        "superficie_sembrada_m2": round(sum(c["superficie_m2"] for c in cultivos_new), 2),
    },
    "detalle": [
        {
            "codigo": por_ficha[c["ficha_id"]]["cod"], "ficha_id": c["ficha_id"],
            "cultivo": c["tipo_cultivo_otro"] or c["tipo_cultivo"],
            "superficie_m2": c["superficie_m2"], "es_principal": c["es_principal"],
        } for c in cultivos_new
    ],
    "lotes_con_animales": sorted(por_ficha[i]["cod"] for i in con_animales),
}
carpeta = os.path.join(os.path.dirname(__file__), "..", "..", "logs_depuracion")
os.makedirs(carpeta, exist_ok=True)
ruta = os.path.abspath(os.path.join(carpeta, "seccion4_alpaka_asignada.json"))
with open(ruta, "w", encoding="utf-8") as f:
    json.dump(log, f, ensure_ascii=False, indent=2)
print("  log de auditoria:", ruta)

print("\nLISTO — {} cultivos, {} animales, {} lotes actualizados.".format(
    len(cultivos_new), len(animales_new), len(updates)))
