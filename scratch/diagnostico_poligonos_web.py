# -*- coding: utf-8 -*-
"""Diagnóstico: fichas que tienen punto GPS pero NO generan polígono catastral en la web."""
import sqlite3
import json
import os

QFIELD_DIR = r'C:\Users\HP\QField\cloud\porotog_levantamiento_offline'
DATA_GPKG = os.path.join(QFIELD_DIR, 'data.gpkg')
CATASTRO_GPKG = os.path.join(QFIELD_DIR, 'CATASTROACTUALIZADORURALCATASTRORURALACTUALIZADO.gpkg')
GEOJSON_CATASTRO = r'C:\Users\HP\OneDrive\Escritorio\CAYAMBE CATASTRO RIEGO\padron-app\public\geo\catastro_geo.geojson'
GEOJSON_FICHAS = r'C:\Users\HP\OneDrive\Escritorio\CAYAMBE CATASTRO RIEGO\padron-app\public\geo\fichas_predios.geojson'

# 1. Cargar polígonos ya exportados
with open(GEOJSON_CATASTRO, 'r', encoding='utf-8') as f:
    catastro = json.load(f)
claves_exportadas = set()
for feat in catastro['features']:
    c = feat['properties'].get('clave_cata')
    if c: claves_exportadas.add(str(c).strip())
print(f"Polígonos exportados en catastro_geo.geojson: {len(claves_exportadas)}")

# 2. Cargar fichas exportadas
with open(GEOJSON_FICHAS, 'r', encoding='utf-8') as f:
    fichas = json.load(f)

# 3. Fichas con coordenadas GPS PERO sin polígono exportado
sin_poligono = []
for feat in fichas['features']:
    p = feat['properties']
    geom = feat['geometry']
    if not geom or not geom.get('coordinates'):
        continue  # Sin GPS, no se muestra en mapa
    
    clave = str(p.get('cod_poligono') or p.get('clave_catastral') or '').strip()
    if not clave or clave not in claves_exportadas:
        sin_poligono.append({
            'id': p.get('id'),
            'cod_poligono': p.get('cod_poligono'),
            'clave_catastral': p.get('clave_catastral'),
            'comunidad': p.get('comunidad'),
            'creado_por': p.get('creado_por'),
            'es_ficha_hija': p.get('es_ficha_hija'),
            'estado': p.get('estado_investigacion'),
            'lat': geom['coordinates'][1],
            'lng': geom['coordinates'][0],
        })

print(f"\nFichas CON GPS pero SIN polígono catastral exportado: {len(sin_poligono)}")

# Desglosar por técnico
por_tecnico = {}
por_comunidad = {}
por_tipo = {'madre': 0, 'hija': 0}
sin_clave_total = 0
clave_no_match = 0

for f in sin_poligono:
    tec = f['creado_por'] or 'Sin Asignar'
    com = f['comunidad'] or 'Sin Comunidad'
    por_tecnico[tec] = por_tecnico.get(tec, 0) + 1
    por_comunidad[com] = por_comunidad.get(com, 0) + 1
    
    if f['es_ficha_hija'] in (1, True):
        por_tipo['hija'] += 1
    else:
        por_tipo['madre'] += 1
    
    clave = str(f['cod_poligono'] or f['clave_catastral'] or '').strip()
    if not clave:
        sin_clave_total += 1
    else:
        clave_no_match += 1

print(f"\nTipo: {por_tipo}")
print(f"Sin clave alguna: {sin_clave_total}")
print(f"Con clave pero no encontrada en catastro: {clave_no_match}")

print(f"\nPor TÉCNICO:")
for k, v in sorted(por_tecnico.items(), key=lambda x: x[1], reverse=True):
    print(f"  {k}: {v} fichas sin polígono")

print(f"\nPor COMUNIDAD:")
for k, v in sorted(por_comunidad.items(), key=lambda x: x[1], reverse=True)[:15]:
    print(f"  {k}: {v} fichas sin polígono")

# Muestra de fichas sin polígono
print(f"\nMuestra de 15 fichas sin polígono:")
for f in sin_poligono[:15]:
    print(f"  ID: {f['id'][:30] if f['id'] else '?'} | CodPol: {f['cod_poligono']} | Clave: {f['clave_catastral']} | Com: {f['comunidad']} | Tec: {f['creado_por']} | Hija: {f['es_ficha_hija']}")
