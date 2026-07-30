# -*- coding: utf-8 -*-
"""
PRUEBA REAL: ¿se puede vincular una ficha adicional a su regante principal
EDITANDO una ficha que ya existe?

Es la pregunta de JAVIKO (2026-07-30) y no se responde leyendo el XML: el
antecedente es que un FilterExpression con current_value() rompió 375 fichas —
QField no lo resolvía y escribía NULL en ficha_madre_id al guardar. Así que
aquí se edita de verdad, se guarda, se cierra y se vuelve a leer del disco.

Trabaja sobre una COPIA del data.gpkg en el scratchpad. NUNCA toca el original
ni el proyecto de campo.

Ejecutar con:
  C:\\OSGeo4W\\bin\\python-qgis.bat scripts/probar_vinculacion_adicional.py
"""

import os
import shutil
import sys
import tempfile

from qgis.core import (QgsApplication, QgsProject, QgsVectorLayer,
                       QgsFeatureRequest)

ORIGEN = r"C:\Users\HP\QField\cloud\porotog_levantamiento_offline"
QGS_NOMBRE = "POROTOG LEVANTAMIENTO_qfield_cloud.qgs"

fallos = []


def check(cond, msg):
    print(('  OK   ' if cond else '  FALLA ') + msg)
    if not cond:
        fallos.append(msg)


# ── sandbox ──
tmp = tempfile.mkdtemp(prefix='prueba_vinc_')
print("sandbox:", tmp)
shutil.copy2(os.path.join(ORIGEN, 'data.gpkg'), os.path.join(tmp, 'data.gpkg'))
shutil.copy2(os.path.join(ORIGEN, QGS_NOMBRE), os.path.join(tmp, QGS_NOMBRE))

app = QgsApplication([], False)
app.initQgis()

proj = QgsProject.instance()
proj.read(os.path.join(tmp, QGS_NOMBRE))
capa = next(l for l in proj.mapLayers().values() if l.name() == 'Fichas_Predios')
print("capa:", capa.name(), "|", capa.featureCount(), "fichas\n")

i_hija = capa.fields().indexOf('es_ficha_hija')
i_madre = capa.fields().indexOf('ficha_madre_id')
i_estado = capa.fields().indexOf('estado_investigacion')
i_pres = capa.fields().indexOf('nom_presidente')
i_km = capa.fields().indexOf('km_canal')

# ── 1. la lista de regantes que verá el técnico ──
# Se evalúa el FilterExpression del ValueRelation directamente sobre la capa
# de origen: eso es exactamente lo que QField resuelve para armar la lista.
print("1) LISTA DE REGANTES PRINCIPALES (el desplegable)")
cfg = capa.editorWidgetSetup(i_madre).config()
filtro = cfg.get('FilterExpression', '')
campo_clave = cfg.get('Key')


def candidatas(capa_):
    req = QgsFeatureRequest()
    if filtro:
        req.setFilterExpression(filtro)
    return {f[campo_clave] for f in capa_.getFeatures(req)}


valores = candidatas(capa)
check(capa.editorWidgetSetup(i_madre).type() == 'ValueRelation',
      f"ficha_madre_id usa un desplegable ValueRelation")
check(len(valores) > 4000, f"el desplegable ofrece {len(valores):,} regantes principales")
check('current_value' not in filtro,
      "el filtro NO usa current_value() — es lo que rompió 375 fichas en su día")
print(f"      filtro: {filtro}")
print(f"      etiqueta: {str(cfg.get('Value'))[:80]}")

# ── 2. tomar una ficha adicional YA EXISTENTE y vincularla ──
print("\n2) EDITAR UNA FICHA EXISTENTE Y VINCULARLA")
victima = None
for f in capa.getFeatures():
    if f[i_hija] in (1, True) and not f[i_madre]:
        victima = f
        break
if victima is None:   # si no hay ninguna suelta, se simula una
    for f in capa.getFeatures():
        if f[i_hija] in (1, True) and f[i_madre]:
            victima = f
            break
    capa.startEditing()
    capa.changeAttributeValue(victima.id(), i_madre, None)
    capa.changeAttributeValue(victima.id(), i_hija, False)
    capa.commitChanges()
    victima = capa.getFeature(victima.id())
    print("      (no había ninguna suelta: se desvinculó una para la prueba)")

fid = victima.id()
madre_elegida = sorted(v for v in valores if v)[0]   # lo que elegiría del desplegable
pres_antes = victima[i_pres]
km_antes = victima[i_km]
print(f"      ficha fid={fid} | es_ficha_hija={victima[i_hija]} | madre={victima[i_madre]}")

capa.startEditing()
capa.changeAttributeValue(fid, i_hija, True)              # marca la casilla
capa.changeAttributeValue(fid, i_madre, madre_elegida)    # elige al regante
capa.changeAttributeValue(fid, i_estado, 'pendiente_produccion')
ok = capa.commitChanges()
check(ok, f"guardar la edición: {capa.commitErrors() if not ok else 'sin errores'}")

# ── 3. releer DEL DISCO: es lo único que prueba que persistió ──
print("\n3) RELEER DEL DISCO (prueba de que no se perdió al guardar)")
proj.clear()
recarga = QgsVectorLayer(
    os.path.join(tmp, 'data.gpkg') +
    '|layername=Fichas_Predios_880eb10d_d887_4fc6_99a2_8af3ac63877e',
    'recarga', 'ogr')
f2 = recarga.getFeature(fid)
j_hija = recarga.fields().indexOf('es_ficha_hija')
j_madre = recarga.fields().indexOf('ficha_madre_id')
j_pres = recarga.fields().indexOf('nom_presidente')
j_km = recarga.fields().indexOf('km_canal')

check(f2[j_hija] in (1, True), f"es_ficha_hija quedó marcada: {f2[j_hija]}")
check(f2[j_madre] == madre_elegida,
      f"ficha_madre_id persistió: {f2[j_madre]}")
check(f2[j_madre] is not None and str(f2[j_madre]) != 'NULL',
      "ficha_madre_id NO se volvió NULL (el fallo de las 375 fichas)")

# ── 4. los defaults NO pisan lo que ya había ──
print("\n4) LOS DEFAULTS NO TOCAN LO QUE YA ESTABA")
check(f2[j_pres] == pres_antes,
      f"nom_presidente intacto tras editar: [{f2[j_pres]}] (antes [{pres_antes}])")
check(f2[j_km] == km_antes,
      f"km_canal intacto tras editar: [{f2[j_km]}] (antes [{km_antes}])")

# ── 5. una vez vinculada, ya no puede figurar como madre de otra ──
print("\n5) COHERENCIA DE LA LISTA")
val2 = candidatas(recarga)
check(victima['id'] not in val2,
      "la ficha recién marcada como adicional salió del desplegable de madres")
check(madre_elegida in val2,
      "el regante principal elegido sigue disponible para otras adicionales")
print(f"      candidatas: {len(valores):,} → {len(val2):,}")

# ── 6. el caso real: una ficha que quedó como PRINCIPAL por error ──
# Es lo que pasó con los técnicos que anotaron la clave en observaciones: la
# ficha existe como principal y hay que convertirla en adicional a posteriori.
print("\n6) CONVERTIR UNA FICHA PRINCIPAL EN ADICIONAL")
capa3 = QgsVectorLayer(
    os.path.join(tmp, 'data.gpkg') +
    '|layername=Fichas_Predios_880eb10d_d887_4fc6_99a2_8af3ac63877e',
    'conv', 'ogr')
k_hija = capa3.fields().indexOf('es_ficha_hija')
k_madre = capa3.fields().indexOf('ficha_madre_id')
k_obs = capa3.fields().indexOf('observaciones')

principal = next(f for f in capa3.getFeatures()
                 if f[k_hija] not in (1, True) and f.id() != fid)
obs_antes = principal[k_obs]
print(f"      ficha fid={principal.id()} era principal")

capa3.startEditing()
capa3.changeAttributeValue(principal.id(), k_hija, True)
capa3.changeAttributeValue(principal.id(), k_madre, madre_elegida)
ok3 = capa3.commitChanges()
check(ok3, "se puede convertir de principal a adicional y guardar")

recarga3 = QgsVectorLayer(
    os.path.join(tmp, 'data.gpkg') +
    '|layername=Fichas_Predios_880eb10d_d887_4fc6_99a2_8af3ac63877e',
    'r3', 'ogr')
f3 = recarga3.getFeature(principal.id())
check(f3[k_hija] in (1, True) and f3[k_madre] == madre_elegida,
      f"quedó vinculada tras releer del disco: madre={f3[k_madre]}")
check(f3[k_obs] == obs_antes,
      "las observaciones del técnico siguen intactas (ahí anotaron la clave)")
check(principal['id'] not in candidatas(recarga3),
      "ya no figura como posible madre de otras fichas")

print()
shutil.rmtree(tmp, ignore_errors=True)
if fallos:
    print(f"XX FALLARON {len(fallos)} COMPROBACIONES")
    app.exitQgis()
    sys.exit(1)
print("VINCULACION OK - editar una ficha existente y vincularla funciona")
app.exitQgis()
