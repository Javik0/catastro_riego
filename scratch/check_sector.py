# -*- coding: utf-8 -*-
import json

with open('public/geo/fichas_predios.geojson', 'r', encoding='utf-8') as f:
    data = json.load(f)

features = data['features']
print(f'Total fichas en GeoJSON web: {len(features)}')

sectores = {}
sin_sector = 0
for ft in features:
    si = ft['properties'].get('sector_investigacion') or 'VACIO/NULL'
    sectores[si] = sectores.get(si, 0) + 1
    if si == 'VACIO/NULL':
        sin_sector += 1

print(f'\nDistribucion de sector_investigacion en la web:')
for k, v in sorted(sectores.items()):
    print(f'  {k}: {v}')
print(f'\nFichas sin sector en la web: {sin_sector}')

print(f'\nMuestra de fichas SIN sector_investigacion (primeras 15):')
count = 0
for ft in features:
    si = ft['properties'].get('sector_investigacion')
    if not si:
        p = ft['properties']
        cod = p.get('codigo_final', '?')
        com = p.get('comunidad', '?')
        par = p.get('parroquia', '?')
        sc = p.get('sector_comunidad', '?')
        tec = p.get('creado_por', '?')
        print(f'  {cod}: comunidad={com}, parroquia={par}, sector_com={sc}, tecnico={tec}')
        count += 1
        if count >= 15:
            break
