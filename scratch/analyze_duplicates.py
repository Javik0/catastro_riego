import json
import os
import re

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

def main():
    base_dir = "c:/Users/HP/OneDrive/Escritorio/CAYAMBE CATASTRO RIEGO/padron-app/public/geo"
    
    # Cargar geojson y jsons
    fichas_path = os.path.join(base_dir, "fichas_predios.geojson")
    cultivos_path = os.path.join(base_dir, "cultivos.json")
    animales_path = os.path.join(base_dir, "animales.json")
    predios_adicionales_path = os.path.join(base_dir, "predios_adicionales.json")

    with open(fichas_path, "r", encoding="utf-8") as f:
        fichas_geojson = json.load(f)
    
    with open(cultivos_path, "r", encoding="utf-8") as f:
        cultivos = json.load(f)

    with open(animales_path, "r", encoding="utf-8") as f:
        animales = json.load(f)

    with open(predios_adicionales_path, "r", encoding="utf-8") as f:
        predios_adicionales = json.load(f)

    # Contar relaciones por ficha_id
    cultivos_by_ficha = {}
    for c in cultivos:
        fid = clean_uuid(c.get("ficha_id"))
        if fid:
            cultivos_by_ficha[fid] = cultivos_by_ficha.get(fid, 0) + 1

    animales_by_ficha = {}
    for a in animales:
        fid = clean_uuid(a.get("ficha_id"))
        if fid:
            animales_by_ficha[fid] = animales_by_ficha.get(fid, 0) + 1

    adicionales_by_ficha = {}
    for pa in predios_adicionales:
        fid = clean_uuid(pa.get("ficha_id"))
        if fid:
            adicionales_by_ficha[fid] = adicionales_by_ficha.get(fid, 0) + 1

    # Procesar fichas
    fichas_list = []
    for feat in fichas_geojson["features"]:
        props = feat["properties"]
        fid = clean_uuid(props.get("id") or props.get("fid"))
        
        # Calcular completitud de campos
        filled_fields = 0
        total_fields = 0
        for k, v in props.items():
            if k in ["id", "fid", "geometry", "_geojson", "fecha_creacion", "dispositivo"]:
                continue
            total_fields += 1
            if v is not None and str(v).strip() != "" and str(v).strip() != "0" and str(v).strip() != "None":
                filled_fields += 1

        num_cultivos = cultivos_by_ficha.get(fid, 0)
        num_animales = animales_by_ficha.get(fid, 0)
        num_adicionales = adicionales_by_ficha.get(fid, 0)

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
            "num_cultivos": num_cultivos,
            "num_animales": num_animales,
            "num_adicionales": num_adicionales,
            "original_properties": props
        })

    # Buscar duplicados por Clave Catastral
    by_clave = {}
    for f in fichas_list:
        clav = f["clave_catastral"]
        if clav and clav != "None" and len(clav) > 5:
            by_clave.setdefault(clav, []).append(f)

    # Buscar duplicados por Cédula (si no tienen clave, o para cruzar)
    by_cedula = {}
    for f in fichas_list:
        ced = f["cedula"]
        if ced and ced != "None" and len(ced) > 5:
            by_cedula.setdefault(ced, []).append(f)

    duplicates_report = []

    # Analizar duplicados de Clave Catastral
    seen_ids = set()
    for clav, group in by_clave.items():
        if len(group) > 1:
            # Ordenar por completitud desc (el más completo primero)
            group_sorted = sorted(
                group, 
                key=lambda x: (x["num_adicionales"], x["num_cultivos"], x["filled_fields"]), 
                reverse=True
            )
            
            # El primero es el "completo", los demás son candidatos a duplicados
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

    # Analizar duplicados de Cédula que no se hayan atrapado por clave catastral
    for ced, group in by_cedula.items():
        if len(group) > 1:
            # Filtrar los que ya están en reportes de clave catastral para no duplicar reporte
            unreported_group = [g for g in group if g["id"] not in seen_ids]
            if len(unreported_group) > 1:
                group_sorted = sorted(
                    unreported_group, 
                    key=lambda x: (x["num_adicionales"], x["num_cultivos"], x["filled_fields"]), 
                    reverse=True
                )
                master = group_sorted[0]
                dups = group_sorted[1:]
                
                duplicates_report.append({
                    "tipo": "Cédula Duplicada (Diferente Clave)",
                    "valor": ced,
                    "master": master,
                    "duplicates": dups
                })

    # Generar markdown
    print(f"Total grupos de duplicados encontrados: {len(duplicates_report)}")
    
    # Guardar reporte completo a markdown
    report_file = "c:/Users/HP/OneDrive/Escritorio/CAYAMBE CATASTRO RIEGO/reporte_fichas_duplicadas.md"
    with open(report_file, "w", encoding="utf-8") as rf:
        rf.write("# Reporte de Fichas Duplicadas (Clave Catastral / Cédula)\n\n")
        rf.write("Este informe identifica los casos donde un mismo regante o predio tiene más de una ficha digitalizada. ")
        rf.write("Se ha clasificado cada grupo ordenándolo de forma que la **Ficha Master (Completa)** sea la que contiene mayor cantidad de información ")
        rf.write("(campos llenos, cultivos, animales y otros predios del regante), y las **Fichas Duplicadas** sean las candidatas a eliminación por estar más vacías.\n\n")
        
        rf.write(f"Total casos/grupos de duplicados detectados: **{len(duplicates_report)}**\n\n")
        
        rf.write("### Aclaración sobre el Técnico y Comunidad Duplicados:\n")
        rf.write("- Si se listan varios nombres en el Técnico Duplicado (ej. `Dylan Chavez, Dylan Chavez`), significa que la ficha se duplicó **más de una vez** (hay 3 o más fichas para el mismo predio).\n")
        rf.write("- Se incluye la columna **Comunidades (Master vs Duplicados)** para observar si los duplicados fueron registrados en la misma comunidad o en áreas distintas.\n\n")

        rf.write("## Tabla Resumen de Casos\n\n")
        rf.write("| # | Tipo | Identificador | Propietario Master | Técnico Master | Técnico Duplicado | Comunidades (M vs D) | Campos (Master vs Dup) | Cultivos/Adicionales (M vs D) |\n")
        rf.write("|---|------|---------------|--------------------|----------------|-------------------|----------------------|------------------------|--------------------------------|\n")
        
        for idx, rep in enumerate(duplicates_report, 1):
            m = rep["master"]
            m_name = get_tecnico_name(m["creado_por"])
            dup_tecnicos = ", ".join([get_tecnico_name(dup["creado_por"]) for dup in rep["duplicates"]])
            
            # Comunidades
            m_com = m["comunidad"] or m["sector_comunidad"] or "—"
            dup_coms = ", ".join([dup["comunidad"] or dup["sector_comunidad"] or "—" for dup in rep["duplicates"]])
            com_comparison = f"{m_com} vs {dup_coms}"
            
            dup_fields = "/".join([str(dup["filled_fields"]) for dup in rep["duplicates"]])
            dup_rels = "/".join([f"{dup['num_cultivos']}c,{dup['num_adicionales']}a" for dup in rep["duplicates"]])
            
            rf.write(f"| {idx} | {rep['tipo']} | `{rep['valor']}` | {m['apellidos']} {m['nombres']} | {m_name} | {dup_tecnicos} | {com_comparison} | {m['filled_fields']} vs {dup_fields} | {m['num_cultivos']}c,{m['num_adicionales']}a vs {dup_rels} |\n")
            
        rf.write("\n## Detalle Completo de Casos\n\n")
        for idx, rep in enumerate(duplicates_report, 1):
            m = rep["master"]
            rf.write(f"### Caso {idx}: {rep['tipo']} - `{rep['valor']}`\n")
            rf.write(f"**Propietario:** {m['apellidos']} {m['nombres']} (CI: `{m['cedula']}` / Clave: `{m['clave_catastral']}`)\n\n")
            
            rf.write("#### 🟢 FICHA MASTER (CONSERVAR)\n")
            rf.write(f"- **ID Ficha:** `{m['id']}`\n")
            rf.write(f"- **Técnico:** `{get_tecnico_name(m['creado_por'])}`\n")
            rf.write(f"- **Comunidad:** `{m['comunidad'] or m['sector_comunidad'] or '—'}`\n")
            rf.write(f"- **Fecha Creación:** `{m['fecha_creacion']}`\n")
            rf.write(f"- **Completitud:** {m['filled_fields']} de {m['total_fields']} campos llenos.\n")
            rf.write(f"- **Datos Relacionales:** {m['num_cultivos']} cultivos, {m['num_animales']} animales, {m['num_adicionales']} otros predios.\n\n")
            
            rf.write("#### 🔴 FICHAS DUPLICADAS (CANDIDATAS A ELIMINACIÓN)\n")
            for d_idx, d in enumerate(rep["duplicates"], 1):
                rf.write(f"##### Duplicado {d_idx}\n")
                rf.write(f"- **ID Ficha:** `{d['id']}`\n")
                rf.write(f"- **Técnico:** `{get_tecnico_name(d['creado_por'])}`\n")
                rf.write(f"- **Comunidad:** `{d['comunidad'] or d['sector_comunidad'] or '—'}`\n")
                rf.write(f"- **Fecha Creación:** `{d['fecha_creacion']}`\n")
                rf.write(f"- **Completitud:** {d['filled_fields']} de {d['total_fields']} campos llenos.\n")
                rf.write(f"- **Datos Relacionales:** {d['num_cultivos']} cultivos, {d['num_animales']} animales, {d['num_adicionales']} otros predios.\n\n")
            rf.write("---\n\n")
            
    print(f"Reporte completo guardado en: {report_file}")

if __name__ == "__main__":
    main()
