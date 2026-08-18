# -*- coding: utf-8 -*-
"""
El cultivo que se quedó con el área vieja, después de corregir el área.

El hallazgo (18-ago-2026, misma sesión que corregir_areas_declaradas_reparto.py)
------------------------------------------------------------------------------
Al revisar el resultado del reparto de áreas en la pantalla de Auditoría, salió
a la vista un problema que ese script no tocaba: en varias fichas donde HOY se
corrigió `area_total` (porque el técnico había dejado el default de QField —
el polígono completo, repetido en cada ficha que comparte el predio), el
**cultivo se quedó con el valor viejo**, el mismo default sin corregir.

El caso que lo destapó: predio 1702521000064 (Carrera), 5 fichas adicionales
—de 5 personas sin relación entre sí, cada una con su propio predio principal
en otro lugar— todas creadas por AUTO-SECCION7 el mismo segundo. El área de
las 5 se corrigió hoy a 7.730 m² cada una (38.649 ÷ 5). Pero Roberto Farinango
Tugulinago sigue con «Pasto no mejorado: 38.649,46 m²» — el polígono completo,
antes de dividir entre los 5. Por eso la pantalla dice que siembra «9,7 veces
su predio»: no es que siembre de más, es que su cultivo nunca se actualizó
cuando se corrigió su área.

Por qué esto sí se puede corregir con la misma certeza que el área
--------------------------------------------------------------------
Un cultivo no puede ser más grande que el predio donde está sembrado. Si HOY
ya se estableció —con la misma prueba que usó `corregir_areas_declaradas_
reparto.py`— cuál es el área real de la ficha, un cultivo que todavía diga el
área vieja (la de antes de dividir) es, por definición, imposible: no cabe.
Se recorta al área nueva de la misma ficha. No es una cifra inventada: es la
misma que ya se corrigió hoy, aplicada al campo que faltaba.

Qué NO corrige
---------------
Las fichas donde el cultivo coincide con el polígono pero **el área de esa
ficha nunca se corrigió** (no hay predio compartido, es la única ficha en su
clave) siguen sin tocarse: ahí no hay una corrección de hoy con la que
alinear el cultivo, así que la certeza no es la misma. Quedan marcadas
«sin verificar» en la pantalla de Auditoría (ver generar_auditoria_areas.py),
no corregidas.

Alcance
-------
Solo fichas que YA tienen la nota «[corregido 18-08-2026: ...]» en
observaciones (las 574 del reparto de áreas) Y cuyo cultivo sigue por encima
de esa área corregida en más del 2% de margen respecto al polígono viejo
(prueba: la superficie del cultivo cae dentro de ±2% del polígono catastral,
no del área nueva de la ficha).

Cómo trata fichas con VARIOS cultivos
--------------------------------------
Solo se recorta la fila que coincide con el polígono viejo (la huella del
default). Las demás filas de cultivo de esa ficha, si las hay, no se tocan:
son datos que el técnico sí distinguió del default.

Uso
---
    "C:\\OSGeo4W\\bin\\python-qgis.bat" -X utf8 scripts/corregir_cultivo_huella_default.py
    "C:\\OSGeo4W\\bin\\python-qgis.bat" -X utf8 scripts/corregir_cultivo_huella_default.py --aplicar

Sin `--aplicar` no escribe nada (regla 7). Con `--aplicar` respalda antes con
la API de backup de SQLite (regla 5).

Cómo revertirlo: docs/CORRECCION-cultivo-huella-default.md.
"""
import argparse
import json
import os
import sqlite3
import time

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
GPKG = os.path.join(os.path.expanduser('~'), 'QField', 'cloud',
                    'porotog_levantamiento_offline', 'data.gpkg')
CATASTRO = os.path.join(BASE, 'public', 'geo', 'catastro_geo.geojson')
RAIZ_RESPALDOS = (r"C:\Users\HP\OneDrive\Escritorio\CAYAMBE CATASTRO RIEGO"
                  r"\respaldos_qgs")
NOTA_HOY = 'corregido 18-08-2026'
MARGEN_POLIGONO = 0.02


def cargar_catastro():
    with open(CATASTRO, encoding='utf-8') as f:
        datos = json.load(f)
    areas = {}
    for ft in datos.get('features', []):
        p = ft.get('properties') or {}
        clave = str(p.get('clave_cata') or '').strip()
        if clave and p.get('area_predi'):
            areas[clave] = float(p['area_predi'])
    return areas


def tablas(cur):
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    todas = [t[0] for t in cur.fetchall()]

    def buscar(clave):
        return next(t for t in todas if clave in t
                    and not any(x in t for x in ('rtree_', 'log_', 'gpkg_')))
    return buscar('Fichas_Predios'), buscar('Cultivos_Agricolas')


def ha(v):
    return '{:,.2f}'.format(v / 10000.0).replace(',', '@').replace('.', ',').replace('@', '.')


def m2(v):
    return '{:,.2f}'.format(v or 0).replace(',', '@').replace('.', ',').replace('@', '.')


def respaldo_sqlite(origen, etiqueta):
    carpeta = os.path.join(RAIZ_RESPALDOS, time.strftime('%Y-%m-%d'))
    os.makedirs(carpeta, exist_ok=True)
    destino = os.path.join(carpeta, '{}.{}-{}.bak'.format(
        os.path.basename(origen), time.strftime('%H%M'), etiqueta))
    src = sqlite3.connect(origen)
    dst = sqlite3.connect(destino)
    with dst:
        src.backup(dst)
    dst.close()
    src.close()
    return destino


def analizar(cur, t_fic, t_cul, areas_cat):
    cur.execute(
        "SELECT f.id, f.clave_catastral, f.area_total, f.apellidos, f.nombres, f.comunidad "
        "FROM \"{}\" f WHERE f.observaciones LIKE ?".format(t_fic), ('%' + NOTA_HOY + '%',))
    fichas_corregidas = {r[0]: r for r in cur.fetchall()}

    correcciones = []
    for fid, (fid2, clave, area_nueva, ape, nom, com) in fichas_corregidas.items():
        pol = areas_cat.get((clave or '').strip())
        if not pol or pol <= 0:
            continue
        cur.execute(
            "SELECT id_cultivo, tipo_cultivo, superficie_m2 FROM \"{}\" WHERE ficha_id = ?"
            .format(t_cul), (fid,))
        for idc, tipo, sup in cur.fetchall():
            if not sup or sup <= area_nueva:
                continue
            if abs(sup - pol) / pol <= MARGEN_POLIGONO:
                correcciones.append({
                    'id_cultivo': idc, 'ficha_id': fid, 'tipo': tipo,
                    'sup_vieja': sup, 'sup_nueva': area_nueva,
                    'clave': clave, 'pol': pol, 'nombre': '{} {}'.format(ape or '', nom or '').strip(),
                    'com': com,
                })
    return correcciones


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--aplicar', action='store_true',
                    help='escribe en el data.gpkg (sin esto solo simula)')
    args = ap.parse_args()

    print('=' * 80)
    print(' CULTIVO CON LA HUELLA DEL DEFAULT (post-reparto de areas)' +
          ('  [APLICAR]' if args.aplicar else '  [SIMULACION - no escribe nada]'))
    print('=' * 80)

    areas_cat = cargar_catastro()
    con = sqlite3.connect(GPKG)
    cur = con.cursor()
    t_fic, t_cul = tablas(cur)

    correcciones = analizar(cur, t_fic, t_cul, areas_cat)
    correcciones.sort(key=lambda c: -(c['sup_vieja'] - c['sup_nueva']))

    print('\n  fichas a corregir: {}'.format(len(correcciones)))
    print('  superficie que se quita: {} ha'.format(
        ha(sum(c['sup_vieja'] - c['sup_nueva'] for c in correcciones))))

    print('\n  muestra (10 mayores):')
    for c in correcciones[:10]:
        print('     {} · {:<24} {:<20} {:>12} -> {:>12} m²'.format(
            c['clave'], c['com'][:24] if c['com'] else '', c['nombre'][:20],
            m2(c['sup_vieja']), m2(c['sup_nueva'])))

    if not args.aplicar:
        print('\n  ' + '-' * 76)
        print('  SIMULACION: no se escribio nada. Para aplicarlo:  --aplicar')
        print('  ' + '-' * 76)
        con.close()
        return

    if not correcciones:
        print('\n  Nada que aplicar.')
        con.close()
        return

    print('\n  respaldando antes de escribir...')
    print('     {}'.format(respaldo_sqlite(GPKG, 'antes-cultivo-huella-default')))

    n = 0
    for c in correcciones:
        cur.execute(
            'UPDATE "{}" SET superficie_m2 = ? WHERE id_cultivo = ?'.format(t_cul),
            (c['sup_nueva'], c['id_cultivo']))
        n += cur.rowcount
    con.commit()
    con.close()
    print('     {} filas de cultivo actualizadas'.format(n))

    con = sqlite3.connect('file:{}?mode=ro'.format(GPKG.replace('\\', '/')), uri=True)
    cur = con.cursor()
    quedan = analizar(cur, t_fic, t_cul, areas_cat)
    con.close()
    print('\n  VERIFICACION (releyendo del disco):')
    print('     fichas que aun tendrian correccion pendiente: {} · se esperaban 0'
          .format(len(quedan)))
    print('\n  {}'.format('CORRECCION APLICADA Y VERIFICADA' if not quedan
                          else '!! REVISAR: quedaron casos sin aplicar'))


if __name__ == '__main__':
    main()
