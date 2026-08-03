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

# Renombres de PRESENTACIÓN: el nombre con el que la comunidad aparece en la
# web, el mapa y el entregable del cliente. El `data.gpkg` NO se toca — en
# QField los técnicos siguen viendo el nombre original, así que renombrar aquí
# no obliga a coordinar una ventana de sincronización.
#
# Un renombre es TAMBIÉN una corrección canónica (se fusiona abajo en
# CORRECCIONES_COM): si solo cambiara el texto mostrado, los scripts que leen
# el data.gpkg crudo seguirían agrupando por el nombre viejo y no cruzarían con
# los que leen el GeoJSON ya renombrado — que es exactamente cómo el caudal de
# Monteserrín volvió a quedar en 0 l/s la primera vez.
RENOMBRES_PRESENTACION = {
    # Monteserrín Bajo se reestructuró en 4 fichas a nombre del Sr. Coloma más
    # 118 adicionales de los comuneros (JAVIKO, 2026-07-30).
    'MONTESERIN BAJO': 'SR. COLOMA MONTESERRIN BAJO',
}

# Escrituras erróneas detectadas en campo → nombre correcto.
# La comparación es por subcadena sobre el nombre ya normalizado y GANA LA
# PRIMERA COINCIDENCIA, así que las reglas específicas van ANTES que las
# genéricas: sin ese orden, 'INSACATA' capturaba a 'COMUNA INSACATA' y fusionaba
# la Comuna Jurídica Izacata (#17 del listado) con Izacata Grande (#18), que son
# comunidades distintas.
CORRECCIONES_COM = {
    'LARCACOCHA': 'LARCACHACA',
    'LARCACOHA': 'LARCACHACA',
    'COMUNA INSACATA': 'COMUNA IZACATA',
    'LOS ANDES INSACATA': 'LOS ANDES IZACATA',
    'INSACATA': 'IZACATA',
    'IZACATA GRANDE': 'IZACATA',
    'CARRERA- ACEROLOMA': 'CARRERA',
    'CARRERA-ACEROLOMA': 'CARRERA',
    'CACHICUNGA': 'CARRERA',
    'PANBAMAQUITO': 'PAMBAMARQUITO',
    'PAMBAMAQUITO': 'PAMBAMARQUITO',
    'PANBAMARQUITO': 'PAMBAMARQUITO',
    **RENOMBRES_PRESENTACION,
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


_NOMBRES_RENOMBRADOS = frozenset(RENOMBRES_PRESENTACION.values())


def nombre_publico(com):
    """Nombre con el que la comunidad se muestra al cliente.

    Devuelve el nombre tal cual viene del campo salvo que tenga un renombre
    explícito. NO canoniza el resto: si lo hiciera, todas las comunidades
    perderían sus acentos ('SAN JOSÉ' -> 'SAN JOSE') y dejarían de coincidir
    con las constantes del frontend.
    """
    c = canonica(com)
    return c if c in _NOMBRES_RENOMBRADOS else (com or '').strip()


# Alias histórico: generar_capas_sectores_comunidades.py llamaba así a canonica().
aplicar_correcciones = canonica
