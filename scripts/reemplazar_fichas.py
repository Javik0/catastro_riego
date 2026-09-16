# -*- coding: utf-8 -*-
"""
Reemplaza fichas ya entregadas por su version nueva, emparejando por NOMBRE DE
ARCHIVO y no por carpeta.

Para que sirve: quien recibe el paquete reorganiza las carpetas —les pone el
numero de cada comunidad delante, por ejemplo— y entonces una copia normal ya
no encaja: Windows crearia carpetas nuevas junto a las suyas en vez de
reemplazar dentro. Como el nombre de cada ficha empieza por su codigo
(S01-C01-R008-F01 ...) y ese codigo es unico en todo el padron, el archivo se
puede encontrar donde sea que este.

Simula por defecto: no toca nada hasta que se pasa --aplicar.

Uso:
    python -X utf8 scripts/reemplazar_fichas.py --destino "E:\\FICHAS PDF POROTOG"
    python -X utf8 scripts/reemplazar_fichas.py --destino "E:\\..." --aplicar
"""
import argparse
import os
import shutil
import sys

ORIGEN_DEF = r'C:\Users\HP\OneDrive\Escritorio\FICHAS ACTUALIZADAS 16-SEP-2026'


def pdfs_de(base):
    """Todos los PDF del arbol, saltando carpetas ocultas como .tiles."""
    encontrados = []
    for raiz, dirs, archivos in os.walk(base):
        dirs[:] = [d for d in dirs if not d.startswith('.')]
        for a in archivos:
            if a.lower().endswith('.pdf'):
                encontrados.append(os.path.join(raiz, a))
    return encontrados


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--origen', default=ORIGEN_DEF,
                    help='carpeta con las fichas nuevas')
    ap.add_argument('--destino', required=True,
                    help='carpeta del paquete a actualizar (la flash, una copia…)')
    ap.add_argument('--aplicar', action='store_true',
                    help='sin esto solo simula y no escribe nada')
    ap.add_argument('--renombrar', action='store_true',
                    help='si el nombre del archivo cambio (un apellido corregido, '
                         'por ejemplo), renombrar tambien el del destino')
    args = ap.parse_args()

    for ruta, etiqueta in ((args.origen, 'origen'), (args.destino, 'destino')):
        if not os.path.isdir(ruta):
            print(f'No existe la carpeta de {etiqueta}: {ruta}')
            return 1

    nuevas = pdfs_de(args.origen)
    print(f'Fichas nuevas   : {len(nuevas)}')

    # nombre de archivo -> rutas en el destino. La clave va en minusculas: hay
    # fichas cuyo nombre difiere solo en mayusculas porque el apellido se
    # corrigio despues de entregarlas, y comparando exacto no se encontrarian.
    # Si un nombre aparece dos veces no se toca ninguna: habria que decidir
    # cual, y eso no lo decide un script.
    destino_por_nombre = {}
    for p in pdfs_de(args.destino):
        destino_por_nombre.setdefault(os.path.basename(p).lower(), []).append(p)
    print(f'Fichas en destino: {sum(len(v) for v in destino_por_nombre.values())}')

    a_reemplazar, sin_pareja, duplicadas, renombrar = [], [], [], []
    for n in nuevas:
        base = os.path.basename(n)
        candidatos = destino_por_nombre.get(base.lower(), [])
        if not candidatos:
            sin_pareja.append(base)
        elif len(candidatos) > 1:
            duplicadas.append((base, candidatos))
        else:
            a_reemplazar.append((n, candidatos[0]))
            if os.path.basename(candidatos[0]) != base:
                renombrar.append((candidatos[0], base))

    print()
    print(f'  se reemplazan            : {len(a_reemplazar)}')
    print(f'  sin pareja en el destino : {len(sin_pareja)}')
    print(f'  nombre repetido (se omite): {len(duplicadas)}')
    if renombrar:
        print(f'  el nombre del archivo cambio: {len(renombrar)}'
              + ('' if args.renombrar else '  (usa --renombrar para actualizarlo)'))
        for viejo, nuevo in renombrar[:5]:
            print('     entregado:', os.path.basename(viejo))
            print('     nuevo    :', nuevo)
    for s in sin_pareja[:10]:
        print('     ! no esta en el destino:', s)
    for nombre, rutas in duplicadas[:5]:
        print('     ! repetida:', nombre)
        for r in rutas:
            print('         ', r)

    # Las carpetas del destino que van a recibir archivos, para que se vea
    # que los nombres reorganizados se respetan.
    carpetas = sorted({os.path.dirname(d) for _, d in a_reemplazar})
    print(f'\n  carpetas del destino afectadas: {len(carpetas)}')
    for c in carpetas[:8]:
        print('     ', os.path.relpath(c, args.destino))
    if len(carpetas) > 8:
        print(f'      … y {len(carpetas) - 8} mas')

    if not args.aplicar:
        print('\nSIMULACION: no se escribio nada. Repite con --aplicar para hacerlo.')
        return 0

    if sin_pareja or duplicadas:
        print('\nHay fichas sin pareja o con nombre repetido: revisa la lista antes '
              'de aplicar. Se reemplazan solo las que emparejan sin ambiguedad.')

    hechos = fallos = renombrados = 0
    for nuevo, viejo in a_reemplazar:
        try:
            shutil.copy2(nuevo, viejo)
            hechos += 1
            if args.renombrar and os.path.basename(viejo) != os.path.basename(nuevo):
                # El contenido ya esta bien; el nombre del archivo tambien debe
                # quedarlo, o el listado seguira mostrando el apellido viejo.
                os.replace(viejo, os.path.join(os.path.dirname(viejo),
                                               os.path.basename(nuevo)))
                renombrados += 1
        except Exception as e:
            fallos += 1
            print('   ! no se pudo copiar', os.path.basename(nuevo), '->', e)

    print(f'\nReemplazadas: {hechos} · renombradas: {renombrados} · fallos: {fallos}')
    return 0 if not fallos else 1


if __name__ == '__main__':
    sys.exit(main())
