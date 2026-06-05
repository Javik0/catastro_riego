import json

filepath = r"c:\Users\HP\OneDrive\Escritorio\CAYAMBE CATASTRO RIEGO\padron-app\public\geo\fichas_predios.geojson"

with open(filepath, "r", encoding="utf-8") as f:
    data = json.load(f)

# Agrupar registros por fecha y comunidad original
analisis = {}

for feat in data['features']:
    props = feat['properties']
    fc = props.get('fecha_creacion')
    com = props.get('comunidad')
    tec = props.get('creado_por')
    
    if fc:
        date_part = fc.split("T")[0]
        # Nos enfocamos en mayo de 2026
        if "2026-05" in date_part:
            if date_part not in analisis:
                analisis[date_part] = {}
            if com not in analisis[date_part]:
                analisis[date_part][com] = {"count": 0, "tecnicos": set()}
            analisis[date_part][com]["count"] += 1
            if tec:
                analisis[date_part][com]["tecnicos"].add(tec)

print("=== Análisis de Registros por Fecha y Comunidad original ===")
for date in sorted(analisis.keys()):
    print(f"\nFecha: {date}")
    for com, info in sorted(analisis[date].items(), key=lambda x: x[0] or ""):
        tecnicos_str = ", ".join(info["tecnicos"])
        print(f"  - Comunidad: {com} | Cantidad: {info['count']} | Técnicos: {tecnicos_str}")
