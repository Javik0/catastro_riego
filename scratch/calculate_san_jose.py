import json
from datetime import datetime

filepath = r"c:\Users\HP\OneDrive\Escritorio\CAYAMBE CATASTRO RIEGO\padron-app\public\geo\fichas_predios.geojson"

with open(filepath, "r", encoding="utf-8") as f:
    data = json.load(f)

# Listas de interés
mal_etiquetados_18 = []
san_jose_originales = []

for feat in data['features']:
    props = feat['properties']
    com = props.get('comunidad') or ''
    
    fc = props.get('fecha_creacion')
    nombre = (props.get('propietario') or f"{props.get('apellidos', '')} {props.get('nombres', '')}").strip()
    clave = props.get('clave_catastral') or 'Sin clave'
    
    # 1. Detectar si es de los 18 reasignados (del 24 de mayo con com original Asoc 17 de Junio)
    if fc:
        try:
            dt = datetime.strptime(fc.replace("Z", ""), "%Y-%m-%dT%H:%M:%S.%f")
        except ValueError:
            try:
                dt = datetime.strptime(fc.replace("Z", ""), "%Y-%m-%dT%H:%M:%S")
            except ValueError:
                continue
                
        if dt.year == 2026 and dt.month == 5 and dt.day == 24:
            if com == 'ASOCIACIÓN 17 DE JUNIO':
                mal_etiquetados_18.append({
                    "nombre": nombre,
                    "clave": clave,
                    "fecha": fc
                })
    
    # 2. Detectar si originalmente es San José o San Jose
    if com == 'SAN JOSÉ' or com == 'SAN JOSE':
        san_jose_originales.append({
            "nombre": nombre,
            "clave": clave,
            "fecha": fc
        })

print("=== 18 REGISTROS REASIGNADOS A SAN JOSÉ ===")
for idx, r in enumerate(mal_etiquetados_18, 1):
    print(f"{idx}. Regante: {r['nombre']} | Clave: {r['clave']}")

total_original = len(san_jose_originales)
total_con_correccion = total_original + len(mal_etiquetados_18)

print("\n=== COMPARATIVA DE TOTALES ===")
print(f"Total original de SAN JOSÉ (sin los 18): {total_original}")
print(f"Total reasignado de domingo 24 de mayo: {len(mal_etiquetados_18)}")
print(f"Total final de SAN JOSÉ (con los 18): {total_con_correccion}")
