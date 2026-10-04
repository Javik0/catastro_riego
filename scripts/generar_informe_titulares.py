# -*- coding: utf-8 -*-
"""
Informe de sustento: titulares entrevistados y conocimiento del proyecto.

Es el documento que se entrega al sociólogo (Alexis Guerrero), que necesita
sostener cuántos titulares fueron entrevistados y cuántos contestaron que
conocen el proyecto. Lleva dentro los dos listados que él pidió —todos los
catastrados y los que contestaron que sí, con cédula y comunidad— como anexos,
de modo que el informe se entiende solo; el Excel trae los mismos listados
filtrables.

Tono y alcance
--------------
Neutro: expone lo que consta en las fichas y dice sobre qué base se calcula
cada porcentaje. No sale ninguna cifra escrita a mano: todo se cuenta del
mismo padrón y con la misma función de carga que el Excel, para que los dos
archivos no puedan contradecirse.

Lo que NO lleva, por decisión del 4-oct-2026: el técnico que levantó cada
ficha. No se pide y solo abre preguntas. Los bloques de resumen (qué consta en
la ficha, cédulas, cédulas distintas) sí van, igual que la fecha de
levantamiento. Todo conteo se dice en FICHAS principales: el documento nunca
afirma que sean personas distintas.

El campo de consentimiento informado está vacío en las 6.830 fichas porque el
consentimiento se dio en la socialización, no en una casilla del formulario;
por eso el documento no lo menciona como respaldo.

Uso:  python -X utf8 scripts/generar_informe_titulares.py
"""
import collections
import os
import sys
from datetime import datetime
from xml.sax.saxutils import escape

from reportlab.platypus import PageBreak

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)

from generar_listado_titulares import cargar  # noqa: E402
from informe_estilo import esn  # noqa: E402
from generar_fichas_pdf import (  # noqa: E402
    AZUL as AZUL_PDF, TINTA, FECHA_CORTE, PROJECT_LOCATION, PROJECT_SUBTITLE,
    PROJECT_SUBTITLE_ALCANCE, PROJECT_TITLE, PUB, colors, mm, Paragraph,
    ParagraphStyle, Spacer, tabla_datos, titulo_seccion,
)
import a_word  # noqa: E402

SALIDA = (r'C:\Users\HP\OneDrive\Escritorio'
          r'\INFORME DE TITULARES ENTREVISTADOS - conocimiento del proyecto.docx')

MESES = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto',
         'septiembre', 'octubre', 'noviembre', 'diciembre']


def fecha_larga(d):
    return f'{d.day} de {MESES[d.month - 1]} de {d.year}'


def pc(a, b):
    """Porcentaje en castellano (coma decimal) o raya si la base es cero."""
    return f'{esn(100 * a / b, 1)} %' if b else '—'


def main():
    filas, por_cedula = cargar()
    N = len(filas)
    si = sum(1 for x in filas if x['conoce'] == 'Sí')
    no = sum(1 for x in filas if x['conoce'] == 'No')
    sr = N - si - no
    resp = si + no

    fechas = [datetime.strptime(x['fecha'], '%d/%m/%Y') for x in filas if x['fecha']]
    n_comunidades = len({x['com_n'] for x in filas})
    con_fecha = len(fechas)
    con_clave = sum(1 for x in filas if x['clave'])
    con_nombre = sum(1 for x in filas if x['nombre'])
    con_gps = sum(1 for x in filas if x['gps'])
    n_dias = len({d.date() for d in fechas})
    ced = collections.Counter(x['estado_ced'] for x in filas)
    sin_ced = ced['Sin cédula']
    con_ced = N - sin_ced
    dup = {c: v for c, v in por_cedula.items() if len(v) > 1}
    en_dup = sum(len(v) for v in dup.values())

    # Cortes por sector y por comunidad (misma regla que el Excel: el sector y
    # la comunidad salen del código de la ficha). `grupos` guarda, por
    # comunidad, las fichas en el orden del código, para los anexos.
    por_sector = collections.OrderedDict()
    por_com = collections.OrderedDict()
    grupos = collections.OrderedDict()
    for x in sorted(filas, key=lambda x: (x['com_n'], x['codigo'])):
        clave = (x['com_n'], x['comunidad'], x['sector'])
        for d in (por_sector.setdefault(x['sector'], collections.Counter()),
                  por_com.setdefault(clave, collections.Counter())):
            d['n'] += 1
            d['si' if x['conoce'] == 'Sí' else 'no' if x['conoce'] == 'No' else 'sr'] += 1
        grupos.setdefault(clave, []).append(x)
    assert sum(d['n'] for d in por_sector.values()) == N
    assert sum(d['n'] for d in por_com.values()) == N
    assert sum(d['si'] for d in por_com.values()) == si

    st_h = ParagraphStyle('h', fontName='Helvetica-Bold', fontSize=13, leading=16,
                          textColor=AZUL_PDF, alignment=1)
    st_sub = ParagraphStyle('sub', fontName='Helvetica', fontSize=9.5, leading=12,
                            alignment=1, textColor=colors.HexColor('#475569'))
    st_p = ParagraphStyle('p', fontName='Helvetica', fontSize=9.5, leading=13,
                          textColor=TINTA, alignment=4)
    st_li = ParagraphStyle('li', parent=st_p, leftIndent=6 * mm, spaceAfter=2)
    st_com = ParagraphStyle('com', fontName='Helvetica-Bold', fontSize=10, leading=13,
                            textColor=AZUL_PDF, alignment=0)

    b = [Paragraph('Titulares entrevistados y conocimiento del proyecto', st_h),
         Spacer(0, 1.5 * mm),
         Paragraph(f'Informe de sustento · Padrón de usuarios · Información al {FECHA_CORTE}',
                   st_sub),
         Spacer(0, 5 * mm),
         Paragraph('Este documento resume el levantamiento del padrón de usuarios del sistema '
                   'de riego comunitario Guanguilquí–Porotog: cuántas fichas principales se '
                   'levantaron, cuántas respondieron la pregunta «¿Conoce el proyecto?» y qué '
                   'consta en cada ficha. Los listados completos, con cédula y comunidad, '
                   'van en los anexos.', st_p)]

    # 1 ─ El levantamiento
    b += titulo_seccion('1. El levantamiento')
    b.append(Paragraph(
        f'El levantamiento se hizo casa por casa entre el {fecha_larga(min(fechas))} y el '
        f'{fecha_larga(max(fechas))}, en {esn(n_comunidades)} comunidades de los tres sectores, '
        f'en {esn(n_dias)} días con registros. '
        f'Cada ficha principal recoge la entrevista a un titular; las fichas adicionales son '
        f'otros predios y no se cuentan como titulares. En total hay '
        f'<b>{esn(N)} fichas principales</b>.', st_p))

    # 2 ─ Respuesta a la pregunta
    b += titulo_seccion('2. Respuesta a «¿Conoce el proyecto?»')
    b.append(tabla_datos(
        ['Concepto', 'Fichas', '% de las fichas', '% de quienes respondieron'],
        [['Fichas principales', esn(N), '100,0 %', '—'],
         ['Respondieron la pregunta', esn(resp), pc(resp, N), '100,0 %'],
         ['Conocen el proyecto (Sí)', esn(si), pc(si, N), pc(si, resp)],
         ['No conocen el proyecto (No)', esn(no), pc(no, N), pc(no, resp)],
         ['Sin respuesta registrada', esn(sr), pc(sr, N), '—']],
        [70 * mm, 24 * mm, 32 * mm, 44 * mm]))
    b.append(Spacer(0, 2 * mm))
    b.append(Paragraph(
        f'La pregunta fue respondida en {esn(resp)} fichas ({pc(resp, N)}). Entre quienes '
        f'respondieron, {esn(si)} ({pc(si, resp)}) dicen que conocen el proyecto. Si la '
        f'proporción se calcula sobre las {esn(N)} fichas principales, es {pc(si, N)}. Ambas '
        f'lecturas parten de las mismas cifras; solo cambia la base del cálculo.', st_p))

    # 3 ─ Por sector
    b += titulo_seccion('3. Por sector')
    filas_s = [[sec, esn(d['n']), esn(d['si'] + d['no']), esn(d['si']), esn(d['no']),
                esn(d['sr']), pc(d['si'], d['si'] + d['no'])]
               for sec, d in sorted(por_sector.items())]
    filas_s.append(['Total', esn(N), esn(resp), esn(si), esn(no), esn(sr), pc(si, resp)])
    b.append(tabla_datos(
        ['Sector', 'Fichas', 'Respondieron', 'Sí', 'No', 'Sin respuesta',
         '% Sí (sobre quienes respondieron)'],
        filas_s, [26 * mm, 20 * mm, 26 * mm, 18 * mm, 18 * mm, 24 * mm, 38 * mm],
        ultima_negrita=True))

    # 4 ─ Qué consta en cada ficha
    b += titulo_seccion('4. Qué consta en cada ficha')
    b.append(tabla_datos(
        ['Dato registrado', 'Fichas', '% de las fichas'],
        [['Apellidos y nombres del titular', esn(con_nombre), pc(con_nombre, N)],
         ['Clave catastral del predio', esn(con_clave), pc(con_clave, N)],
         ['Fecha de levantamiento', esn(con_fecha), pc(con_fecha, N)],
         ['Coordenadas del punto de levantamiento', esn(con_gps), pc(con_gps, N)]],
        [90 * mm, 30 * mm, 40 * mm]))

    # 5 ─ Identificación de los titulares
    b += titulo_seccion('5. Identificación de los titulares')
    b.append(tabla_datos(
        ['Cédula', 'Fichas', '% de las fichas'],
        [['Con cédula registrada', esn(con_ced), pc(con_ced, N)],
         ['   con dígito verificador válido', esn(ced['Dígito verificador válido']),
          pc(ced['Dígito verificador válido'], N)],
         ['   con dígito verificador no válido', esn(ced['Dígito verificador NO válido']),
          pc(ced['Dígito verificador NO válido'], N)],
         ['   en otro formato (RUC o pasaporte)', esn(ced['Otro formato (RUC / pasaporte)']),
          pc(ced['Otro formato (RUC / pasaporte)'], N)],
         ['Sin cédula registrada', esn(sin_ced), pc(sin_ced, N)]],
        [90 * mm, 30 * mm, 40 * mm]))
    b.append(Spacer(0, 2 * mm))
    b.append(Paragraph(
        f'Las {esn(N)} fichas principales corresponden a {esn(len(por_cedula))} cédulas '
        f'distintas y {esn(sin_ced)} fichas sin cédula registrada. {esn(len(dup))} cédulas '
        f'figuran en más de una ficha principal ({esn(en_dup)} fichas). El dígito verificador '
        f'comprueba que el número de cédula está bien formado; la consulta al Registro Civil '
        f'no forma parte de este levantamiento.', st_p))

    # 5 ─ Listados que acompañan
    b += titulo_seccion('6. Listados que acompañan a este informe')
    for t in [
        '<b>Anexo 1.</b> Respuesta por comunidad.',
        f'<b>Anexo 2.</b> Las {esn(N)} fichas principales, por comunidad, con código de '
        'ficha, cédula, apellidos y nombres, respuesta a «¿Conoce el proyecto?» y fecha de '
        'levantamiento.',
        f'<b>Anexo 3.</b> Las {esn(si)} fichas que respondieron que sí conocen el proyecto, '
        'por comunidad, con cédula y fecha de levantamiento.',
    ]:
        b.append(Paragraph(t, st_li))
    b.append(Spacer(0, 2 * mm))
    b.append(Paragraph('El Excel «Listado de titulares entrevistados» contiene estos mismos '
                       'listados, filtrables, con la clave catastral de cada ficha.', st_p))

    # Anexo 1 ─ por comunidad
    b.append(PageBreak())
    b += titulo_seccion('Anexo 1. Respuesta por comunidad')
    filas_c = [[nom, sec, esn(d['n']), esn(d['si'] + d['no']), esn(d['si']),
                pc(d['si'], d['si'] + d['no'])]
               for (_, nom, sec), d in por_com.items()]
    filas_c.append(['Total', '', esn(N), esn(resp), esn(si), pc(si, resp)])
    b.append(tabla_datos(
        ['Comunidad', 'Sector', 'Fichas', 'Respondieron', 'Sí conocen',
         '% Sí (sobre quienes respondieron)'],
        filas_c, [58 * mm, 20 * mm, 18 * mm, 26 * mm, 22 * mm, 34 * mm],
        ultima_negrita=True))

    # Anexo 2 ─ todas las fichas principales, por comunidad
    b.append(PageBreak())
    b += titulo_seccion('Anexo 2. Fichas principales por comunidad')
    n = 0
    for (_, nom, sec), lista in grupos.items():
        b.append(Paragraph(f'<b>{escape(nom)} · {sec} · {esn(len(lista))} fichas</b>', st_com))
        filas_l = []
        for x in lista:
            n += 1
            filas_l.append([str(n), x['codigo'], x['cedula'] or '—', x['nombre'], x['conoce'],
                            x['fecha']])
        b.append(tabla_datos(['N°', 'Código de ficha', 'Cédula', 'Apellidos y nombres',
                              '¿Conoce el proyecto?', 'Fecha de levantamiento'],
                             filas_l, [11 * mm, 32 * mm, 24 * mm, 54 * mm, 20 * mm, 24 * mm]))
    assert n == N, (n, N)

    # Anexo 3 ─ quienes respondieron que sí, por comunidad
    b.append(PageBreak())
    b += titulo_seccion('Anexo 3. Fichas que respondieron que sí conocen el proyecto')
    n = 0
    n_tablas_si = 0
    for (_, nom, sec), lista in grupos.items():
        lista = [x for x in lista if x['conoce'] == 'Sí']
        if not lista:
            continue
        b.append(Paragraph(f'<b>{escape(nom)} · {sec} · {esn(len(lista))} fichas</b>', st_com))
        filas_l = []
        for x in lista:
            n += 1
            filas_l.append([str(n), x['codigo'], x['cedula'] or '—', x['nombre'], x['fecha']])
        b.append(tabla_datos(['N°', 'Código de ficha', 'Cédula', 'Apellidos y nombres',
                              'Fecha de levantamiento'],
                             filas_l, [12 * mm, 32 * mm, 26 * mm, 62 * mm, 24 * mm]))
        n_tablas_si += 1
    assert n == si, (n, si)

    a_word.escribir(b, SALIDA, cabecera_estudio=dict(
        titulo=PROJECT_TITLE, subtitulo=PROJECT_SUBTITLE,
        alcance=PROJECT_SUBTITLE_ALCANCE, ubicacion=PROJECT_LOCATION,
        logo_izq=os.path.join(PUB, 'logo-izq.png'),
        logo_der=os.path.join(PUB, 'logo-der.png'),
        pie_izquierda='AP&CATASTROS',
        pie_derecha_prefijo=f'CONSORCIO CAYAMBE SPT · Datos al {FECHA_CORTE} · pág. '))

    # Se vuelve a leer el .docx: lo que se entrega es lo que quedó en disco.
    import docx
    d = docx.Document(SALIDA)
    texto = '\n'.join(p.text for p in d.paragraphs)
    for esperado in (esn(N), esn(si), pc(si, resp), pc(si, N)):
        assert esperado in texto, f'falta «{esperado}» en el Word'
    # Cuerpo: respuesta, sector, ficha, cédula (4) + anexo 1 + una tabla por
    # comunidad en el anexo 2 y en el anexo 3.
    esperadas = 4 + 1 + len(grupos) + n_tablas_si
    assert len(d.tables) == esperadas, (len(d.tables), esperadas)
    t = d.tables
    assert len(t[4].rows) == n_comunidades + 2
    filas_anexo2 = sum(len(x.rows) - 1 for x in t[5:5 + len(grupos)])
    filas_anexo3 = sum(len(x.rows) - 1 for x in t[5 + len(grupos):])
    assert filas_anexo2 == N, (filas_anexo2, N)
    assert filas_anexo3 == si, (filas_anexo3, si)
    for palabra in ('técnico', 'Técnico'):
        assert palabra not in texto, f'quedó «{palabra}» en el Word'

    print(f'Fichas principales : {esn(N)}')
    print(f'  Sí / respondieron: {esn(si)} / {esn(resp)} = {pc(si, resp)} '
          f'(sobre fichas: {pc(si, N)})')
    print(f'  anexo 2: {esn(filas_anexo2)} filas en {len(grupos)} comunidades · '
          f'anexo 3: {esn(filas_anexo3)} filas en {n_tablas_si}')
    print('Contenido releído del .docx: cifras, tablas y filas de anexos cuadran.')
    print('✔', SALIDA)
    return 0


if __name__ == '__main__':
    sys.exit(main())
