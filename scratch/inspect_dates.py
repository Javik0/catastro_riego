import json
import os

filepath = r"c:\Users\HP\OneDrive\Escritorio\CAYAMBE CATASTRO RIEGO\padron-app\public\geo\fichas_predios.geojson"

if not os.path.exists(filepath):
    print("Archivo no encontrado")
    exit()

with open(filepath, "r", encoding="utf-8") as f:
    data = json.load(f)

print(f"Total de registros: {len(data['features'])}")

# Busquemos los registros del reporte: CHIQUIMBA ECHESI MARIA BEATRIZ, ASERO CHIMARRO MARIA ENCARNACION, SALAZAR PILCA MARTHA BEATRIZ
nombres_buscar = [
    "CHIQUIMBA ECHESI MARIA BEATRIZ",
    "ASERO CHIMARRO MARIA ENCARNACION",
    "SALAZAR PILCA MARTHA BEATRIZ"
]

print("\n--- Registros específicos ---")
for feat in data['features']:
    props = feat['properties']
    prop_name = (props.get('propietario') or f"{props.get('apellidos', '')} {props.get('nombres', '')}").strip().upper()
    
    # Comprobar si alguno de los nombres a buscar está en prop_name
    match = False
    for n in nombres_buscar:
        if n in prop_name:
            match = True
            break
            
    if match:
        print(f"ID: {props.get('id') or props.get('fid')}")
        print(f"Nombre: {prop_name}")
        print(f"Comunidad original: {props.get('comunidad')}")
        print(f"Fecha creación original: {props.get('fecha_creacion')}")
        print(f"Creado por: {props.get('creado_por')}")
        print("-" * 30)

print("\n--- Conteo por comunidad original en el GeoJSON ---")
comunidades = {}
for feat in data['features']:
    com = feat['properties'].get('comunidad')
    comunidades[com] = comunidades.get(com, 0) + 1
for com, count in sorted(comunidades.items(), key=lambda x: str(x[0])):
    print(f"{com}: {count}")

print("\n--- Conteo de registros vacíos sin comunidad por fecha de creación (Mayo 2026) ---")
fechas_vacias = {}
for feat in data['features']:
    props = feat['properties']
    com = props.get('comunidad')
    if not com or com.strip() == "" or com.lower() == "none":
        fc = props.get('fecha_creacion')
        if fc:
            date_part = fc.split("T")[0]
            fechas_vacias[date_part] = fechas_vacias.get(date_part, 0) + 1
for date, count in sorted(fechas_vacias.items()):
    print(f"{date}: {count}")
