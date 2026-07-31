# -*- coding: utf-8 -*-
"""
Respaldos FUERA de la carpeta que sincroniza QFieldCloud.

POR QUÉ EXISTE
--------------
Los scripts que escriben en `data.gpkg` o en el `.qgs` hacían la copia de
seguridad junto al original, es decir DENTRO de
`C:\\Users\\HP\\QField\\cloud\\porotog_levantamiento_offline`.

Esa carpeta es la que sincroniza QFieldCloud: QFieldSync veía los `.bak-*` como
archivos del proyecto y proponía subirlos. En una sola jornada se acumularon 8
archivos y 48 MB de basura que iban a viajar a la nube y a las tablets.

Todos los respaldos van ahora a `CAYAMBE CATASTRO RIEGO\\respaldos_qgs\\AAAA-MM-DD\\`,
fuera del alcance de la sincronización.
"""

import os
import shutil
import time

RAIZ_RESPALDOS = (r"C:\Users\HP\OneDrive\Escritorio\CAYAMBE CATASTRO RIEGO"
                  r"\respaldos_qgs")


def respaldar(ruta, etiqueta=''):
    """Copia `ruta` a la carpeta de respaldos del día y devuelve el destino.

    `etiqueta` permite distinguir varios respaldos del mismo archivo en un día
    (p. ej. 'antes-de-restaurar').
    """
    if not os.path.exists(ruta):
        raise FileNotFoundError(ruta)
    carpeta = os.path.join(RAIZ_RESPALDOS, time.strftime('%Y-%m-%d'))
    os.makedirs(carpeta, exist_ok=True)
    base = os.path.basename(ruta)
    sufijo = time.strftime('%H%M') + (f'-{etiqueta}' if etiqueta else '')
    destino = os.path.join(carpeta, f'{base}.{sufijo}.bak')
    shutil.copy2(ruta, destino)
    return destino


def aviso(destino):
    """Texto corto para imprimir tras respaldar."""
    return '   respaldo: {}'.format(
        os.path.relpath(destino, os.path.dirname(RAIZ_RESPALDOS)))
