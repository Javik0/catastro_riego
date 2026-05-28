import json
data = json.load(open('public/geo/fichas_predios.geojson', 'r', encoding='utf-8'))
sin_com = []
for f in data['features']:
    c = f['properties'].get('comunidad', '')
    if not c:
        sc = f['properties'].get('sector_comunidad', '')
        if sc:
            sin_com.append(sc)
        else:
            sin_com.append('[VACIO]')

from collections import Counter
cnt = Counter(sin_com)
print(f"Fichas sin comunidad mapeada: {len(sin_com)}")
print(f"\nValores de sector_comunidad sin mapear ({len(cnt)} unicos):")
for v, n in cnt.most_common():
    print(f"  [{n:3d}] {v}")
