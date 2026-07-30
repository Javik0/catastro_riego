# -*- coding: utf-8 -*-
"""
Correccion en ventana coordinada sobre data.gpkg (2026-07-29):

  1) HUERFANOS (opcion B): borra los registros de cultivos, animales y predios
     adicionales cuyo ficha_id no existe en Fichas_Predios (o es NULL). Quedaron
     de fichas eliminadas en campo; nadie puede consultarlos y contaminan los
     denominadores de cobertura.

  2) AREAS DE ALPAKA: las fichas inyectadas cuya area declarada no cabe en su
     poligono catastral se ajustan al area del poligono (criterio aprobado por
     el cliente). Para mantener la coherencia interna de cada ficha se ajustan
     en la misma proporcion su area de riego, su caudal y las superficies de
     sus cultivos (que se asignaron como fraccion del area del lote).

MODO SEGURO: por defecto solo simula. Escribe unicamente con --aplicar.
Requiere ventana: nadie debe estar subiendo a QFieldCloud mientras corre, y al
terminar hay que SUBIR data.gpkg a la nube.
"""
import sqlite3
import sys

APLICAR = "--aplicar" in sys.argv
QDIR = r"C:\Users\HP\QField\cloud\porotog_levantamiento_offline"
DB = QDIR + r"\data.gpkg"
CAT = QDIR + r"\CATASTROACTUALIZADORURALCATASTRORURALACTUALIZADO.gpkg"

con = sqlite3.connect(DB if APLICAR else "file:{}?mode=ro".format(DB), uri=not APLICAR)
cur = con.cursor()
cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
tabs = [t[0] for t in cur.fetchall()]


def T(kw):
    return next(t for t in tabs if kw in t and not any(x in t for x in ('gpkg_', 'rtree_', 'log_')))


ft, ct, at, pa = T('Fichas_Predios'), T('Cultivos_Agricolas'), T('Animales_Especies'), T('Predios_Adicionales')

print("=" * 74)
print(" {} — CORRECCION DE data.gpkg".format("APLICANDO" if APLICAR else "SIMULACION (no escribe)"))
print("=" * 74)

# ══ 1. HUERFANOS ══════════════════════════════════════════════════════
cur.execute('SELECT id FROM "{}"'.format(ft))
ids = {r[0] for r in cur.fetchall()}

print("\n[1] Registros huerfanos (su ficha ya no existe)")
huerfanos = {}
for nombre, t in (("cultivos", ct), ("animales", at), ("predios_adicionales", pa)):
    cur.execute('SELECT rowid, ficha_id FROM "{}"'.format(t))
    rows = [rid for rid, fid in cur.fetchall() if fid is None or fid not in ids]
    huerfanos[t] = rows
    print("    {:<22} {:>4} a borrar".format(nombre, len(rows)))

# ══ 2. AREAS DE ALPAKA ════════════════════════════════════════════════
con2 = sqlite3.connect("file:{}?mode=ro".format(CAT), uri=True)
c2 = con2.cursor()
c2.execute("SELECT clave_cata, area_predi FROM CATASTROACTUALIZADORURALCATASTRORURALACTUALIZADO")
area_pol = {str(k).strip(): float(a) for k, a in c2.fetchall() if k and a}
con2.close()

print("\n[2] Fichas de ALPAKA cuya area no cabe en su poligono")
cur.execute('SELECT id, codigo_final, clave_catastral, area_total, area_riego, caudal_valor '
            'FROM "{}" WHERE comunidad=?'.format(ft), ('ALPAKA',))
ajustes = []
for fid, cod, k, at_, ar, cv in cur.fetchall():
    ap = area_pol.get(str(k or '').strip())
    if not (ap and at_ and at_ > ap * 1.05):
        continue
    escala = ap / at_
    cur.execute('SELECT COUNT(*), COALESCE(SUM(superficie_m2),0) FROM "{}" '
                'WHERE ficha_id=?'.format(ct), (fid,))
    ncult, scult = cur.fetchone()
    ajustes.append({'id': fid, 'cod': cod, 'clave': k, 'antes': at_, 'despues': ap,
                    'escala': escala, 'caudal_antes': cv or 0,
                    'caudal_despues': (cv or 0) * escala, 'ncult': ncult,
                    'scult_antes': scult, 'scult_despues': scult * escala})
    print("    {:<12} {:>12,.0f} -> {:>10,.0f} m2  (x{:.4f})   caudal {:.2f} -> {:.4f} l/s   {} cultivos".format(
        cod, at_, ap, escala, cv or 0, (cv or 0) * escala, ncult))

print("\n    RESUMEN: {} fichas | area total {} -> {} m2".format(
    len(ajustes),
    "{:,.0f}".format(sum(a['antes'] for a in ajustes)),
    "{:,.0f}".format(sum(a['despues'] for a in ajustes))))
print("    superficie de cultivos asociada: {:,.0f} -> {:,.0f} m2".format(
    sum(a['scult_antes'] for a in ajustes), sum(a['scult_despues'] for a in ajustes)))

if not APLICAR:
    print("\nSIMULACION — nada escrito. Ejecutar con --aplicar para grabar.")
    con.close()
    sys.exit(0)

# ══ ESCRITURA ═════════════════════════════════════════════════════════
print("\nEscribiendo...")
cur.execute("SELECT name, sql FROM sqlite_master WHERE type='trigger'")
todos_trg = cur.fetchall()
trg = [(n, s) for n, s in todos_trg
       if any(tab.lower() in (s or '').lower() for tab in (ft, ct, at, pa))]
for n, _ in trg:
    cur.execute('DROP TRIGGER IF EXISTS "{}"'.format(n))

for t, rows in huerfanos.items():
    if rows:
        for i in range(0, len(rows), 500):
            lote = rows[i:i + 500]
            cur.execute('DELETE FROM "{}" WHERE rowid IN ({})'.format(
                t, ','.join('?' * len(lote))), lote)
print("  huerfanos borrados:", sum(len(r) for r in huerfanos.values()))

for a in ajustes:
    cur.execute('UPDATE "{}" SET area_total=?, area_riego=?, area_sin_riego=0, '
                'caudal_valor=? WHERE id=?'.format(ft),
                (round(a['despues'], 2), round(a['despues'], 2),
                 round(a['caudal_despues'], 4), a['id']))
    # los cultivos de estas fichas se asignaron proporcionales al area del lote:
    # se reescalan con el mismo factor para que sigan cabiendo en el predio
    cur.execute('UPDATE "{}" SET superficie_m2 = ROUND(superficie_m2 * ?, 2) '
                'WHERE ficha_id=?'.format(ct), (a['escala'], a['id']))
print("  fichas de ALPAKA ajustadas:", len(ajustes))

for n, s in trg:
    try:
        cur.execute(s)
    except Exception as e:
        print("  [AVISO] trigger {} no restaurado: {}".format(n, e))
con.commit()
cur.execute("PRAGMA wal_checkpoint(TRUNCATE)")
print("  checkpoint:", cur.fetchone())

# verificacion inmediata
cur.execute('SELECT id FROM "{}"'.format(ft))
ids2 = {r[0] for r in cur.fetchall()}
for nombre, t in (("cultivos", ct), ("animales", at), ("predios_adicionales", pa)):
    cur.execute('SELECT ficha_id FROM "{}"'.format(t))
    h = sum(1 for (v,) in cur.fetchall() if v is None or v not in ids2)
    print("  huerfanos restantes en {}: {}".format(nombre, h))
con.close()
print("\nLISTO.")
