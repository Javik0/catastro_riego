import sqlite3
from collections import Counter
import datetime

GPKG = r'C:\Users\HP\QField\cloud\porotog_levantamiento_offline\data.gpkg'
conn = sqlite3.connect(GPKG)
cur = conn.cursor()

cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
all_tables = [t[0] for t in cur.fetchall()]
fichas_table = next(t for t in all_tables if 'Fichas_Predios' in t and not any(x in t for x in ('rtree_','log_','gpkg_')))

cur.execute(f'PRAGMA table_info("{fichas_table}")')
cols = [c[1] for c in cur.fetchall()]

cur.execute(f'SELECT * FROM "{fichas_table}"')
rows = cur.fetchall()

fichas = []
for r in rows:
    fichas.append({cols[i]: r[i] for i in range(len(cols))})

print(f"Total fichas leídas: {len(fichas)}")

# 1. Agrupamiento por fecha_dia y creado_por
def get_dia(fecha_str):
    if not fecha_str:
        return None
    try:
        # Formatos comunes: '2026-05-21T12:00:00' o '2026-05-21'
        return fecha_str[:10]
    except:
        return None

# Mapear comunidades
VARIANTES_COMUNIDAD = [
    ("LARCACHACA", "LARCACHACA"),
    ("LARCACACHA", "LARCACHACA"),
    ("LARCACOCHA", "LARCACHACA"),
    ("LARCACHA", "LARCACHACA"),
    ("LA ARCACHA", "LARCACHACA"),
    ("ALCACHACA", "LARCACHACA"),
    ("HUASIPUNGO", "LARCACHACA"),
    ("GUASIPUNGO", "LARCACHACA"),
    ("GUALIMBURO", "LARCACHACA"),
    ("PARCELA", "LARCACHACA"),
    ("MORAS", "LARCACHACA"),
    ("PÁRAMO", "LARCACHACA"),
    ("LIBERAD", "LA LIBERTAD"),
    ("LIBERTAD", "LA LIBERTAD"),
    ("CENTRAL LIBERTAD", "LA LIBERTAD"),
    ("SAN ANTONIO", "SAN ANTONIO"),
    ("SAM ANTONIO", "SAN ANTONIO"),
    ("PAILLACO", "SAN ANTONIO"),
    ("PAYLLACHO", "SAN ANTONIO"),
    ("PAILLACHO", "SAN ANTONIO"),
    ("SAN JOSÉ", "SAN JOSÉ"),
    ("SAN JOSE", "SAN JOSÉ"),
    ("SAN  PEDRO", "SAN JOSÉ"),
    ("SAN PEDRO", "SAN JOSÉ"),
    ("YACUTIGRANA", "SAN JOSÉ"),
    ("PORTADAS", "SAN JOSÉ"),
    ("NINARUMI", "SAN JOSÉ"),
    ("NINA RUMI", "SAN JOSÉ"),
    ("INARUMI", "SAN JOSÉ"),
    ("ÑAVIPOGYO", "SAN JOSÉ"),
    ("ÑAVIPUYO", "SAN JOSÉ"),
    ("ÑAWIPUKYU", "SAN JOSÉ"),
    ("GUALIMPURO", "SAN JOSÉ"),
    ("LOS ANDES", "SAN JOSÉ"),
    ("MILAGRO", "MILAGRO"),
    ("ASOSIACION 17", "ASOCIACIÓN 17 DE JUNIO"),
    ("ASOCIACIÓN 17", "ASOCIACIÓN 17 DE JUNIO"),
    ("ASOCIACION 17", "ASOCIACIÓN 17 DE JUNIO"),
    ("17 DE JUNIO", "ASOCIACIÓN 17 DE JUNIO"),
    ("17 DE JULIO", "ASOCIACIÓN 17 DE JUNIO"),
    ("AVELLANEDA", "AVELLANEDA"),
    ("CHAMBITOLA", "CHAMBITOLA"),
    ("CHAMITOLA", "CHAMBITOLA"),
    ("CAMBITOLA", "CHAMBITOLA"),
    ("CHIMBATOLA", "CHAMBITOLA"),
    ("CANDELARIA", "LA CANDELARIA"),
    ("CARRERA", "CARRERA"),
    ("CARERRA", "CARRERA"),
    ("ACERO LOMA", "CARRERA"),
    ("MATÍAS IMBAGO", "MATÍAS IMBAGO"),
    ("MATIAS IMBAGO", "MATÍAS IMBAGO"),
    ("COCHAPAMBA", "COCHAPAMBA"),
    ("GRAN PODER", "JESÚS GRAN PODER"),
    ("SANTA BÁRBARA", "SANTA BÁRBARA"),
    ("SANTA BARBARA", "SANTA BÁRBARA"),
    ("ASOCIACIÓN POROTOG", "ASOCIACIÓN POROTOG"),
    ("ASOCIACION POROTOG", "ASOCIACIÓN POROTOG"),
    ("COMUNA POROTOG", "COMUNA POROTOG"),
    ("CORDILLERAS", "CORDILLERAS DE LOS ANDES"),
    ("COMUNA INSACATA", "COMUNA INSACATA"),
    ("IZACATA", "COMUNA INSACATA"),
    ("INSACATA", "COMUNA INSACATA"),
    ("INSACATA GRANDE", "INSACATA GRANDE"),
    ("LOS ANDES INSACATA", "LOS ANDES INSACATA"),
    ("LOMA GORDA", "LOMA GORDA"),
    ("SAN JACINTO", "SAN JACINTO"),
    ("CRUZ LOMA", "SAN JOSÉ"),
    ("CRUZLOMA", "SAN JOSÉ"),
    ("TOTORA", "SAN JOSÉ"),
    ("TOTORAS", "SAN JOSÉ"),
    ("MULAPOTERO", "SAN JOSÉ"),
    ("MULA POTRERO", "SAN JOSÉ"),
    ("BANDURRIA", "SAN JOSÉ"),
    ("BANDURIA", "SAN JOSÉ"),
    ("BARROLOMA", "SAN JOSÉ"),
    ("PLAYA", "SAN JOSÉ"),
    ("CALDERA", "SAN JOSÉ"),
    ("POCARALOMA", "SAN JOSÉ"),
    ("CENTRAL", "SAN JOSÉ"),
    ("CÓNDOR LOMA", "SAN JOSÉ"),
    ("PUKARA", "SAN JOSÉ"),
    ("SOPALO LOMA", "LA CANDELARIA"),
    ("GUANGUILQUI", "LARCACHACA"),
    ("CANGAHUA", "LARCACHACA"),
]
VARIANTES_COMUNIDAD.sort(key=lambda x: len(x[0]), reverse=True)

def derivar_comunidad(sc_val):
    if not sc_val:
        return None
    sc = str(sc_val).upper().strip()
    for var, com in VARIANTES_COMUNIDAD:
        if var in sc:
            return com
    return None

# Primero derivar comunidad para todos
for f in fichas:
    if not f.get('comunidad'):
        der = derivar_comunidad(f.get('sector_comunidad'))
        if der:
            f['comunidad'] = der

# Agrupar
grupos_dia_tec = {}
grupos_dia = {}

for f in fichas:
    dia = get_dia(f['fecha_creacion'])
    tec = f['creado_por']
    if not dia or not tec:
        continue
    
    key_dt = (dia, tec)
    if key_dt not in grupos_dia_tec:
        grupos_dia_tec[key_dt] = []
    grupos_dia_tec[key_dt].append(f)
    
    if dia not in grupos_dia:
        grupos_dia[dia] = []
    grupos_dia[dia].append(f)

def calc_modas(fichas_grupo):
    # Calcular modas de campos categóricos
    parroquias = [f['parroquia'] for f in fichas_grupo if f.get('parroquia')]
    sectores = [f['sector'] for f in fichas_grupo if f.get('sector')]
    comunidades = [f['comunidad'] for f in fichas_grupo if f.get('comunidad')]
    caudal_tipos = [f['caudal_tipo'] for f in fichas_grupo if f.get('caudal_tipo')]
    frecuencias = [f['frecuencia_riego'] for f in fichas_grupo if f.get('frecuencia_riego')]
    
    # Caudal valor promedio (no nulos ni ceros)
    caudales = [f['caudal_valor'] for f in fichas_grupo if f.get('caudal_valor') and f['caudal_valor'] > 0]
    
    # Método riego más común
    # Guardamos tuplas de (aspersion, gravedad, goteo)
    metodos = []
    for f in fichas_grupo:
        asp = f.get('metodo_aspersion_pct') or 0
        grav = f.get('metodo_gravedad_pct') or 0
        got = f.get('metodo_goteo_pct') or 0
        if asp > 0 or grav > 0 or got > 0:
            metodos.append((asp, grav, got))
            
    modas = {
        'parroquia': Counter(parroquias).most_common(1)[0][0] if parroquias else 'CANGAHUA',
        'sector': Counter(sectores).most_common(1)[0][0] if sectores else None,
        'comunidad': Counter(comunidades).most_common(1)[0][0] if comunidades else None,
        'caudal_tipo': Counter(caudal_tipos).most_common(1)[0][0] if caudal_tipos else None,
        'frecuencia_riego': Counter(frecuencias).most_common(1)[0][0] if frecuencias else None,
        'caudal_valor': sum(caudales)/len(caudales) if caudales else None,
        'metodo_riego': Counter(metodos).most_common(1)[0][0] if metodos else None
    }
    return modas

# Precalcular modas para grupos
modas_dia_tec = {}
for key, fs in grupos_dia_tec.items():
    modas_dia_tec[key] = calc_modas(fs)

modas_dia = {}
for dia, fs in grupos_dia.items():
    modas_dia[dia] = calc_modas(fs)

# Imputar vacíos
modificados = []
for f in fichas:
    # Guardar copia antes de imputar
    f_orig = f.copy()
    
    dia = get_dia(f['fecha_creacion'])
    tec = f['creado_por']
    if not dia or not tec:
        continue
    
    m_dt = modas_dia_tec.get((dia, tec))
    m_d = modas_dia.get(dia)
    
    cambio = False
    
    # Parroquia
    if not f.get('parroquia'):
        f['parroquia'] = m_dt.get('parroquia') or m_d.get('parroquia') or 'CANGAHUA'
        cambio = True
        
    # Sector
    if not f.get('sector'):
        f['sector'] = m_dt.get('sector') or m_d.get('sector') or 'Porotog'
        cambio = True
        
    # Comunidad
    if not f.get('comunidad'):
        f['comunidad'] = m_dt.get('comunidad') or m_d.get('comunidad')
        if f['comunidad']:
            cambio = True
            
    # Caudal Tipo
    if not f.get('caudal_tipo'):
        f['caudal_tipo'] = m_dt.get('caudal_tipo') or m_d.get('caudal_tipo')
        if f['caudal_tipo']:
            cambio = True
            
    # Frecuencia Riego
    if not f.get('frecuencia_riego'):
        f['frecuencia_riego'] = m_dt.get('frecuencia_riego') or m_d.get('frecuencia_riego')
        if f['frecuencia_riego']:
            cambio = True
            
    # Caudal Valor
    if not f.get('caudal_valor') or f['caudal_valor'] == 0:
        val = m_dt.get('caudal_valor') or m_d.get('caudal_valor')
        if val:
            f['caudal_valor'] = round(val, 2)
            cambio = True
            
    # Método Riego
    asp = f.get('metodo_aspersion_pct') or 0
    grav = f.get('metodo_gravedad_pct') or 0
    got = f.get('metodo_goteo_pct') or 0
    if asp == 0 and grav == 0 and got == 0:
        val_metodo = m_dt.get('metodo_riego') or m_d.get('metodo_riego')
        if val_metodo:
            f['metodo_aspersion_pct'] = val_metodo[0]
            f['metodo_gravedad_pct'] = val_metodo[1]
            f['metodo_goteo_pct'] = val_metodo[2]
            cambio = True
            
    if cambio:
        modificados.append((f_orig, f))

print(f"Total fichas imputadas: {len(modificados)}")

# Mostrar algunos ejemplos
print("\nEjemplos de fichas imputadas (Antes -> Después):")
for i, (orig, new) in enumerate(modificados[:10]):
    print(f"\nEjemplo {i+1} - ID: {new['id']} ({new['apellidos']} {new['nombres']}) | Fecha: {new['fecha_creacion']}")
    print(f"  Comunidad:  {orig.get('comunidad')} -> {new.get('comunidad')}")
    print(f"  Caudal:     {orig.get('caudal_valor')} -> {new.get('caudal_valor')}")
    print(f"  Riego Asp:  {orig.get('metodo_aspersion_pct')} -> {new.get('metodo_aspersion_pct')}")
    print(f"  Riego Grav: {orig.get('metodo_gravedad_pct')} -> {new.get('metodo_gravedad_pct')}")

conn.close()
