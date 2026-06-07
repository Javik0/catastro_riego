import json
import os
import math

TECNICOS_MAP = {
    'u0_a314': 'Melany Jara',
    'u0_a319': 'Melany Jara',
    'jvk-editor': 'Melany Jara',
    'u0_a504': 'Adriana Cuascota',
    'jvk-editor6': 'Adriana Cuascota',
    'u0_a279': 'Huguito Ipial',
    'jvk-editor2': 'Huguito Ipial',
    'u0_a70': 'Pablo Barrionuevo',
    'jvk-editor5': 'Pablo Barrionuevo',
    'u0_a330': 'Mayra Benavides',
    'mayralisseth201': 'Mayra Benavides',
    'u0_a362': 'Martha Simbaña',
    'u0_a335': 'Martha Simbaña',
    'jvk-editor4': 'Martha Simbaña',
    'u0_a2': 'JVK-DIGITALIZACION',
    'jvk-digitalizacion': 'JVK-DIGITALIZACION',
    'u0_a302': 'Dylan Chavez',
    'jvk-editor3': 'Dylan Chavez',
    'u0_a200': 'Melanie2',
}

def get_tecnico_name(username):
    if not username:
        return "—"
    return TECNICOS_MAP.get(username, username)

def clean_uuid(uuid_str):
    if not uuid_str:
        return ""
    return uuid_str.replace("{", "").replace("}", "").lower().strip()

def haversine_distance(lat1, lon1, lat2, lon2):
    if lat1 is None or lon1 is None or lat2 is None or lon2 is None:
        return None
    # Convertir a radianes
    lon1, lat1, lon2, lat2 = map(math.radians, [lon1, lat1, lon2, lat2])
    dlon = lon2 - lon1 
    dlat = lat2 - lat1 
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a)) 
    r = 6371000 # Radio de la Tierra en metros
    return c * r

def main():
    base_dir = "c:/Users/HP/OneDrive/Escritorio/CAYAMBE CATASTRO RIEGO/padron-app/public/geo"
    
    # Cargar geojson
    fichas_path = os.path.join(base_dir, "fichas_predios.geojson")
    with open(fichas_path, "r", encoding="utf-8") as f:
        fichas_geojson = json.load(f)

    # Procesar fichas y obtener coordenadas
    fichas_list = []
    for feat in fichas_geojson["features"]:
        props = feat["properties"]
        geom = feat.get("geometry")
        
        lat = None
        lng = None
        if geom and geom.get("type") == "Point" and geom.get("coordinates"):
            lng = geom["coordinates"][0]
            lat = geom["coordinates"][1]
        
        # Completitud de campos
        filled_fields = 0
        total_fields = 0
        for k, v in props.items():
            if k in ["id", "fid", "geometry", "_geojson", "fecha_creacion", "dispositivo"]:
                continue
            total_fields += 1
            if v is not None and str(v).strip() != "" and str(v).strip() != "0" and str(v).strip() != "None":
                filled_fields += 1

        fichas_list.append({
            "id": props.get("id"),
            "clave_catastral": (props.get("clave_catastral") or "").strip(),
            "cedula": (props.get("cedula") or "").strip(),
            "apellidos": (props.get("apellidos") or "").strip(),
            "nombres": (props.get("nombres") or "").strip(),
            "comunidad": (props.get("comunidad") or "").strip(),
            "sector_comunidad": (props.get("sector_comunidad") or "").strip(),
            "creado_por": props.get("creado_por"),
            "fecha_creacion": props.get("fecha_creacion"),
            "filled_fields": filled_fields,
            "total_fields": total_fields,
            "lat": lat,
            "lng": lng
        })

    # Agrupar duplicados por clave catastral
    by_clave = {}
    for f in fichas_list:
        clav = f["clave_catastral"]
        if clav and clav != "None" and len(clav) > 5:
            by_clave.setdefault(clav, []).append(f)

    # Agrupar duplicados por cedula
    by_cedula = {}
    for f in fichas_list:
        ced = f["cedula"]
        if ced and ced != "None" and len(ced) > 5:
            by_cedula.setdefault(ced, []).append(f)

    duplicates_report = []
    seen_ids = set()

    # Analizar duplicados de Clave Catastral
    for clav, group in by_clave.items():
        if len(group) > 1:
            group_sorted = sorted(group, key=lambda x: x["filled_fields"], reverse=True)
            master = group_sorted[0]
            dups = group_sorted[1:]
            for d in dups:
                seen_ids.add(d["id"])
                seen_ids.add(master["id"])
            duplicates_report.append({
                "tipo": "Clave Catastral Duplicada",
                "valor": clav,
                "master": master,
                "duplicates": dups
            })

    # Analizar duplicados de Cédula (no atrapados por clave)
    for ced, group in by_cedula.items():
        if len(group) > 1:
            unreported_group = [g for g in group if g["id"] not in seen_ids]
            if len(unreported_group) > 1:
                group_sorted = sorted(unreported_group, key=lambda x: x["filled_fields"], reverse=True)
                master = group_sorted[0]
                dups = group_sorted[1:]
                duplicates_report.append({
                    "tipo": "Cédula Duplicada (Diferente Clave)",
                    "valor": ced,
                    "master": master,
                    "duplicates": dups
                })

    # Guardar reporte de análisis espacial
    report_file = "c:/Users/HP/OneDrive/Escritorio/CAYAMBE CATASTRO RIEGO/reporte_duplicados_espacial.md"
    
    same_location_count = 0
    different_location_count = 0
    same_comunidad_count = 0
    different_comunidad_count = 0
    no_coords_count = 0

    with open(report_file, "w", encoding="utf-8") as rf:
        rf.write("# Reporte de Análisis Espacial y de Comunidad en Duplicados\n\n")
        rf.write("Este informe analiza si las fichas duplicadas están ubicadas en el **mismo predio** (coordenadas GPS muy cercanas, < 15 metros) ")
        rf.write("o en **diferentes predios/comunidades**, lo cual ayuda a decidir si se trata de un error de digitación en el mismo lugar o de predios distintos asignados incorrectamente.\n\n")

        rf.write("## Resumen Estadístico de Duplicados\n\n")
        
        # Primero procesamos los datos para calcular las estadísticas
        details_md = []
        for idx, rep in enumerate(duplicates_report, 1):
            m = rep["master"]
            m_com = m["comunidad"] or m["sector_comunidad"] or "—"
            
            for d_idx, d in enumerate(rep["duplicates"], 1):
                d_com = d["comunidad"] or d["sector_comunidad"] or "—"
                
                # Calcular distancia
                dist = haversine_distance(m["lat"], m["lng"], d["lat"], d["lng"])
                
                com_match = "SÍ" if m_com.upper().strip() == d_com.upper().strip() else "NO"
                if m_com == "—" or d_com == "—":
                    com_match = "Parcial/Faltante"
                
                if com_match == "SÍ":
                    same_comunidad_count += 1
                elif com_match == "NO":
                    different_comunidad_count += 1
                
                loc_type = ""
                if dist is None:
                    loc_type = "Sin GPS"
                    no_coords_count += 1
                elif dist < 15:
                    loc_type = "Mismo Predio / Punto Cercano (<15m)"
                    same_location_count += 1
                else:
                    loc_type = f"Diferente Predio / Distante ({dist:.1f} metros)"
                    different_location_count += 1

                dist_str = f"{dist:.1f} m" if dist is not None else "Sin GPS"
                
                details_md.append((
                    idx, rep["tipo"], rep["valor"], f"{m['apellidos']} {m['nombres']}",
                    f"{get_tecnico_name(m['creado_por'])} vs {get_tecnico_name(d['creado_por'])}",
                    f"{m_com} vs {d_com}", com_match, dist_str, loc_type
                ))

        rf.write(f"- Total parejas de duplicados analizadas: **{len(details_md)}**\n")
        rf.write(f"- Ubicados en el **Mismo Predio (distancia < 15m)**: **{same_location_count}** (fichas duplicadas sobre el mismo terreno físico)\n")
        rf.write(f"- Ubicados en **Diferente Predio / Distante**: **{different_location_count}** (fichas separadas geográficamente)\n")
        rf.write(f"- Parejas con la **Misma Comunidad**: **{same_comunidad_count}**\n")
        rf.write(f"- Parejas con **Diferente Comunidad**: **{different_comunidad_count}**\n")
        rf.write(f"- Fichas sin coordenadas GPS: **{no_coords_count}**\n\n")

        rf.write("## Tabla de Resultados de Análisis Espacial\n\n")
        rf.write("| # | Tipo | Identificador | Propietario | Técnicos (M vs D) | Comunidades (M vs D) | ¿Misma Comunidad? | Distancia GPS | Clasificación de Ubicación |\n")
        rf.write("|---|------|---------------|-------------|-------------------|----------------------|-------------------|---------------|-----------------------------|\n")
        
        for det in details_md:
            rf.write(f"| {det[0]} | {det[1]} | `{det[2]}` | {det[3]} | {det[4]} | {det[5]} | {det[6]} | {det[7]} | {det[8]} |\n")

    print(f"Reporte espacial guardado en: {report_file}")
    
    # Imprimir el análisis para el caso del ejemplo
    print("\n--- ANÁLISIS ESPACIAL DEL CASO EJEMPLO (CI 1710854975 / CLAVE 1702520580195) ---")
    for rep in duplicates_report:
        if rep["valor"] == "1702520580195" or rep["valor"] == "1710854975":
            m = rep["master"]
            for d in rep["duplicates"]:
                dist = haversine_distance(m["lat"], m["lng"], d["lat"], d["lng"])
                print(f"Master Ficha: {m['id']} ({get_tecnico_name(m['creado_por'])}) - Coords: ({m['lat']}, {m['lng']})")
                print(f"  Comunidad: {m['comunidad']} (Sector Comunidad: {m['sector_comunidad']})")
                print(f"Duplicate Ficha: {d['id']} ({get_tecnico_name(d['creado_por'])}) - Coords: ({d['lat']}, {d['lng']})")
                print(f"  Comunidad: {d['comunidad']} (Sector Comunidad: {d['sector_comunidad']})")
                print(f"Distancia entre puntos GPS: {f'{dist:.2f} metros' if dist is not None else 'Sin GPS'}")
                print(f"Clasificación: {'Mismo Predio' if dist < 15 else 'Diferente Predio'}")

if __name__ == "__main__":
    main()
