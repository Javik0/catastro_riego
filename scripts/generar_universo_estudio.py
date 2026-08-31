# -*- coding: utf-8 -*-
"""
Universo de estudio del proyecto — cifras para el Dashboard.

Pedido de Armando por WhatsApp (30-ago-2026) y de JAVIKO (31-ago-2026):
mostrar el área total del universo de estudio (el catastro RURAL completo),
cuánta área y cuántos predios están investigados, cuánto resta, y que el
cuadre sea exacto. Además, en cuántos predios están las fichas principales y
en cuántos las adicionales.

El Dashboard mostraba «24.452» fijo en el código (firestoreService.ts) y ya
estaba desactualizado. Este script publica las cifras CALCULADAS en
public/geo/universo_estudio.json para que la web las lea como fuente única y
no vuelvan a envejecer.

CÓMO SE CALCULA
---------------
· Universo = catastro RURAL completo de catastro_poligonos.json (fid <
  1.000.000; los urbanos van desplazados +1.000.000 en el export y NO son
  parte del universo de estudio). Área por Shoelace equirectangular sobre
  WGS84 — a la latitud del proyecto (~0°) el error es despreciable, y se
  verifica contra la cifra oficial (ver abajo).
· Investigado = los predios de catastro_geo.geojson (los mismos 5.987 del
  mapa y el Dashboard) con el área oficial de superficie_por_comunidad.json
  (fuente única, regla 12). El área Shoelace de esos mismos polígonos se usa
  SOLO para verificar que ambas mediciones coinciden; si difieren más del
  1 % el script avisa y no publica.
· Resto = universo − investigado, por resta directa: el cuadre es exacto por
  construcción (pedido explícito de JAVIKO).
· Predios de fichas principales / adicionales: cada ficha resuelve su predio
  por clave_catastral y cod_poligono como respaldo (regla 14), contra el set
  de claves investigadas. Un predio con ficha principal Y adicional cuenta
  en ambos grupos (por eso principales + adicionales ≥ investigados).

Se corre con el Python del PATH (no lee el data.gpkg):
    python -X utf8 scripts/generar_universo_estudio.py
"""

import json
import math
import os
import sys

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
GEO = os.path.join(BASE, 'public', 'geo')
SALIDA = os.path.join(GEO, 'universo_estudio.json')

R = 6378137.0
FID_URBANO = 1000000  # export_geojson.py desplaza los fid urbanos +1e6


def leer(nombre):
    with open(os.path.join(GEO, nombre), encoding='utf-8') as f:
        return json.load(f)


def area_anillo(ring):
    lat0 = math.radians(sum(p[1] for p in ring) / len(ring))
    k = math.cos(lat0)
    a = 0.0
    for i in range(len(ring)):
        x1, y1 = ring[i]
        x2, y2 = ring[(i + 1) % len(ring)]
        a += (math.radians(x1) * k * R * math.radians(y2) * R -
              math.radians(x2) * k * R * math.radians(y1) * R)
    return abs(a) / 2


def area_geom(geom):
    coords = (geom['coordinates'] if geom['type'] == 'MultiPolygon'
              else [geom['coordinates']])
    total = 0.0
    for poly in coords:
        total += area_anillo(poly[0]) - sum(area_anillo(r) for r in poly[1:])
    return total


def main():
    poligonos = leer('catastro_poligonos.json')
    investigados = leer('catastro_geo.geojson')['features']
    fichas = [x['properties'] for x in leer('fichas_predios.geojson')['features']]
    sup = leer('superficie_por_comunidad.json')['total']

    # ── universo: catastro rural completo ──
    rural = {int(k): g for k, g in poligonos.items() if int(k) < FID_URBANO}
    universo_n = len(rural)
    universo_ha = sum(area_geom(g) for g in rural.values()) / 10000.0

    # ── investigado: cifras oficiales + verificación de la medición ──
    inv_n = len(investigados)
    inv_ha_oficial = sup['superficie_catastral_ha']
    if inv_n != sup['predios_catastrales']:
        print(f'⚠ catastro_geo trae {inv_n} predios y la fuente única '
              f'{sup["predios_catastrales"]} — revisar antes de publicar')
        sys.exit(1)
    fids_inv = {f['properties']['fid'] for f in investigados}
    inv_ha_shoelace = sum(area_geom(rural[fid]) for fid in fids_inv
                          if fid in rural) / 10000.0
    desvio = abs(inv_ha_shoelace - inv_ha_oficial) / inv_ha_oficial * 100
    if desvio > 1.0:
        print(f'⚠ La medición propia ({inv_ha_shoelace:,.2f} ha) difiere '
              f'{desvio:.2f} % de la oficial ({inv_ha_oficial:,.2f} ha) — '
              'no se publica')
        sys.exit(1)

    # ── resto: por resta directa, cuadre exacto por construcción ──
    resto_n = universo_n - inv_n
    resto_ha = round(universo_ha - inv_ha_oficial, 2)
    universo_ha = round(inv_ha_oficial + resto_ha, 2)  # sin residuo de redondeo

    # ── predios de principales y de adicionales (regla 14), con sus áreas ──
    area_por_clave = {}
    for f in investigados:
        clave = str(f['properties'].get('clave_cata') or '').strip()
        if clave:
            area_por_clave[clave] = (area_por_clave.get(clave, 0.0) +
                                     (f['properties'].get('area_predi') or 0))
    claves_inv = set(area_por_clave)
    pri, adi = set(), set()
    for p in fichas:
        clave = (str(p.get('clave_catastral') or '').strip() or
                 str(p.get('cod_poligono') or '').strip())
        if clave not in claves_inv:
            continue
        (adi if p.get('es_ficha_hija') == 1 else pri).add(clave)

    # Área que ocupan: los (pocos) predios con ficha principal Y adicional se
    # asignan a principales para que principales + adicionales = investigado
    # EXACTO (pedido de JAVIKO, 31-ago-2026: «debe cuadrar con el total
    # investigado de ha»). La suma de area_predi de catastro_geo coincide al
    # centavo con la cifra oficial (verificado); adicionales sale por resta
    # para que el redondeo no deje residuo.
    area_pri = round(sum(area_por_clave[c] for c in pri) / 10000.0, 2)
    area_adi = round(inv_ha_oficial - area_pri, 2)

    salida = {
        'generado_por': 'scripts/generar_universo_estudio.py',
        'nota': ('Universo de estudio = catastro RURAL completo. El resto se '
                 'obtiene por resta contra el área oficial de '
                 'superficie_por_comunidad.json: el cuadre es exacto por '
                 'construcción. Un predio con ficha principal y adicional '
                 'cuenta en ambos grupos.'),
        'universo': {'predios': universo_n, 'area_ha': universo_ha},
        'investigado': {'predios': inv_n, 'area_ha': inv_ha_oficial,
                        'predios_de_principales': len(pri),
                        'predios_de_adicionales': len(adi),
                        'predios_en_ambos': len(pri & adi),
                        'area_de_principales_ha': area_pri,
                        'area_de_adicionales_ha': area_adi},
        'resto': {'predios': resto_n, 'area_ha': resto_ha},
        'verificacion': {'area_investigada_shoelace_ha':
                         round(inv_ha_shoelace, 2),
                         'desvio_pct': round(desvio, 3)},
    }
    with open(SALIDA, 'w', encoding='utf-8') as f:
        json.dump(salida, f, ensure_ascii=False, indent=1)

    print(f'✔ universo_estudio.json — universo {universo_n:,} predios / '
          f'{universo_ha:,.2f} ha = investigado {inv_n:,} / '
          f'{inv_ha_oficial:,.2f} + resto {resto_n:,} / {resto_ha:,.2f}')
    print(f'  medición propia de lo investigado: {inv_ha_shoelace:,.2f} ha '
          f'(desvío {desvio:.2f} % vs oficial)')
    print(f'  predios de principales: {len(pri):,} ({area_pri:,.2f} ha) · '
          f'de adicionales: {len(adi):,} ({area_adi:,.2f} ha) · en ambos: '
          f'{len(pri & adi):,} — cuadre: {area_pri + area_adi:,.2f} ha')


if __name__ == '__main__':
    main()
