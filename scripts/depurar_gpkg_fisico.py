# -*- coding: utf-8 -*-
"""
Script de Depuración Física Final para el GeoPackage (data.gpkg)
Aplica de forma definitiva en la base de datos SQLite/GPKG local de QGIS:
  - Unificaciones de duplicados (eliminando fichas secundarias y reasociando cultivos/animales/lotes)
  - Imputaciones inteligentes de campos vacíos (por modas de día/técnico)
  - Correcciones manuales personalizadas de comunidades

Uso:
  python scripts/depurar_gpkg_fisico.py
"""

import sqlite3
import shutil
import os
import re
from datetime import datetime
from collections import Counter

# ── Rutas ──────────────────────────────────────────────────────
QFIELD_DIR = r'C:\Users\HP\QField\cloud\porotog_levantamiento_offline'
DATA_GPKG  = os.path.join(QFIELD_DIR, 'data.gpkg')
BACKUP_GPKG = os.path.join(QFIELD_DIR, 'data.gpkg.bak')

MAPEO_TECNICOS = {
    'u0_a314': 'Melany Jara', 'u0_a319': 'Melany Jara', 'jvk-editor': 'Melany Jara',
    'u0_a504': 'Adriana Cuascota', 'jvk-editor6': 'Adriana Cuascota',
    'u0_a279': 'Huguito Ipial', 'jvk-editor2': 'Huguito Ipial',
    'u0_a70': 'Pablo Barrionuevo', 'jvk-editor5': 'Pablo Barrionuevo',
    'u0_a330': 'Mayra Benavides', 'mayralisseth201': 'Mayra Benavides',
    'u0_a362': 'Martha Simbaña', 'u0_a335': 'Martha Simbaña', 'jvk-editor4': 'Martha Simbaña',
    'u0_a2': 'JVK-DIGITALIZACION', 'jvk-digitalizacion': 'JVK-DIGITALIZACION',
    'u0_a302': 'Dylan Chavez', 'jvk-editor3': 'Dylan Chavez', 'u0_a200': 'Melanie2'
}

VARIANTES_COMUNIDAD = [
    ("LARCACHACA", "LARCACHACA"), ("LARCACACHA", "LARCACHACA"), ("LARCACOCHA", "LARCACHACA"),
    ("LARCACHA", "LARCACHACA"), ("LA ARCACHA", "LARCACHACA"), ("ALCACHACA", "LARCACHACA"),
    ("HUASIPUNGO", "LARCACHACA"), ("GUASIPUNGO", "LARCACHACA"), ("GUALIMBURO", "LARCACHACA"),
    ("PARCELA", "LARCACHACA"), ("MORAS", "LARCACHACA"), ("PÁRAMO", "LARCACHACA"),
    ("LIBERAD", "LA LIBERTAD"), ("LIBERTAD", "LA LIBERTAD"), ("CENTRAL LIBERTAD", "LA LIBERTAD"),
    ("SAN ANTONIO", "SAN ANTONIO"), ("SAM ANTONIO", "SAN ANTONIO"), ("PAILLACO", "SAN ANTONIO"),
    ("PAYLLACHO", "SAN ANTONIO"), ("PAILLACHO", "SAN ANTONIO"),
    ("SAN JOSÉ", "SAN JOSÉ"), ("SAN JOSE", "SAN JOSÉ"), ("SAN  PEDRO", "SAN JOSÉ"),
    ("SAN PEDRO", "SAN JOSÉ"), ("YACUTIGRANA", "SAN JOSÉ"), ("PORTADAS", "SAN JOSÉ"),
    ("NINARUMI", "SAN JOSÉ"), ("NINA RUMI", "SAN JOSÉ"), ("INARUMI", "SAN JOSÉ"),
    ("ÑAVIPOGYO", "SAN JOSÉ"), ("ÑAVIPUYO", "SAN JOSÉ"), ("ÑAWIPUKYU", "SAN JOSÉ"),
    ("GUALIMPURO", "SAN JOSÉ"), ("LOS ANDES", "SAN JOSÉ"),
    ("MILAGRO", "MILAGRO"),
    ("ASOSIACION 17", "ASOCIACIÓN 17 DE JUNIO"), ("ASOCIACIÓN 17", "ASOCIACIÓN 17 DE JUNIO"),
    ("ASOCIACION 17", "ASOCIACIÓN 17 DE JUNIO"), ("17 DE JUNIO", "ASOCIACIÓN 17 DE JUNIO"),
    ("17 DE JULIO", "ASOCIACIÓN 17 DE JUNIO"),
    ("AVELLANEDA", "AVELLANEDA"),
    ("CHAMBITOLA", "CHAMBITOLA"), ("CHAMITOLA", "CHAMBITOLA"), ("CAMBITOLA", "CHAMBITOLA"), ("CHIMBATOLA", "CHAMBITOLA"),
    ("CANDELARIA", "LA CANDELARIA"),
    ("CARRERA", "CARRERA"), ("CARERRA", "CARRERA"), ("ACERO LOMA", "CARRERA"),
    ("MATÍAS IMBAGO", "MATÍAS IMBAGO"), ("MATIAS IMBAGO", "MATÍAS IMBAGO"),
    ("COCHAPAMBA", "COCHAPAMBA"),
    ("GRAN PODER", "JESÚS GRAN PODER"),
    ("SANTA BÁRBARA", "SANTA BÁRBARA"), ("SANTA BARBARA", "SANTA BÁRBARA"),
    ("ASOCIACIÓN POROTOG", "ASOCIACIÓN POROTOG"), ("ASOCIACION POROTOG", "ASOCIACIÓN POROTOG"),
    ("COMUNA POROTOG", "COMUNA POROTOG"),
    ("CORDILLERAS", "CORDILLERAS DE LOS ANDES"),
    ("COMUNA IZACATA", "COMUNA IZACATA"), ("COMUNA INSACATA", "COMUNA IZACATA"), ("IZACATA", "COMUNA IZACATA"), ("INSACATA", "COMUNA IZACATA"),
    ("IZACATA GRANDE", "IZACATA GRANDE"), ("INSACATA GRANDE", "IZACATA GRANDE"),
    ("LOS ANDES IZACATA", "LOS ANDES IZACATA"), ("LOS ANDES INSACATA", "LOS ANDES IZACATA"),
    ("LOMA GORDA", "LOMA GORDA"),
    ("SAN JACINTO", "SAN JACINTO"),
    ("CRUZ LOMA", "SAN JOSÉ"), ("CRUZLOMA", "SAN JOSÉ"),
    ("TOTORA", "SAN JOSÉ"), ("TOTORAS", "SAN JOSÉ"),
    ("MULAPOTERO", "SAN JOSÉ"), ("MULA POTRERO", "SAN JOSÉ"),
    ("BANDURRIA", "SAN JOSÉ"), ("BANDURIA", "SAN JOSÉ"),
    ("BARROLOMA", "SAN JOSÉ"), ("PLAYA", "SAN JOSÉ"), ("CALDERA", "SAN JOSÉ"),
    ("POCARALOMA", "SAN JOSÉ"), ("CENTRAL", "SAN JOSÉ"), ("CÓNDOR LOMA", "SAN JOSÉ"),
    ("PUKARA", "SAN JOSÉ"), ("SOPALO LOMA", "LA CANDELARIA"),
    ("GUANGUILQUI", "LARCACHACA"), ("CANGAHUA", "LARCACHACA"),
]
VARIANTES_COMUNIDAD.sort(key=lambda x: len(x[0]), reverse=True)

def normalizar_texto(texto):
    if not texto: return ""
    texto = texto.upper().strip()
    replacements = (
        ("Á", "A"), ("É", "E"), ("Í", "I"), ("Ó", "O"), ("Ú", "U"),
        ("Ñ", "N"), ("Ü", "U")
    )
    for a, b in replacements:
        texto = texto.replace(a, b)
    texto = re.sub(r'\s+', ' ', texto)
    return texto

def derivar_comunidad(sector_comunidad_valor):
    sc = (sector_comunidad_valor or '').upper().strip()
    if not sc: return None
    for variante, comunidad_oficial in VARIANTES_COMUNIDAD:
        if variante in sc:
            return comunidad_oficial
    return None

def main():
    print("═" * 65)
    print("  DEPURACIÓN FÍSICA FINAL DEL GEOPACKAGE (data.gpkg)")
    print("═" * 65)

    if not os.path.exists(DATA_GPKG):
        print(f"❌ Error: No se encontró {DATA_GPKG}")
        return

    # 1. Crear copia de seguridad
    print(f"📦 Creando respaldo de seguridad...")
    shutil.copy2(DATA_GPKG, BACKUP_GPKG)
    print(f"   💾 Respaldo guardado en: {BACKUP_GPKG}")

    # Conectar a la base de datos
    conn = sqlite3.connect(DATA_GPKG)
    cursor = conn.cursor()

    # 2. Identificar tablas dinámicamente
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    all_tables = [t[0] for t in cursor.fetchall()]

    fichas_table = next((t for t in all_tables if 'Fichas_Predios' in t and not any(x in t for x in ('rtree_','log_','gpkg_'))), None)
    cultivos_table = next((t for t in all_tables if 'Cultivos_Agricolas' in t and not any(x in t for x in ('rtree_','log_','gpkg_'))), None)
    animales_table = next((t for t in all_tables if 'Animales_Especies' in t and not any(x in t for x in ('rtree_','log_','gpkg_'))), None)
    predios_table = 'Predios_Adicionales' # Nombre estático en GPKG

    if not fichas_table:
        print("❌ Error: No se encontró la tabla de Fichas_Predios")
        conn.close()
        return
    print(f"✓ Tabla Fichas: {fichas_table}")
    print(f"✓ Tabla Cultivos: {cultivos_table}")
    print(f"✓ Tabla Animales: {animales_table}")
    print(f"✓ Tabla Predios Adicionales: {predios_table}")

    # Obtener info de columnas para Fichas
    cursor.execute(f'PRAGMA table_info("{fichas_table}")')
    fichas_cols = [c[1] for c in cursor.fetchall()]

    # ── Desactivar triggers espaciales temporalmente ────────────────
    print("\n⚠️  Desactivando triggers espaciales temporalmente para evitar dependencias de SpatiaLite...")
    cursor.execute(f"SELECT name, sql FROM sqlite_master WHERE type='trigger' AND tbl_name='{fichas_table}'")
    triggers_info = cursor.fetchall()
    
    triggers_a_reactivar = []
    for t_name, t_sql in triggers_info:
        if t_sql and 'ST_' in t_sql:
            print(f"  - Desactivando trigger: {t_name}")
            cursor.execute(f'DROP TRIGGER IF EXISTS "{t_name}"')
            triggers_a_reactivar.append((t_name, t_sql))
    conn.commit()

    # Cargar todos los registros físicos actuales
    cursor.execute(f'SELECT * FROM "{fichas_table}"')
    rows = cursor.fetchall()
    fichas_list = []
    for r in rows:
        item = {fichas_cols[i]: r[i] for i in range(len(fichas_cols))}
        fichas_list.append(item)

    print(f"\n📊 Registros de fichas leídos: {len(fichas_list)}")

    # 3. Detectar duplicados (mismo algoritmo que export_geojson)
    regantes_por_cedula = {}
    fichas_sin_cedula_valida = []

    for f in fichas_list:
        ced_norm = (f.get('cedula') or "").strip()
        es_ced_valida = len(ced_norm) == 10 and ced_norm.isdigit()
        f['es_ced_valida'] = es_ced_valida
        f['ced_norm'] = ced_norm
        
        ape_norm = normalizar_texto(f.get('apellidos'))
        nom_norm = normalizar_texto(f.get('nombres'))
        f['nombre_completo_normalizado'] = f"{ape_norm} {nom_norm}".strip()
        
        if es_ced_valida:
            if ced_norm not in regantes_por_cedula:
                regantes_por_cedula[ced_norm] = []
            regantes_por_cedula[ced_norm].append(f)
        else:
            fichas_sin_cedula_valida.append(f)

    regantes_por_nombre = {}
    for f in fichas_sin_cedula_valida:
        name = f['nombre_completo_normalizado']
        if not name: name = "SIN_NOMBRE_REGISTRADO"
        if name not in regantes_por_nombre:
            regantes_por_nombre[name] = []
        regantes_por_nombre[name].append(f)

    duplicados_cedula = {ced: lista for ced, lista in regantes_por_cedula.items() if len(lista) > 1}
    duplicados_nombre = {name: lista for name, lista in regantes_por_nombre.items() if len(lista) > 1 and name != "SIN_NOMBRE_REGISTRADO"}

    print(f"🔍 Duplicados detectados por Cédula: {len(duplicados_cedula)} regantes")
    print(f"🔍 Duplicados detectados por Nombre: {len(duplicados_nombre)} regantes")

    # Mapeo de unificaciones físicas
    ficha_redirect_map = {}
    virtual_predios_adicionales = []

    # Procesar duplicados por cédula
    for ced, lista in duplicados_cedula.items():
        lista_ordenada = sorted(lista, key=lambda x: x.get('area_total') or 0.0, reverse=True)
        ficha_madre = lista_ordenada[0]
        fichas_secundarias = lista_ordenada[1:]
        
        for fs in fichas_secundarias:
            ficha_redirect_map[fs['id']] = ficha_madre['id']
            tec = MAPEO_TECNICOS.get(fs.get('creado_por'), fs.get('creado_por') or "")
            obs = f"Unificación física. Ficha original: {fs['id']}. Técnico: {tec} en {fs.get('fecha_creacion')}."
            if fs.get('observaciones'):
                obs += f" Obs. Orig: {fs['observaciones']}"
            
            ar_val = fs.get('area_riego') or 0.0
            if ar_val == 0:
                ar_val = fs.get('area_total') or 0.0

            virtual_predios_adicionales.append({
                'id_adicional': fs['id'],
                'ficha_id': ficha_madre['id'],
                'clave_catastral_otro': fs.get('clave_catastral') or "",
                'area_total_otro': fs.get('area_total') or 0.0,
                'area_riego_otro': ar_val,
                'area_sin_riego_otro': 0.0,
                'area_lote_asignado_otro': fs.get('area_total') or 0.0,
                'tiene_observaciones': 1,
                'observaciones_otro': obs
            })

    # Procesar duplicados por nombre
    for name, lista in duplicados_nombre.items():
        lista_ordenada = sorted(lista, key=lambda x: x.get('area_total') or 0.0, reverse=True)
        ficha_madre = lista_ordenada[0]
        fichas_secundarias = lista_ordenada[1:]
        
        for fs in fichas_secundarias:
            ficha_redirect_map[fs['id']] = ficha_madre['id']
            tec = MAPEO_TECNICOS.get(fs.get('creado_por'), fs.get('creado_por') or "")
            obs = f"Unificación física (coincidencia de Nombre). Ficha original: {fs['id']}. Técnico: {tec} en {fs.get('fecha_creacion')}."
            if fs.get('observaciones'):
                obs += f" Obs. Orig: {fs['observaciones']}"
            
            ar_val = fs.get('area_riego') or 0.0
            if ar_val == 0:
                ar_val = fs.get('area_total') or 0.0

            virtual_predios_adicionales.append({
                'id_adicional': fs['id'],
                'ficha_id': ficha_madre['id'],
                'clave_catastral_otro': fs.get('clave_catastral') or "",
                'area_total_otro': fs.get('area_total') or 0.0,
                'area_riego_otro': ar_val,
                'area_sin_riego_otro': 0.0,
                'area_lote_asignado_otro': fs.get('area_total') or 0.0,
                'tiene_observaciones': 1,
                'observaciones_otro': obs
            })

    print(f"🔄 Se van a unificar {len(ficha_redirect_map)} fichas secundarias en sus fichas madre.")

    # 4. Reasociar tablas hijas y crear predios adicionales en la BD física
    print("\n🛠️  Aplicando reasociaciones y unificaciones físicas en la base de datos...")
    
    # Insertar en Predios_Adicionales
    predios_insertados = 0
    for pa in virtual_predios_adicionales:
        # Verificar si ya existe este id_adicional para no duplicar en caso de ejecuciones repetidas
        cursor.execute(f'SELECT COUNT(*) FROM "{predios_table}" WHERE id_adicional = ?', (pa['id_adicional'],))
        if cursor.fetchone()[0] == 0:
            cursor.execute(f'''
                INSERT INTO "{predios_table}" (id_adicional, ficha_id, clave_catastral_otro, area_total_otro, area_riego_otro, area_sin_riego_otro, area_lote_asignado_otro, tiene_observaciones, observaciones_otro)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                pa['id_adicional'], pa['ficha_id'], pa['clave_catastral_otro'],
                pa['area_total_otro'], pa['area_riego_otro'], pa['area_sin_riego_otro'],
                pa['area_lote_asignado_otro'], pa['tiene_observaciones'], pa['observaciones_otro']
            ))
            predios_insertados += 1

    print(f"  ✓ {predios_insertados} parcelas secundarias insertadas en la tabla {predios_table}.")

    # Reasociar cultivos
    cultivos_modificados = 0
    if cultivos_table:
        for f_secundaria, f_madre in ficha_redirect_map.items():
            cursor.execute(f'UPDATE "{cultivos_table}" SET ficha_id = ? WHERE ficha_id = ?', (f_madre, f_secundaria))
            cultivos_modificados += cursor.rowcount
    print(f"  ✓ {cultivos_modificados} registros de cultivos reasociados.")

    # Reasociar animales
    animales_modificados = 0
    if animales_table:
        for f_secundaria, f_madre in ficha_redirect_map.items():
            cursor.execute(f'UPDATE "{animales_table}" SET ficha_id = ? WHERE ficha_id = ?', (f_madre, f_secundaria))
            animales_modificados += cursor.rowcount
    print(f"  ✓ {animales_modificados} registros de animales pecuarios reasociados.")

    # Eliminar fichas secundarias
    fichas_eliminadas = 0
    for f_secundaria in ficha_redirect_map.keys():
        cursor.execute(f'DELETE FROM "{fichas_table}" WHERE id = ?', (f_secundaria,))
        fichas_eliminadas += cursor.rowcount
    print(f"  ✓ {fichas_eliminadas} fichas secundarias duplicadas eliminadas de {fichas_table}.")

    # 5. Imputaciones inteligentes y correcciones manuales
    print("\n🧹 Aplicando imputación de campos vacíos y correcciones manuales de comunidad...")

    # Cargar de nuevo las fichas restantes (las principales y las no unificadas) para calcular modas
    cursor.execute(f'SELECT * FROM "{fichas_table}"')
    rows_clean = cursor.fetchall()
    fichas_restantes = []
    for r in rows_clean:
        item = {fichas_cols[i]: r[i] for i in range(len(fichas_cols))}
        fichas_restantes.append(item)

    # Agrupar por día y técnico
    def get_dia(fecha_str):
        if not fecha_str: return None
        return str(fecha_str)[:10]

    grupos_dia_tec = {}
    grupos_dia = {}
    for f in fichas_restantes:
        dia = get_dia(f.get('fecha_creacion'))
        tec = f.get('creado_por')
        if not dia or not tec: continue
        
        key_dt = (dia, tec)
        if key_dt not in grupos_dia_tec: grupos_dia_tec[key_dt] = []
        grupos_dia_tec[key_dt].append(f)
        
        if dia not in grupos_dia: grupos_dia[dia] = []
        grupos_dia[dia].append(f)

    def calc_modas(grupo):
        parroquias = [fg['parroquia'] for fg in grupo if fg.get('parroquia')]
        sectores = [fg['sector'] for fg in grupo if fg.get('sector')]
        comunidades = [fg['comunidad'] for fg in grupo if fg.get('comunidad')]
        caudal_tipos = [fg['caudal_tipo'] for fg in grupo if fg.get('caudal_tipo')]
        frecuencias = [fg['frecuencia_riego'] for fg in grupo if fg.get('frecuencia_riego')]
        caudales = [fg['caudal_valor'] for fg in grupo if fg.get('caudal_valor') and fg['caudal_valor'] > 0]
        
        metodos = []
        for fg in grupo:
            asp = fg.get('metodo_aspersion_pct') or 0
            grav = fg.get('metodo_gravedad_pct') or 0
            got = fg.get('metodo_goteo_pct') or 0
            if asp > 0 or grav > 0 or got > 0:
                metodos.append((asp, grav, got))
                
        return {
            'parroquia': Counter(parroquias).most_common(1)[0][0] if parroquias else 'CANGAHUA',
            'sector': Counter(sectores).most_common(1)[0][0] if sectores else None,
            'comunidad': Counter(comunidades).most_common(1)[0][0] if comunidades else None,
            'caudal_tipo': Counter(caudal_tipos).most_common(1)[0][0] if caudal_tipos else None,
            'frecuencia_riego': Counter(frecuencias).most_common(1)[0][0] if frecuencias else None,
            'caudal_valor': sum(caudales)/len(caudales) if caudales else None,
            'metodo_riego': Counter(metodos).most_common(1)[0][0] if metodos else None
        }

    modas_dia_tec = {key: calc_modas(fs) for key, fs in grupos_dia_tec.items()}
    modas_dia = {dia: calc_modas(fs) for dia, fs in grupos_dia.items()}

    # Listas de reasignación manual basadas en la lógica de App.tsx
    cidsToSanJose = [
        '1711308682', '1717858011', '1716464753', '1715022719', 
        '1722217930', '1707701726', '1714912233', '1712437407', '1707701700',
        '1708098619', '1715377154'
    ]
    clavesToSanJose = [
        '1702520560029', '1702520560018', '1702520560013', '1702520560004',
        '1702520560048', '1702520550007', '1702520980102', '1702520560039', '1702520980069',
        '1702520560058', '1702521400047', '170251400047'
    ]
    cidsToLaLibertad = [
        '1715033013', '1708546179', '1711492486', '1718241027', '1721253639', '1711492148', '1711589687'
    ]
    clavesToLaLibertad = [
        '1702520540066', '1702520530014', '1702521020084', '1702520690010', '1702521100076', '1702520540014', '1702521020030'
    ]
    cidsToSanAntonio = ['1709870602']
    clavesToSanAntonio = ['1702520680118']

    fichas_actualizadas = 0
    for f in fichas_restantes:
        fid = f['id']
        ced = (f.get('cedula') or '').strip()
        clav = (f.get('clave_catastral') or '').strip()
        fecha_creacion = f.get('fecha_creacion') or ""
        creado_por = f.get('creado_por') or ""
        dia = get_dia(fecha_creacion)
        
        # 1. Determinar comunidad inicial limpia
        com_orig = (f.get('comunidad') or '').replace('LARCACOHA', 'LARCACHACA').replace('LARCACOCHA', 'LARCACHACA').replace('None', '').strip()
        if not com_orig:
            com_orig = derivar_comunidad(f.get('sector_comunidad'))
            
        com_final = com_orig
        
        # 2. Imputación inteligente de comunidad por fecha/hora
        if not com_final and dia:
            # Reglas generales por dia
            if '2026-05-22' in fecha_creacion:
                com_final = 'LA LIBERTAD'
            elif '2026-05-26' in fecha_creacion:
                com_final = 'CHAMBITOLA'
            elif '2026-05-25' in fecha_creacion:
                # Regla de hora para el lunes 25 de mayo
                try:
                    # Formato ISO e.g. 2026-05-25T09:30:48.842Z o similar
                    t_str = fecha_creacion.split('T')[1][:5]
                    hour = int(t_str.split(':')[0])
                    if hour >= 8 and hour < 15:
                        com_final = 'MILAGRO'
                    elif hour >= 15:
                        com_final = 'ASOCIACIÓN 17 DE JUNIO'
                except:
                    pass
            
            # Si sigue vacía, usar la moda del día/técnico
            if not com_final:
                m_dt = modas_dia_tec.get((dia, creado_por), {})
                m_d = modas_dia.get(dia, {})
                com_final = m_dt.get('comunidad') or m_d.get('comunidad')

        # 3. Corrección para el 24 de mayo (Asociación 17 de Junio -> San José)
        if dia == '2026-05-24' and com_final in ('ASOCIACIÓN 17 DE JUNIO', 'ASOCIACION 17 DE JUNIO'):
            com_final = 'SAN JOSÉ'

        # 4. Overrides manuales explícitos
        if ced in cidsToSanJose or clav in clavesToSanJose:
            com_final = 'SAN JOSÉ'
        elif ced in cidsToLaLibertad or clav in clavesToLaLibertad:
            com_final = 'LA LIBERTAD'
        elif ced in cidsToSanAntonio or clav in clavesToSanAntonio:
            com_final = 'SAN ANTONIO'

        # 5. Imputar otros campos nulos o vacíos
        parroquia_final = f.get('parroquia')
        if not parroquia_final:
            m_dt = modas_dia_tec.get((dia, creado_por), {})
            m_d = modas_dia.get(dia, {})
            parroquia_final = m_dt.get('parroquia') or m_d.get('parroquia') or 'CANGAHUA'

        sector_final = f.get('sector')
        if not sector_final:
            m_dt = modas_dia_tec.get((dia, creado_por), {})
            m_d = modas_dia.get(dia, {})
            sector_final = m_dt.get('sector') or m_d.get('sector') or 'Porotog'

        caudal_tipo_final = f.get('caudal_tipo')
        if not caudal_tipo_final:
            m_dt = modas_dia_tec.get((dia, creado_por), {})
            m_d = modas_dia.get(dia, {})
            caudal_tipo_final = m_dt.get('caudal_tipo') or m_d.get('caudal_tipo')

        frecuencia_final = f.get('frecuencia_riego')
        if not frecuencia_final:
            m_dt = modas_dia_tec.get((dia, creado_por), {})
            m_d = modas_dia.get(dia, {})
            frecuencia_final = m_dt.get('frecuencia_riego') or m_d.get('frecuencia_riego')

        caudal_valor_final = f.get('caudal_valor') or 0.0
        if caudal_valor_final == 0.0:
            m_dt = modas_dia_tec.get((dia, creado_por), {})
            m_d = modas_dia.get(dia, {})
            val = m_dt.get('caudal_valor') or m_d.get('caudal_valor')
            if val:
                caudal_valor_final = round(val, 2)

        asp_pct = f.get('metodo_aspersion_pct') or 0
        grav_pct = f.get('metodo_gravedad_pct') or 0
        got_pct = f.get('metodo_goteo_pct') or 0
        if asp_pct == 0 and grav_pct == 0 and got_pct == 0:
            m_dt = modas_dia_tec.get((dia, creado_por), {})
            m_d = modas_dia.get(dia, {})
            val_m = m_dt.get('metodo_riego') or m_d.get('metodo_riego')
            if val_m:
                asp_pct, grav_pct, got_pct = val_m

        area_total_val = f.get('area_total') or 0.0
        area_riego_val = f.get('area_riego') or 0.0
        area_sin_riego_val = f.get('area_sin_riego') or 0.0
        if area_riego_val == 0.0:
            area_riego_val = area_total_val
            area_sin_riego_val = 0.0

        # Escribir de vuelta a SQLite
        cursor.execute(f'''
            UPDATE "{fichas_table}"
            SET comunidad = ?,
                parroquia = ?,
                sector = ?,
                caudal_tipo = ?,
                frecuencia_riego = ?,
                caudal_valor = ?,
                metodo_aspersion_pct = ?,
                metodo_gravedad_pct = ?,
                metodo_goteo_pct = ?,
                area_riego = ?,
                area_sin_riego = ?
            WHERE id = ?
        ''', (
            com_final, parroquia_final, sector_final, caudal_tipo_final,
            frecuencia_final, caudal_valor_final, asp_pct, grav_pct, got_pct,
            area_riego_val, area_sin_riego_val, fid
        ))
        fichas_actualizadas += 1

    conn.commit()
    print(f"  ✓ {fichas_actualizadas} fichas principales actualizadas con comunidades correctas e imputaciones.")

    # 6. Comprobación de integridad final
    print("\n🔍 Validando resultados finales en la base de datos...")
    
    # Recuento final de fichas
    cursor.execute(f'SELECT COUNT(*) FROM "{fichas_table}"')
    final_count = cursor.fetchone()[0]
    print(f"  ✓ Fichas físicas restantes en {fichas_table}: {final_count}")
    if final_count == 1593:
        print("  🎉 ¡ÉXITO! Se alcanzaron exactamente las 1,593 fichas limpias principales.")
    else:
        print(f"  ⚠ Alerta: Se esperaban 1,593 fichas pero hay {final_count}.")

    # Verificar huérfanos de cultivos
    if cultivos_table:
        cursor.execute(f'''
            SELECT COUNT(*) FROM "{cultivos_table}" 
            WHERE ficha_id NOT IN (SELECT id FROM "{fichas_table}")
        ''')
        c_huerfanos = cursor.fetchone()[0]
        print(f"  ✓ Cultivos huérfanos detectados: {c_huerfanos}")

    # Verificar huérfanos de animales
    if animales_table:
        cursor.execute(f'''
            SELECT COUNT(*) FROM "{animales_table}" 
            WHERE ficha_id NOT IN (SELECT id FROM "{fichas_table}")
        ''')
        a_huerfanos = cursor.fetchone()[0]
        print(f"  ✓ Animales huérfanos detectados: {a_huerfanos}")

    # ── Reactivar triggers espaciales ──────────────────────────────
    if triggers_a_reactivar:
        print("\n⚡ Reactivando triggers espaciales en la base de datos...")
        for t_name, t_sql in triggers_a_reactivar:
            print(f"  - Reactivando trigger: {t_name}")
            cursor.execute(t_sql)
        conn.commit()

    conn.close()
    print("\n" + "═" * 65)
    print("  ✅ PROCESO DE DEPURACIÓN FÍSICA COMPLETADO CON ÉXITO")
    print("═" * 65)

if __name__ == '__main__':
    main()
