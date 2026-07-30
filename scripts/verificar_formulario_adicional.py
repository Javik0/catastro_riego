# -*- coding: utf-8 -*-
"""
Verifica con la API de QGIS que el formulario modificado por
preparar_formulario_adicional_qfield.py quedó exactamente como se diseñó.

Ejecutar con:  C:\\OSGeo4W\\bin\\python-qgis.bat scripts/verificar_formulario_adicional.py

Sale con código != 0 si algo no cuadra (mismo patrón que construir_qgz_pyqgis.py:
QGIS relee el proyecto real, no confiamos en el texto que escribimos).
"""

import sys

from qgis.core import QgsApplication, QgsProject

QGS = r"C:\Users\HP\QField\cloud\porotog_levantamiento_offline\POROTOG LEVANTAMIENTO_qfield_cloud.qgs"

app = QgsApplication([], False)
app.initQgis()

fallos = []


def check(cond, msg):
    print(('  ✓ ' if cond else '  ✗ ') + msg)
    if not cond:
        fallos.append(msg)


proj = QgsProject.instance()
check(proj.read(QGS), 'el proyecto abre sin errores')

capa = next((l for l in proj.mapLayers().values() if l.name() == 'Fichas_Predios'), None)
check(capa is not None, 'capa Fichas_Predios encontrada')

cfg = capa.editFormConfig()
tabs = cfg.tabs()
nombres = [t.name() for t in tabs]
print('\n  pestañas:', ' | '.join(nombres))

# 1) la pestaña nueva existe y está en 2.ª posición
check('➕ PREDIO ADICIONAL' in nombres, 'pestaña ➕ PREDIO ADICIONAL existe')
check(nombres.index('➕ PREDIO ADICIONAL') == 1 if '➕ PREDIO ADICIONAL' in nombres else False,
      'está justo después de 1. DATOS DEL PROPIETARIO')

# 2) contenido de la pestaña
tab = tabs[nombres.index('➕ PREDIO ADICIONAL')]
hijos = tab.children()
campos_directos = [c.name() for c in hijos if c.type() == c.AeTypeField]
grupos = [c for c in hijos if c.type() == c.AeTypeContainer]
check('es_ficha_hija' in campos_directos, 'es_ficha_hija visible directo en la pestaña')
check(len(grupos) == 1, 'un grupo de vinculación')
if grupos:
    g = grupos[0]
    dentro = [c.name() for c in g.children() if c.type() == c.AeTypeField]
    check('ficha_madre_id' in dentro and 'estado_investigacion' in dentro,
          'ficha_madre_id + estado_investigacion dentro del grupo')
    expr = g.visibilityExpression()
    check(expr.enabled() and 'es_ficha_hija' in expr.data().expression(),
          'el grupo solo aparece si la casilla está marcada: ' + expr.data().expression())

# 3) en Auditoría ya no están duplicados
aud = tabs[nombres.index('8. AUDITORÍA')] if '8. AUDITORÍA' in nombres else None


def campos_recursivos(cont):
    out = []
    for c in cont.children():
        if c.type() == c.AeTypeField:
            out.append(c.name())
        elif c.type() == c.AeTypeContainer:
            out += campos_recursivos(c)
    return out


if aud:
    en_aud = campos_recursivos(aud)
    check('ficha_madre_id' not in en_aud and 'estado_investigacion' not in en_aud,
          'ficha_madre_id/estado_investigacion ya no están en Auditoría')
    check('completado_por' in en_aud and 'origen_datos' in en_aud,
          'completado_por y origen_datos siguen en Auditoría')

# 4) defaults: valor correcto y que NUNCA pisen al técnico
print()
ESPERADOS = {
    'es_ficha_hija': ('false', False),
    'conoce_presa': ("'Sí'", False),
    'como_elige_dir': ("'Asamblea general'", False),
    'anios_sistema': ('60', False),
    'km_canal': ('63', False),
    'recibio_capacitacion': ("'Sí'", False),
    'le_gustaria_cap': ("'Sí'", False),
    # los upper() conservan applyOnUpdate=1 pero con coalesce que respeta el dato
    'nom_presidente': ("upper(coalesce(nullif(trim(\"nom_presidente\"), ''), 'JOSE JOAQUIN TIPANLUISA'))", True),
    'temas_capacitacion': ("upper(coalesce(nullif(trim(\"temas_capacitacion\"), ''), 'RIEGO'))", True),
}
for nombre, (expr_esp, upd_esp) in ESPERADOS.items():
    idx = capa.fields().indexOf(nombre)
    d = capa.defaultValueDefinition(idx)
    ok = d.expression() == expr_esp and d.applyOnUpdate() == upd_esp
    check(ok, '{}: [{}] applyOnUpdate={}'.format(nombre, d.expression(), d.applyOnUpdate()))

# operador_sector NO lleva default de VALOR (varía por comunidad). Conserva su
# upper() de normalización, que ya estaba antes de este cambio.
d = capa.defaultValueDefinition(capa.fields().indexOf('operador_sector'))
check(d.expression() == 'upper("operador_sector")',
      'operador_sector sin default de valor, solo su upper() preexistente')

# 5) la casilla nace desmarcada -> las fichas normales no cambian
print()
if fallos:
    print('✗ VERIFICACIÓN FALLÓ: {} problemas'.format(len(fallos)))
    app.exitQgis()
    sys.exit(1)
print('✓ VERIFICACION OK — el formulario quedó como se diseñó')
app.exitQgis()
