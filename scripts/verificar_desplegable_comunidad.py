# -*- coding: utf-8 -*-
"""
Verifica con la API de QGIS que el desplegable de comunidad quedó sin la
expresión que borraba datos, y que muestra el número del listado oficial.

Ejecutar:  C:\\OSGeo4W\\bin\\python-qgis.bat scripts/verificar_desplegable_comunidad.py
"""

import sys

from qgis.core import (QgsApplication, QgsProject, QgsFeatureRequest,
                       QgsExpression, QgsExpressionContext,
                       QgsExpressionContextUtils)

QGS = r"C:\Users\HP\QField\cloud\porotog_levantamiento_offline\POROTOG LEVANTAMIENTO_qfield_cloud.qgs"

fallos = []


def check(cond, msg):
    print(('  OK    ' if cond else '  FALLA ') + msg)
    if not cond:
        fallos.append(msg)


app = QgsApplication([], False)
app.initQgis()
proj = QgsProject.instance()
check(proj.read(QGS), 'el proyecto abre sin errores')

capa = next(l for l in proj.mapLayers().values() if l.name() == 'Fichas_Predios')
cfg = capa.editorWidgetSetup(capa.fields().indexOf('comunidad')).config()

print()
check('current_value' not in (cfg.get('FilterExpression') or ''),
      'el filtro ya no usa current_value — es lo que borraba la comunidad')
check(not (cfg.get('FilterExpression') or '').strip(),
      f"sin filtro dinámico: [{cfg.get('FilterExpression')}]")
check('n' in (cfg.get('Value') or ''),
      f"el texto incluye el número: {cfg.get('Value')}")

# ── lo que verá el técnico ──
ref = next((l for l in proj.mapLayers().values()
            if l.name().startswith('Comunidades_Sectores')), None)
check(ref is not None, 'la tabla Comunidades_Sectores está en el proyecto')
if ref:
    e = QgsExpression(cfg['Value'])
    ctx = QgsExpressionContext()
    ctx.appendScopes(QgsExpressionContextUtils.globalProjectLayerScopes(ref))
    e.prepare(ctx)
    opciones = []
    for f in ref.getFeatures(QgsFeatureRequest()):
        ctx.setFeature(f)
        opciones.append(e.evaluate(ctx))
    check(len(opciones) == 50, f'ofrece {len(opciones)} comunidades (deben ser 50)')
    check(all(o and o[:2].isdigit() for o in opciones),
          'todas llevan el número delante')
    ordenadas = sorted(opciones)
    check(ordenadas == sorted(opciones, key=lambda x: int(x[:2])),
          'el orden alfabético coincide con el numérico (por eso el 0 delante)')
    print('\n  lo que verá el técnico:')
    for o in ordenadas[:3] + ['   ...'] + ordenadas[21:23] + ['   ...'] + ordenadas[-2:]:
        print(f"     {o}")

# ── la pestaña de predio adicional sigue en pie ──
print()
nombres = [t.name() for t in capa.editFormConfig().tabs()]
check('➕ PREDIO ADICIONAL' in nombres, 'la pestaña ➕ PREDIO ADICIONAL sigue en el formulario')
d = capa.defaultValueDefinition(capa.fields().indexOf('conoce_presa'))
check(d.expression() == "'Sí'", f'la encuesta sigue precargada: conoce_presa={d.expression()}')

print()
if fallos:
    print(f"XX FALLARON {len(fallos)} COMPROBACIONES")
    app.exitQgis()
    sys.exit(1)
print("VERIFICACION OK")
app.exitQgis()
