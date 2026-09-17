# -*- coding: utf-8 -*-
"""
Los cinco documentos del Producto 5, en la hoja membretada de la Prefectura.

Lo pidio el consorcio: los instructivos que van dentro de las carpetas 2 a 6
tienen que salir en el membrete oficial de la Prefectura de Pichincha, no en
la cabecera del estudio.

No se reescribe ningun documento: se vuelven a generar los mismos, con la
variable MEMBRETE_PREFECTURA puesta, de modo que su contenido es identico al
que ya se entrego y lo unico que cambia es la hoja. Asi no hay dos versiones
del texto que puedan separarse con el tiempo.

Uso:  python -X utf8 scripts/generar_producto5_membretado.py
"""
import os
import shutil
import sys
import zipfile

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)

ESCRITORIO = r'C:\Users\HP\OneDrive\Escritorio'
SALIDA = os.path.join(ESCRITORIO, 'PRODUCTO 5 - PDF MEMBRETADOS')
ZIP = os.path.join(ESCRITORIO, 'PRODUCTO 5 - PDF MEMBRETADOS.zip')
TEMPORAL = os.path.join(SALIDA, '_generando')

# Se activa antes de importar nada: los generadores leen la variable al armar
# su documento.
os.environ['MEMBRETE_PREFECTURA'] = '1'
os.environ['SALIDA_MEMBRETE'] = TEMPORAL

# Como los nombra cada generador  ->  como deben quedar en la entrega
NOMBRES = {
    '0 - DICCIONARIO DE DATOS.pdf': '2 - DICCIONARIO DE DATOS.pdf',
    '0 - MEMORIA TECNICA DEL GEOVISOR.pdf': '4 - MEMORIA TECNICA DEL GEOVISOR.pdf',
    '0 - MANUAL DE USO DEL GEOVISOR.pdf': '5 - MANUAL DE USO DEL GEOVISOR.pdf',
}


def main():
    if os.path.exists(SALIDA):
        shutil.rmtree(SALIDA)
    os.makedirs(TEMPORAL, exist_ok=True)

    print('[1] Diccionario, memoria y manual…', flush=True)
    import generar_diccionario_datos
    import generar_memoria_geovisor
    import generar_manual_geovisor
    for modulo in (generar_diccionario_datos, generar_memoria_geovisor,
                   generar_manual_geovisor):
        modulo.main()

    print('\n[2] Link de la plataforma y avance…', flush=True)
    import armar_producto5
    # Los dos se escriben dentro de su carpeta numerada; aqui se redirigen al
    # temporal para no tocar la entrega que ya esta armada.
    armar_producto5.DESTINO = TEMPORAL
    for carpeta in ('3 - LINK DE LA PLATAFORMA',
                    '6 - PORCENTAJE DE AVANCE Y FECHA DE CORTE'):
        os.makedirs(os.path.join(TEMPORAL, carpeta), exist_ok=True)
    armar_producto5.link()
    armar_producto5.avance()

    print('\n[3] Ordenando…', flush=True)
    for raiz, _dirs, archivos in os.walk(TEMPORAL):
        for a in archivos:
            if not a.lower().endswith('.pdf'):
                continue
            destino = NOMBRES.get(a, a)
            if a == 'LINK DE LA PLATAFORMA.pdf':
                destino = '3 - LINK DE LA PLATAFORMA.pdf'
            elif a == 'PORCENTAJE DE AVANCE Y FECHA DE CORTE.pdf':
                destino = '6 - PORCENTAJE DE AVANCE Y FECHA DE CORTE.pdf'
            shutil.move(os.path.join(raiz, a), os.path.join(SALIDA, destino))
    shutil.rmtree(TEMPORAL, ignore_errors=True)

    pdfs = sorted(a for a in os.listdir(SALIDA) if a.lower().endswith('.pdf'))
    print(f'    {len(pdfs)} documentos:')
    for a in pdfs:
        print(f'      {a}   ({os.path.getsize(os.path.join(SALIDA, a)) / 1024:.0f} KB)')

    print('\n[4] Verificando el membrete…', flush=True)
    import fitz
    for a in pdfs:
        d = fitz.open(os.path.join(SALIDA, a))
        p = d[0]
        con_logo = len(p.get_images()) > 0
        texto_pie = 'pichincha.gob.ec' in p.get_text().lower()
        print(f'      {a[:44]:46} {len(d):>2} pág · logo {"sí" if con_logo else "NO"}'
              f' · pie {"sí" if texto_pie else "no (es imagen)"}')

    print('\n[5] Comprimiendo…', flush=True)
    with zipfile.ZipFile(ZIP, 'w', zipfile.ZIP_DEFLATED) as z:
        for a in pdfs:
            z.write(os.path.join(SALIDA, a), a)
    print(f'    {ZIP}  ({os.path.getsize(ZIP) / 1048576:.1f} MB)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
