# -*- coding: utf-8 -*-
"""
El informe de las 12 comunidades de Armando, también en Word.

Mismo principio que `generar_producto5_word.py`: no se reescribe el
contenido. Se ejecuta `generar_informe_comunidades_armando.py` tal cual y se
intercepta la lista de bloques justo antes de que `SimpleDocTemplate.build()`
la convierta en PDF, así que el Word sale del mismo material, número por
número.

Este informe no lleva el membrete de la Prefectura —es un documento interno
para Armando, no un entregable del contrato—, así que el Word reproduce la
cabecera del propio estudio (los mismos logos y títulos que las 6.830
fichas), armada en `a_word.agregar_cabecera_pie_estudio()`.

Uso:  python -X utf8 scripts/generar_informe_comunidades_armando_word.py
"""
import os
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)

SALIDA = r'C:\Users\HP\OneDrive\Escritorio\INFORME COMUNIDADES ARMANDO.docx'

capturado = []


def _espiar():
    from reportlab.platypus import SimpleDocTemplate
    original = SimpleDocTemplate.build

    def build(self, flowables, *a, **kw):
        capturado.append(list(flowables))
        return original(self, flowables, *a, **kw)

    SimpleDocTemplate.build = build


def main():
    _espiar()

    print('[1] Ejecutando el generador del PDF…', flush=True)
    import generar_informe_comunidades_armando as informe
    informe.main()

    if not capturado:
        print('No se capturó ningún documento.')
        return 1
    bloques = capturado[0]
    print(f'\n[2] {len(bloques)} bloques capturados', flush=True)

    print('\n[3] Escribiendo el Word…', flush=True)
    import a_word
    PUB = os.path.join(informe.BASE, 'public')
    a_word.escribir(bloques, SALIDA, cabecera_estudio=dict(
        titulo='ESTUDIO DEFINITIVO DE PRESA EN EL RIO POROTOG',
        subtitulo='PADRÓN DE USUARIOS: SISTEMA DE RIEGO COMUNITARIO GUANGUILQUÍ–POROTOG',
        alcance='Ficha de empadronamiento predial y productivo – línea base censal',
        ubicacion='Provincia Pichincha — Cantón Cayambe',
        logo_izq=os.path.join(PUB, 'logo-izq.png'),
        logo_der=os.path.join(PUB, 'logo-der.png'),
        pie_izquierda='AP&CATASTROS',
        pie_derecha_prefijo='CONSORCIO CAYAMBE SPT · Datos al 19 de agosto de 2026 · pág. ',
    ))
    print(f'    {SALIDA}   ({os.path.getsize(SALIDA) / 1024:.0f} KB)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
