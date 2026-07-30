# -*- coding: utf-8 -*-
"""
Formulario QField: sección visible para marcar una ficha como PREDIO ADICIONAL
y valores por defecto de la Sección 5 (Encuesta).

PROBLEMA (JAVIKO, 2026-07-30)
-----------------------------
El instructivo "Registrar un predio adicional de un regante" pide activar la
casilla "Es Ficha Hija", pero ese campo NUNCA se colocó en el formulario: el
widget CheckBox está configurado y el campo existe en la base, pero el técnico
no lo ve. `ficha_madre_id` y `estado_investigacion` sí están, pero enterrados
en la pestaña "8. AUDITORÍA". Por eso los técnicos siguieron anotando la clave
catastral en observaciones.

Además, la Sección 5 (Encuesta) se dejaba vacía en las fichas nuevas aunque las
respuestas son las mismas en casi todo el sistema (validado contra las 6.793
fichas: presa Sí 87%, Asamblea general 97%, presidente JOSE JOAQUIN TIPANLUISA,
60 años, 63 km). Se precargan esos valores para que el técnico solo corrobore.

QUÉ HACE
--------
1. Inserta la pestaña "➕ PREDIO ADICIONAL" entre "1. DATOS DEL PROPIETARIO" y
   "2. PREDIO Y RIEGO":
     - es_ficha_hija (casilla, siempre visible, default false)
     - grupo "Vincular al regante principal" con ficha_madre_id y
       estado_investigacion, visible SOLO si la casilla está marcada
   Una ficha normal no cambia en nada: la casilla nace desmarcada y el grupo
   de vinculación permanece oculto.
2. Quita ficha_madre_id y estado_investigacion del grupo "Datos de Ficha Hija"
   de Auditoría (quedan origen_datos, completado_por y fecha_completado, que sí
   son de auditoría).
3. Defaults de la Sección 5 con applyOnUpdate="0": SOLO se aplican al CREAR la
   ficha. Al editar, QGIS/QField nunca los re-evalúa, así que lo que escriba el
   técnico prevalece siempre sobre el default (pedido explícito de JAVIKO).
   operador_sector NO lleva default: varía por comunidad.

CÓMO
----
Cirugía de texto sobre el .qgs (es XML plano) copiando patrones que ya existen
en el archivo — nunca inventar elementos (lección del intento fallido con
<editformconfig>). Simula por defecto; escribe solo con --aplicar, con respaldo
previo. Verificar después con verificar_formulario_adicional.py (PyQGIS).

Tras aplicar: subir el proyecto a QFieldCloud en ventana coordinada (QFieldSync
reemplaza archivos completos) y que los técnicos sincronicen.
"""

import re
import shutil
import sys
import time

QGS = r"C:\Users\HP\QField\cloud\porotog_levantamiento_offline\POROTOG LEVANTAMIENTO_qfield_cloud.qgs"

# Campo -> expresión QGIS del valor por defecto (solo al crear; applyOnUpdate=0).
# Valores en el formato EXACTO de los datos existentes ('Sí', no 'SÍ') para que
# los ValueMap/CheckBox los reconozcan.
DEFAULTS = {
    'es_ficha_hija': 'false',
    'conoce_presa': "'Sí'",
    'como_elige_dir': "'Asamblea general'",
    'anios_sistema': '60',    # MEDIUMINT en el gpkg
    'km_canal': '63',         # REAL en el gpkg
    'recibio_capacitacion': "'Sí'",
    'le_gustaria_cap': "'Sí'",
}

# Estos dos YA tienen una expresión viva con applyOnUpdate="1" que pasa a
# mayúsculas lo que escribe el técnico en cada edición. No se pisa: se integra.
# Vacío -> default de la ficha de papel; con texto -> upper(texto del técnico).
# El dato del técnico prevalece siempre (solo cambia su capitalización, que es
# el comportamiento que ya estaba en producción).
DEFAULTS_CON_UPPER = {
    'nom_presidente': 'JOSE JOAQUIN TIPANLUISA',
    'temas_capacitacion': 'RIEGO',
}

LABEL = ('<labelStyle labelColor="" overrideLabelColor="0" overrideLabelFont="0">\n'
         '              <labelFont bold="0" description="Segoe UI,8.3,-1,5,400,0,0,0,0,0,0,0,0,0,0,1,,0,0"'
         ' italic="0" strikethrough="0" style="" underline="0"/>\n'
         '            </labelStyle>')


def campo(nombre, index):
    return ('<attributeEditorField horizontalStretch="0" index="{i}" name="{n}" showLabel="1" verticalStretch="0">\n'
            '            {l}\n'
            '          </attributeEditorField>').format(i=index, n=nombre, l=LABEL)


# Pestaña nueva. Índices tomados del propio .qgs: ficha_madre_id=66,
# es_ficha_hija=67 (alias), estado_investigacion=68.
NUEVA_PESTANA = (
    '<attributeEditorContainer collapsed="0" collapsedExpression="" collapsedExpressionEnabled="0"'
    ' columnCount="1" groupBox="0" horizontalStretch="0" name="➕ PREDIO ADICIONAL" showLabel="1"'
    ' type="Tab" verticalStretch="0" visibilityExpression="" visibilityExpressionEnabled="0">\n'
    '          ' + LABEL + '\n'
    '          ' + campo('es_ficha_hija', 67) + '\n'
    '          <attributeEditorContainer collapsed="0" collapsedExpression="" collapsedExpressionEnabled="0"'
    ' columnCount="1" groupBox="1" horizontalStretch="0" name="🔗 Vincular al regante principal" showLabel="1"'
    ' type="GroupBox" verticalStretch="0"'
    ' visibilityExpression="coalesce(&quot;es_ficha_hija&quot;, false) = true" visibilityExpressionEnabled="1">\n'
    '            ' + LABEL + '\n'
    '            ' + campo('ficha_madre_id', 66) + '\n'
    '            ' + campo('estado_investigacion', 68) + '\n'
    '          </attributeEditorContainer>\n'
    '        </attributeEditorContainer>\n        '
)


def main():
    aplicar = '--aplicar' in sys.argv
    s = open(QGS, encoding='utf-8').read()
    original = s

    # ── validaciones previas: anclajes únicos ──
    for ancla, n_esperado in [
        (r'name="2\. PREDIO Y RIEGO"', 1),
        (r'name="➕ PREDIO ADICIONAL"', 0),          # no aplicado aún (idempotencia)
        (r'<layername>Fichas_Predios</layername>', 1),
    ]:
        n = len(re.findall(ancla, s))
        if n != n_esperado:
            if ancla == r'name="➕ PREDIO ADICIONAL"' and n > 0:
                raise SystemExit("ABORTADO: la pestaña ➕ PREDIO ADICIONAL ya existe (ya se aplicó antes)")
            raise SystemExit(f"ABORTADO: ancla {ancla} aparece {n} veces (esperado {n_esperado})")

    # ── 1. insertar la pestaña antes de "2. PREDIO Y RIEGO" ──
    m = re.search(r'<attributeEditorContainer[^>]*name="2\. PREDIO Y RIEGO"', s)
    s = s[:m.start()] + NUEVA_PESTANA + s[m.start():]
    print("  ✓ pestaña ➕ PREDIO ADICIONAL insertada antes de '2. PREDIO Y RIEGO'")

    # ── 2. sacar los dos campos de Auditoría (ahora hay 2 de cada; la copia
    #       vieja es la SEGUNDA, dentro de 'Datos de Ficha Hija') ──
    for nombre in ('ficha_madre_id', 'estado_investigacion'):
        patron = re.compile(
            r'<attributeEditorField[^>]*name="' + nombre + r'"[^>]*>.*?</attributeEditorField>\s*', re.S)
        hits = list(patron.finditer(s))
        if len(hits) != 2:
            raise SystemExit(f"ABORTADO: {nombre} aparece {len(hits)} veces tras insertar (se esperaban 2)")
        h = hits[1]  # la segunda = la de Auditoría (la pestaña nueva va antes)
        s = s[:h.start()] + s[h.end():]
        print(f"  ✓ {nombre} retirado de '8. AUDITORÍA → Datos de Ficha Hija'")

    # ── 3. defaults (solo al crear: applyOnUpdate="0" garantiza que al editar
    #       prevalece lo que escribió el técnico) ──
    for f_, expr in DEFAULTS.items():
        expr_xml = expr.replace('&', '&amp;').replace('"', '&quot;').replace('<', '&lt;')
        patron = re.compile(r'<default applyOnUpdate="0" expression="[^"]*" field="' + f_ + r'"/>')
        hits = patron.findall(s)
        if len(hits) != 1:
            raise SystemExit(f"ABORTADO: default de {f_} aparece {len(hits)} veces (se esperaba 1)")
        if 'expression=""' not in hits[0]:
            print(f"  ⚠ {f_} ya tenía default [{hits[0]}]; se respeta y NO se toca")
            continue
        s = patron.sub(f'<default applyOnUpdate="0" expression="{expr_xml}" field="{f_}"/>', s, count=1)
        print(f"  ✓ default {f_} = {expr}  (solo al crear, nunca al editar)")

    # ── 3b. campos con upper() vivo: integrar el default sin perder la
    #        normalización a mayúsculas ni pisar lo que escriba el técnico ──
    for f_, valor in DEFAULTS_CON_UPPER.items():
        viejo = (f'<default applyOnUpdate="1" expression="upper(&quot;{f_}&quot;)" field="{f_}"/>')
        if s.count(viejo) != 1:
            raise SystemExit(f"ABORTADO: la expresión upper() de {f_} no está como se esperaba")
        expr = (f"upper(coalesce(nullif(trim(&quot;{f_}&quot;), ''), '{valor}'))")
        s = s.replace(viejo, f'<default applyOnUpdate="1" expression="{expr}" field="{f_}"/>', 1)
        print(f"  ✓ default {f_} = '{valor}' si está vacío; si no, upper(lo del técnico) como antes")

    # ── resumen y escritura ──
    print(f"\n  {len(original):,} → {len(s):,} bytes ({len(s)-len(original):+,})")
    if not aplicar:
        print("\n  SIMULACIÓN — nada se escribió. Ejecuta con --aplicar para escribir.")
        return
    respaldo = QGS + time.strftime('.bak-%Y%m%d-%H%M')
    shutil.copy2(QGS, respaldo)
    print(f"  ✓ respaldo: {respaldo}")
    # El .qgs original es 100% CRLF; newline='\r\n' lo mantiene uniforme.
    with open(QGS, 'w', encoding='utf-8', newline='\r\n') as f:
        f.write(s)
    print(f"  ✓ ESCRITO: {QGS}")
    print("\n  Siguiente paso: python-qgis scripts/verificar_formulario_adicional.py")


if __name__ == '__main__':
    main()
