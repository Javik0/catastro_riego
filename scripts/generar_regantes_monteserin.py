# -*- coding: utf-8 -*-
"""
Script de Generacion e Insercion Masiva de Regantes (Hacienda Monteserin Bajo)
Genera puntos uniformemente distribuidos dentro del poligono 1702510040121,
copia los datos complementarios de las dos fichas de referencia existentes,
e inserta los 118 regantes de forma segura desactivando temporalmente los triggers.

Uso:
  python padron-app/scripts/generar_regantes_monteserin.py
"""

import os
import sqlite3
import json
import struct
import shutil
import uuid
from datetime import datetime
from pyproj import Transformer
from shapely.wkb import loads as wkb_loads
from shapely.geometry import Point
import numpy as np

# --- Rutas de Archivos ------------------------------------------
QFIELD_DIR = r'C:\Users\HP\QField\cloud\porotog_levantamiento_offline'
DATA_GPKG  = os.path.join(QFIELD_DIR, 'data.gpkg')
BACKUP_GPKG = os.path.join(QFIELD_DIR, 'data.gpkg.bak')
CATASTRO_GPKG = os.path.join(QFIELD_DIR, 'CATASTROACTUALIZADORURALCATASTRORURALACTUALIZADO.gpkg')

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PADRON_APP_DIR = os.path.dirname(SCRIPT_DIR)
REGANTES_JSON = os.path.join(PADRON_APP_DIR, 'scratch', 'regantes_factura.json')

def extract_wkb_from_gpkg_geom(gpkg_bin):
    """Extrae el WKB estandar de una geometria de GeoPackage eliminando la cabecera."""
    if not gpkg_bin or len(gpkg_bin) < 8:
        return None
    magic = gpkg_bin[:2]
    if magic != b'GP':
        raise ValueError("No es un formato GeoPackage valido (falta magic number GP)")
    flags = gpkg_bin[3]
    envelope_indicator = (flags >> 1) & 7
    envelope_sizes = {0: 0, 1: 32, 2: 48, 3: 48, 4: 64}
    envelope_size = envelope_sizes.get(envelope_indicator, 0)
    header_size = 8 + envelope_size
    return gpkg_bin[header_size:]

def make_gpkg_point(lon, lat, srs_id=4326):
    """Crea una geometria binaria de punto compatible con GeoPackage (sin envelope, little-endian)."""
    # Cabecera GPKG: Magic 'GP', version 0, flags=1 (little-endian, no envelope), SRS ID
    header = struct.pack('<2sBBi', b'GP', 0, 1, srs_id)
    # WKB estandar: byte order 1, geom type 1 (Point), X (lon), Y (lat)
    wkb = struct.pack('<BIdd', 1, 1, lon, lat)
    return header + wkb

def clean_cedula(ced_str):
    """Limpia la cedula quitando guiones y espacios, dejando solo digitos."""
    if not ced_str:
        return ""
    return "".join(c for c in str(ced_str) if c.isdigit())

def main():
    print("=" * 70)
    print("  GENERACION E INSERCION MASIVA DE REGANTES - HDA. MONTESERIN BAJO")
    print("=" * 70)

    # 1. Validaciones previas
    if not os.path.exists(DATA_GPKG):
        print(f"Error: No se encontro la base de datos de fichas: {DATA_GPKG}")
        return
    if not os.path.exists(CATASTRO_GPKG):
        print(f"Error: No se encontro la base de datos de catastro: {CATASTRO_GPKG}")
        return
    if not os.path.exists(REGANTES_JSON):
        print(f"Error: No se encontro el JSON de regantes en: {REGANTES_JSON}")
        return

    # Cargar regantes
    with open(REGANTES_JSON, 'r', encoding='utf-8') as f:
        regantes = json.load(f)
    num_regantes = len(regantes)
    print(f"Cargados {num_regantes} regantes desde {os.path.basename(REGANTES_JSON)}")

    # 2. Respaldar base de datos
    print(f"Creando copia de seguridad de data.gpkg...")
    shutil.copy2(DATA_GPKG, BACKUP_GPKG)
    print(f"Respaldo guardado en: {BACKUP_GPKG}")

    # 3. Leer geometria del predio catastral
    print("Leyendo geometria del predio catastral 1702510040121...")
    conn_cat = sqlite3.connect(CATASTRO_GPKG)
    cursor_cat = conn_cat.cursor()
    cursor_cat.execute("""
        SELECT geom FROM CATASTROACTUALIZADORURALCATASTRORURALACTUALIZADO
        WHERE clave_cata = '1702510040121'
    """)
    row_cat = cursor_cat.fetchone()
    if not row_cat:
        print("Error: No se encontro el poligono 1702510040121 en el Catastro.")
        conn_cat.close()
        return
    geom_bytes = row_cat[0]
    conn_cat.close()

    # Cargar geometria en Shapely
    wkb = extract_wkb_from_gpkg_geom(geom_bytes)
    poly = wkb_loads(wkb)
    print(f"Poligono catastral cargado. Tipo: {poly.geom_type}, Area total: {poly.area:,.2f} m2")

    # 4. Generacion de puntos uniformes dentro del poligono (FPS)
    print("Generando grilla homogenea de puntos...")
    min_x, min_y, max_x, max_y = poly.bounds
    
    # Intentamos con espaciado de 50 metros primero
    spacing = 50.0
    candidates = []
    x = min_x + spacing / 2.0
    while x < max_x:
        y = min_y + spacing / 2.0
        while y < max_y:
            pt = Point(x, y)
            if poly.contains(pt):
                candidates.append(pt)
            y += spacing
        x += spacing

    print(f"Candidatos con grilla de {spacing}m: {len(candidates)}")
    
    # Si hay menos candidatos que regantes, hacemos la grilla mas fina (25m)
    if len(candidates) < num_regantes:
        print("Grilla muy gruesa, densificando a 25m...")
        spacing = 25.0
        candidates = []
        x = min_x + spacing / 2.0
        while x < max_x:
            y = min_y + spacing / 2.0
            while y < max_y:
                pt = Point(x, y)
                if poly.contains(pt):
                    candidates.append(pt)
                y += spacing
            x += spacing
        print(f"Candidatos con grilla de {spacing}m: {len(candidates)}")

    if len(candidates) < num_regantes:
        print(f"Error critico: Aun con grilla de 25m no hay suficientes puntos ({len(candidates)} < {num_regantes})")
        return

    # Farthest Point Sampling (FPS) para distribucion uniforme
    print("Aplicando muestreo del punto mas lejano (FPS) para uniformidad...")
    coords = np.array([[pt.x, pt.y] for pt in candidates])
    centroid = poly.centroid
    centroid_coords = np.array([centroid.x, centroid.y])
    
    # El primer punto es el mas cercano al centroide
    first_idx = np.argmin(np.sum((coords - centroid_coords)**2, axis=1))
    selected_indices = [first_idx]
    
    # Inicializar distancias minimas al primer punto seleccionado
    min_distances = np.sum((coords - coords[first_idx])**2, axis=1)
    
    for _ in range(num_regantes - 1):
        next_idx = np.argmax(min_distances)
        selected_indices.append(next_idx)
        # Distancias al nuevo punto seleccionado
        new_distances = np.sum((coords - coords[next_idx])**2, axis=1)
        min_distances = np.minimum(min_distances, new_distances)
        
    selected_points = [candidates[idx] for idx in selected_indices]
    print(f"Generados exactamente {len(selected_points)} puntos distribuidos uniformemente.")

    # Proyectar puntos a EPSG:4326 (WGS 84)
    print("Proyectando coordenadas UTM 17S a WGS 84 (Lat/Lon)...")
    transformer = Transformer.from_crs("epsg:32717", "epsg:4326", always_xy=True)
    points_projected = []
    for pt in selected_points:
        lon, lat = transformer.transform(pt.x, pt.y)
        points_projected.append((lon, lat, pt.x, pt.y))

    # 5. Obtener ficha de referencia y columnas en data.gpkg
    conn = sqlite3.connect(DATA_GPKG)
    cursor = conn.cursor()

    # Identificar tabla de fichas
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    all_tables = [t[0] for t in cursor.fetchall()]
    fichas_table = next((t for t in all_tables if 'Fichas_Predios' in t and not any(x in t for x in ('rtree_','log_','gpkg_'))), None)
    if not fichas_table:
        print("Error: No se encontro la tabla de Fichas_Predios en data.gpkg")
        conn.close()
        return
    print(f"Tabla de fichas en data.gpkg: {fichas_table}")

    # Obtener columnas
    cursor.execute(f'PRAGMA table_info("{fichas_table}")')
    cols_info = cursor.fetchall()
    cols = [c[1] for c in cols_info]

    # Buscar fichas de referencia
    cursor.execute(f"SELECT * FROM \"{fichas_table}\" WHERE clave_catastral = '1702510040121'")
    ref_rows = cursor.fetchall()
    if not ref_rows:
        print("Error: No se encontraron fichas existentes para la clave 1702510040121 para usar como plantilla.")
        conn.close()
        return
    
    # Usamos la primera como plantilla de referencia
    ref_record = dict(zip(cols, ref_rows[0]))
    print(f"Ficha de plantilla cargada (ID original: {ref_record['id']})")

    # Columnas a copiar/clonar de la plantilla
    fields_to_copy = [
        'parroquia', 'caudal_tipo', 'tiene_reservorio', 'creado_por',
        'telefono_celular', 'telefono_casa', 'hijos_hombres', 'hijos_mujeres',
        'sector', 'tenencia_predio', 'nivel_instruccion', 'area_total',
        'org_riego', 'sector_comunidad', 'canal', 'area_riego', 'area_sin_riego',
        'frecuencia_riego', 'metodo_gravedad_pct', 'metodo_aspersion_pct', 'metodo_goteo_pct',
        'dias_riego', 'horas_turno', 'valor_tarifa', 'tipo_tarifa', 'agua_consumo',
        'energia_electrica', 'material_construccion', 'cota_msnm', 'conoce_presa',
        'como_elige_dir', 'nom_presidente', 'operador_sector', 'anios_sistema',
        'km_canal', 'recibio_capacitacion', 'le_gustaria_cap', 'temas_capacitacion',
        'caudal_valor', 'soberania_aliment_pct', 'act_productivas_pct', 'actividad_productiva',
        'observaciones', 'material_constr_otro', 'como_elige_dir_otro', 'comunidad',
        'sector_investigacion'
    ]

    # 6. Desactivar Triggers Espaciales
    print("Desactivando triggers espaciales temporalmente para evitar dependencias de SpatiaLite...")
    cursor.execute(f"SELECT name, sql FROM sqlite_master WHERE type='trigger' AND tbl_name='{fichas_table}'")
    triggers_info = cursor.fetchall()
    
    triggers_a_reactivar = []
    for t_name, t_sql in triggers_info:
        if t_sql and 'ST_' in t_sql:
            print(f"  - Desactivando trigger: {t_name}")
            cursor.execute(f'DROP TRIGGER IF EXISTS "{t_name}"')
            triggers_a_reactivar.append((t_name, t_sql))
    conn.commit()

    # 7. Ejecutar insercion masiva
    print(f"Insertando {num_regantes} nuevos regantes...")
    timestamp_actual = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
    
    insertados_count = 0
    try:
        for idx, item in enumerate(regantes):
            nombre_completo = item.get("nombre_completo", "").strip()
            # Separar nombres y apellidos por el primer espacio
            parts = nombre_completo.split(" ", 1)
            if len(parts) == 2:
                ape = parts[0].strip()
                nom = parts[1].strip()
            else:
                ape = nombre_completo
                nom = ""
                
            ced_limpia = clean_cedula(item.get("cedula", ""))
            
            # Generar datos del nuevo registro
            nuevo_id = f"{{{str(uuid.uuid4())}}}"
            # num_predio secuencial a partir del 3
            num_predio_nuevo = idx + 3
            codigo_final_nuevo = f"S-C-P{str(num_predio_nuevo).zfill(3)}"
            
            lon_wgs, lat_wgs, utm_x, utm_y = points_projected[idx]
            geom_bin = make_gpkg_point(lon_wgs, lat_wgs)

            # Construir dict para la insercion
            record = {}
            # Inicializar con nulos/vacios
            for c in cols:
                record[c] = None
                
            # Copiar campos comunes de la plantilla
            for f in fields_to_copy:
                record[f] = ref_record.get(f)
                
            # Asignar campos especificos
            record['id'] = nuevo_id
            record['geom'] = geom_bin
            record['cod_poligono'] = '1702510040121'
            record['clave_catastral'] = '1702510040121'
            record['num_predio'] = num_predio_nuevo
            record['codigo_final'] = codigo_final_nuevo
            record['propietario'] = ref_record.get('propietario', 'COLOMA ESCOBAR ALEJANDRA')
            record['apellidos'] = ape
            record['nombres'] = nom
            record['cedula'] = ced_limpia
            record['fecha_creacion'] = timestamp_actual
            record['coord_x_utm'] = utm_x
            record['coord_y_utm'] = utm_y
            
            # Construir sentencia INSERT
            columnas_insert = [f'"{c}"' for c in cols if c != 'fid_1'] # fid_1 es autoincremental
            valores_placeholder = [f":" + c for c in cols if c != 'fid_1']
            
            sql = f"""
                INSERT INTO "{fichas_table}" ({", ".join(columnas_insert)})
                VALUES ({", ".join(valores_placeholder)})
            """
            
            # Filtrar dict para el insert
            params = {c: record[c] for c in cols if c != 'fid_1'}
            cursor.execute(sql, params)
            insertados_count += 1

        conn.commit()
        print(f"Insercion masiva completada con exito. Se insertaron {insertados_count} registros.")

    except Exception as e:
        conn.rollback()
        print(f"Error durante la insercion masiva: {e}")
        print("Cambios revertidos.")
        insertados_count = 0

    # 8. Reactivar Triggers Espaciales
    if triggers_a_reactivar:
        print("Reactivando triggers espaciales...")
        for t_name, t_sql in triggers_a_reactivar:
            print(f"  - Reactivando trigger: {t_name}")
            cursor.execute(t_sql)
        conn.commit()

    conn.close()
    
    print("=" * 70)
    if insertados_count > 0:
        print(f"PROCESO FINALIZADO CON EXITO!")
        print(f"Se agregaron {insertados_count} regantes al predio Monteserin Bajo.")
        print(f"Base de datos de fichas actualizada en: {DATA_GPKG}")
    else:
        print("El proceso no se completo.")
    print("=" * 70)

if __name__ == "__main__":
    main()
