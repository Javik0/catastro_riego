# -*- coding: utf-8 -*-
import sqlite3
import os

QFIELD_DIR = r'C:\Users\HP\QField\cloud\porotog_levantamiento_offline'
DATA_GPKG = os.path.join(QFIELD_DIR, 'data.gpkg')
CATASTRO_GPKG = os.path.join(QFIELD_DIR, 'CATASTROACTUALIZADORURALCATASTRORURALACTUALIZADO.gpkg')

conn = sqlite3.connect(DATA_GPKG)
cursor = conn.cursor()

cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [t[0] for t in cursor.fetchall()]
fichas_table = next((t for t in tables if 'Fichas_Predios' in t and not any(x in t for x in ('rtree_','log_','gpkg_'))), None)

# Claves de fichas MADRE y HIJA
cursor.execute(f"SELECT DISTINCT clave_catastral FROM \"{fichas_table}\" WHERE (es_ficha_hija IS NULL OR es_ficha_hija = 0) AND NOT (id LIKE 'H-%') AND clave_catastral IS NOT NULL AND clave_catastral != ''")
claves_madre = set(r[0] for r in cursor.fetchall())

cursor.execute(f"SELECT DISTINCT clave_catastral FROM \"{fichas_table}\" WHERE (es_ficha_hija = 1 OR id LIKE 'H-%') AND clave_catastral IS NOT NULL AND clave_catastral != ''")
claves_hija = set(r[0] for r in cursor.fetchall())

hijas_unicas = claves_hija - claves_madre

print(f"Claves distintas en fichas MADRE: {len(claves_madre)}")
print(f"Claves distintas en fichas HIJA ÚNICAS: {len(hijas_unicas)}")

conn_cat = sqlite3.connect(CATASTRO_GPKG)
cur_cat = conn_cat.cursor()
cat_table = 'CATASTROACTUALIZADORURALCATASTRORURALACTUALIZADO'

def count_found(claves_set):
    claves_list = list(claves_set)
    chunk_size = 500
    found = 0
    for i in range(0, len(claves_list), chunk_size):
        chunk = claves_list[i:i+chunk_size]
        placeholders = ','.join('?' * len(chunk))
        cur_cat.execute(f'SELECT COUNT(DISTINCT clave_cata) FROM "{cat_table}" WHERE clave_cata IN ({placeholders})', chunk)
        found += cur_cat.fetchone()[0]
    return found

found_madre = count_found(claves_madre)
found_hunas = count_found(hijas_unicas)

print(f"\nPolígonos en catastro rural para fichas MADRE: {found_madre} / {len(claves_madre)}")
print(f"Polígonos en catastro rural para fichas HIJA ÚNICAS: {found_hunas} / {len(hijas_unicas)}")

# Total polígonos exportados en export_catastro:
cursor.execute(f"SELECT DISTINCT COALESCE(cod_poligono, clave_catastral) FROM \"{fichas_table}\" WHERE COALESCE(cod_poligono, clave_catastral) IS NOT NULL")
todas_claves = set(r[0] for r in cursor.fetchall())
found_todas = count_found(todas_claves)
print(f"\nTotal polígonos exportados para TODAS las fichas: {found_todas} / {len(todas_claves)}")

conn.close()
conn_cat.close()
