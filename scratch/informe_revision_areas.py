# -*- coding: utf-8 -*-
"""
Genera el informe en Markdown para que los TECNICOS revisen y validen en campo
las fichas cuyas areas no cuadran con el poligono catastral.

Distingue DOS problemas que son distintos:

  PROBLEMA 1 — AREA DEL TERRENO
      'Area total' de la ficha (el tamaño del predio que declaro el regante)
      es mayor que el poligono catastral al que esta asociada la ficha.

  PROBLEMA 2 — SUPERFICIE DE CULTIVOS
      La suma de las superficies sembradas (Seccion 4) no cabe dentro del
      poligono. Puede pasar aunque el area del terreno este bien.

Y separa fichas PRINCIPALES de ADICIONALES, porque el criterio de revision
no es el mismo.

NO MODIFICA NADA. Solo produce el .md.

Uso:  python -X utf8 padron-app/scratch/informe_revision_areas.py
"""
import collections
import json
import os
from datetime import datetime

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
GEO = os.path.join(BASE, 'public', 'geo')
SALIDA = os.path.abspath(os.path.join(BASE, '..', 'docs',
                                      'REVISION-AREAS-fichas-a-verificar.md'))

TECNICOS = {
    'u0_a314': 'Melany Jara', 'u0_a319': 'Melany Jara', 'jvk-editor': 'Melany Jara',
    'u0_a504': 'Adriana Cuascota', 'jvk-editor6': 'Adriana Cuascota',
    'u0_a279': 'Huguito Ipial', 'jvk-editor2': 'Huguito Ipial',
    'u0_a70': 'Pablo Barrionuevo', 'jvk-editor5': 'Pablo Barrionuevo',
    'u0_a330': 'Mayra Benavides', 'mayralisseth201': 'Mayra Benavides',
    'u0_a362': 'Martha Simbaña', 'u0_a335': 'Martha Simbaña', 'jvk-editor4': 'Martha Simbaña',
    'u0_a2': 'JVK-DIGITALIZACION', 'jvk-digitalizacion': 'JVK-DIGITALIZACION',
    'u0_a302': 'Dylan Chavez', 'jvk-editor3': 'Dylan Chavez',
    'u0_a200': 'Melanie2', 'jvk-corp': 'Melany Recalde',
    'AUTO-SECCION7': 'Generada desde Seccion 7',
}


def cargar(n):
    with open(os.path.join(GEO, n), encoding='utf-8') as f:
        return json.load(f)


def es_hija(p):
    return p.get('es_ficha_hija') in (1, True)


def tec(f):
    c = str(f.get('creado_por') or '').strip()
    return TECNICOS.get(c, c or '(sin técnico)')


def m2(v):
    return "{:,.0f}".format(v or 0).replace(',', '.')


def main():
    fichas = [f['properties'] for f in cargar('fichas_predios.geojson')['features']]
    catastro = cargar('catastro_geo.geojson')['features']
    cultivos = cargar('cultivos.json')

    area_cat = {}
    for ft in catastro:
        p = ft.get('properties') or {}
        k = str(p.get('clave_cata') or '').strip()
        if k and p.get('area_predi'):
            area_cat[k] = float(p['area_predi'])

    cult_por_ficha = collections.defaultdict(list)
    for c in cultivos:
        cult_por_ficha[c.get('ficha_id')].append(c)

    # ── recolectar los casos, ficha por ficha ──
    p1, p2 = [], []          # problema 1 (terreno), problema 2 (cultivos)
    for f in fichas:
        k = str(f.get('clave_catastral') or f.get('cod_poligono') or '').strip()
        ac = area_cat.get(k)
        if not ac or ac <= 0:
            continue
        at = f.get('area_total') or 0
        sup = sum(c.get('superficie_m2') or 0 for c in cult_por_ficha.get(f.get('id'), []))
        base = {
            'clave': k, 'codigo': f.get('codigo_final') or '',
            'regante': ("{} {}".format(f.get('apellidos') or '', f.get('nombres') or '')).strip(),
            'cedula': f.get('cedula') or '', 'comunidad': f.get('comunidad') or '',
            'tecnico': tec(f), 'tipo': 'Adicional' if es_hija(f) else 'Principal',
            'area_cat': ac, 'area_dec': at, 'sup_cult': sup,
        }
        if at > ac * 1.05:
            base['factor'] = at / ac
            p1.append(dict(base))
        if sup > ac * 1.05:
            base2 = dict(base)
            base2['factor'] = sup / ac
            p2.append(base2)

    # areas declaradas repetidas: sintoma de que el formulario arrastro el valor
    rep = collections.Counter(round(c['area_dec']) for c in p1)
    for c in p1:
        c['area_repetida_en'] = rep[round(c['area_dec'])]

    hoy = datetime.now().strftime('%d/%m/%Y')
    L = []
    A = L.append

    A("# Revisión de áreas — fichas a verificar en campo")
    A("")
    A("**Generado:** {}  ".format(hoy))
    A("**Para:** equipo técnico de campo  ")
    A("**Qué hacer:** revisar cada ficha listada, confirmar el área real del")
    A("predio y corregirla en QField si está equivocada. Si el dato está bien,")
    A("anotarlo en la columna de observaciones de este documento.")
    A("")
    A("---")
    A("")
    A("## De qué se trata")
    A("")
    A("Cada ficha está asociada a un **polígono del catastro** (su clave catastral).")
    A("Se compararon dos cosas contra el tamaño de ese polígono:")
    A("")
    A("| | Qué se comparó | Fichas con diferencia |")
    A("|---|---|---|")
    A("| **Problema 1** | El **área del terreno** que declaró el regante (campo *Área total*) | **{}** |".format(len(p1)))
    A("| **Problema 2** | La **superficie sembrada** sumando los cultivos de la Sección 4 | **{}** |".format(len(p2)))
    A("")
    A("Son cosas distintas: una ficha puede tener bien el área del terreno pero")
    A("haber declarado más cultivos de los que caben, o al revés.")
    A("")
    A("### Por qué pasa (lo más probable)")
    A("")
    A("- **El formulario arrastró el área de la ficha anterior.** Hay valores de área")
    A("  idénticos repetidos en muchos predios distintos. Si el área que aparece en")
    A("  la lista es la misma en varias fichas seguidas suyas, es este caso.")
    A("- **La clave catastral asignada no corresponde al predio.** El regante tiene")
    A("  más terreno del que abarca ese polígono, o se seleccionó el polígono vecino.")
    A("- **Terreno comunal.** El regante declaró la extensión de todo el terreno de")
    A("  la comuna en vez de su parcela. En ese caso hay que poner solo su parcela.")
    A("")
    A("---")
    A("")

    # ── PROBLEMA 1 ──
    A("## Problema 1 · Área del terreno mayor que el polígono")
    A("")
    A("Total: **{}** fichas.".format(len(p1)))
    A("")
    porTec = collections.defaultdict(list)
    for c in p1:
        porTec[c['tecnico']].append(c)
    A("| Técnico | Fichas a revisar |")
    A("|---|---:|")
    for t, cs in sorted(porTec.items(), key=lambda x: -len(x[1])):
        A("| {} | {} |".format(t, len(cs)))
    A("")

    for t, cs in sorted(porTec.items(), key=lambda x: -len(x[1])):
        A("### {} — {} fichas".format(t, len(cs)))
        A("")
        cs.sort(key=lambda c: (c['comunidad'], -c['factor']))
        A("| Comunidad | Clave catastral | Código | Regante | Cédula | Área declarada | Área del polígono | Veces | ¿Área repetida? | Observación del técnico |")
        A("|---|---|---|---|---|---:|---:|---:|:---:|---|")
        for c in cs:
            rep_txt = ("sí, en {} fichas".format(c['area_repetida_en'])
                       if c['area_repetida_en'] > 1 else "no")
            A("| {} | {} | {} | {} | {} | {} m² | {} m² | {:.1f}x | {} | |".format(
                c['comunidad'], c['clave'], c['codigo'], c['regante'], c['cedula'],
                m2(c['area_dec']), m2(c['area_cat']), c['factor'], rep_txt))
        A("")

    # ── PROBLEMA 2 ──
    A("---")
    A("")
    A("## Problema 2 · Cultivos que no caben en el polígono")
    A("")
    A("Total: **{}** fichas. Aquí la suma de las superficies de los cultivos".format(len(p2)))
    A("(Sección 4) es mayor que el terreno disponible.")
    A("")
    porTec2 = collections.defaultdict(list)
    for c in p2:
        porTec2[c['tecnico']].append(c)
    A("| Técnico | Fichas a revisar |")
    A("|---|---:|")
    for t, cs in sorted(porTec2.items(), key=lambda x: -len(x[1])):
        A("| {} | {} |".format(t, len(cs)))
    A("")
    for t, cs in sorted(porTec2.items(), key=lambda x: -len(x[1])):
        A("### {} — {} fichas".format(t, len(cs)))
        A("")
        cs.sort(key=lambda c: (c['comunidad'], -c['factor']))
        A("| Comunidad | Clave catastral | Código | Regante | Cédula | Cultivos suman | Área del polígono | Veces | Observación del técnico |")
        A("|---|---|---|---|---|---:|---:|---:|---|")
        for c in cs:
            A("| {} | {} | {} | {} | {} | {} m² | {} m² | {:.1f}x | |".format(
                c['comunidad'], c['clave'], c['codigo'], c['regante'], c['cedula'],
                m2(c['sup_cult']), m2(c['area_cat']), c['factor']))
        A("")

    A("---")
    A("")
    A("## Cómo corregir en QField")
    A("")
    A("1. Busque la ficha por la **clave catastral** o por el nombre del regante.")
    A("2. Verifique con el regante la extensión real de **su** parcela (no la del")
    A("   terreno comunal completo).")
    A("3. Corrija el campo **Área total** y, si aplica, **Área con riego**.")
    A("4. Revise que las superficies de los cultivos sumen como máximo el área")
    A("   del predio.")
    A("5. Guarde y sincronice.")
    A("")
    A("Si el área declarada es correcta y la diferencia viene de que la **clave**")
    A("**catastral está mal asignada**, no cambie el área: anótelo en la columna de")
    A("observaciones indicando *\"clave incorrecta\"* para corregir el polígono.")
    A("")

    os.makedirs(os.path.dirname(SALIDA), exist_ok=True)
    with open(SALIDA, 'w', encoding='utf-8') as f:
        f.write("\n".join(L))

    print("=" * 70)
    print(" INFORME PARA LOS TECNICOS")
    print("=" * 70)
    print("  Problema 1 (area del terreno) : {:>4} fichas".format(len(p1)))
    print("     principales: {}   adicionales: {}".format(
        sum(1 for c in p1 if c['tipo'] == 'Principal'),
        sum(1 for c in p1 if c['tipo'] == 'Adicional')))
    print("  Problema 2 (cultivos)         : {:>4} fichas".format(len(p2)))
    print("     principales: {}   adicionales: {}".format(
        sum(1 for c in p2 if c['tipo'] == 'Principal'),
        sum(1 for c in p2 if c['tipo'] == 'Adicional')))
    print("\n  por tecnico (problema 1):")
    for t, cs in sorted(porTec.items(), key=lambda x: -len(x[1])):
        print("     {:<26} {:>4}".format(t, len(cs)))
    print("\n  guardado en: {}".format(SALIDA))
    print("  tamaño: {:,.0f} KB".format(os.path.getsize(SALIDA) / 1024))


if __name__ == '__main__':
    main()
