# -*- coding: utf-8 -*-
"""
Reproduce el fallo que reportan los técnicos (2026-07-31):

  "creo la ficha principal, luego creo la adicional, y al buscar por cédula en
   ID de Ficha Madre no aparece la ficha que acabo de crear"

Crea una ficha principal como lo haría QField (con los defaults del formulario),
la guarda, y comprueba si aparece entre las candidatas del ValueRelation y si se
puede encontrar escribiendo la cédula.

Trabaja sobre una COPIA en el scratchpad. No toca el proyecto de campo.

Ejecutar:  C:\\OSGeo4W\\bin\\python-qgis.bat scripts/probar_ficha_madre_recien_creada.py
"""

import os
import shutil
import sys
import tempfile

from qgis.core import (QgsApplication, QgsProject, QgsFeature, QgsFeatureRequest,
                       QgsExpressionContext, QgsExpressionContextUtils,
                       QgsExpression, QgsVectorLayerUtils)

ORIGEN = r"C:\Users\HP\QField\cloud\porotog_levantamiento_offline"
QGS = "POROTOG LEVANTAMIENTO_qfield_cloud.qgs"
CEDULA_PRUEBA = '1799999999'
APELLIDOS, NOMBRES = 'PRUEBA CACHE', 'REGANTE NUEVO'

fallos = []


def check(cond, msg):
    print(('  OK    ' if cond else '  FALLA ') + msg)
    if not cond:
        fallos.append(msg)


tmp = tempfile.mkdtemp(prefix='prueba_madre_')
shutil.copy2(os.path.join(ORIGEN, 'data.gpkg'), os.path.join(tmp, 'data.gpkg'))
shutil.copy2(os.path.join(ORIGEN, QGS), os.path.join(tmp, QGS))

app = QgsApplication([], False)
app.initQgis()
proj = QgsProject.instance()
proj.read(os.path.join(tmp, QGS))
capa = next(l for l in proj.mapLayers().values() if l.name() == 'Fichas_Predios')

cfg = capa.editorWidgetSetup(capa.fields().indexOf('ficha_madre_id')).config()
filtro, key, valor_expr = cfg['FilterExpression'], cfg['Key'], cfg['Value']
print(f"filtro : {filtro}")
print(f"texto  : {valor_expr}\n")


def candidatas(capa_):
    """Lo que el desplegable ofrece: (id, texto mostrado)."""
    req = QgsFeatureRequest()
    if filtro:
        req.setFilterExpression(filtro)
    e = QgsExpression(valor_expr)
    ctx = QgsExpressionContext()
    ctx.appendScopes(QgsExpressionContextUtils.globalProjectLayerScopes(capa_))
    e.prepare(ctx)
    out = []
    for f in capa_.getFeatures(req):
        ctx.setFeature(f)
        out.append((f[key], e.evaluate(ctx)))
    return out


antes = candidatas(capa)
print(f"1) ANTES DE CREAR: {len(antes):,} regantes en el desplegable")

# ── crear la ficha principal como lo hace QField (aplicando los defaults) ──
print("\n2) CREAR LA FICHA PRINCIPAL (con los defaults del formulario)")
ctx = QgsExpressionContext()
ctx.appendScopes(QgsExpressionContextUtils.globalProjectLayerScopes(capa))
nueva = QgsVectorLayerUtils.createFeature(capa, context=ctx)
nueva['apellidos'] = APELLIDOS
nueva['nombres'] = NOMBRES
nueva['cedula'] = CEDULA_PRUEBA
nueva['comunidad'] = 'CARRERA'
nueva['clave_catastral'] = '1702520999999'
capa.startEditing()
ok = capa.addFeature(nueva)
ok = capa.commitChanges() and ok
check(ok, f"se guarda la ficha: {capa.commitErrors() if not ok else 'sin errores'}")

creada = next((f for f in capa.getFeatures() if f['cedula'] == CEDULA_PRUEBA), None)
check(creada is not None, 'la ficha existe tras guardar')
if creada:
    print(f"      id={creada['id']}  es_ficha_hija={creada['es_ficha_hija']!r} "
          f"(tipo {type(creada['es_ficha_hija']).__name__})")

# ── ¿aparece ya en el desplegable? ──
print("\n3) BUSCARLA EN EL DESPLEGABLE")
despues = candidatas(capa)
check(len(despues) == len(antes) + 1,
      f"el desplegable pasa de {len(antes):,} a {len(despues):,} regantes")

mia = [(k, v) for k, v in despues if v and CEDULA_PRUEBA in str(v)]
check(bool(mia), f"se encuentra escribiendo la cédula {CEDULA_PRUEBA}")
if mia:
    print(f"      texto en la lista: {mia[0][1]}")

por_ape = [(k, v) for k, v in despues if v and APELLIDOS in str(v)]
check(bool(por_ape), f"se encuentra escribiendo el apellido '{APELLIDOS}'")

# ── el filtro no la excluye ──
print("\n4) ¿EL FILTRO LA DEJA PASAR?")
e = QgsExpression(filtro)
c2 = QgsExpressionContext()
c2.appendScopes(QgsExpressionContextUtils.globalProjectLayerScopes(capa))
c2.setFeature(creada)
check(e.evaluate(c2) in (1, True),
      f"coalesce(es_ficha_hija,false)=false evalúa a {e.evaluate(c2)!r} para la ficha nueva")

# ── ¿se puede buscar por clave catastral? (pregunta de JAVIKO) ──
print("\n5) ¿SE PUEDE BUSCAR POR CLAVE CATASTRAL?")
hay_clave = any(v and '1702520999999' in str(v) for _, v in despues)
print('  ' + ('OK    ' if hay_clave else 'NO    ')
      + 'la clave catastral '
      + ('aparece' if hay_clave else 'NO aparece')
      + ' en el texto del desplegable')
if not hay_clave:
    print('        -> hoy solo se puede buscar por apellidos, nombres o cédula')

shutil.rmtree(tmp, ignore_errors=True)
print()
if fallos:
    print(f"XX FALLARON {len(fallos)} COMPROBACIONES")
    app.exitQgis()
    sys.exit(1)
print("A NIVEL DE DATOS TODO FUNCIONA — si en la tablet no aparece, es la caché de QField")
app.exitQgis()
