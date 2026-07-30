# -*- coding: utf-8 -*-
"""
Reestructura el predio Monteserrin Bajo (poligono 1702510040121) segun el acta
de campo del 21/6/2026 validada con el presidente de la comunidad (30/7/2026):

  1. HACIENDA MONTESERRIN BAJO SR. COLOMA (CI 1792616743)
       80 ha con riego | 65% del caudal comunal (14,65) = 9,5225 l/s
       S4: Frutales 30 ha (arandanos, mora y zarzamora -> observaciones), caballos
  2. SR. COLOMA MONTESERRIN BAJO - COMUNIDAD (CI 1792010373)  [ficha resumen]
       120 ha con riego | 35% = 5,1275 l/s
       S4: arveja, maiz, papas, hortalizas + flores (~12,5%), 30 vacas,
       1.000 cuyes, 100 borregos, 1.200 gallinas
       -> los 118 comuneros pasan a FICHAS ADICIONALES suyas con AREA 0
          (no todos tienen la misma superficie; se contabilizan como fichas)
  3. SR. COLOMA MONTESERRIN BAJO BOSQUE PRODUCTIVO (CI 1792010373)  [nueva]
       400 ha sin riego | eucalipto y pinos
  4. SR. COLOMA MONTESERRIN BAJO PARAMO (CI 1792010373)  [nueva]
       209,38 ha sin riego (el remanente: asi las 4 fichas suman el poligono
       exacto, 8.093.825,23 m2)

MODO SEGURO: simula por defecto; escribe solo con --aplicar.
"""
import sqlite3
import struct
import sys
import uuid
from datetime import datetime, timezone

APLICAR = "--aplicar" in sys.argv
QDIR = r"C:\Users\HP\QField\cloud\porotog_levantamiento_offline"
DB = QDIR + r"\data.gpkg"
CAT = QDIR + r"\CATASTROACTUALIZADORURALCATASTRORURALACTUALIZADO.gpkg"

K = '1702510040121'
AREA_POL = 8093825.23
CAUDAL = 14.65
A_HAC, A_COM, A_BOSQ = 800000.0, 1200000.0, 4000000.0
A_PARAMO = round(AREA_POL - A_HAC - A_COM - A_BOSQ, 2)   # 2.093.825,23
C_HAC = round(CAUDAL * 0.65, 4)    # 9.5225
C_COM = round(CAUDAL * 0.35, 4)    # 5.1275
CI_HAC, CI_COM = '1792616743', '1792010373'

con = sqlite3.connect(DB if APLICAR else "file:{}?mode=ro".format(DB), uri=not APLICAR)
cur = con.cursor()
cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
tabs = [t[0] for t in cur.fetchall()]


def T(kw):
    return next(t for t in tabs if kw in t and not any(x in t for x in ('gpkg_', 'rtree_', 'log_')))


ft, ct, at = T('Fichas_Predios'), T('Cultivos_Agricolas'), T('Animales_Especies')

cur.execute('SELECT id, cedula, codigo_final, area_total FROM "{}" '
            'WHERE clave_catastral=? AND area_total > 1000000'.format(ft), (K,))
grandes = {r[1]: r[0] for r in cur.fetchall()}
id_hac, id_com = grandes.get(CI_HAC), grandes.get(CI_COM)
if not id_hac or not id_com:
    print("ERROR: no encuentro las 2 fichas grandes por cedula", grandes)
    sys.exit(1)

cur.execute('SELECT COUNT(*) FROM "{}" WHERE clave_catastral=? AND area_total<=1000000'.format(ft), (K,))
n_com = cur.fetchone()[0]

print("=" * 72)
print(" {} — REESTRUCTURACION MONTESERRIN BAJO".format("APLICANDO" if APLICAR else "SIMULACION"))
print("=" * 72)
print("  hacienda  (CI {}): id {}".format(CI_HAC, id_hac[:18]))
print("  comunidad (CI {}): id {}".format(CI_COM, id_com[:18]))
print("  comuneros a convertir en adicionales:", n_com)
print("\n  areas: hacienda {:,.0f} + comunidad {:,.0f} + bosque {:,.0f} + paramo {:,.2f}".format(
    A_HAC, A_COM, A_BOSQ, A_PARAMO))
print("       = {:,.2f}  (poligono: {:,.2f})  {}".format(
    A_HAC + A_COM + A_BOSQ + A_PARAMO, AREA_POL,
    "CIERRA EXACTO" if abs(A_HAC + A_COM + A_BOSQ + A_PARAMO - AREA_POL) < 0.01 else "NO CIERRA"))
print("  caudal: {} + {} = {}  (comunal: {})".format(C_HAC, C_COM, C_HAC + C_COM, CAUDAL))

# S4 nueva
CULT_HAC = [('Frutales', None, 300000.0, 1)]
CULT_COM = [('Maíz', None, 262500.0, 1), ('Otros', 'Arveja', 262500.0, 0),
            ('Papas', None, 262500.0, 0), ('Hortalizas', None, 262500.0, 0),
            ('Flores', None, 150000.0, 0)]
CULT_BOSQ = [('Bosque', None, A_BOSQ, 1)]
CULT_PAR = [('Monte', None, A_PARAMO, 1)]
ANIM_HAC = [('Equinos', 12)]
ANIM_COM = [('Vacas en producción', 30), ('Cuyes / Conejos', 1000),
            ('Ovejas / Cabras', 100), ('Gallinas de campo', 1200)]
print("\n  S4 comunidad suma cultivos: {:,.0f} m2 (= sus 120 ha)".format(
    sum(c[2] for c in CULT_COM)))

if not APLICAR:
    print("\nSIMULACION — nada escrito. Usar --aplicar.")
    con.close()
    sys.exit(0)

# ── puntos interiores para las 2 fichas nuevas ────────────────────────
from shapely.wkb import loads as wkb_loads
from shapely.geometry import Point
from pyproj import Transformer

con2 = sqlite3.connect("file:{}?mode=ro".format(CAT), uri=True)
c2 = con2.cursor()
c2.execute("SELECT geom FROM CATASTROACTUALIZADORURALCATASTRORURALACTUALIZADO WHERE clave_cata=?", (K,))
blob = c2.fetchone()[0]
con2.close()
flags = blob[3]
env = (flags >> 1) & 7
off = 8 + {0: 0, 1: 32, 2: 48, 3: 48, 4: 64}.get(env, 0)
poly = wkb_loads(blob[off:])
minx, miny, maxx, maxy = poly.bounds


def punto_interior(fx, fy):
    for d in (0.0, 0.02, -0.02, 0.05, -0.05):
        p = Point(minx + (maxx - minx) * (fx + d), miny + (maxy - miny) * (fy + d))
        if poly.contains(p):
            return p
    return poly.representative_point()


tr = Transformer.from_crs("epsg:32717", "epsg:4326", always_xy=True)


def geom_punto(p):
    lon, lat = tr.transform(p.x, p.y)
    return struct.pack('<2sBBi', b'GP', 0, 1, 4326) + struct.pack('<BIdd', 1, 1, lon, lat)


p_bosq, p_par = punto_interior(0.30, 0.65), punto_interior(0.70, 0.35)

# ── escritura ─────────────────────────────────────────────────────────
cur.execute("SELECT name, sql FROM sqlite_master WHERE type='trigger'")
trg = [(n, s) for n, s in cur.fetchall()
       if any(t.lower() in (s or '').lower() for t in (ft, ct, at))]
for n, _ in trg:
    cur.execute('DROP TRIGGER IF EXISTS "{}"'.format(n))

hoy = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.000Z')
NOTA = (' | Reestructurado 30/7/2026 segun acta de campo 21/6/2026 validada con el '
        'presidente de la comunidad: hacienda 80 ha riego (65% caudal), comunidad '
        '120 ha riego (35%), bosque productivo 400 ha, paramo el resto.')

# 1. hacienda
cur.execute('SELECT observaciones FROM "{}" WHERE id=?'.format(ft), (id_hac,))
obs = (cur.fetchone()[0] or '')
cur.execute('UPDATE "{}" SET apellidos=?, nombres=?, propietario=?, area_total=?, '
            'area_riego=?, area_sin_riego=0, caudal_valor=?, observaciones=? '
            'WHERE id=?'.format(ft),
            ('HACIENDA MONTESERRIN BAJO', 'SR. COLOMA', 'HACIENDA MONTESERRIN BAJO SR. COLOMA',
             A_HAC, A_HAC, C_HAC,
             obs + NOTA + ' Frutales 30 ha: arandanos, mora y zarzamora.', id_hac))

# 2. comunidad
cur.execute('SELECT observaciones FROM "{}" WHERE id=?'.format(ft), (id_com,))
obs = (cur.fetchone()[0] or '')
cur.execute('UPDATE "{}" SET apellidos=?, nombres=?, propietario=?, area_total=?, '
            'area_riego=?, area_sin_riego=0, caudal_valor=?, observaciones=? '
            'WHERE id=?'.format(ft),
            ('SR. COLOMA MONTESERRIN BAJO', 'COMUNIDAD', 'SR. COLOMA MONTESERRIN BAJO - COMUNIDAD',
             A_COM, A_COM, C_COM,
             obs + NOTA + ' Ficha resumen de la comunidad: sus 118 regantes constan '
             'como fichas adicionales con area 0 (superficies individuales por confirmar).', id_com))

# S4 de las 2: reemplazo total
for fid in (id_hac, id_com):
    cur.execute('DELETE FROM "{}" WHERE ficha_id=?'.format(ct), (fid,))
    cur.execute('DELETE FROM "{}" WHERE ficha_id=?'.format(at), (fid,))


def alta_s4(fid, cultivos, animales):
    for tipo, otro, sup, ppal in cultivos:
        cur.execute('INSERT INTO "{}" (id_cultivo, ficha_id, tipo_cultivo, tipo_cultivo_otro, '
                    'superficie_m2, es_principal, es_autoconsumo) VALUES (?,?,?,?,?,?,1)'.format(ct),
                    ('{' + str(uuid.uuid4()) + '}', fid, tipo, otro, sup, ppal))
    for esp, cant in animales:
        cur.execute('INSERT INTO "{}" (id_animal, ficha_id, especie, cantidad, es_autoconsumo) '
                    'VALUES (?,?,?,?,1)'.format(at),
                    ('{' + str(uuid.uuid4()) + '}', fid, esp, cant))


alta_s4(id_hac, CULT_HAC, ANIM_HAC)
alta_s4(id_com, CULT_COM, ANIM_COM)

# 3 y 4: fichas nuevas de bosque y paramo (clonan datos generales de la comunidad)
cur.execute('PRAGMA table_info("{}")'.format(ft))
cols = [c[1] for c in cur.fetchall()]
cur.execute('SELECT * FROM "{}" WHERE id=?'.format(ft), (id_com,))
plantilla = dict(zip(cols, cur.fetchone()))

cur.execute('SELECT MAX(num_predio) FROM "{}" WHERE clave_catastral=?'.format(ft), (K,))
sig = int(cur.fetchone()[0] or 120) + 1

NUEVAS = [
    ('SR. COLOMA MONTESERRIN BAJO', 'BOSQUE PRODUCTIVO', A_BOSQ, p_bosq, CULT_BOSQ,
     'Bosque productivo de eucalipto y pinos (400 ha), sin riego.'),
    ('SR. COLOMA MONTESERRIN BAJO', 'PARAMO', A_PARAMO, p_par, CULT_PAR,
     'Paramo y bosque natural (parque natural), sin riego. Area = remanente del '
     'poligono para cuadrar con el catastro.'),
]
ids_nuevas = []
for ape, nom, area, punto, cults, obs_n in NUEVAS:
    reg = dict(plantilla)
    nid = '{' + str(uuid.uuid4()) + '}'
    reg.update({'id': nid, 'geom': geom_punto(punto), 'num_predio': sig,
                'codigo_final': 'S-C-P{:03d}'.format(sig),
                'apellidos': ape, 'nombres': nom,
                'propietario': '{} {}'.format(ape, nom), 'cedula': CI_COM,
                'area_total': area, 'area_riego': 0.0, 'area_sin_riego': area,
                'caudal_valor': 0.0, 'fecha_creacion': hoy,
                'creado_por': 'jvk-digitalizacion',
                'es_ficha_hija': None, 'ficha_madre_id': None,
                'estado_investigacion': None, 'completado_por': None,
                'observaciones': obs_n + NOTA,
                'coord_x_utm': punto.x, 'coord_y_utm': punto.y})
    cols_ins = [c for c in cols if c != 'fid_1']
    cur.execute('INSERT INTO "{}" ({}) VALUES ({})'.format(
        ft, ','.join('"{}"'.format(c) for c in cols_ins),
        ','.join(':' + c for c in cols_ins)), {c: reg.get(c) for c in cols_ins})
    ids_nuevas.append((reg['codigo_final'], nom))
    sig += 1

# 118 comuneros -> adicionales de la comunidad, area 0
cur.execute('UPDATE "{}" SET es_ficha_hija=1, ficha_madre_id=?, area_total=0, '
            'area_riego=0, area_sin_riego=0, caudal_valor=0, '
            'estado_investigacion=?, completado_por=?, '
            'propietario=TRIM(COALESCE(apellidos,\'\') || \' \' || COALESCE(nombres,\'\')) '
            'WHERE clave_catastral=? AND id NOT IN (?,?) AND area_total <= 1000000 '
            'AND COALESCE(es_ficha_hija,0) NOT IN (1)'.format(ft),
            (id_com, 'completada', 'jvk-editor2', K, id_hac, id_com))
n_conv = cur.rowcount
print("  comuneros convertidos a adicionales:", n_conv)
print("  fichas nuevas:", ids_nuevas)

for n, s in trg:
    try:
        cur.execute(s)
    except Exception as e:
        print("  [AVISO] trigger {}: {}".format(n, e))
con.commit()
cur.execute("PRAGMA wal_checkpoint(TRUNCATE)")
print("  checkpoint:", cur.fetchone())

# verificacion
cur.execute('SELECT SUM(area_total), COUNT(*) FROM "{}" WHERE clave_catastral=?'.format(ft), (K,))
sa, n = cur.fetchone()
print("\n  VERIFICACION: {} fichas en el poligono | area sumada {:,.2f} m2 "
      "(poligono {:,.2f}) {}".format(n, sa, AREA_POL,
                                     "OK EXACTO" if abs(sa - AREA_POL) < 1 else "REVISAR"))
cur.execute('SELECT SUM(caudal_valor) FROM "{}" WHERE clave_catastral=?'.format(ft), (K,))
print("  caudal sumado del poligono: {:.4f} l/s (esperado {:.2f})".format(cur.fetchone()[0], CAUDAL))
con.close()
print("LISTO.")
