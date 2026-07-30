# -*- coding: utf-8 -*-
"""
Nombre canónico de comunidad — fuente única de verdad.

POR QUÉ EXISTE ESTE MÓDULO
--------------------------
Los técnicos escriben el nombre de la comunidad a mano en QField, así que el
mismo lugar aparece como 'IZACATA GRANDE', 'INSACATA', 'MONTESERÍN BAJO' o
'MONTESERIN BAJO'. Varios scripts leen el mismo `data.gpkg` y agrupan por
comunidad:

  · export_geojson.py                     → caudal_por_comunidad.json
  · generar_capas_sectores_comunidades.py → comunidades.geojson / sectores.geojson
  · generar_gpkg_cliente.py               → entregable cartográfico

Cuando cada uno normalizaba a su manera, las claves no coincidían y el caudal
de una comunidad se perdía en silencio (Monteserrín Bajo y el grupo Izacata
quedaron en 0 l/s). Todos deben importar `canonica()` de aquí.

REGLA: si hay que corregir la escritura de una comunidad, se agrega a
CORRECCIONES_COM en este archivo y NO en ningún otro.
"""

import re
import unicodedata

# Escrituras erróneas detectadas en campo → nombre correcto.
# La comparación es por subcadena sobre el nombre ya normalizado, así que
# 'INSACATA' captura también 'INSACATA GRANDE'.
CORRECCIONES_COM = {
    'LARCACOCHA': 'LARCACHACA',
    'LARCACOHA': 'LARCACHACA',
    'INSACATA': 'IZACATA',
    'IZACATA GRANDE': 'IZACATA',
    'CARRERA- ACEROLOMA': 'CARRERA',
    'CARRERA-ACEROLOMA': 'CARRERA',
    'CACHICUNGA': 'CARRERA',
    'PANBAMAQUITO': 'PAMBAMARQUITO',
    'PAMBAMAQUITO': 'PAMBAMARQUITO',
    'PANBAMARQUITO': 'PAMBAMARQUITO',
}


def normalizar(texto):
    """MAYÚSCULAS, sin acentos, sin espacios repetidos. No corrige nombres."""
    if not texto:
        return ""
    texto = texto.upper().strip()
    texto = unicodedata.normalize('NFD', texto)
    texto = ''.join(c for c in texto if unicodedata.category(c) != 'Mn')
    return re.sub(r'\s+', ' ', texto)


def canonica(com):
    """Nombre con el que TODOS los scripts deben agrupar por comunidad."""
    com_norm = normalizar(com)
    for original, correcto in CORRECCIONES_COM.items():
        if normalizar(original) in com_norm:
            return correcto
    return com_norm


# Alias histórico: generar_capas_sectores_comunidades.py llamaba así a canonica().
aplicar_correcciones = canonica
