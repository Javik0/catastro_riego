# -*- coding: utf-8 -*-
"""
Aplica al proyecto QGIS/QField tres correcciones que van juntas en una sola subida
a QFieldCloud (28-07-2026):

1) FICHAS QUE SE QUEDAN BLANCAS
   El default de 'estado_investigacion' solo marcaba 'completada' cuando la ficha
   estaba en 'pendiente_produccion'. Las que quedaron en 'en_revision' nunca se
   marcaban aunque el tecnico cargara cultivos y animales, y la simbologia las
   pintaba blancas para siempre. Se cambia la condicion a "distinto de completada".

2) MELANY RECALDE (usuario jvk-corp)
   No tenia regla de simbologia: sus fichas caian en "Otro". Se agregan las dos
   reglas (ficha principal y ficha adicional completada) en color magenta y se
   la excluye de la categoria "Otro".

3) VINCULAR UNA FICHA ADICIONAL NUEVA A SU REGANTE PRINCIPAL
   'ficha_madre_id' y 'es_ficha_hija' estaban bloqueados en el formulario, asi que
   el tecnico no podia indicar de quien era el predio nuevo. Se habilitan, y
   ficha_madre_id pasa a ser un desplegable buscable con las fichas principales
   de la misma comunidad.

MODO SEGURO: por defecto solo simula. Para escribir hay que pasar --aplicar.
El XML se valida antes de guardar; si algo no cuadra, no se escribe nada.
"""
import re
import sys
import xml.etree.ElementTree as ET

APLICAR = "--aplicar" in sys.argv
QGS = r"C:\Users\HP\QField\cloud\porotog_levantamiento_offline\POROTOG LEVANTAMIENTO_qfield_cloud.qgs"
LAYER_ID = "Fichas_Predios_880eb10d_d887_4fc6_99a2_8af3ac63877e"
LAYER_SRC = "./data.gpkg|layername={}|option:QGIS_FORCE_WAL=ON".format(LAYER_ID)

with open(QGS, encoding="utf-8") as f:
    xml = f.read()
original = xml
cambios = []


def sustituir(viejo, nuevo, etiqueta, esperado=1):
    global xml
    n = xml.count(viejo)
    if n != esperado:
        print("  [ERROR] '{}': esperaba {} coincidencia(s), encontre {}".format(etiqueta, esperado, n))
        return False
    xml = xml.replace(viejo, nuevo)
    cambios.append("{} ({} reemplazo/s)".format(etiqueta, n))
    return True


ok = True
print("=" * 74)
print(" {} — PROYECTO QGIS/QFIELD".format("APLICANDO" if APLICAR else "SIMULACION (no escribe)"))
print("=" * 74)

# ── 1. El default que dejaba fichas en blanco ──────────────────────────
print("\n[1] Regla automatica de 'completada'")
ok &= sustituir(
    "AND coalesce(&quot;estado_investigacion&quot;,'pendiente_produccion') = 'pendiente_produccion' THEN 'completada'",
    "AND coalesce(&quot;estado_investigacion&quot;,'pendiente_produccion') &lt;> 'completada' THEN 'completada'",
    "ahora cubre tambien 'en_revision'")

# ── 2. Melany Recalde (jvk-corp) ───────────────────────────────────────
print("\n[2] Simbologia de Melany Recalde (jvk-corp)")

# 2a. excluirla de "Otro"
ok &= sustituir(
    "'u0_a302', 'jvk-editor3', 'Melany', 'Adriana', 'Huguito', 'Pablo', 'Mayra', 'Martha', 'JVK-DIGITALIZACION', 'Dylan')",
    "'u0_a302', 'jvk-editor3', 'jvk-corp', 'Melany', 'Adriana', 'Huguito', 'Pablo', 'Mayra', 'Martha', 'JVK-DIGITALIZACION', 'Dylan', 'Melany Recalde')",
    "excluida de la categoria 'Otro'")

# 2b. regla de ficha adicional completada (antes de la regla 'Otro')
regla_hija = ('<rule filter="coalesce(&quot;es_ficha_hija&quot;, false) = true AND '
              '&quot;estado_investigacion&quot; = \'completada\' AND '
              '(&quot;completado_por&quot; IN (\'jvk-corp\') OR '
              '&quot;completado_por&quot; = \'Melany Recalde\')" '
              'key="{b1f4c7a2-3e55-4d10-9c88-71a0e5d4f001}" '
              'label="Hija completada — Melany Recalde" symbol="19"/>')
ancla_otro = '<rule filter="coalesce(&quot;es_ficha_hija&quot;, false) = true AND &quot;estado_investigacion&quot; = \'completada\' AND coalesce(&quot;completado_por&quot;, \'\') NOT IN'
ok &= sustituir(ancla_otro, "          " + regla_hija + "\n          " + ancla_otro,
                "regla 'Hija completada — Melany Recalde'")

# 2c. regla de ficha principal (antes del ELSE)
regla_ppal = ('<rule filter="coalesce(&quot;es_ficha_hija&quot;, false) = false AND '
              '&quot;creado_por&quot; IN (\'jvk-corp\')" '
              'key="{b1f4c7a2-3e55-4d10-9c88-71a0e5d4f002}" '
              'label="Melany Recalde" symbol="20"/>')
ancla_else = '<rule filter="ELSE" key="{7bf00f17-7ff6-46b6-ad7a-3dc22d7f8e3d}" label="Otro / Sin asignar" symbol="18"/>'
ok &= sustituir(ancla_else, regla_ppal + "\n          " + ancla_else,
                "regla 'Melany Recalde' (ficha principal)")

# 2d. los dos simbolos magenta, clonando la estructura de los existentes
m = re.search(r'(<symbol alpha="1"[^>]*name="14" type="marker">.*?</symbol>)', xml, re.S)
if not m:
    print("  [ERROR] no encontre el simbolo base para clonar")
    ok = False
else:
    base = m.group(1)
    MAGENTA = '255,0,255,255,rgb:1,0,1,1'
    # 20 = ficha principal de Melany Recalde (borde negro, como los demas)
    s20 = base.replace('name="14" type="marker"', 'name="20" type="marker"')
    s20 = s20.replace('<Option name="color" type="QString" value="0,255,255,255,rgb:0,1,1,1"/>',
                      '<Option name="color" type="QString" value="{}"/>'.format(MAGENTA))
    # 19 = ficha adicional completada (borde azul, como las demas hijas completadas)
    s19 = s20.replace('name="20" type="marker"', 'name="19" type="marker"')
    s19 = s19.replace('<Option name="outline_color" type="QString" value="0,0,0,255,rgb:0,0,0,1"/>',
                      '<Option name="outline_color" type="QString" value="37,99,235,255,rgb:0.145098,0.3882353,0.9215686,1"/>')
    if 'name="19"' in xml or 'name="20" type="marker"' in xml:
        print("  [AVISO] los simbolos 19/20 ya existen, no se duplican")
    else:
        xml = xml.replace(base, base + "\n          " + s19 + "\n          " + s20, 1)
        cambios.append("simbolos 19 y 20 en magenta")

# ── 3. Vinculacion de la ficha adicional con su regante principal ──────
print("\n[3] Vinculacion ficha adicional -> regante principal")

ok &= sustituir('<field editable="0" name="ficha_madre_id"/>',
                '<field editable="1" name="ficha_madre_id"/>',
                "'ficha_madre_id' pasa a editable")
ok &= sustituir('<field editable="0" name="es_ficha_hija"/>',
                '<field editable="1" name="es_ficha_hija"/>',
                "'es_ficha_hija' pasa a editable")

# widget desplegable buscable, filtrado a las fichas principales de la comunidad
widget_viejo = ('<field configurationFlags="NoFlag" name="ficha_madre_id">\n'
                '          <editWidget type="">\n'
                '            <config>\n'
                '              <Option/>\n'
                '            </config>\n'
                '          </editWidget>\n'
                '        </field>')
widget_nuevo = (
    '<field configurationFlags="NoFlag" name="ficha_madre_id">\n'
    '          <editWidget type="ValueRelation">\n'
    '            <config>\n'
    '              <Option type="Map">\n'
    '                <Option name="AllowMulti" type="bool" value="false"/>\n'
    '                <Option name="AllowNull" type="bool" value="true"/>\n'
    '                <Option name="Description" type="QString" value=""/>\n'
    '                <Option name="FilterExpression" type="QString" '
    'value="coalesce(&quot;es_ficha_hija&quot;, false) = false AND '
    '&quot;comunidad&quot; = current_value(\'comunidad\')"/>\n'
    '                <Option name="Key" type="QString" value="id"/>\n'
    '                <Option name="Layer" type="QString" value="{lid}"/>\n'
    '                <Option name="LayerName" type="QString" value="Fichas_Predios"/>\n'
    '                <Option name="LayerProviderName" type="QString" value="ogr"/>\n'
    '                <Option name="LayerSource" type="QString" value="{lsrc}"/>\n'
    '                <Option name="NofColumns" type="int" value="1"/>\n'
    '                <Option name="OrderByValue" type="bool" value="true"/>\n'
    '                <Option name="UseCompleter" type="bool" value="true"/>\n'
    '                <Option name="Value" type="QString" '
    'value="concat(&quot;apellidos&quot;, \' \', &quot;nombres&quot;, \' — CI \', '
    'coalesce(&quot;cedula&quot;, \'s/n\'))"/>\n'
    '              </Option>\n'
    '            </config>\n'
    '          </editWidget>\n'
    '        </field>').format(lid=LAYER_ID, lsrc=LAYER_SRC)
ok &= sustituir(widget_viejo, widget_nuevo, "desplegable buscable de regante principal")

# ── validacion y escritura ─────────────────────────────────────────────
print("\n" + "-" * 74)
if not ok:
    print("HAY ERRORES — no se modifica el proyecto.")
    sys.exit(1)

try:
    ET.fromstring(xml)
    print("XML valido tras los cambios.")
except ET.ParseError as e:
    print("XML INVALIDO tras los cambios: {} — no se escribe nada.".format(e))
    sys.exit(2)

print("\nCambios preparados:")
for c in cambios:
    print("   - " + c)
print("\nTamano: {:,} -> {:,} bytes".format(len(original), len(xml)))

if not APLICAR:
    print("\nSIMULACION — no se escribio. Ejecutar con --aplicar para guardar.")
    sys.exit(0)

with open(QGS, "w", encoding="utf-8") as f:
    f.write(xml)
print("\nPROYECTO ACTUALIZADO. Falta subirlo a QFieldCloud desde QGIS.")
