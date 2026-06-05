import json
from datetime import datetime

filepath = r"c:\Users\HP\OneDrive\Escritorio\CAYAMBE CATASTRO RIEGO\padron-app\public\geo\fichas_predios.geojson"

with open(filepath, "r", encoding="utf-8") as f:
    data = json.load(f)

registros_24_25 = []

for feat in data['features']:
    props = feat['properties']
    fc = props.get('fecha_creacion')
    if fc:
        # Ejemplo: 2026-05-24T07:46:00.258Z
        try:
            # Parsear fecha ISO
            dt = datetime.strptime(fc.replace("Z", ""), "%Y-%m-%dT%H:%M:%S.%f")
        except ValueError:
            try:
                dt = datetime.strptime(fc.replace("Z", ""), "%Y-%m-%dT%H:%M:%S")
            except ValueError:
                continue
                
        if dt.year == 2026 and dt.month == 5 and dt.day in [24, 25]:
            registros_24_25.append({
                "id": props.get('id') or props.get('fid'),
                "nombre": (props.get('propietario') or f"{props.get('apellidos', '')} {props.get('nombres', '')}").strip(),
                "comunidad": props.get('comunidad'),
                "fecha_creacion": fc,
                "dia_utc": dt.day,
                "hora_utc": dt.hour,
                "minuto_utc": dt.minute,
                "tecnico": props.get('creado_por')
            })

# Ordenar por fecha_creacion
registros_24_25.sort(key=lambda x: x["fecha_creacion"])

print(f"Total registros 24 y 25 de mayo: {len(registros_24_25)}")
print("\n=== REGISTROS DEL 24 DE MAYO ===")
count_24 = 0
for r in registros_24_25:
    if r["dia_utc"] == 24:
        count_24 += 1
        print(f"{count_24}. [{r['fecha_creacion']}] H:{r['hora_utc']}:{r['minuto_utc']} | Com: {r['comunidad']} | Tec: {r['tecnico']} | Regante: {r['nombre']}")

print("\n=== REGISTROS DEL 25 DE MAYO ===")
count_25 = 0
for r in registros_24_25:
    if r["dia_utc"] == 25:
        count_25 += 1
        print(f"{count_25}. [{r['fecha_creacion']}] H:{r['hora_utc']}:{r['minuto_utc']} | Com: {r['comunidad']} | Tec: {r['tecnico']} | Regante: {r['nombre']}")
