# -*- coding: utf-8 -*-
"""
Corrige el desplegable de vinculacion (ficha_madre_id) del proyecto de campo.

CAUSA DEL BUG: el ValueRelation llevaba el filtro
    coalesce("es_ficha_hija", false) = false AND "comunidad" = current_value('comunidad')
QField no resuelve current_value() en ese contexto: la lista salia vacia y al
guardar la ficha escribia NULL en ficha_madre_id. Toda ficha adicional que un
tecnico completara con ese formulario perdia el vinculo con su regante.

CORRECCION: el filtro queda solo con
    coalesce("es_ficha_hija", false) = false
(la lista muestra todas las fichas principales; el buscador del desplegable
sigue permitiendo filtrar por apellido o cedula al escribir).
"""
import shutil
import sys
import xml.etree.ElementTree as ET
from datetime import datetime

QGS = r"C:\Users\HP\QField\cloud\porotog_levantamiento_offline\POROTOG LEVANTAMIENTO_qfield_cloud.qgs"
RESPALDO = (r"C:\Users\HP\OneDrive\Escritorio\CAYAMBE CATASTRO RIEGO\respaldos"
            r"\POROTOG_qgs_{}_pre-fix-widget.qgs".format(datetime.now().strftime('%Y-%m-%d_%H%M')))

VIEJO = ('value="coalesce(&quot;es_ficha_hija&quot;, false) = false AND '
         '&quot;comunidad&quot; = current_value(\'comunidad\')"')
NUEVO = 'value="coalesce(&quot;es_ficha_hija&quot;, false) = false"'

with open(QGS, encoding='utf-8') as f:
    xml = f.read()

n = xml.count(VIEJO)
print("apariciones del filtro con current_value:", n)
if n != 1:
    print("ERROR: esperaba exactamente 1. No se toca nada.")
    sys.exit(1)

shutil.copy2(QGS, RESPALDO)
print("respaldo:", RESPALDO)

xml = xml.replace(VIEJO, NUEVO)
try:
    ET.fromstring(xml)
    print("XML valido tras el cambio")
except ET.ParseError as e:
    print("XML INVALIDO:", e)
    sys.exit(2)

with open(QGS, 'w', encoding='utf-8') as f:
    f.write(xml)
print("PROYECTO CORREGIDO. Falta subirlo a QFieldCloud junto con data.gpkg.")
