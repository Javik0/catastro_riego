import json

def main():
    geojson_path = "c:/Users/HP/OneDrive/Escritorio/CAYAMBE CATASTRO RIEGO/padron-app/public/geo/fichas_predios.geojson"
    with open(geojson_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    target_ci = "1715033013"
    target_clave = "1702520540066"
    
    found = False
    for feature in data["features"]:
        props = feature["properties"]
        if props.get("cedula") == target_ci or props.get("clave_catastral") == target_clave:
            print("--- FICHA ENCONTRADA ---")
            print(f"ID: {props.get('id')}")
            print(f"Propietario: {props.get('propietario')}")
            print(f"Cédula: {props.get('cedula')}")
            print(f"Clave Catastral: {props.get('clave_catastral')}")
            print(f"Parroquia: {props.get('parroquia')}")
            print(f"Sector: {props.get('sector')}")
            print(f"Comunidad: {props.get('comunidad')}")
            print(f"Sector Comunidad (Original QField): {props.get('sector_comunidad')}")
            print(f"Técnico: {props.get('creado_por')}")
            print(f"Fecha Creación: {props.get('fecha_creacion')}")
            print("------------------------")
            found = True
            
    if not found:
        print("No se encontró ninguna ficha con esa cédula o clave catastral en el GeoJSON.")

if __name__ == "__main__":
    main()
