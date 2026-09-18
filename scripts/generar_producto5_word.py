# -*- coding: utf-8 -*-
"""
Los cinco documentos del Producto 5, tambien en Word y sobre el membrete.

El contenido NO se reescribe: se ejecutan los generadores de siempre y se
interceptan los bloques justo antes de que se conviertan en PDF. De ahi salen
las dos versiones, PDF y Word, del mismo material. Si manana cambia una cifra
en el generador, cambia en las dos sin que nadie tenga que acordarse.

La plantilla es el `membrete.docx` de la Prefectura, asi que el Word lleva su
cabecera y su pie de verdad —los del documento que entregaron— y se puede
editar como cualquier otro.

Uso:  python -X utf8 scripts/generar_producto5_word.py
"""
import os
import shutil
import sys
import zipfile

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)

ESCRITORIO = r'C:\Users\HP\OneDrive\Escritorio'
PLANTILLA = os.path.join(ESCRITORIO, 'CAYAMBE CATASTRO RIEGO', 'membrete.docx')
SALIDA = os.path.join(ESCRITORIO, 'PRODUCTO 5 - WORD MEMBRETADOS')
ZIP = os.path.join(ESCRITORIO, 'PRODUCTO 5 - WORD MEMBRETADOS.zip')
TEMPORAL = os.path.join(SALIDA, '_generando')

os.environ['MEMBRETE_PREFECTURA'] = '1'
os.environ['SALIDA_MEMBRETE'] = TEMPORAL

# Como nombra cada generador su PDF  ->  como debe quedar el Word
NOMBRES = {
    '0 - DICCIONARIO DE DATOS.pdf': '2 - DICCIONARIO DE DATOS.docx',
    '0 - MEMORIA TECNICA DEL GEOVISOR.pdf': '4 - MEMORIA TECNICA DEL GEOVISOR.docx',
    '0 - MANUAL DE USO DEL GEOVISOR.pdf': '5 - MANUAL DE USO DEL GEOVISOR.docx',
    'LINK DE LA PLATAFORMA.pdf': '3 - LINK DE LA PLATAFORMA.docx',
    'PORCENTAJE DE AVANCE Y FECHA DE CORTE.pdf':
        '6 - PORCENTAJE DE AVANCE Y FECHA DE CORTE.docx',
}

capturado = []          # (nombre del PDF, bloques)


def _espiar():
    """Guarda los bloques de cada documento sin estorbar la creacion del PDF.

    Se envuelve SimpleDocTemplate.build en vez de tocar los cuatro
    generadores: ellos siguen haciendo lo suyo y aqui solo se mira de paso lo
    que construyeron. Menos codigo que cambiar y ningun riesgo de que el PDF y
    el Word queden con contenidos distintos.
    """
    from reportlab.platypus import SimpleDocTemplate
    original = SimpleDocTemplate.build

    def build(self, flowables, *a, **kw):
        capturado.append((os.path.basename(self.filename), list(flowables)))
        return original(self, flowables, *a, **kw)

    SimpleDocTemplate.build = build


def main():
    if not os.path.exists(PLANTILLA):
        print('No encuentro el membrete:', PLANTILLA)
        return 1
    if os.path.exists(SALIDA):
        shutil.rmtree(SALIDA)
    os.makedirs(TEMPORAL, exist_ok=True)

    _espiar()

    print('[1] Ejecutando los generadores…', flush=True)
    import generar_diccionario_datos
    import generar_memoria_geovisor
    import generar_manual_geovisor
    for modulo in (generar_diccionario_datos, generar_memoria_geovisor,
                   generar_manual_geovisor):
        modulo.main()

    import armar_producto5
    armar_producto5.DESTINO = TEMPORAL
    for carpeta in ('3 - LINK DE LA PLATAFORMA',
                    '6 - PORCENTAJE DE AVANCE Y FECHA DE CORTE'):
        os.makedirs(os.path.join(TEMPORAL, carpeta), exist_ok=True)
    armar_producto5.link()
    armar_producto5.avance()

    print(f'\n[2] Bloques capturados de {len(capturado)} documentos', flush=True)

    print('\n[3] Escribiendo los Word…', flush=True)
    import a_word
    hechos = []
    for pdf, bloques in capturado:
        nombre = NOMBRES.get(pdf)
        if not nombre:
            print(f'    · se omite {pdf} (no es del Producto 5)')
            continue
        destino = os.path.join(SALIDA, nombre)
        a_word.escribir(bloques, destino, PLANTILLA)
        hechos.append(nombre)
        print(f'    {nombre}   ({os.path.getsize(destino) / 1024:.0f} KB)')

    shutil.rmtree(TEMPORAL, ignore_errors=True)

    if len(hechos) != 5:
        print(f'\n    ! se esperaban 5 documentos y salieron {len(hechos)}')

    print('\n[4] Comprimiendo…', flush=True)
    with zipfile.ZipFile(ZIP, 'w', zipfile.ZIP_DEFLATED) as z:
        for a in sorted(hechos):
            z.write(os.path.join(SALIDA, a), a)
    print(f'    {ZIP}  ({os.path.getsize(ZIP) / 1048576:.1f} MB)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
