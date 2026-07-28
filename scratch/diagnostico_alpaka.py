# -*- coding: utf-8 -*-
"""Corregir las 490 fichas de ALPAKA: asignar clave_catastral Y cod_poligono desde el Excel."""
import sqlite3
import pandas as pd
import os

QFIELD_DIR = r'C:\Users\HP\QField\cloud\porotog_levantamiento_offline'
DATA_GPKG = os.path.join(QFIELD_DIR, 'data.gpkg')
EXCEL_PATH = r'C:\Users\HP\OneDrive\Escritorio\CAYAMBE CATASTRO RIEGO\ALPAKA FRACCIONAMIENTO CON CLAVES CATASTRALES.xlsx'

def clean_text(val):
    if pd.isna(val) or not val:
        return ""
    return str(val).strip().upper()

conn = sqlite3.connect(DATA_GPKG)
cursor = conn.cursor()

cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [t[0] for t in cursor.fetchall()]
fichas_table = next((t for t in tables if 'Fichas_Predios' in t and not any(x in t for x in ('rtree_','log_','gpkg_'))), None)

print("=" * 80)
print(" DIAGNOSTICANDO Y REPARANDO CLAVES ALPAKA")
print("=" * 80)

# 1. Leer el Excel
df = pd.read_excel(EXCEL_PATH, header=None)
df_data = df.iloc[7:].copy()
df_data.columns = ['No', 'LOTE', 'AREA_UTIL', 'AREA_PROT_Q', 'AREA_PROT_C', 'AREA_BRUTA', 'PROPIETARIO', 'CC', 'CLAVE_CATASTRAL']
df_data = df_data.dropna(subset=['CLAVE_CATASTRAL', 'LOTE']).reset_index(drop=True)
print(f"[INFO] Cargados {len(df_data)} registros del Excel de Alpaka con clave catastral.")

# 2. Revisar los codigo_final en la BD
cursor.execute(f"""
    SELECT DISTINCT TRIM(UPPER(codigo_final)) FROM "{fichas_table}" 
    WHERE comunidad = 'ALPAKA' AND (clave_catastral IS NULL OR clave_catastral = '')
""")
codigos_bd = set(r[0] for r in cursor.fetchall())
print(f"[INFO] Códigos únicos en BD ALPAKA sin clave: {len(codigos_bd)}")

# 3. Revisar los LOTE en el Excel
lotes_excel = set(clean_text(row['LOTE']) for _, row in df_data.iterrows())
print(f"[INFO] Lotes únicos en Excel: {len(lotes_excel)}")

# 4. Match
coinciden = codigos_bd & lotes_excel
no_en_excel = codigos_bd - lotes_excel
no_en_bd = lotes_excel - codigos_bd
print(f"[INFO] Coinciden exactamente: {len(coinciden)}")
print(f"[INFO] En BD pero NO en Excel: {len(no_en_excel)}")
print(f"[INFO] En Excel pero NO en BD: {len(no_en_bd)}")

if no_en_excel:
    print(f"\nMuestra de códigos en BD pero NO en Excel:")
    for c in list(no_en_excel)[:10]:
        print(f"  '{c}'")
if no_en_bd:
    print(f"\nMuestra de lotes en Excel pero NO en BD:")
    for c in list(no_en_bd)[:10]:
        print(f"  '{c}'")

conn.close()
