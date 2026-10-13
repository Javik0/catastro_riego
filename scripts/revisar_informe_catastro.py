# -*- coding: utf-8 -*-
"""
Revisa el «Informe Producto 5 — catastro» de Armando contra la base y arma la
hoja de correcciones.

Ese informe es el «informe catastral (I)» que observó la Prefectura (INFORME-
JAFG-2026-002: C01, C02, C03, C06 y C08 salen de sus tablas). Armando prepara
una versión corregida; este script lee su Word, sin modificarlo, y dice qué
cambiar, con el valor exacto:

1. Filas de las tablas de resumen (4 a 6) que no coinciden con la base. La
   referencia es el Anexo A1 de la matriz de respuesta (conciliación por
   comunidad, catálogo C01–C50), que sale de la base entregada.
2. Sumas: filas contra el TOTAL de cada tabla, y la columna «Observaciones»
   (total de fichas − comuneros).
3. Número de comuneros distinto entre las tablas de programación (1 a 3) y las
   de resumen. Ese dato viene de los listados de cada comunidad, no de la
   base: aquí solo se señala, la decisión es de Armando.
4. Fechas: días de la semana que no corresponden a la fecha, e inicio de cada
   sector frente a la primera ficha registrada (C06).
5. Referencias a documentos de la reentrega v2 que no existen, y detalles de
   forma (control de versiones, literales, erratas).

Sirve también para la versión siguiente: se vuelve a ejecutar sobre el Word
nuevo y la hoja sale con lo que quede pendiente.

Uso:  python -X utf8 scripts/revisar_informe_catastro.py ["ruta del Word"]
"""
import collections
import datetime
import os
import re
import sys
import unicodedata

import docx
import openpyxl
from docx.table import Table
from docx.text.paragraph import Paragraph as ParrafoDocx

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)

import a_word  # noqa: E402
import armar_producto5 as ap5  # noqa: E402
from generar_fichas_pdf import (  # noqa: E402
    AZUL as AZUL_PDF, TINTA, FECHA_CORTE, PROJECT_LOCATION, PROJECT_SUBTITLE,
    PROJECT_SUBTITLE_ALCANCE, PROJECT_TITLE, PUB, colors, mm, Paragraph,
    ParagraphStyle, Spacer, tabla_datos, titulo_seccion,
)
from informe_estilo import esn  # noqa: E402

RAIZ = os.path.dirname(os.path.dirname(AQUI))
RESP = os.path.join(RAIZ, 'CONTRATO Y FISCALIZACION', 'RESPUESTA OBSERVACIONES PRODUCTO 5')
ANEXOS = os.path.join(RESP, 'PARA ARMANDO (10-oct-2026)', '1 - PARA ENVIAR AL CONSEJO PROVINCIAL',
                      '2 - ANEXOS DE RESPALDO A1 a A4.xlsx')
SALIDA_DIR = os.path.join(RESP, 'PARA ARMANDO (10-oct-2026)', '3 - SOLO PARA ARMANDO (no enviar)')
NOMBRE = 'CORRECCIONES AL INFORME CATASTRO V2'
WORD_ARMANDO = r'C:\Users\HP\Downloads\INFORME CATASTRO V2.docx'

# Nombres de las tablas de programación -> número de la comunidad en el catálogo
# (C01–C50; 51 = San Vicente de Guayllabamba, que no tiene fichas). Se escriben
# como vienen en el informe; un nombre que no esté aquí se informa, no se pierde.
PROGRAMACION = {
    'LARCACHACA': 1, 'LA LIBERTAD': 2, 'SAN ANTONIO': 3, 'SAN JOSE': 4, 'MILAGRO': 5,
    'CHAMBITOLA': 6, 'LA CANDELARIA': 7, 'CARRERA': 8, 'COCHAPAMBA': 9, 'JESUS GRAN PODER': 10,
    'SANTA BARBARA': 11, 'ASOCIACION POROTOG': 12, 'COMUNA POROTOG': 13,
    'ASOCIACION 17 DE JUNIO': 14, 'AVELLANEDA': 15, 'CORDILLERAS D LOS ANDES': 16,
    'CORDILLERA DE LOS ANDES': 16, 'COMUNA IZACATA': 17, 'IZACATA GRANDE': 18,
    'LOS ANDES IZACATA': 19, 'LOMA GORDA': 20, 'SAN JACINTO': 21, 'MATIAS IMBAGO': 22,
    'CUARTO LOTE': 23, 'ASOC. SAN VICENTE BAJO': 24, 'SANTA ROSA DE PACCHA': 25,
    'ASOC. SAN VICENTE ALTO': 26, 'PUCARA': 27, 'ASOCIACION SAN PEDRO': 28, 'PITANA ALTO': 29,
    'ALPAKA': 30, 'ASOC. PITANA BAJO': 31, 'PROMEJ. PITANA BAJO': 32, 'SANTA ROSA DE PINGULMI': 33,
    'STA MARIANITA DE PINGULMI': 34, 'PAMBAMARCA': 35, 'OTONCITO': 36, 'PANBAMAQUITO': 37,
    'PAMBAMARQUITO': 37, 'SR. HERNAN TIMPE': 38, 'HDA. SAN FRANCISCO': 39, 'MONTESERRIN ALTO': 40,
    'CHAUPIESTANCIA': 41, 'PUEBLO DE OTON': 42, 'CANGAHUA PUNGO': 43, 'CHINCHINLOMA': 44,
    'ASOCIACION ROSALIA': 45, 'SR. COLOMA MONTESERIN BAJO': 46, 'HDA. GUANGUILQUI': 47,
    'PUEBLO DE ASCAZUBI': 48, 'EL MANZANO': 49, 'JUNTA SAN LUIS': 50,
    'SAN VICENTE DE GUAYLLABAMBA': 51,
}
DIAS = ['lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado', 'domingo']
MESES = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre',
         'octubre', 'noviembre', 'diciembre']
ERRATAS = [('Cordilleras d los Andes', 'Cordillera de los Andes'), ('PANBAMAQUITO', 'PAMBAMARQUITO'),
           ('GRN PODER', 'GRAN PODER'), ('ADICIONL.', 'ADICIONALES')]
# Documentos que la reentrega v2 NO tiene en versión 2 (se entregan igual que en septiembre).
SIN_V2 = {'PORCENTAJE DE AVANCE': 'PORCENTAJE DE AVANCE Y FECHA DE CORTE-signed, junto con la NOTA '
                                  'ACLARATORIA - porcentaje de avance (observación C05)',
          'LINK DE LA PLATAFORMA': 'LINK DE LA PLATAFORMA-signed',
          'MEMORIA TECNICA': 'MEMORIA TECNICA DEL GEOVISOR-signed',
          'MANUAL DE USO': 'MANUAL DE USO DEL GEOVISOR-signed'}


def _sin_tildes(s):
    s = unicodedata.normalize('NFKD', ' '.join(str(s or '').upper().split()))
    return ''.join(c for c in s if not unicodedata.combining(c))


def _entero(s):
    s = str(s or '').replace('.', '').replace(',', '').replace('+', '').strip()
    return int(s) if re.fullmatch(r'-?\d+', s) else None


# ── lectura ────────────────────────────────────────────────────────────────
def leer_word(ruta):
    """Párrafos y tablas en el orden del documento (celdas combinadas una vez)."""
    d = docx.Document(ruta)
    parrafos, tablas = [], []
    for el in d.element.body.iterchildren():
        tag = el.tag.split('}')[1]
        if tag == 'p':
            t = ParrafoDocx(el, d).text.strip()
            if t:
                parrafos.append(t)
        elif tag == 'tbl':
            filas = []
            for r in Table(el, d).rows:
                celdas, prev = [], None
                for c in r.cells:
                    if c._tc is not prev:
                        celdas.append(' '.join(c.text.split()))
                    prev = c._tc
                filas.append(celdas)
            tablas.append(filas)
    return parrafos, tablas


def leer_base():
    """Anexo A1: por número de comunidad, fichas principales, adicionales y fechas."""
    ws = openpyxl.load_workbook(ANEXOS, read_only=True)['Anexo A1 Comunidades']
    base = {}
    for f in ws.iter_rows(min_row=5, values_only=True):
        if f[0] and re.fullmatch(r'C\d\d', str(f[0])):
            base[int(f[0][1:])] = dict(nombre=f[1], sector=int(f[3][-1]), pri=f[4], adi=f[5],
                                       tot=f[4] + f[5], primera=f[9], ultima=f[10])
    assert len(base) == 50 and sum(b['pri'] for b in base.values()) == 4307
    return base


def clasificar(tablas):
    prog, resu, gral, version = [], [], None, None
    for t in tablas:
        cab = ' '.join(' '.join(f) for f in t[:3]).upper()
        if 'TOTAL SECTOR' in ' '.join(' '.join(f) for f in t).upper():
            gral = t
        elif 'FICHAS PRINCIPAL' in cab:
            resu.append(t)
        elif 'FECHA' in cab and ('PREDIO' in cab or 'COMUNAS' in cab or 'COMUNIDAD' in cab):
            prog.append(t)
        elif cab.startswith('VERSIÓN') or cab.startswith('VERSION'):
            version = t
    return prog, resu, gral, version


def filas_programacion(t):
    """[(nombre, comuneros, fecha)] y el TOTAL de la tabla."""
    filas, total, ultimo = [], None, None
    for f in t:
        nombre = f[0] if f else ''
        num = _entero(f[1]) if len(f) > 1 else None
        if _sin_tildes(nombre) == 'TOTAL' or (not nombre and len(f) > 1 and _sin_tildes(f[0]) == 'TOTAL'):
            total = num
            continue
        if nombre and num is not None:
            fecha = f[2] if len(f) > 2 else ''
            filas.append((nombre, num, fecha))
            ultimo = nombre
        elif not nombre and ultimo and len(f) > 2 and re.search(r'\d+/\d+/\d{4}', ' '.join(f)):
            pass                    # segundo día de la misma comunidad
    for f in t:
        if any(_sin_tildes(c) == 'TOTAL' for c in f):
            nums = [_entero(c) for c in f if _entero(c) is not None]
            total = nums[0] if nums else total
    return filas, total


def filas_resumen(t):
    """{n: (nombre, comuneros, principales, adicionales, total, observ)} y la fila TOTAL."""
    filas, total = {}, None
    for f in t:
        if len(f) < 7:
            continue
        if re.fullmatch(r'\d+', f[0] or ''):
            filas[int(f[0])] = (f[1], _entero(f[2]), _entero(f[3]), _entero(f[4]), _entero(f[5]),
                                _entero(f[6]))
        elif _sin_tildes(f[1]) == 'TOTAL':
            total = tuple(_entero(c) for c in f[2:7])
    return filas, total


# ── revisión ───────────────────────────────────────────────────────────────
def revisar(ruta):
    parrafos, tablas = leer_word(ruta)
    base = leer_base()
    prog_t, resu_t, gral, version = clasificar(tablas)
    assert len(prog_t) == 3 and len(resu_t) == 3, (len(prog_t), len(resu_t))
    r = collections.OrderedDict()

    # 1. filas de resumen frente a la base
    resumen, totales = {}, []
    for i, t in enumerate(resu_t):
        filas, tot = filas_resumen(t)
        resumen.update({n: (i + 4,) + v for n, v in filas.items()})
        totales.append((i + 4, filas, tot))
    r['filas'] = []
    for n, (tabla, nom, com, pri, adi, tot, obs) in sorted(resumen.items()):
        b = base[n]
        if (pri, adi, tot) != (b['pri'], b['adi'], b['tot']):
            r['filas'].append(dict(tabla=tabla, n=n, nombre=nom, dice=(pri, adi, tot),
                                   debe=(b['pri'], b['adi'], b['tot']),
                                   obs_debe=b['tot'] - com if com is not None else None))
    r['faltan'] = sorted(set(base) - set(resumen))

    # 2. sumas: filas (ya corregidas con la base) contra el TOTAL de cada tabla
    r['sumas'] = []
    for tabla, filas, tot in totales:
        if not tot:
            continue
        com_f = sum(v[1] or 0 for v in filas.values())
        pri_f = sum(base[n]['pri'] for n in filas)
        adi_f = sum(base[n]['adi'] for n in filas)
        for etiqueta, fila, dice in (('comuneros', com_f, tot[0]), ('fichas principales', pri_f, tot[1]),
                                     ('fichas adicionales', adi_f, tot[2]),
                                     ('total de fichas', pri_f + adi_f, tot[3])):
            if fila != dice:
                r['sumas'].append(dict(tabla=tabla, que=etiqueta, total=dice, filas=fila))
    r['obs_mal'] = [dict(n=n, nombre=v[1], obs=v[6], debe=v[5] - v[2])
                    for n, v in sorted(resumen.items())
                    if None not in (v[2], v[5], v[6]) and v[6] != v[5] - v[2]
                    and not any(f['n'] == n for f in r['filas'])]

    # 3. comuneros: programación frente a resumen
    prog, prog_totales, sin_mapa = {}, [], []
    for i, t in enumerate(prog_t):
        filas, tot = filas_programacion(t)
        prog_totales.append(tot)
        for nombre, num, fecha in filas:
            n = PROGRAMACION.get(_sin_tildes(nombre))
            if n is None:
                sin_mapa.append(nombre)
            else:
                prog[n] = (nombre, num, fecha)
    r['sin_mapa'] = sin_mapa
    r['comuneros'] = [dict(n=n, nombre=resumen[n][1], prog=prog[n][1], resu=resumen[n][2])
                      for n in sorted(prog) if n in resumen and prog[n][1] != resumen[n][2]]
    r['prog_totales'] = prog_totales
    r['resu_com'] = [sum(v[1] or 0 for v in filas.values()) for _, filas, _ in totales]
    r['svg'] = prog.get(51, (None, 0))[1]
    r['cifras_texto'] = {}
    for p in parrafos:
        m = re.search(r'total de (\d[\d.]*) comuneros', p)
        if m:
            r['cifras_texto']['total'] = _entero(m.group(1))
        m = re.search(r'universo de (\d[\d.]*) comuneros', p)
        if m:
            r['cifras_texto']['universo'] = _entero(m.group(1))

    # 4. fechas
    r['dias'] = []
    textos = parrafos + [' '.join(f) for t in prog_t for f in t]
    for t in textos:
        for m in re.finditer(r'(?i)\b(lunes|martes|miércoles|jueves|viernes|sábado|domingo)\s+(\d{1,2})'
                             r'(?:\s+de\s+(\w+)|/(\d{1,2})/(\d{4}))', t):
            dia, dd = m.group(1).lower(), int(m.group(2))
            mes = MESES.index(m.group(3).lower()) + 1 if m.group(3) and m.group(3).lower() in MESES else (
                int(m.group(4)) if m.group(4) else None)
            if not mes:
                continue
            anio = int(m.group(5)) if m.group(5) else 2026
            real = DIAS[datetime.date(anio, mes, dd).weekday()]
            if real != dia:
                r['dias'].append(dict(texto=m.group(0), real=real, fecha=f'{dd:02d}/{mes:02d}/{anio}'))
    inicios = [p for p in parrafos if 'se inicia' in p.lower()]
    r['inicios'] = []
    for s, p in enumerate(inicios[:3], 1):
        m = re.search(r'(\d{1,2}) de (\w+)', p)
        if not m or m.group(2).lower() not in MESES:
            continue
        dicho = datetime.date(2026, MESES.index(m.group(2).lower()) + 1, int(m.group(1)))
        antes = sorted((b['primera'].date(), b['nombre']) for b in base.values()
                       if b['sector'] == s and b['primera'] and b['primera'].date() < dicho)
        primera = min(b['primera'].date() for b in base.values() if b['sector'] == s and b['primera'])
        r['inicios'].append(dict(sector=s, dicho=dicho, primera=primera, antes=antes))
    r['r_dias'] = sorted({x['texto'] for x in r['dias']})

    # 5. referencias y forma
    r['refs'] = []
    for p in parrafos:
        up = _sin_tildes(p)
        for clave, debe in SIN_V2.items():
            if clave in up and 'V2' in up:
                r['refs'].append(dict(dice=p, debe=debe))
    r['sin_nota'] = not any('NOTA ACLARATORIA' in _sin_tildes(p) for p in parrafos)
    r['version'] = [f[0] for f in (version or [])[1:] if f and f[0]]
    lit = [m.group(1) for p in parrafos for m in [re.match(r'^([a-h])\)', p)] if m]
    r['literales_faltan'] = [chr(c) for c in range(ord('a'), ord(max(lit)) + 1)
                             if chr(c) not in lit] if lit else []
    r['doce_am'] = sum(' '.join(f).count('12am') for t in prog_t for f in t)
    todo = '\n'.join(parrafos + [' '.join(f) for t in tablas for f in t])
    r['erratas'] = [(a, b) for a, b in ERRATAS if a in todo]
    return r


# ── documento ──────────────────────────────────────────────────────────────
def _fila3(v):
    return ' / '.join(esn(x) for x in v)


def bloques(r, nombre_word):
    st_h = ParagraphStyle('h', fontName='Helvetica-Bold', fontSize=13, leading=16, textColor=AZUL_PDF,
                          alignment=1)
    st_sub = ParagraphStyle('sub', fontName='Helvetica', fontSize=9.5, leading=12, alignment=1,
                            textColor=colors.HexColor('#475569'))
    st_p = ParagraphStyle('p', fontName='Helvetica', fontSize=9.5, leading=13, textColor=TINTA, alignment=4)
    hoy = datetime.date.today()
    b = [Paragraph('Correcciones al Informe Catastro', st_h), Spacer(0, 1.5 * mm),
         Paragraph(f'Revisión de «{nombre_word}» contra la base · {hoy.day} de {MESES[hoy.month - 1]} '
                   f'de {hoy.year}', st_sub), Spacer(0, 5 * mm),
         Paragraph('El informe catastral firmado el 18 de septiembre es el que observó la Prefectura: las cifras '
                   'de C01, C02, C03, C06 y C08 del informe JAFG-2026-002 salen de sus tablas. Esta hoja dice qué '
                   'cambiar en la versión 2 para que esas observaciones queden resueltas. Los valores «debe '
                   'decir» salen de la base entregada (Anexo A1 de la matriz de respuesta).', st_p)]

    b += titulo_seccion('1. Filas que no coinciden con la base (C01 y C02)')
    if r['filas']:
        b.append(tabla_datos(['Tabla', 'Comunidad', 'Dice (princ. / adic. / total)', 'Debe decir',
                              'Observaciones'],
                             [[str(f['tabla']), f'{f["n"]}. {f["nombre"]}', _fila3(f['dice']),
                               _fila3(f['debe']),
                               ('+' if (f['obs_debe'] or 0) >= 0 else '') + esn(f['obs_debe'])]
                              for f in r['filas']],
                             [14 * mm, 52 * mm, 40 * mm, 34 * mm, 30 * mm]))
        b.append(Spacer(0, 1.5 * mm))
        b.append(Paragraph('«Observaciones» se recalcula como en el informe: total de fichas menos número de '
                           'comuneros de la misma fila.', st_p))
    else:
        b.append(Paragraph('Todas las filas coinciden con la base.', st_p))
    if r['faltan']:
        b.append(Paragraph('Comunidades del catálogo que no aparecen en las tablas: '
                           + ', '.join(str(n) for n in r['faltan']) + '.', st_p))
    if r['obs_mal']:
        b.append(Paragraph('«Observaciones» mal restada: ' + '; '.join(
            f'{o["n"]}. {o["nombre"]} dice {esn(o["obs"])}, debe decir {esn(o["debe"])}' for o in r['obs_mal'])
            + '.', st_p))

    b += titulo_seccion('2. Sumas de las tablas, ya con las filas corregidas')
    if r['sumas']:
        b.append(tabla_datos(['Tabla', 'Columna', 'Dice el TOTAL', 'Suman las filas'],
                             [[str(s['tabla']), s['que'], esn(s['total']), esn(s['filas'])] for s in r['sumas']],
                             [18 * mm, 60 * mm, 40 * mm, 40 * mm]))
        b.append(Spacer(0, 1.5 * mm))
        b.append(Paragraph('Las diferencias en «comuneros» se explican en el punto 3. Las de fichas desaparecen '
                           'al corregir las filas del punto 1.' if any(s['que'] == 'comuneros' for s in r['sumas'])
                           else '', st_p))
    else:
        b.append(Paragraph('Con las filas corregidas, todas las tablas suman lo que dice su TOTAL.', st_p))

    b += titulo_seccion('3. Número de comuneros distinto entre tablas (C03 y C08)')
    pt, rc = r['prog_totales'], r['resu_com']
    if r['comuneros']:
        b.append(Paragraph('El número de comuneros de estas comunidades no es el mismo en la programación '
                           '(tablas 1 a 3) que en el resumen (tablas 4 a 6). Ese dato sale de los listados de '
                           'cada comunidad, no de la base: <b>hay que decidir cuál es el correcto</b> y usar el '
                           'mismo en todas las tablas y en el texto.', st_p))
        b.append(Spacer(0, 2 * mm))
        b.append(tabla_datos(['Comunidad', 'Programación', 'Resumen'],
                             [[f'{c["n"]}. {c["nombre"]}', esn(c['prog']), esn(c['resu'])] for c in r['comuneros']],
                             [80 * mm, 40 * mm, 40 * mm]))
        b.append(Spacer(0, 2 * mm))
    efectos = []
    if pt and rc and pt[0] is not None:
        efectos.append(f'Las tablas de programación suman {esn(sum(x or 0 for x in pt))} comuneros '
                       f'({" + ".join(esn(x) for x in pt)}); las filas de las tablas de resumen suman '
                       f'{esn(sum(rc))} ({" + ".join(esn(x) for x in rc)}).')
    ct = r['cifras_texto']
    if 'total' in ct and 'universo' in ct and r['svg']:
        resta = ct['total'] - r['svg']
        if resta != ct['universo']:
            efectos.append(f'El texto dice que de {esn(ct["total"])} comuneros, sin los {esn(r["svg"])} de San '
                           f'Vicente de Guayllabamba, queda un universo de {esn(ct["universo"])}; pero '
                           f'{esn(ct["total"])} − {esn(r["svg"])} = {esn(resta)}.')
    for e in efectos:
        b.append(Paragraph(e, st_p))
    if not r['comuneros'] and not efectos:
        b.append(Paragraph('El número de comuneros coincide entre todas las tablas y el texto.', st_p))
    if r['sin_mapa']:
        b.append(Paragraph('Nombres de la programación que no se pudieron emparejar (revisar a mano): '
                           + ', '.join(r['sin_mapa']) + '.', st_p))

    b += titulo_seccion('4. Fechas (C06)')
    hubo = False
    for x in r['r_dias']:
        real = next(d for d in r['dias'] if d['texto'] == x)
        b.append(Paragraph(f'«{x}»: el {real["fecha"]} fue <b>{real["real"]}</b>.', st_p))
        hubo = True
    for i in r['inicios']:
        if i['antes']:
            hubo = True
            b.append(Paragraph(
                f'El texto dice que el Sector {i["sector"]} inicia el {i["dicho"].day} de '
                f'{MESES[i["dicho"].month - 1]}, pero la primera ficha del sector es del {i["primera"].day} de '
                f'{MESES[i["primera"].month - 1]}. Comunidades con fichas anteriores a esa fecha: '
                + '; '.join(f'{n} ({d.day}-{MESES[d.month - 1][:3]})' for d, n in i['antes']) + '.', st_p))
    if hubo:
        b.append(Spacer(0, 1.5 * mm))
        b.append(Paragraph('Sugerencia: titular las tablas 1 a 3 como «Programación» y añadir una frase con la '
                           'ejecución efectiva, que consta en la fecha y hora de cada ficha (Anexo A1, columnas '
                           '«Primera ficha» y «Última ficha»).', st_p))
    else:
        b.append(Paragraph('Las fechas del texto y de las tablas son coherentes.', st_p))

    b += titulo_seccion('5. Referencias a la reentrega v2')
    for x in r['refs']:
        b.append(Paragraph(f'Dice «{x["dice"]}». Ese documento no tiene versión 2: debe decir «{x["debe"]}».', st_p))
    if r['sin_nota']:
        b.append(Paragraph('Conviene que la frase «se completa el 100 % de las propiedades declaradas» remita a la '
                           'NOTA ACLARATORIA del porcentaje de avance (observación C05), que va en la carpeta 6 '
                           'de la reentrega.', st_p))
    if not r['refs'] and not r['sin_nota']:
        b.append(Paragraph('Las referencias coinciden con los archivos de la reentrega v2.', st_p))

    b += titulo_seccion('6. Forma')
    forma = []
    if r['version'] and r['version'][-1].upper() == 'V0':
        forma.append('El control de versiones sigue en V0. Añadir una fila V1 con la fecha y la descripción '
                     '«Atiende las observaciones del INFORME-JAFG-2026-002», y actualizar la fecha del documento.')
    if r['literales_faltan']:
        forma.append('En «Entregables» falta el literal ' + ', '.join(f'{x})' for x in r['literales_faltan'])
                     + '.')
    if r['doce_am']:
        forma.append(f'En las tablas de programación «12am» aparece {r["doce_am"]} veces: significa medianoche; '
                     'debe ser 12h00 (o 12pm).')
    for a, c in r['erratas']:
        forma.append(f'Errata: «{a}» → «{c}».')
    for f in forma or ['Sin observaciones de forma.']:
        b.append(Paragraph('• ' + f, st_p))
    return _secciones_juntas(b)


def _secciones_juntas(b):
    """Cada título viaja con su contenido: sin esto un título puede quedar solo
    al pie de una página. Las secciones son cortas, así que se agrupan enteras."""
    from reportlab.platypus import KeepTogether
    grupos, actual = [], []
    for x in b:
        if type(x).__name__ == 'Table' and a_word._es_titulo_seccion(x) and actual:
            previo = actual.pop() if actual and type(actual[-1]).__name__ == 'Spacer' else None
            grupos.append(actual)
            actual = [previo] if previo else []
        actual.append(x)
    grupos.append(actual)
    return grupos[0] + [KeepTogether(g) for g in grupos[1:]]


def main():
    ruta = sys.argv[1] if len(sys.argv) > 1 else WORD_ARMANDO
    r = revisar(ruta)
    nombre_word = os.path.basename(ruta)
    pdf = os.path.join(SALIDA_DIR, NOMBRE + '.pdf')
    word = os.path.join(SALIDA_DIR, NOMBRE + '.docx')
    ap5._cerrar(ap5._doc(pdf, 'Correcciones al Informe Catastro'), bloques(r, nombre_word))
    a_word.escribir(bloques(r, nombre_word), word, cabecera_estudio=dict(
        titulo=PROJECT_TITLE, subtitulo=PROJECT_SUBTITLE, alcance=PROJECT_SUBTITLE_ALCANCE,
        ubicacion=PROJECT_LOCATION, logo_izq=os.path.join(PUB, 'logo-izq.png'),
        logo_der=os.path.join(PUB, 'logo-der.png'), pie_izquierda='AP&CATASTROS',
        pie_derecha_prefijo=f'CONSORCIO CAYAMBE SPT · Datos al {FECHA_CORTE} · pág. '))
    print('filas a corregir :', [(f['n'], f['nombre'], f['dice'], f['debe']) for f in r['filas']])
    print('sumas            :', r['sumas'])
    print('comuneros        :', [(c['nombre'], c['prog'], c['resu']) for c in r['comuneros']])
    print('totales prog/res :', r['prog_totales'], r['resu_com'], r['cifras_texto'], 'SVG', r['svg'])
    print('días mal         :', r['r_dias'])
    print('inicios          :', [(i['sector'], str(i['dicho']), str(i['primera']), len(i['antes'])) for i in r['inicios']])
    print('referencias      :', len(r['refs']), '| sin nota:', r['sin_nota'])
    print('forma            :', r['version'], r['literales_faltan'], r['doce_am'], r['erratas'])
    print('sin emparejar    :', r['sin_mapa'], '| faltan:', r['faltan'])
    print('✔', pdf)
    print('✔', word)


if __name__ == '__main__':
    main()
