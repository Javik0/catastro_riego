# -*- coding: utf-8 -*-
"""
Los documentos 2 a 6 de la reentrega v2, en Word editable con el membrete.

Armando los pidió el 12-oct-2026 para poner su nombre y firmarlos: en el zip
de la reentrega todos van en PDF.

* 2 (diccionario v2) y la nota aclaratoria de la carpeta 6 son nuevos de la
  v2: se sacan aquí con la técnica de `generar_producto5_word.py`, que toma los
  bloques exactos del PDF justo antes de construirlo y los escribe en Word sobre
  `membrete.docx`. El contenido no se reescribe: PDF y Word salen del mismo
  material.
* 3, 4, 5 y 6 (link, memoria, manual y porcentaje de avance) no cambiaron en la
  v2: se copian los Word del 17-sep (`PRODUCTO 5 - WORD MEMBRETADOS`), que son
  los que corresponden a esos PDF.

Uso:  python -X utf8 scripts/generar_reentrega_v2_word.py
      (después de armar_reentrega_producto5.py, que deja la v2 al día)
"""
import os
import shutil
import sys
import tempfile
import zipfile

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)

ESCRITORIO = r'C:\Users\HP\OneDrive\Escritorio'
PLANTILLA = os.path.join(ESCRITORIO, 'CAYAMBE CATASTRO RIEGO', 'membrete.docx')
V2 = os.path.join(ESCRITORIO, 'PRODUCTO 5 - REENTREGA v2 (oct-2026)')
WORD_SEP = os.path.join(ESCRITORIO, 'PRODUCTO 5 - WORD MEMBRETADOS')
SALIDA = os.path.join(ESCRITORIO, 'PRODUCTO 5 - REENTREGA v2 - WORD EDITABLES')
ZIP = SALIDA + '.zip'

os.environ['MEMBRETE_PREFECTURA'] = '1'      # como los Word del 17-sep

# Cómo nombra cada generador su PDF  ->  cómo se llama el Word
NUEVOS = {
    'DICCIONARIO DE DATOS v2.pdf': '2 - DICCIONARIO DE DATOS v2.docx',
    'NOTA ACLARATORIA - porcentaje de avance (observacion C05).pdf':
        '6 - NOTA ACLARATORIA - porcentaje de avance (observacion C05).docx',
}
SIN_CAMBIOS = ['3 - LINK DE LA PLATAFORMA.docx', '4 - MEMORIA TECNICA DEL GEOVISOR.docx',
               '5 - MANUAL DE USO DEL GEOVISOR.docx', '6 - PORCENTAJE DE AVANCE Y FECHA DE CORTE.docx']

capturado = []          # (nombre del PDF, bloques)


def _espiar():
    """Guarda los bloques de cada documento sin estorbar la creación del PDF."""
    from reportlab.platypus import SimpleDocTemplate
    original = SimpleDocTemplate.build

    def build(self, flowables, *a, **kw):
        capturado.append((os.path.basename(self.filename), list(flowables)))
        return original(self, flowables, *a, **kw)

    SimpleDocTemplate.build = build


def main():
    for r in (PLANTILLA, V2, WORD_SEP):
        if not os.path.exists(r):
            print('No encuentro:', r)
            return 1
    if os.path.exists(SALIDA):
        shutil.rmtree(SALIDA)
    os.makedirs(SALIDA)

    _espiar()
    import a_word
    import armar_reentrega_producto5 as ar
    import reentrega_documentos as rd

    gpkg = os.path.join(V2, ar.C_QGIS, 'padron_riego_porotog.gpkg')
    with tempfile.TemporaryDirectory() as tmp:
        rd.diccionario_v2(gpkg, os.path.join(V2, ar.C_SHP), tmp)
        rd.nota_avance(gpkg, tmp)

    hechos = []
    for pdf, bloques in capturado:
        nombre = NUEVOS.get(pdf)
        if not nombre:
            continue
        a_word.escribir(bloques, os.path.join(SALIDA, nombre), PLANTILLA)
        hechos.append(nombre)
    for nombre in SIN_CAMBIOS:
        shutil.copy2(os.path.join(WORD_SEP, nombre), os.path.join(SALIDA, nombre))
        hechos.append(nombre)
    assert len(hechos) == 6, hechos

    with zipfile.ZipFile(ZIP, 'w', zipfile.ZIP_DEFLATED) as z:
        for a in sorted(hechos):
            z.write(os.path.join(SALIDA, a), a)
    for a in sorted(hechos):
        print(f'  {a}   ({os.path.getsize(os.path.join(SALIDA, a)) / 1024:.0f} KB)')
    print(f'✔ {ZIP}  ({os.path.getsize(ZIP) / 1048576:.1f} MB)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
