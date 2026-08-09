# -*- coding: utf-8 -*-
"""
Hoja de trabajo en Excel para la revisión de campo, con seguimiento automático.

Por qué un Excel y por qué así
------------------------------
`REVISION-CAMPO.md` sirve para leer y planificar, pero no para trabajar: no se
filtra, no se ordena y no deja constancia de lo revisado. Esto es lo mismo en
formato de hoja de cálculo, con una regla de diseño que conviene entender antes
de tocarlo:

    **El Excel NO es donde se corrige. Se corrige en QField.**

Si el técnico llena el Excel, ese dato no llega a ninguna parte: el padrón sale
del `data.gpkg`, y lo que no esté ahí no existe para los informes. Peor aún,
tendríamos dos versiones del mismo dato sin saber cuál manda. Por eso las
columnas de trabajo son de *seguimiento* (¿ya fui?, ¿qué pasó?), no de datos.

Cómo evita que se pierdan
-------------------------
El seguimiento no depende de que nadie marque nada:

* Cada vez que se ejecuta, vuelve a leer el `data.gpkg`. Lo que ya se corrigió
  **desaparece de Pendientes y aparece en la hoja «Resueltos»**, con la fecha en
  que se detectó. El avance se ve solo.
* Las notas escritas a mano (Estado, Fecha, Observación) **se conservan** entre
  ejecuciones: se leen del Excel anterior y se vuelven a colocar en la fila que
  les corresponde. Se puede regenerar sin miedo a perder el trabajo del revisor.

Hojas
-----
1. **Instrucciones** — cómo se usa, en una pantalla.
2. **Resumen** — cuánto falta en cada comunidad, para decidir la ruta.
3. **Pendientes** — una fila por ficha y por dato faltante. Filtros activados.
4. **Resueltos** — lo que se ha ido corrigiendo, con la fecha.

Salida
------
docs/REVISION-CAMPO.xlsx
"""
import json
import os
import sys
from datetime import datetime
from importlib import util as _util

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation
from osgeo import ogr

ogr.UseExceptions()

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
SALIDA = os.path.join(BASE, 'docs', 'REVISION-CAMPO.xlsx')
HISTORICO = os.path.join(BASE, 'docs', '.revision-campo-historico.json')

# La definición de «qué es un pendiente» vive en un solo sitio: el script que
# genera el Markdown. Duplicarla aquí garantizaría que un día digan cosas
# distintas y nadie sepa cuál vale.
_spec = _util.spec_from_file_location(
    'revision_campo', os.path.join(os.path.dirname(__file__),
                                   'generar_revision_campo.py'))
_rc = _util.module_from_spec(_spec)
_spec.loader.exec_module(_rc)

ESTADOS = ['Pendiente', 'Corregido en QField', 'No aplica',
           'No se pudo (anotar por qué)', 'Predio ya no existe']

AZUL = 'FF1F4E79'
GRIS = 'FFF2F2F2'
VERDE = 'FFE2EFDA'
AMBAR = 'FFFFF2CC'
ROJO = 'FFFCE4E4'

FINA = Side(style='thin', color='FFBFBFBF')
BORDE = Border(left=FINA, right=FINA, top=FINA, bottom=FINA)


def cabecera(ws, fila, titulos, anchos):
    for i, (t, a) in enumerate(zip(titulos, anchos), start=1):
        c = ws.cell(row=fila, column=i, value=t)
        c.font = Font(bold=True, color='FFFFFFFF', size=10)
        c.fill = PatternFill('solid', fgColor=AZUL)
        c.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
        c.border = BORDE
        ws.column_dimensions[get_column_letter(i)].width = a
    ws.row_dimensions[fila].height = 28


def leer_notas_previas():
    """Estado, fecha y observación que el revisor escribió en la versión anterior."""
    if not os.path.exists(SALIDA):
        return {}
    try:
        wb = load_workbook(SALIDA, read_only=True, data_only=True)
        if 'Pendientes' not in wb.sheetnames:
            return {}
        ws = wb['Pendientes']
        notas = {}
        encabezados = None
        for fila in ws.iter_rows(values_only=True):
            if encabezados is None:
                if fila and fila[0] == 'Comunidad':
                    encabezados = list(fila)
                continue
            if not fila or len(fila) < 10 or not fila[9]:
                continue
            clave = '{}|{}'.format(fila[9], fila[4])       # id | qué falta
            estado, fecha, obs = (fila[6] if len(fila) > 6 else None,
                                  fila[7] if len(fila) > 7 else None,
                                  fila[8] if len(fila) > 8 else None)
            if any([estado and estado != 'Pendiente', fecha, obs]):
                notas[clave] = (estado, fecha, obs)
        wb.close()
        return notas
    except Exception as e:
        print("      aviso: no se pudo leer el Excel anterior ({}); se generará "
              "uno limpio".format(e))
        return {}


def main():
    print("=" * 74)
    print(" HOJA DE TRABAJO EN EXCEL - REVISION DE CAMPO")
    print("=" * 74)

    if not os.path.exists(_rc.GPKG):
        print("ERROR: no se encuentra el data.gpkg de QField.")
        return 1

    notas = leer_notas_previas()
    print("\n  notas del revisor recuperadas de la version anterior: {}"
          .format(len(notas)))

    # El histórico solo vale si se escribió con el mismo tipo de clave. Si el
    # esquema cambió (pasó al cambiar de `codigo_final` al `id` de QField), las
    # claves viejas no se parecen a las nuevas y TODO figuraría como resuelto de
    # golpe. Mejor empezar de cero que anunciar un avance que no existe.
    ESQUEMA = 'id|falta'
    previos = {}
    if os.path.exists(HISTORICO):
        try:
            with open(HISTORICO, encoding='utf-8') as f:
                cargado = json.load(f)
            if cargado.get('esquema_claves') == ESQUEMA:
                previos = cargado
            else:
                print("      el historico anterior usaba otro identificador; se "
                      "descarta para no marcar todo como resuelto")
        except Exception:
            previos = {}

    ds = ogr.Open(_rc.GPKG, 0)              # SOLO LECTURA
    t = '"{}"'.format(_rc.CAPA)
    corte = (_rc.consultar(ds, "SELECT MAX(fecha_creacion) FROM {}".format(t))[0][0]
             or '')[:10]
    total = _rc.consultar(ds, "SELECT COUNT(*) FROM {}".format(t))[0][0]

    # ── pendientes actuales ──
    # El identificador de seguimiento es el `id` de QField, no el «código» de la
    # ficha: `codigo_final` vale S-C-P001 en 5.529 de las 6.831 fichas (es el
    # valor por defecto del formulario y casi nunca se cambió), así que usarlo
    # mezclaría el estado de miles de fichas distintas.
    filas = []
    for campo, etq, cond, _listar in _rc.PENDIENTES:
        datos = _rc.consultar(ds,
            "SELECT COALESCE(NULLIF(TRIM(comunidad),''),'(sin comunidad)') com, "
            "COALESCE(clave_catastral,'') clave, "
            "TRIM(COALESCE(apellidos,'') || ' ' || COALESCE(nombres,'')) nombre, "
            "COALESCE(cedula,'') ced, COALESCE(creado_por,'') tec, "
            "COALESCE(id,'') uid "
            "FROM {} WHERE {} AND {} ORDER BY com, clave"
            .format(t, cond, _rc.PRINCIPALES))
        for com, clave, nombre, ced, tec, uid in datos:
            falta = etq.replace('Sin ', '')
            filas.append({
                'comunidad': com, 'clave': clave, 'regante': nombre,
                'cedula': ced, 'falta': falta, 'tecnico': tec, 'uid': uid,
                'clave_seg': '{}|{}'.format(uid or clave, falta),
            })
    ds = None

    actuales = {f['clave_seg'] for f in filas}
    hoy = datetime.now().strftime('%d/%m/%Y')

    # ── resueltos: estaban en la corrida anterior y ya no están ──
    resueltos = dict(previos.get('resueltos', {}))
    antes = set(previos.get('pendientes', []))
    nuevos_resueltos = antes - actuales
    for k in nuevos_resueltos:
        resueltos.setdefault(k, hoy)
    print("  pendientes ahora        : {:,}".format(len(actuales)))
    print("  resueltos desde la ultima ejecucion: {:,}".format(len(nuevos_resueltos)))
    print("  resueltos acumulados    : {:,}".format(len(resueltos)))

    wb = Workbook()

    # ── 1. Instrucciones ──
    ws = wb.active
    ws.title = 'Instrucciones'
    ws.column_dimensions['A'].width = 3
    ws.column_dimensions['B'].width = 110
    lineas = [
        ('Revisión de campo — Padrón Guanguilquí–Porotog', 'titulo'),
        ('Última ficha en el sistema: {}  ·  Generado: {}'.format(corte, hoy), 'sub'),
        ('', ''),
        ('LO PRIMERO, PORQUE ES LO QUE MÁS SE CONFUNDE', 'h'),
        ('Las correcciones se hacen EN QFIELD, no en este Excel. Lo que se escriba '
         'aquí no llega al padrón: los informes salen del archivo de QField.', ''),
        ('Este archivo sirve para saber qué falta, repartir el trabajo y dejar '
         'constancia de lo que se revisó.', ''),
        ('', ''),
        ('CÓMO SE USA', 'h'),
        ('1. En la hoja «Resumen» mira qué comunidades tienen más pendientes y arma '
         'la salida por ahí.', ''),
        ('2. En la hoja «Pendientes» filtra por tu comunidad (o por tu usuario en la '
         'columna «Levantó»). Cada fila es una ficha y un dato que le falta.', ''),
        ('3. Busca la ficha en QField por su CLAVE CATASTRAL y completa el dato ahí.', ''),
        ('   OJO: no busques por el «código» de la ficha. Ese campo vale S-C-P001 en '
         '5.529 de las 6.831 fichas (es el valor por defecto del formulario), así que '
         'no sirve para encontrar nada. La clave catastral sí está en todas.', ''),
        ('4. Vuelve a esta hoja y marca el ESTADO. Si no se pudo, escribe por qué en '
         'OBSERVACIÓN: un campo vacío no distingue entre «falta ir» y «no aplica».', ''),
        ('', ''),
        ('QUÉ PASA CUANDO SE VUELVE A GENERAR ESTE ARCHIVO', 'h'),
        ('Lo que ya se corrigió en QField desaparece de «Pendientes» y pasa a la hoja '
         '«Resueltos» con la fecha. No hay que marcar nada para que eso ocurra.', ''),
        ('Tus notas (Estado, Fecha, Observación) se conservan: se leen del archivo '
         'anterior y se vuelven a colocar. Se puede regenerar sin perder trabajo.', ''),
        ('', ''),
        ('LO QUE NO HAY QUE HACER', 'h'),
        ('· No crear una ficha nueva para completar datos: se duplica el predio.', ''),
        ('· No borrar filas de este archivo: se regenera solo.', ''),
        ('· Las fichas marcadas con AVISO en la hoja Resumen no se tocan sin '
         'consultar con la dirección del proyecto.', ''),
        ('', ''),
        ('Se regenera con:  python scripts/generar_excel_revision_campo.py', 'sub'),
    ]
    r = 2
    for texto, tipo in lineas:
        c = ws.cell(row=r, column=2, value=texto)
        if tipo == 'titulo':
            c.font = Font(bold=True, size=16, color=AZUL)
        elif tipo == 'h':
            c.font = Font(bold=True, size=11, color=AZUL)
        elif tipo == 'sub':
            c.font = Font(italic=True, size=9, color='FF808080')
        else:
            c.font = Font(size=10)
            c.alignment = Alignment(wrap_text=True, vertical='top')
        r += 1

    # ── 2. Resumen por comunidad ──
    ws = wb.create_sheet('Resumen')
    cabecera(ws, 1, ['Comunidad', 'Pendientes', 'Fichas afectadas', 'Aviso'],
             [38, 13, 17, 62])
    por_com = {}
    for f in filas:
        d = por_com.setdefault(f['comunidad'], {'n': 0, 'fichas': set()})
        d['n'] += 1
        d['fichas'].add(f['uid'] or f['clave'])
    r = 2
    for com in sorted(por_com, key=lambda c: -por_com[c]['n']):
        d = por_com[com]
        aviso = _rc.NO_SON_ENCUESTAS.get(com.strip().upper(), '')
        ws.cell(row=r, column=1, value=com).border = BORDE
        ws.cell(row=r, column=2, value=d['n']).border = BORDE
        ws.cell(row=r, column=3, value=len(d['fichas'])).border = BORDE
        c = ws.cell(row=r, column=4,
                    value=('NO TOCAR SIN CONSULTAR — ' + aviso) if aviso else '')
        c.border = BORDE
        c.alignment = Alignment(wrap_text=True, vertical='center')
        if aviso:
            for col in range(1, 5):
                ws.cell(row=r, column=col).fill = PatternFill('solid', fgColor=ROJO)
        r += 1
    ws.auto_filter.ref = 'A1:D{}'.format(r - 1)
    ws.freeze_panes = 'A2'

    # ── 3. Pendientes ──
    ws = wb.create_sheet('Pendientes')
    titulos = ['Comunidad', 'Clave catastral', 'Regante', 'Cédula',
               'Qué falta', 'Levantó', 'ESTADO', 'Fecha revisión', 'OBSERVACIÓN',
               'id (no tocar)']
    cabecera(ws, 1, titulos, [30, 18, 34, 13, 24, 16, 24, 14, 46, 12])
    r = 2
    for f in sorted(filas, key=lambda x: (x['comunidad'], x['clave'], x['falta'])):
        estado, fecha, obs = notas.get(f['clave_seg'], ('Pendiente', None, None))
        vals = [f['comunidad'], f['clave'], f['regante'], f['cedula'],
                f['falta'], f['tecnico'], estado or 'Pendiente', fecha, obs,
                f['uid']]
        for i, v in enumerate(vals, start=1):
            c = ws.cell(row=r, column=i, value=v)
            c.border = BORDE
            c.font = Font(size=10)
            if i in (7, 8, 9):
                c.fill = PatternFill('solid', fgColor=GRIS)
        if _rc.NO_SON_ENCUESTAS.get(f['comunidad'].strip().upper()):
            ws.cell(row=r, column=1).fill = PatternFill('solid', fgColor=ROJO)
        if estado and estado != 'Pendiente':
            ws.cell(row=r, column=7).fill = PatternFill('solid', fgColor=VERDE)
        r += 1

    dv = DataValidation(type='list', formula1='"{}"'.format(','.join(ESTADOS)),
                        allow_blank=True, showDropDown=False)
    dv.error = 'Elige una opción de la lista'
    ws.add_data_validation(dv)
    dv.add('G2:G{}'.format(max(r - 1, 2)))
    ws.auto_filter.ref = 'A1:J{}'.format(max(r - 1, 1))
    ws.freeze_panes = 'C2'
    # el id es lo que permite reencontrar cada fila al regenerar el archivo y
    # devolverle sus notas; se deja oculto para no invitar a editarlo
    ws.column_dimensions['J'].hidden = True

    # ── 4. Resueltos ──
    ws = wb.create_sheet('Resueltos')
    cabecera(ws, 1, ['Código', 'Qué faltaba', 'Detectado como resuelto el'],
             [18, 30, 26])
    r = 2
    for k in sorted(resueltos, key=lambda x: resueltos[x], reverse=True):
        cod, _, falta = k.partition('|')
        for i, v in enumerate([cod, falta, resueltos[k]], start=1):
            c = ws.cell(row=r, column=i, value=v)
            c.border = BORDE
            c.fill = PatternFill('solid', fgColor=VERDE)
            c.font = Font(size=10)
        r += 1
    if r == 2:
        ws.cell(row=2, column=1,
                value='Todavía no hay nada resuelto: esta hoja se llena sola '
                      'cuando se vuelva a generar el archivo.').font = Font(
            italic=True, color='FF808080')
    ws.auto_filter.ref = 'A1:C{}'.format(max(r - 1, 1))
    ws.freeze_panes = 'A2'

    wb.save(SALIDA)

    with open(HISTORICO, 'w', encoding='utf-8') as f:
        json.dump({'esquema_claves': ESQUEMA, 'generado': hoy, 'corte': corte,
                   'total_fichas': total, 'pendientes': sorted(actuales),
                   'resueltos': resueltos},
                  f, ensure_ascii=False, indent=1)

    print("\n  hojas    : Instrucciones · Resumen · Pendientes · Resueltos")
    print("  filas    : {:,} pendientes en {} comunidades"
          .format(len(filas), len(por_com)))
    print("  guardado : {} ({:,.0f} KB)"
          .format(os.path.relpath(SALIDA, BASE), os.path.getsize(SALIDA) / 1024))
    print("=" * 74)
    return 0


if __name__ == '__main__':
    sys.exit(main())
