# -*- coding: utf-8 -*-
"""
Corrección definitiva de las 490 fichas de ALPAKA:
  - Asigna clave_catastral Y cod_poligono desde el Excel fuente.
  - Desactiva triggers GPKG para evitar errores de ST_IsEmpty.
"""
import sqlite3
import pandas as pd
import os

QFIELD_DIR = r'C:\Users\HP\QField\cloud\porotog_levantamiento_offline'
DATA_GPKG = os.path.join(QFIELD_DIR, 'data.gpkg')
CATASTRO_GPKG = os.path.join(QFIELD_DIR, 'CATASTROACTUALIZADORURALCATASTRORURALACTUALIZADO.gpkg')
EXCEL_PATH = r'C:\Users\HP\OneDrive\Escritorio\CAYAMBE CATASTRO RIEGO\ALPAKA FRACCIONAMIENTO CON CLAVES CATASTRALES.xlsx'

def clean_text(val):
    if pd.isna(val) or not val:
        return ""
    return str(val).strip().upper()

print("=" * 80)
print(" CORRECCIÓN DEFINITIVA: CLAVES CATASTRALES DE ALPAKA")
print("=" * 80)

# 1. Leer el Excel
df = pd.read_excel(EXCEL_PATH, header=None)
df_data = df.iloc[7:].copy()
df_data.columns = ['No', 'LOTE', 'AREA_UTIL', 'AREA_PROT_Q', 'AREA_PROT_C', 'AREA_BRUTA', 'PROPIETARIO', 'CC', 'CLAVE_CATASTRAL']
df_data = df_data.dropna(subset=['CLAVE_CATASTRAL', 'LOTE']).reset_index(drop=True)
print(f"[INFO] Excel cargado: {len(df_data)} registros con clave catastral.")

# 2. Verificar que esas claves existen en el catastro GPKG
conn_cat = sqlite3.connect(CATASTRO_GPKG)
cursor_cat = conn_cat.cursor()
cursor_cat.execute("SELECT clave_cata FROM CATASTROACTUALIZADORURALCATASTRORURALACTUALIZADO")
claves_catastro = set(str(r[0]).strip() for r in cursor_cat.fetchall() if r[0])
conn_cat.close()
print(f"[INFO] Polígonos en catastro GPKG: {len(claves_catastro)}")

claves_excel = set(clean_text(row['CLAVE_CATASTRAL']) for _, row in df_data.iterrows())
match_catastro = claves_excel & claves_catastro
print(f"[INFO] Claves del Excel que existen en catastro: {len(match_catastro)}/{len(claves_excel)}")

# 3. Conectar a la BD
conn = sqlite3.connect(DATA_GPKG)
cursor = conn.cursor()

cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [t[0] for t in cursor.fetchall()]
fichas_table = next((t for t in tables if 'Fichas_Predios' in t and not any(x in t for x in ('rtree_','log_','gpkg_'))), None)

# Estado ANTES
cursor.execute(f"""
    SELECT COUNT(*) FROM "{fichas_table}"
    WHERE comunidad = 'ALPAKA' AND (clave_catastral IS NULL OR clave_catastral = '')
""")
sin_clave_antes = cursor.fetchone()[0]
print(f"\n[ANTES] Fichas ALPAKA sin clave_catastral: {sin_clave_antes}")

# 4. DESACTIVAR triggers GPKG que usan funciones espaciales
cursor.execute("SELECT name, sql FROM sqlite_master WHERE type='trigger'")
triggers = cursor.fetchall()
fichas_triggers = [(t[0], t[1]) for t in triggers if fichas_table.lower() in (t[1] or '').lower()]
print(f"[INFO] Desactivando {len(fichas_triggers)} triggers de {fichas_table}...")

for tname, tsql in fichas_triggers:
    cursor.execute(f'DROP TRIGGER IF EXISTS "{tname}"')
conn.commit()

# 5. Aplicar la corrección
actualizados = 0
no_encontrados = []

for idx, row in df_data.iterrows():
    lote = clean_text(row['LOTE'])
    clave_cata = clean_text(row['CLAVE_CATASTRAL'])
    
    if not lote or not clave_cata:
        continue
    
    cursor.execute(f"""
        UPDATE "{fichas_table}"
        SET clave_catastral = ?, cod_poligono = ?
        WHERE comunidad = 'ALPAKA' AND TRIM(UPPER(codigo_final)) = ?
          AND (clave_catastral IS NULL OR clave_catastral = '')
    """, (clave_cata, clave_cata, lote))
    
    if cursor.rowcount > 0:
        actualizados += cursor.rowcount
    else:
        no_encontrados.append(lote)

conn.commit()

# 6. RESTAURAR triggers
print(f"[INFO] Restaurando {len(fichas_triggers)} triggers...")
for tname, tsql in fichas_triggers:
    try:
        cursor.execute(tsql)
    except Exception as e:
        print(f"  [AVISO] No se pudo restaurar trigger {tname}: {e}")
conn.commit()

# 7. Estado DESPUÉS
cursor.execute(f"""
    SELECT COUNT(*) FROM "{fichas_table}"
    WHERE comunidad = 'ALPAKA' AND (clave_catastral IS NULL OR clave_catastral = '')
""")
sin_clave_despues = cursor.fetchone()[0]
cursor.execute(f"""
    SELECT COUNT(*) FROM "{fichas_table}"
    WHERE comunidad = 'ALPAKA' AND (cod_poligono IS NULL OR cod_poligono = '')
""")
sin_codpol_despues = cursor.fetchone()[0]

print(f"\n[RESULTADO]")
print(f"  Fichas actualizadas: {actualizados}")
print(f"  Fichas sin clave_catastral (antes -> después): {sin_clave_antes} -> {sin_clave_despues}")
print(f"  Fichas sin cod_poligono (después): {sin_codpol_despues}")
if no_encontrados:
    print(f"  Lotes no encontrados ({len(no_encontrados)}): {no_encontrados[:10]}...")

# 8. Verificar muestra
cursor.execute(f"""
    SELECT codigo_final, clave_catastral, cod_poligono FROM "{fichas_table}"
    WHERE comunidad = 'ALPAKA' AND clave_catastral IS NOT NULL AND clave_catastral != ''
    LIMIT 10
""")
print(f"\nMuestra de fichas corregidas:")
for r in cursor.fetchall():
    print(f"  {r[0]} -> clave: {r[1]} | cod_pol: {r[2]}")

conn.close()
print(f"\n{'='*80}")
print(f" CORRECCION COMPLETADA EXITOSAMENTE")
print(f"{'='*80}")
