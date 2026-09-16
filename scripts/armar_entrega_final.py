# -*- coding: utf-8 -*-
"""
Arma la entrega definitiva para el consorcio, lista para escribir de una vez.

Nace de que la memoria USB murio a mitad de un reemplazo masivo: parchear un
paquete a medio escribir no tiene sentido, asi que la entrega se rehace entera
y se verifica antes de salir.

Que hace, en orden:
  1. Copia el paquete original a una carpeta nueva.
  2. Aplica encima las fichas actualizadas, emparejando por NOMBRE DE ARCHIVO
     (el codigo de la ficha es unico, asi que no depende de la carpeta).
  3. Renombra las carpetas de comunidad al formato de los filtros de la web:
     "1. LARCACHACA", "49. ASO. EL MANZANO"… El numero y el rotulo salen del
     catalogo oficial de constants.ts, no se escriben a mano.
  4. Mete dentro la carpeta del Producto 5.
  5. Verifica: cuenta, PDF corruptos y que no quede ninguna ficha con la
     redaccion vieja de la seccion 1.
  6. Deja un ZIP unico. Subir 6.840 archivos sueltos a Drive es lentisimo por
     el tramite de cada uno; un solo archivo sube muchisimo mas rapido.

Uso:  python -X utf8 scripts/armar_entrega_final.py
"""
import io
import os
import re
import shutil
import sys
import unicodedata
import zipfile

ESCRITORIO = r'C:\Users\HP\OneDrive\Escritorio'
ORIGINAL = os.path.join(ESCRITORIO, 'FICHAS PDF POROTOG')
ACTUALIZADAS = os.path.join(ESCRITORIO, 'FICHAS ACTUALIZADAS 16-SEP-2026')
PRODUCTO5 = os.path.join(ESCRITORIO, 'PRODUCTO 5 - ENTREGA 18-SEP-2026')
DESTINO = os.path.join(ESCRITORIO, 'ENTREGA CONSORCIO - 16-SEP-2026')
ZIP = os.path.join(ESCRITORIO, 'ENTREGA CONSORCIO - 16-SEP-2026.zip')
CONSTANTS = os.path.join(
    ESCRITORIO, 'CAYAMBE CATASTRO RIEGO', 'padron-app', 'src', 'lib', 'constants.ts')

TITULO_VIEJO = 'DATOS DEL PROPIETARIO / TITULAR'


def _sin_tildes(s):
    return ''.join(c for c in unicodedata.normalize('NFD', s)
                   if unicodedata.category(c) != 'Mn').upper().strip()


def catalogo():
    """Las 50 comunidades con su numero y su rotulo, tal como los muestra la web.

    Devuelve dos indices: por nombre sin tildes —las carpetas del disco van sin
    ellas, porque el generador sanea los nombres de archivo— y por numero, que
    es el que sirve cuando el nombre de la carpeta no coincide con ninguno.
    """
    s = io.open(CONSTANTS, encoding='utf-8').read()
    filas = re.findall(
        r"\{\s*n:\s*(\d+),\s*sector:\s*'([^']+)',\s*oficial:\s*'([^']+)',"
        r"\s*datos:\s*'([^']*)'\s*\}", s)
    por_nombre = {_sin_tildes(d): f'{n}. {ofi}' for n, sec, ofi, d in filas if d}
    por_numero = {int(n): f'{n}. {ofi}' for n, sec, ofi, d in filas}
    return por_nombre, por_numero


def numero_por_las_fichas(carpeta):
    """El numero de comunidad que llevan los codigos de las fichas de la carpeta.

    Hace falta porque alguna carpeta quedo con un nombre que no esta en el
    catalogo —«IZACATA» en vez de «IZACATA GRANDE»—. El codigo de la ficha
    (S01-C18-R001-F01) sí dice a que comunidad pertenece, y es el dato bueno.
    Devuelve None si las fichas no coinciden todas en la misma.
    """
    numeros = set()
    for a in os.listdir(carpeta):
        m = re.match(r'S\d{2}-C(\d{2})-R\d{3}-F\d{2}', a)
        if m:
            numeros.add(int(m.group(1)))
    return numeros.pop() if len(numeros) == 1 else None


def pdfs_de(base):
    encontrados = []
    for raiz, dirs, archivos in os.walk(base):
        dirs[:] = [d for d in dirs if not d.startswith('.')]
        for a in archivos:
            if a.lower().endswith('.pdf'):
                encontrados.append(os.path.join(raiz, a))
    return encontrados


def paso(n, texto):
    print(f'\n[{n}] {texto}', flush=True)


def main():
    for ruta in (ORIGINAL, ACTUALIZADAS, PRODUCTO5):
        if not os.path.isdir(ruta):
            print('Falta la carpeta:', ruta)
            return 1

    paso(1, 'Copiando el paquete original…')
    if os.path.exists(DESTINO):
        shutil.rmtree(DESTINO)
    # .tiles es la cache de mosaicos satelitales: no forma parte de la entrega.
    shutil.copytree(ORIGINAL, DESTINO,
                    ignore=shutil.ignore_patterns('.tiles', '*.tmp'))
    print('    copiados', len(pdfs_de(DESTINO)), 'PDF', flush=True)

    paso(2, 'Aplicando las fichas actualizadas…')
    # La clave va en minusculas: alguna ficha tiene el apellido corregido y su
    # nombre cambio de "lanchimba" a "LANCHIMBA".
    destino_por_nombre = {}
    for p in pdfs_de(DESTINO):
        destino_por_nombre.setdefault(os.path.basename(p).lower(), []).append(p)

    nuevas = pdfs_de(ACTUALIZADAS)
    puestas = renombradas = sin_pareja = ambiguas = 0
    for n in nuevas:
        base = os.path.basename(n)
        candidatos = destino_por_nombre.get(base.lower(), [])
        if not candidatos:
            sin_pareja += 1
            print('    ! sin pareja:', base)
            continue
        if len(candidatos) > 1:
            ambiguas += 1
            print('    ! nombre repetido:', base)
            continue
        viejo = candidatos[0]
        shutil.copy2(n, viejo)
        puestas += 1
        if os.path.basename(viejo) != base:
            os.replace(viejo, os.path.join(os.path.dirname(viejo), base))
            renombradas += 1
    print(f'    aplicadas {puestas} · renombradas {renombradas} · '
          f'sin pareja {sin_pareja} · repetidas {ambiguas}', flush=True)

    paso(3, 'Numerando las carpetas como los filtros de la web…')
    por_nombre, por_numero = catalogo()
    print(f'    catálogo: {len(por_numero)} comunidades', flush=True)
    renombrados, por_codigo, sin_catalogo = 0, 0, []
    for sector in sorted(os.listdir(DESTINO)):
        ruta_sector = os.path.join(DESTINO, sector)
        if not os.path.isdir(ruta_sector) or not sector.startswith('Sector'):
            continue
        for com in sorted(os.listdir(ruta_sector)):
            actual = os.path.join(ruta_sector, com)
            if not os.path.isdir(actual) or com[0].isdigit():
                continue                     # ya numerada
            nuevo_nombre = por_nombre.get(_sin_tildes(com))
            if not nuevo_nombre:
                n = numero_por_las_fichas(actual)
                nuevo_nombre = por_numero.get(n) if n else None
                if nuevo_nombre:
                    por_codigo += 1
                    print(f'    · {com} -> {nuevo_nombre} (por el código de sus fichas)')
            if not nuevo_nombre:
                sin_catalogo.append(f'{sector}/{com}')
                continue
            os.rename(actual, os.path.join(ruta_sector, nuevo_nombre))
            renombrados += 1
    print(f'    renombradas {renombrados} carpetas '
          f'({por_codigo} resueltas por el código de las fichas)', flush=True)
    for s in sin_catalogo:
        print('    ! SIN NUMERO:', s)

    paso(4, 'Agregando el Producto 5…')
    shutil.copytree(PRODUCTO5, os.path.join(DESTINO, os.path.basename(PRODUCTO5)))
    print('    listo', flush=True)

    paso(5, 'Verificando…')
    import fitz
    todos = pdfs_de(DESTINO)
    fichas = [p for p in todos
              if os.path.basename(p).startswith('S0') and ' - ' in os.path.basename(p)]
    malos, con_viejo, peso = 0, 0, 0
    for p in todos:
        sz = os.path.getsize(p); peso += sz
        with open(p, 'rb') as f:
            h = f.read(5); f.seek(max(0, sz - 2048)); t = f.read()
        if h != b'%PDF-' or b'%%EOF' not in t:
            malos += 1
            print('    ! corrupto:', p)
    for p in fichas:
        if TITULO_VIEJO in fitz.open(p)[0].get_text():
            con_viejo += 1
    print(f'    fichas          : {len(fichas)}')
    print(f'    PDF totales     : {len(todos)}')
    print(f'    corruptos       : {malos}')
    print(f'    con título viejo: {con_viejo}')
    print(f'    peso            : {peso / 1073741824:.2f} GB', flush=True)

    paso(6, 'Comprimiendo para subir a Drive…')
    if os.path.exists(ZIP):
        os.remove(ZIP)
    # Los PDF ya vienen comprimidos: guardarlos tal cual es mucho mas rapido y
    # ocupa casi lo mismo. Solo se comprime lo que si se beneficia.
    n = 0
    with zipfile.ZipFile(ZIP, 'w', zipfile.ZIP_STORED, allowZip64=True) as z:
        for raiz, dirs, archivos in os.walk(DESTINO):
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            for a in archivos:
                p = os.path.join(raiz, a)
                rel = os.path.relpath(p, DESTINO)
                comp = (zipfile.ZIP_DEFLATED
                        if a.lower().endswith(('.xlsx', '.shp', '.dbf', '.dxf', '.qgz'))
                        else zipfile.ZIP_STORED)
                z.write(p, rel, compress_type=comp)
                n += 1
    print(f'    {n} archivos · {os.path.getsize(ZIP) / 1048576:.0f} MB', flush=True)

    print(f'\nCarpeta : {DESTINO}')
    print(f'ZIP     : {ZIP}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
