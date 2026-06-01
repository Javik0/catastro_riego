# -*- coding: utf-8 -*-
"""
Script para auditar duplicados de regantes en data.gpkg.
Identifica fichas con misma cédula o nombre completo, propone la Ficha Madre
(mayor área) y detalla qué predios se convertirán en "Otros Predios"
y cuántos cultivos/animales se reasociarán.
Genera un reporte en markdown.
"""

import sqlite3
import os
import re

gpkg_path = r'C:\Users\HP\QField\cloud\porotog_levantamiento_offline\data.gpkg'
report_path = r'c:\Users\HP\OneDrive\Escritorio\CAYAMBE CATASTRO RIEGO\reporte_auditoria_duplicados.md'

# Diccionario de técnicos para traducir códigos de QField
MAPEO_TECNICOS = {
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

def normalizar_texto(texto):
    if not texto:
        return ""
    # Quitar acentos y caracteres especiales comunes
    texto = texto.upper().strip()
    replacements = (
        ("Á", "A"), ("É", "E"), ("Í", "I"), ("Ó", "O"), ("Ú", "U"),
        ("Ñ", "N"), ("Ü", "U")
    )
    for a, b in replacements:
        texto = texto.replace(a, b)
    # Reemplazar múltiples espacios por uno solo
    texto = re.sub(r'\s+', ' ', texto)
    return texto

def run_audit():
    print("📋 Iniciando Auditoría de Regantes Duplicados...")
    if not os.path.exists(gpkg_path):
        print(f"❌ Error: No se encontró la base de datos en: {gpkg_path}")
        return

    conn = sqlite3.connect(gpkg_path)
    cursor = conn.cursor()

    # 1. Identificar nombres de tablas físicas
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    all_tables = [t[0] for t in cursor.fetchall()]

    fichas_table = next((t for t in all_tables if 'Fichas_Predios' in t and not any(x in t for x in ('rtree_','log_','gpkg_'))), None)
    cultivos_table = next((t for t in all_tables if 'Cultivos_Agricolas' in t and not any(x in t for x in ('rtree_','log_','gpkg_'))), None)
    animales_table = next((t for t in all_tables if 'Animales_Especies' in t and not any(x in t for x in ('rtree_','log_','gpkg_'))), None)
    predios_table = 'Predios_Adicionales'

    if not fichas_table:
        print("❌ Error: No se encontró la tabla de Fichas_Predios")
        conn.close()
        return

    print(f"✓ Tabla Fichas: {fichas_table}")
    print(f"✓ Tabla Cultivos: {cultivos_table}")
    print(f"✓ Tabla Animales: {animales_table}")

    # Obtener el total de fichas en data.gpkg
    cursor.execute(f'SELECT COUNT(*) FROM "{fichas_table}"')
    total_fichas = cursor.fetchone()[0]

    # Cargar todas las fichas en memoria para procesar agrupaciones
    # Campos que necesitamos para el reporte
    cursor.execute(f'''
        SELECT id, cedula, apellidos, nombres, area_total, creado_por, fecha_creacion, clave_catastral, sector_comunidad, parroquia, comunidad
        FROM "{fichas_table}"
    ''')
    fichas_raw = cursor.fetchall()
    
    # Procesar y normalizar fichas
    fichas = []
    for f in fichas_raw:
        fid, ced, ape, nom, area, creador, fecha, clave, sector, parr, com = f
        ced_norm = (ced or "").strip()
        # Si la cédula es válida de 10 dígitos
        es_ced_valida = len(ced_norm) == 10 and ced_norm.isdigit()
        
        ape_norm = normalizar_texto(ape)
        nom_norm = normalizar_texto(nom)
        nombre_completo = f"{ape_norm} {nom_norm}".strip()
        
        fichas.append({
            'id': fid,
            'cedula': ced_norm,
            'es_ced_valida': es_ced_valida,
            'apellidos': (ape or "").strip(),
            'nombres': (nom or "").strip(),
            'nombre_completo_normalizado': nombre_completo,
            'area_total': area or 0.0,
            'creado_por': MAPEO_TECNICOS.get((creador or "").strip(), (creador or "").strip()),
            'fecha_creacion': fecha,
            'clave_catastral': clave,
            'sector_comunidad': sector,
            'parroquia': parr,
            'comunidad': com
        })

    # Agrupar regantes
    # Algoritmo de agrupación:
    # 1. Agrupar por Cédula Válida (10 dígitos).
    # 2. Para los que NO tienen cédula válida, agrupar por Nombre Completo Normalizado.
    
    regantes_por_cedula = {}
    fichas_sin_cedula_valida = []

    for f in fichas:
        if f['es_ced_valida']:
            ced = f['cedula']
            if ced not in regantes_por_cedula:
                regantes_por_cedula[ced] = []
            regantes_por_cedula[ced].append(f)
        else:
            fichas_sin_cedula_valida.append(f)

    regantes_por_nombre = {}
    for f in fichas_sin_cedula_valida:
        name = f['nombre_completo_normalizado']
        if not name:
            name = "SIN_NOMBRE_REGISTRADO"
        if name not in regantes_por_nombre:
            regantes_por_nombre[name] = []
        regantes_por_nombre[name].append(f)

    # Identificar grupos de duplicados (tamaño > 1)
    duplicados_cedula = {ced: lista for ced, lista in regantes_por_cedula.items() if len(lista) > 1}
    duplicados_nombre = {name: lista for name, lista in regantes_por_nombre.items() if len(lista) > 1 and name != "SIN_NOMBRE_REGISTRADO"}

    # Contadores
    total_regantes_duplicados = len(duplicados_cedula) + len(duplicados_nombre)
    total_fichas_duplicadas = sum(len(l) for l in duplicados_cedula.values()) + sum(len(l) for l in duplicados_nombre.values())
    fichas_a_eliminar = total_fichas_duplicadas - total_regantes_duplicados

    # Empezar a generar reporte
    md = []
    md.append("# Reporte de Auditoría: Regantes con Fichas Duplicadas")
    md.append(f"\nGenerado automáticamente sobre la base de datos de QField (`data.gpkg`).")
    md.append(f"\nEste reporte detalla las fichas redundantes levantadas durante los primeros días de la investigación, las cuales se consolidarán en una sola Ficha Madre (la de mayor área) y sus predios adicionales correspondientes.")
    
    md.append("\n## 📊 Resumen Ejecutivo de la Auditoría")
    md.append(f"- **Total de Fichas Registradas en el Sistema (Original):** {total_fichas}")
    md.append(f"- **Total de Regantes Únicos con Duplicados Detectados:** {total_regantes_duplicados}")
    md.append(f"- **Total de Fichas Involucradas en Duplicidad:** {total_fichas_duplicadas}")
    md.append(f"- **Fichas Redundantes que se Reducirán:** {fichas_a_eliminar}")
    md.append(f"- **Total de Fichas Estimado tras la Unificación:** {total_fichas - fichas_a_eliminar}")
    md.append(f"- **Porcentaje de Reducción en Base de Datos:** {(fichas_a_eliminar / total_fichas * 100):.2f}%")

    md.append("\n## 🔍 Detalle de Regantes Duplicados por Cédula (10 dígitos)")
    md.append(f"Se encontraron **{len(duplicados_cedula)}** regantes con múltiples fichas asociadas a la misma cédula.")
    
    grupo_idx = 1
    for ced, lista in sorted(duplicados_cedula.items(), key=lambda x: len(x[1]), reverse=True):
        # Ordenar fichas por área total descendente
        lista_ordenada = sorted(lista, key=lambda x: x['area_total'], reverse=True)
        ficha_madre = lista_ordenada[0]
        fichas_secundarias = lista_ordenada[1:]
        
        md.append(f"\n### {grupo_idx}. Regante: {ficha_madre['apellidos']} {ficha_madre['nombres']} (Cédula: `{ced}`)")
        md.append(f"- **Total Fichas:** {len(lista)}")
        md.append(f"- ⭐ **FICHA MADRE (Mayor Área):** `{ficha_madre['id']}`")
        md.append(f"  - **Clave Catastral:** `{ficha_madre['clave_catastral']}`")
        md.append(f"  - **Área Total:** {ficha_madre['area_total']:.2f} m²")
        md.append(f"  - **Sector/Comunidad:** {ficha_madre['sector_comunidad'] or 'No registrado'} / Parroquia: {ficha_madre['parroquia']}")
        md.append(f"  - **Técnico / Fecha:** {ficha_madre['creado_por']} el {ficha_madre['fecha_creacion']}")
        
        md.append("\n  **Fichas Secundarias a Unificar (se convertirán en Otros Predios):**")
        for fs in fichas_secundarias:
            # Consultar cultivos y animales asociados a esta ficha secundaria
            cant_cultivos = 0
            cant_animales = 0
            if cultivos_table:
                cursor.execute(f'SELECT COUNT(*) FROM "{cultivos_table}" WHERE ficha_id = ?', (fs['id'],))
                cant_cultivos = cursor.fetchone()[0]
            if animales_table:
                cursor.execute(f'SELECT COUNT(*) FROM "{animales_table}" WHERE ficha_id = ?', (fs['id'],))
                cant_animales = cursor.fetchone()[0]

            md.append(f"  - 📂 **Ficha:** `{fs['id']}`")
            md.append(f"    - **Clave Catastral:** `{fs['clave_catastral']}` | **Área:** {fs['area_total']:.2f} m²")
            md.append(f"    - **Sector:** {fs['sector_comunidad'] or 'No registrado'}")
            md.append(f"    - **Técnico / Fecha:** {fs['creado_por']} el {fs['fecha_creacion']}")
            md.append(f"    - **Carga de Datos:** {cant_cultivos} cultivos, {cant_animales} animales a reasociar.")
        
        grupo_idx += 1

    md.append("\n## 🔍 Detalle de Regantes Duplicados por Nombre (Sin Cédula Registrada)")
    md.append(f"Se encontraron **{len(duplicados_nombre)}** regantes con múltiples fichas que coinciden por coincidencia de nombre exacto (cédula en blanco o incompleta).")

    for name, lista in sorted(duplicados_nombre.items(), key=lambda x: len(x[1]), reverse=True):
        lista_ordenada = sorted(lista, key=lambda x: x['area_total'], reverse=True)
        ficha_madre = lista_ordenada[0]
        fichas_secundarias = lista_ordenada[1:]
        
        md.append(f"\n### {grupo_idx}. Regante: {ficha_madre['apellidos']} {ficha_madre['nombres']} (Búsqueda por Nombre)")
        md.append(f"- **Nombre Normalizado:** `{name}`")
        md.append(f"- **Total Fichas:** {len(lista)}")
        md.append(f"- ⭐ **FICHA MADRE (Mayor Área):** `{ficha_madre['id']}`")
        md.append(f"  - **Clave Catastral:** `{ficha_madre['clave_catastral']}`")
        md.append(f"  - **Área Total:** {ficha_madre['area_total']:.2f} m²")
        md.append(f"  - **Sector/Comunidad:** {ficha_madre['sector_comunidad'] or 'No registrado'} / Parroquia: {ficha_madre['parroquia']}")
        md.append(f"  - **Técnico / Fecha:** {ficha_madre['creado_por']} el {ficha_madre['fecha_creacion']}")
        
        md.append("\n  **Fichas Secundarias a Unificar (se convertirán en Otros Predios):**")
        for fs in fichas_secundarias:
            cant_cultivos = 0
            cant_animales = 0
            if cultivos_table:
                cursor.execute(f'SELECT COUNT(*) FROM "{cultivos_table}" WHERE ficha_id = ?', (fs['id'],))
                cant_cultivos = cursor.fetchone()[0]
            if animales_table:
                cursor.execute(f'SELECT COUNT(*) FROM "{animales_table}" WHERE ficha_id = ?', (fs['id'],))
                cant_animales = cursor.fetchone()[0]

            md.append(f"  - 📂 **Ficha:** `{fs['id']}`")
            md.append(f"    - **Clave Catastral:** `{fs['clave_catastral']}` | **Área:** {fs['area_total']:.2f} m²")
            md.append(f"    - **Sector:** {fs['sector_comunidad'] or 'No registrado'}")
            md.append(f"    - **Técnico / Fecha:** {fs['creado_por']} el {fs['fecha_creacion']}")
            md.append(f"    - **Carga de Datos:** {cant_cultivos} cultivos, {cant_animales} animales a reasociar.")
        
        grupo_idx += 1

    conn.close()

    # Guardar reporte
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(md))
    
    print(f"✓ Auditoría completada con éxito. Reporte guardado en: {report_path}")
    print(f"  Fichas redundantes a eliminar: {fichas_a_eliminar} de {total_fichas} en total.")

if __name__ == '__main__':
    run_audit()
