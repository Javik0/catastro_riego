# -*- coding: utf-8 -*-
"""Excel con las 54 clasificadas, para que Armando las valide en el mapa."""
import os, sys
from importlib import util as _util
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
import sqlite3

BASE = r"C:\Users\HP\OneDrive\Escritorio\CAYAMBE CATASTRO RIEGO\padron-app"
sys.path.insert(0, os.path.join(BASE, 'scripts'))
_spec = _util.spec_from_file_location(
    'cor', os.path.join(BASE, 'scripts', 'corregir_areas_sin_riego.py'))
_c = _util.module_from_spec(_spec)
_spec.loader.exec_module(_c)

SALIDA = os.path.join(BASE, 'docs', 'REVISION-54-areas-sobre-el-canal.xlsx')
AZUL, ROJO, VERDE, AMBAR = 'FF1F4E79', 'FFFCE4E4', 'FFE2EFDA', 'FFFFF2CC'
FINA = Side(style='thin', color='FFBFBFBF')
BORDE = Border(left=FINA, right=FINA, top=FINA, bottom=FINA)

con = sqlite3.connect(_c.GPKG)
cur = con.cursor()
t = '"{}"'.format(_c.TABLA)
fallo, n_reg = _c.clasificar_por_canal(cur, t, 25.0, 15)
cur.execute(
    "SELECT COALESCE(clave_catastral,''), "
    "TRIM(COALESCE(apellidos,'')||' '||COALESCE(nombres,'')), "
    "COALESCE(comunidad,'(sin comunidad)'), COALESCE(cedula,''), "
    "COALESCE(area_total,0), COALESCE(coord_x_utm,0), COALESCE(coord_y_utm,0), "
    "SUBSTR(CAST(fecha_creacion AS TEXT),1,10) "
    "FROM {} WHERE {} ORDER BY 3, 5 DESC".format(t, _c.PATRON))
filas = cur.fetchall()
con.close()

wb = Workbook()
ws = wb.active
ws.title = 'Las 54'
tit = ['Clave catastral', 'Regante', 'Comunidad', 'Cédula', 'Área (ha)',
       'Cota (m)', 'Cota vecinas', 'Diferencia', 'VEREDICTO', '¿CORRECTO?',
       'Observación', 'X (UTM 17S)', 'Y (UTM 17S)']
anchos = [17, 34, 18, 13, 11, 10, 13, 11, 26, 14, 40, 13, 13]
for i, (t_, a) in enumerate(zip(tit, anchos), start=1):
    c = ws.cell(row=1, column=i, value=t_)
    c.font = Font(bold=True, color='FFFFFFFF', size=10)
    c.fill = PatternFill('solid', fgColor=AZUL)
    c.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
    c.border = BORDE
    ws.column_dimensions[get_column_letter(i)].width = a
ws.row_dimensions[1].height = 30

r = 2
n_sobre = n_bajo = 0
for clave, nom, com, ced, area, x, y, fecha in filas:
    v = fallo.get(clave.strip())
    if v:
        direccion, cota, ref, dif = v
        sobre = direccion == 'riego'
        ver = 'SOBRE el canal — NO riega' if sobre else 'BAJO el canal — SÍ riega'
        limite = abs(dif - 25.0) <= 10
    else:
        cota = ref = dif = None
        sobre, limite = False, True
        ver = 'sin cota — revisar'
    n_sobre += 1 if sobre else 0
    n_bajo += 0 if sobre else 1
    vals = [clave, nom, com, ced, round(area/10000.0, 2),
            round(cota) if cota else None, round(ref) if ref else None,
            round(dif) if dif is not None else None, ver, '',
            'Cerca del límite: conviene mirarla' if limite else '',
            round(x) if x else None, round(y) if y else None]
    for i, val in enumerate(vals, start=1):
        c = ws.cell(row=r, column=i, value=val)
        c.border = BORDE
        c.font = Font(size=10)
        if i == 9:
            c.fill = PatternFill('solid', fgColor=ROJO if sobre else VERDE)
        if i == 10:
            c.fill = PatternFill('solid', fgColor='FFF2F2F2')
        if i == 11 and limite:
            c.fill = PatternFill('solid', fgColor=AMBAR)
    r += 1

ws.auto_filter.ref = 'A1:M{}'.format(r - 1)
ws.freeze_panes = 'C2'

ws2 = wb.create_sheet('Cómo se clasificó')
ws2.column_dimensions['B'].width = 108
lineas = [
    ('Las 54 fichas con el área repetida tres veces', 'titulo'),
    ('', ''),
    ('QUÉ PASA CON ESTAS FICHAS', 'h'),
    ('En las 54, el área total, el área con riego y el área sin riego traen el mismo '
     'número. Es imposible: un predio no puede estar entero con riego y entero sin '
     'riego a la vez. Son 56,38 ha contadas dos veces, y son la única causa de que la '
     'superficie del padrón no cuadre.', ''),
    ('Todas son del mismo levantamiento, entre el 24 y el 30 de julio de 2026.', ''),
    ('', ''),
    ('CÓMO SE DECIDIÓ CUÁL DE LOS DOS CAMPOS SOBRA', 'h'),
    ('Armando lo resolvió el 12 de agosto mirando las fichas en el mapa: en PAMBAMARCA '
     '«casi todos los adicionales están sobre el canal, no tienen riego»; en '
     'CHAUPIESTANCIA «todos están bajo el canal, deben tener riego».', ''),
    ('El canal riega por gravedad, así que lo que queda por encima de su cota no recibe '
     'agua aunque esté al lado. Para aplicar ese criterio ficha por ficha se compara la '
     'cota de cada predio con la de las 15 fichas regantes más cercanas: si está más de '
     '25 m por encima, quedó sobre el canal.', ''),
    ('El resultado reproduce lo que dijo Armando sin habérselo indicado al programa: '
     'Pambamarca 22 sobre y 8 bajo; Chaupiestancia 1 sobre y 17 bajo.', ''),
    ('', ''),
    ('QUÉ HAY QUE REVISAR', 'h'),
    ('Las filas con observación en ámbar están cerca del límite de los 25 m: son las que '
     'conviene mirar en el mapa antes de aplicar nada. El resto tiene un margen claro.', ''),
    ('Marcar en la columna ¿CORRECTO? con SÍ o NO. Con eso se aplica la corrección.', ''),
    ('', ''),
    ('QUÉ PASA DESPUÉS', 'h'),
    ('A las que quedan SOBRE el canal se les pone el área con riego en cero; a las que '
     'quedan BAJO, el área sin riego. En los dos casos el área total del predio no se '
     'toca, porque el catastro la confirma.', ''),
]
rr = 2
for texto, tipo in lineas:
    c = ws2.cell(row=rr, column=2, value=texto)
    if tipo == 'titulo':
        c.font = Font(bold=True, size=15, color=AZUL)
    elif tipo == 'h':
        c.font = Font(bold=True, size=11, color=AZUL)
    else:
        c.font = Font(size=10)
        c.alignment = Alignment(wrap_text=True, vertical='top')
    rr += 1

wb.save(SALIDA)
print("guardado: {}".format(SALIDA))
print("   {} fichas · {} sobre el canal · {} bajo el canal".format(
    len(filas), n_sobre, n_bajo))
