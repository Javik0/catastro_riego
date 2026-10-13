# -*- coding: utf-8 -*-
"""
Las 116 fichas cuya cédula se conserva tal como se declaró.

De las 627 fichas con observación de cédula (solicitud a campo del 4-oct),
511 se resolvieron en oficina. Las 116 restantes NO quedan «en verificación de
campo»: el padrón es un censo de lo que declaró cada comunero, en las reuniones
comunitarias o en la visita al predio, según el listado de cada comunidad. La
cédula se registró como la dio el titular, y la conciliación definitiva de
identidades corresponde a los padrones certificados de cada organización
(§11.1-g del informe JAFG-2026-002). Decisión de JAVIKO del 12-oct-2026.

Un solo lugar para clasificarlas: la matriz de respuesta (C04) y la marca de
la tabla `correspondencia_fichas` de la reentrega v2 leen de aquí, así las
cifras de los dos documentos no pueden separarse.

Categorías (en este orden de prioridad):
  organizacion  comunidad, comité, asociación o empresa: no le aplica cédula;
                su RUC no se proporcionó o está incompleto.
  no_valida     persona cuya cédula declarada no supera el dígito verificador.
  repetida      persona cuya cédula consta en más de una ficha principal y en
                oficina no se pudo atribuir a un mismo titular.
  sin_cedula    persona que no proporcionó la cédula.
"""
import collections
import os
import re

import openpyxl

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(os.path.dirname(AQUI))
OFICINA = os.path.join(RAIZ, 'CONTRATO Y FISCALIZACION', 'RESPUESTA OBSERVACIONES PRODUCTO 5',
                       'VERIFICACIONES EN OFICINA (7-oct-2026).xlsx')

ORGANIZACION = re.compile(r'\b(COMIT[EÉ]|COMUNIDAD|COMUNA|ASOCIACI[OÓ]N|COOPERATIVA|JUNTA|IMPORTADORA|'
                          r'EMPRESA|COMPA[NÑ][IÍ]A|FUNDACI[OÓ]N|IGLESIA|S\.A\.?S?\.?|C[IÍ]A\.?|S\.C\.C)(\W|$)')

ORDEN = ('organizacion', 'no_valida', 'repetida', 'sin_cedula')

MARCA = {
    'organizacion': 'Titular es una organización: no aplica cédula; RUC no proporcionado o incompleto',
    'no_valida': 'Cédula según lo declarado: no supera el dígito verificador',
    'repetida': 'Cédula según lo declarado: consta en más de una ficha principal',
    'sin_cedula': 'Cédula no proporcionada por el titular',
}
SUFIJO_MARCA = '; se concilia con el padrón certificado de la organización'


def categoria(que_revisar, titular):
    """Se decide por el nombre del titular, no por el número: un número de 10
    dígitos con tercer dígito 6 o 9 parece un RUC cortado, pero si el titular es
    una persona es una cédula que no valida."""
    q = (que_revisar or '').lower()
    if ('ruc' in q or 'sin cédula' in q) and ORGANIZACION.search((titular or '').upper()):
        return 'organizacion'
    if 'dígito verificador' in q or 'ruc' in q:
        return 'no_valida'
    if 'misma cédula' in q:
        return 'repetida'
    return 'sin_cedula'


def leer():
    """{código de ficha: categoría} de las fichas que la oficina no resolvió."""
    ws = openpyxl.load_workbook(OFICINA, read_only=True)['Solicitud 4-oct']
    salida = collections.OrderedDict()
    for f in ws.iter_rows(min_row=5, values_only=True):
        if f[0] and 'requiere campo' in str(f[5] or '').lower():
            salida[f[0]] = categoria(f[4], f[2])
    return salida


def conteo():
    c = collections.Counter(leer().values())
    return {k: c.get(k, 0) for k in ORDEN}


if __name__ == '__main__':
    c = conteo()
    print(c, sum(c.values()))
