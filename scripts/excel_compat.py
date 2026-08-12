# -*- coding: utf-8 -*-
"""
Parche de compatibilidad para los Excel que genera openpyxl.

El problema que resuelve
------------------------
Los colores y bordes de los Excel del proyecto estaban ESCRITOS en el archivo
(se verificó leyéndolos de vuelta) pero el Excel del usuario los mostraba en
blanco. Se encontró comparando, dentro del mismo archivo, una celda pintada a
mano en Excel contra una generada por openpyxl:

    pintada a mano : <xf fontId="1" fillId="2" ... applyFont="1" applyFill="1">
    de openpyxl    : <xf fontId="1" fillId="2" ...>

La norma OOXML dice que los atributos `applyFill` / `applyBorder` / `applyFont`
indican si el formato del `<xf>` se usa o se hereda del estilo base (que no
tiene relleno ni bordes). openpyxl no los escribe nunca, y hay builds de Excel
que ante su ausencia heredan: el color queda en el archivo pero no se pinta.
La prueba definitiva: al guardar el usuario su copia, Excel descartó todos los
rellenos y bordes generados — para su parser nunca estuvieron aplicados.

Qué hace
--------
`aplicar_formatos(ruta)` reescribe el `xl/styles.xml` del archivo ya guardado,
añadiendo `applyFont="1" applyFill="1" applyBorder="1"` a cada `<xf>` de
`<cellXfs>` que no los traiga. No toca nada más del archivo.

Uso
---
    from excel_compat import aplicar_formatos
    wb.save(SALIDA)
    aplicar_formatos(SALIDA)
"""
import os
import re
import shutil
import tempfile
import zipfile


def _parchar_xf(m):
    xf = m.group(0)
    for attr in ('applyFont', 'applyFill', 'applyBorder'):
        if attr not in xf:
            # insertar antes del cierre, sea '/>' o '>'
            cierre = '/>' if xf.endswith('/>') else '>'
            xf = xf[:-len(cierre)] + ' {}="1"'.format(attr) + cierre
    return xf


def aplicar_formatos(ruta):
    """Añade los applyX a cellXfs del xlsx en `ruta`. Devuelve cuántos parchó."""
    with zipfile.ZipFile(ruta) as z:
        entradas = {n: z.read(n) for n in z.namelist()}

    estilos = entradas['xl/styles.xml'].decode('utf-8')
    m = re.search(r'<cellXfs.*?</cellXfs>', estilos, re.S)
    if not m:
        return 0
    bloque = m.group(0)
    nuevos, n = re.subn(r'<xf [^>]*?/?>', _parchar_xf, bloque)
    if nuevos == bloque:
        return 0
    entradas['xl/styles.xml'] = estilos.replace(bloque, nuevos).encode('utf-8')

    # reescribir el zip completo en un temporal y reemplazar
    fd, tmp = tempfile.mkstemp(suffix='.xlsx', dir=os.path.dirname(ruta) or '.')
    os.close(fd)
    try:
        with zipfile.ZipFile(tmp, 'w', zipfile.ZIP_DEFLATED) as z:
            for nombre, datos in entradas.items():
                z.writestr(nombre, datos)
        shutil.move(tmp, ruta)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)
    return n
