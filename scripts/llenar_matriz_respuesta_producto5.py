# -*- coding: utf-8 -*-
"""Llena el modelo de matriz de respuesta que mandó el Consejo Provincial con las
respuestas a las observaciones del INFORME-JAFG-2026-002 (Producto 5).

El modelo llegó a Descargas el 9-oct-2026; se guardó una copia junto a la
respuesta («MODELO - ...xlsx» en CONTRATO Y FISCALIZACION\\RESPUESTA
OBSERVACIONES PRODUCTO 5) y se lee de ahí, sin modificarlo. La respuesta se
escribe en esa misma carpeta. Las celdas en amarillo son las que debe completar
otro responsable (componente social, Producto 6, administración del contrato) o
que esperan una decisión; el amarillo se quita antes de enviar.

La fila «Gral.» deja constancia de los dos documentos que el informe cita y que
no se pudieron identificar (el «informe catastral» I y el informe técnico de
revisión del oficio 048). Lo que de ellos se pudo reconstruir desde la base
está en cada observación; la C09 lleva su tabla en la hoja «Anexo C09».

Regenerar SOBRESCRIBE lo que se haya escrito a mano en la respuesta.
Uso:  python -X utf8 scripts/llenar_matriz_respuesta_producto5.py
"""
import os
import sqlite3
import sys
import zipfile

import openpyxl
from openpyxl.styles import Alignment, Font, PatternFill

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
from excel_compat import aplicar_formatos  # noqa: E402
from informe_estilo import esn  # noqa: E402

CARPETA = os.path.join(r'C:\Users\HP\OneDrive\Escritorio\CAYAMBE CATASTRO RIEGO', 'CONTRATO Y FISCALIZACION',
                       'RESPUESTA OBSERVACIONES PRODUCTO 5')
MODELO = os.path.join(CARPETA, 'MODELO - matriz_respuesta_octubre2026 (Consejo Provincial).xlsx')
SALIDA = os.path.join(CARPETA, 'matriz_respuesta_octubre2026 - respuestas (borrador).xlsx')
ENTREGA = r'C:\Users\HP\OneDrive\Escritorio\PRODUCTO 5 - ENTREGA 18-SEP-2026.zip'
AMARILLO = PatternFill('solid', fgColor='FFF2CC')
PEND = '[Por completar]'

# ── superficies sin redondear (§9-c), medidas sobre la base entregada ──────
gpkg = os.path.join(os.environ.get('TEMP', CARPETA), 'entrega18_matriz.gpkg')
if not os.path.exists(gpkg):
    with zipfile.ZipFile(ENTREGA) as z:
        open(gpkg, 'wb').write(z.read([n for n in z.namelist() if n.endswith('.gpkg')][0]))
con = sqlite3.connect(gpkg)
claves = {r[0] for r in con.execute('select clave_catastral from predios_investigados')}
CAT_M2 = sum(r[0] or 0 for r in con.execute('select area_catastro_m2 from predios_investigados'))
DECL_M2 = sum(r[1] or 0 for r in con.execute('select clave_catastral, area_total_m2 from fichas') if r[0] in claves)
con.close()

E1 = 'Anexo A1 – Conciliación por comunidad'
E2 = 'Anexo A2 – Fichas sin polígono'
E3 = 'Anexo A3 – Claves catastrales y hoja de cálculo'
E4 = 'Anexo A4 – Grupos de codificación'
I11 = 'Informe 11 comunidades – riego, cultivos y pecuario (Excel y PDF)'
REENTREGA = 'Base geoespacial del Producto 5, v2 (SHP, GeoPackage, CAD)'

# (código, observación, respuesta, acción, documento, ubicación, evidencia, estado)
# PEND en una celda = la completa otro responsable (se pinta de amarillo).
F = []


def fila(*v):
    F.append(list(v))


SOC = PEND + ' Componente social.'
P6 = PEND + ' Producto 6 (agronomía).'
ADM = PEND + ' Administración del contrato (Consorcio).'

# ── 5. Expediente social ───────────────────────────────────────────────────
for cod, obs in [
    ('S01', 'Socializaciones y actas: 21 eventos hasta agosto y 22 actas hasta el 5-sep. Conciliar corte, relación '
            'evento–acta y criterio de inclusión; cuadro con fecha, lugar, comunidad, objetivo, convocados, '
            'asistentes y anexos.'),
    ('S02', 'Fotografías y asistencia: 13 figuras frente a 31 fotografías anunciadas; entregar originales, actas y '
            'listas; conciliar 164 representantes de 48 comunidades con la cuota de 4 delegados; distinguir '
            'convocatoria de asistencia.'),
    ('S04', 'Poder e interés: categorías cambiantes y ponderación 50 % tierra / 50 % caudal sin cálculo '
            'reproducible.'),
    ('S05', 'Acuerdos y participación: matriz de acuerdos con responsable, plazo, estado y evidencia de cierre.'),
    ('S07', 'Modelo de gestión: estructura e índice preliminar para revisión por DRYD, con versión y responsable.'),
    ('S08', 'Socialización del proyecto de construcción: identificar la entrega específica; si se propone '
            'ejecución posterior, sustentar causa, cronograma y aprobación del ajuste.'),
]:
    fila(cod, obs, SOC, PEND, PEND, PEND, PEND, '')
fila('S03', 'Mapeo de actores: 39 denominaciones frente a 50 comunidades; catálogo común y matriz con ubicación, '
            'rol, representatividad y clasificación interna/externa.',
     'Aporte del catastro: catálogo único de las 50 comunidades con código (C01–C50), nombre oficial, nombre usado '
     'en la base y sector, que puede servir de catálogo común para el mapeo de actores. ' + SOC,
     'Propuesta: entrega del catálogo de comunidades. ' + PEND, 'Catálogo de comunidades (v1)', '', E1, '')
fila('S06', 'Línea base: metodología, fuentes, cobertura y análisis territorial; separar hogares, personas, '
            'usuarios, fichas y predios; variables, vacíos y anexos reproducibles.',
     'Aporte del catastro: universos separados y definidos desde la base (corte 19-ago-2026): 6.830 fichas '
     '(4.307 principales y 2.523 adicionales), 3.961 titulares únicos por cédula entre las fichas principales y '
     '5.987 predios catastrales con al menos una ficha (ver C03). ' + SOC,
     PEND, PEND, PEND, E1, '')
fila('S-adic.', 'Corregir fechas marzo/abril, encabezados de sector, nombres y horarios inconsistentes en actas e '
                'informes (sección 5).', SOC, PEND, PEND, PEND, PEND, '')

# ── Documentos citados que no se pudieron identificar ───────────────────────
NOTA_I = ('Las cifras observadas proceden del «informe catastral» (I), documento que la Consultora no ha podido '
          'identificar (ver fila «Gral.»). ')
fila('Gral.', 'Documentos de referencia citados en el informe JAFG-2026-002.',
     'El informe se apoya en dos documentos que la Consultora no ha podido identificar o de los que no dispone de '
     'copia: (1) el «informe catastral» (referencia I), fuente de las cifras observadas en C01, C02, C03, C06 y C08. '
     'No corresponde a los documentos del componente catastral entregados el 18-sep-2026 (base geoespacial, '
     'diccionario de datos, enlace al geovisor, memoria técnica, manual de uso y porcentaje de avance), y varias de '
     'sus cifras no coinciden con ninguna versión de la base validada. (2) El «Informe técnico integral de revisión '
     'catastral y productiva» (Informe-Prefectura-Observaciones-oficio-048), del que proceden los códigos C01–C18 y '
     'los hallazgos numéricos ampliados. Sin perjuicio de las respuestas de esta matriz, construidas desde la base '
     'validada, se solicita identificar ambos documentos (título, fecha, autor y versión) o remitir copia, para '
     'contrastar cada cifra con la misma fuente y cerrar las observaciones. Las acciones que esta matriz señala '
     'como «Propuesta» constituyen la propuesta de subsanación de la Consultora y se ejecutarán según el cronograma '
     'que se acuerde con la Administración del Contrato (§11.1-f).',
     'Solicitud de identificación o copia de los dos documentos. Las acciones propuestas se ejecutan según el '
     'cronograma de subsanación que se acuerde.', '—', '—', '—', 'Abierta')

# ── 6. Catastro: agregación y universo ─────────────────────────────────────
fila('C01', 'Seis comunidades no concilian: La Libertad 155/153; San Antonio 182/185; San José 202/200; Milagro '
            '80/81; Alpaka cambia tipo de ficha; Otón con error de suma.',
     NOTA_I + 'Desde la base validada (corte 19-ago-2026), que coincide con el resumen de fichas (R): La Libertad '
     '153, San Antonio 185, San José 200 y Milagro 81 fichas; Pueblo de Otón 193 (153 principales y 40 '
     'adicionales); Alpaka 492 fichas principales. Se revisaron todas las versiones de la base desde el 15-ago-2026: '
     'los valores 155, 202 y 80 no aparecen en ninguna, y 182 corresponde a una versión intermedia del 18-ago-2026, '
     'previa al cierre de la depuración.',
     'Ejecutada: cuadro de conciliación por comunidad generado desde la base, con subtotales y totales por fórmula, '
     'para reemplazar los cuadros del documento citado una vez identificado.',
     'Cuadro de conciliación por comunidad (Anexo A1)', 'Hoja «Anexo A1 Comunidades»', E1, 'En revisión')
fila('C02', 'Sector 2: detalle 1.726/518 frente a subtotal 1.728/516. Otón 153 + 16 = 169 frente a 193. Las '
            'columnas suman 6.806 y las filas 6.830.',
     NOTA_I + 'La base registra en el Sector 2 1.728 fichas principales y 516 adicionales (2.244), igual al '
     'subtotal citado; el detalle de filas del informe catastral es el que no suma. En Pueblo de Otón las 40 fichas '
     'adicionales constan en el resumen R y en la base, y todas las versiones de la base desde el 15-ago-2026 '
     'registran 193 fichas: 153 + 40 = 193 es el valor correcto. Total del padrón: 4.307 + 2.523 = 6.830 fichas.',
     'Ejecutada: subtotales y totales por sector regenerados desde la base, con fórmulas, para reemplazar las '
     'tablas 5 y 6 del documento citado una vez identificado.',
     'Cuadro de conciliación por comunidad (Anexo A1)', 'Anexo A1, bloque «Subtotales por sector»', E1,
     'En revisión')
fila('C03', '4.165 − 453 = 3.712 frente a 3.681 comuneros declarados; las filas finales suman 3.664. Fijar '
            'universo de usuarios únicos, distinto del de fichas y predios.',
     NOTA_I + 'De la operación citada, el valor 453 coincide con la meta de planificación de la comunidad San '
     'Vicente de Guayllabamba, que figura en el listado de comunidades pero no tiene fichas en el padrón; los '
     'valores 4.165 y 3.664 no se pudieron identificar. '
     'Se definen tres universos separados: (1) fichas: 6.830 (4.307 principales y 2.523 adicionales); (2) '
     'titulares únicos: 3.961 cédulas distintas entre las fichas principales (63 fichas principales sin cédula '
     'registrada), en proceso de verificación de cédulas; (3) predios: 5.987 predios catastrales con al menos una '
     'ficha. Los listados de las 50 comunidades registran 3.681 comuneros; su conciliación por cédula se presenta '
     'en la matriz de las 50 comunidades (§11.1-g).',
     'Propuesta: incorporar la definición de los tres universos en el diccionario de datos.',
     'Diccionario de datos (v2)', 'Sección «Universos»', E1, 'En revisión')
fila('C04', '4.218 grupos S-C-R, 128 con varias principales y 138 sin principal; identificación coincidente con '
            'nombres diferentes. Verificar identidades; reglas y tabla de correspondencia, sin eliminar registros.',
     'Se reproduce el resultado sobre el resumen R. El código S-C-R-F agrupa a cada titular por cédula dentro de '
     'su comunidad (por nombre cuando no hay cédula). Grupos sin ficha principal (138): 81 fichas adicionales '
     'registradas a nombre de un familiar y vinculadas a la ficha principal que las declaró; 25 de titulares cuya '
     'ficha principal está en otra comunidad; 32 adicionales sin cédula. Grupos con varias principales (128): 96 '
     'titulares con fichas principales sobre predios distintos; 25 cédulas compartidas entre familiares; 7 predios '
     'con dos fichas principales del mismo titular. Las identidades se contrastaron con el catastro municipal y el '
     'dígito verificador: de 627 fichas con observación de cédula, 511 quedan resueltas en oficina y 116 se '
     'verifican en campo.',
     'Propuesta: tabla de correspondencia ficha–titular–predio–polígono con las reglas de codificación. Ningún '
     'registro se elimina; las correcciones de identidad se aplican con registro de cambios.',
     'Tabla de correspondencia (nueva); ' + REENTREGA, 'Capa «fichas», campo de código', E4, 'En revisión')
fila('C05', 'Se declara 100 % sin universo predial conciliado; 6.830 fichas y 5.987 filas no son unidades '
            'equivalentes. Presentar universo total, levantados, pendientes, fórmula, corte y respaldo.',
     'El documento «Porcentaje de avance y fecha de corte» expresa el 100 % sobre las propiedades declaradas por '
     'los comuneros y advierte que no existe un universo predial de referencia. Se acoge la observación: se propone '
     'expresar el avance por universo definido (fichas, titulares y predios) y calcular el porcentaje predial con la '
     'matriz de las 50 comunidades contra los padrones certificados (§11.1-g), con fórmula, corte y respaldo.',
     'Propuesta: reformular el documento «Porcentaje de avance y fecha de corte» (documento 6 de la entrega del '
     'Producto 5 del 18-sep-2026) sobre los universos definidos.',
     '«Porcentaje de avance y fecha de corte» (documento 6 de la entrega del 18-sep-2026), v2',
     'Sección «Avance sobre el universo»', E1, 'En revisión')
fila('C06', 'Fechas de ejecución anteriores al inicio declarado: Sector 2, 8/06 frente a 10/06; Rosalía, 10/06 '
            'frente a 15/06. Separar programación y ejecución.',
     'Las fechas 10/06 y 15/06 constan en el «informe catastral» (I), documento que la Consultora no ha podido '
     'identificar (ver fila «Gral.»). Los registros de campo (fecha y hora de cada ficha) confirman la ejecución: '
     'el Sector 2 inició el 8-jun-2026 (Santa Rosa de Pingulmi y Comuna Izacata) y Rosalía el 10-jun-2026; las '
     'fechas 10/06 y 15/06 corresponden, por tanto, a la programación.',
     'Ejecutada: primera y última ficha registrada por comunidad, como respaldo de la ejecución efectiva.',
     'Cuadro de conciliación por comunidad (Anexo A1)', 'Anexo A1, columnas «Primera ficha» y «Última ficha»',
     E1 + ' (columnas de fechas)', 'En revisión')

# ── 7. Conciliación y vínculos ─────────────────────────────────────────────
fila('C07', 'Variantes de denominación (Izacata/Izacata Grande, Avellaneda/Eliot) y errores de codificación. '
            'Catálogo con código único y equivalencias; no fusionar por similitud.',
     'La base usa una sola denominación por comunidad (50 valores). Izacata Grande, Comuna Izacata y Los Andes '
     'Izacata son tres comunidades distintas del listado oficial, no variantes. Las variantes provienen del nombre '
     'corto usado en la base frente al oficial («Avellaneda» / «Eliot Avellaneda»), del campo de sector o barrio, '
     'de texto libre, y de la capa de comunas del contratante, que conserva sus nombres originales.',
     'Propuesta: catálogo C01–C50 con nombre oficial, nombre en la base y equivalencias; código y nombre oficial '
     'de comunidad en todas las capas. Ninguna comunidad se fusiona por similitud.',
     'Catálogo de comunidades (nuevo); ' + REENTREGA, 'Todas las capas, campos de comunidad', E1, 'En revisión')
fila('C08', 'La diferencia entre fichas y comuneros se interpreta como nuevos usuarios: 1.624 reportado; '
            '3.410 − 1.769 = 1.641.',
     NOTA_I + 'La operación coincide con el Sector 1: 3.410 son sus fichas (1.790 principales y 1.620 '
     'adicionales) y 1.769 se aproxima a la meta de comuneros planificados del Sector 1 en el sistema (1.768). Si '
     'ese es el cálculo, la resta compara fichas con una meta de planificación y no mide usuarios nuevos: una ficha '
     'no es un usuario (las 4.307 fichas principales corresponden a 3.961 cédulas distintas). La base no calcula '
     'un indicador de «nuevos usuarios».',
     'Propuesta: no usar esa resta como indicador; medir los usuarios que no constan en el padrón certificado, por '
     'cédula, en la matriz de las 50 comunidades (§11.1-g).',
     '—', '—', E1, 'En revisión')
fila('C09', 'R: 4.307 + 2.523 = 6.830 fichas. X: 4.298 + 2.523 = 6.821. Diferencia de 9 principales y de tipo en '
            '25 comunidades.',
     'La diferencia corresponde exactamente a 9 fichas principales cuyo predio no tiene polígono en el catastro del '
     'cantón Cayambe: 8 de la Asociación Rosalía, con clave catastral del Distrito Metropolitano de Quito (consta en '
     'la observación de cada ficha), y 1 de La Libertad cuya clave declarada no existe en el catastro. X cuenta '
     'predios con polígono y R cuenta fichas: no hay omisiones. Las diferencias de tipo en 25 comunidades se '
     'reproducen exactamente (hoja «Anexo C09»): la tabla X asigna cada predio a la comunidad de su primera ficha, '
     'de modo que en los predios con fichas de dos comunidades todas se cuentan en una sola; a ello se suman las 9 '
     'fichas sin polígono. El total de fichas no cambia, solo la comunidad en que se cuentan. El detalle de origen '
     'de esta observación procede del informe técnico de revisión, del que no se dispone de copia (ver fila '
     '«Gral.»).',
     'Ejecutada: listado nominal de las 9 fichas con su causa y conciliación por comunidad. Propuesta: tabla '
     '«fichas sin polígono» y comunidad de cada ficha en la tabla de correspondencia; confirmación de la clave de '
     'La Libertad con el titular.',
     REENTREGA + ' (tabla «fichas sin polígono»)', 'GeoPackage, capas «fichas» y «predios_investigados»',
     E2 + '; hoja «Anexo C09» de esta matriz', 'En revisión')
fila('C10', '5.987 fid; 5.979 claves; 7 repetidas; 30 claves numéricas de más de 15 dígitos; X no contiene los '
            'códigos completos de R.',
     'En la base las claves se almacenan como texto: 5.987 filas y 5.987 claves distintas, ninguna repetida (5.951 '
     'de 13 dígitos, 30 urbanas de 23 dígitos y 6 de 10 dígitos). Al abrir la tabla en una hoja de cálculo, las '
     'claves se leen como número y se conservan solo 15 cifras: las 30 claves urbanas se truncan y resultan '
     'exactamente 5.979 claves y 7 repetidas.',
     'Propuesta: versión Excel con la clave en formato texto y tabla de relaciones ficha–titular–predio–polígono '
     'con el código S-C-R-F de cada ficha.',
     REENTREGA + '; versión Excel de atributos (nueva)', 'Capa «predios_investigados», campo clave_catastral', E3,
     'En revisión')
fila('C17', 'Cultivo «500», textos mal codificados, 6 propietarios del catastro y 5 riego_pct vacíos (filas 1138, '
            '4696, 4982).',
     'Cultivo «500»: el registro original indica «Pasto no mejorado»; el valor «500» estaba en el campo '
     'complementario «otro», que la tabla mostraba con prioridad. Textos: el SHP está en UTF-8 con su archivo .cpg; '
     'las filas citadas contienen tildes o raya («Maíz», «producción», «Guanguilquí–Porotog»), que se alteran al '
     'abrir el DBF directamente en una hoja de cálculo. Vacíos: los 5 riego_pct son los 5 predios cuya ficha no '
     'declara condición de riego; los 6 propietarios vacíos son predios que el catastro municipal entrega sin '
     'propietario.',
     'Propuesta: corrección del cultivo y del orden de lectura (prevalece el tipo de cultivo); versión Excel y '
     'nota de apertura del SHP; dominios y valores nulos en el diccionario, con registro de cambios.',
     REENTREGA + '; Diccionario de datos (v2)', 'Capas «predios_investigados» y «cultivos»', E3, 'En revisión')

# ── 7.1 Archivos, corte, campo sector ──────────────────────────────────────
fila('§7.1-a', 'Verificar SHP, mpk y CAD, geometrías, sistema de referencia, atributos, diccionario, enlace del '
               'geovisor, memoria y manual.',
     'Se entregaron el 18-sep-2026: SHP y CAD (DXF) en EPSG:32717, GeoPackage con proyecto QGIS, diccionario de '
     'datos, enlace al geovisor, memoria técnica y manual de uso. El paquete de mapa se entregó como proyecto QGIS '
     '(.qgz), formato abierto equivalente al .mpk.',
     'Propuesta: reentrega con inventario de archivos. ' + PEND + ' Confirmar si se genera además el .mpk.',
     REENTREGA, 'Carpeta 1 de la entrega', '—', 'En revisión')
fila('§7.1-b', 'I y R declaran corte al 19-ago-2026; X no presenta corte interno y P se emite el 18-sep. '
               'Acreditar compatibilidad de versiones.',
     'X proviene de la misma base y corte que R (19-ago-2026), pero no lo declara en sus atributos.',
     'Propuesta: fecha de corte y versión en los metadatos de cada capa y en el diccionario. ' + P6,
     REENTREGA + '; Diccionario de datos (v2)', 'Metadatos de cada capa', '', 'En revisión')
fila('§7.1-c', 'El campo «sector riego» contiene sistemas o comités; validar la correspondencia con los sectores '
               '1–3.',
     'El campo registra el sistema u organización de riego que declaró el titular (Guanguilquí–Porotog, Guanguilquí, '
     'comités de Buena Esperanza y de Pitana Bajo, Porotog), no el sector 1–3.',
     'Propuesta: el campo se renombra como «sistema de riego declarado» y se añade el campo «sector» (1–3) según '
     'el catálogo de comunidades.', REENTREGA, 'Capa «predios_investigados»', '', 'En revisión')

# ── 8. Producto 6 ───────────────────────────────────────────────────────────
fila('C11', 'P declara 6.848 registros frente a 6.830 fichas de R y 5.987 filas de X; 4.095 productores sin llave '
            'personal reproducible.',
     'Aporte del catastro: la base contiene 6.830 fichas; la tabla de correspondencia ficha–titular–predio (código '
     'S-C-R-F y cédula) es la llave para conciliar el universo de productores. ' + P6,
     PEND, PEND, PEND, '—', '')
fila('C12', 'P reporta 6.880,42 ha; las áreas de cultivos en X suman 6.857,29 ha (−23,13 ha).',
     'La superficie de cultivos de la base es 6.880,37 ha, la misma del Producto 6 (diferencia de 0,05 ha por '
     'versión). La suma de 6.857,29 ha se obtiene del campo de texto «cultivos_predio» de X, que es un resumen '
     'legible y no la fuente de cálculo: omite los registros de cultivo sin nombre (19,63 ha) y las 9 fichas sin '
     'polígono (3,42 ha). La fuente editable es la tabla de cultivos del GeoPackage (un registro por cultivo y '
     'ficha). ' + P6,
     PEND, 'GeoPackage, capa «cultivos»', '', '', '')
fila('C13', 'Once comunidades: P 1.876,17 ha; X 1.865,17 ha; referencia 1.875,62 ha sin fuente; tabla 3 de P '
            '1.876,16 ha.',
     'El área sembrada declarada en la base para las once comunidades del sistema Porotog es 1.876,17 ha, igual a '
     'la del Producto 6. El valor de X proviene del mismo resumen de texto (ver C12) y la referencia de 1.875,62 ha '
     'corresponde a otra versión de los datos. Se entrega el informe de las once comunidades con la superficie por '
     'cultivo y por comunidad calculada desde la base.',
     'Ejecutada: informe de las 11 comunidades (superficie con y sin riego, área sembrada por cultivo y comunidad).',
     I11, 'Tablas 2 y 3; hojas «Área sembrada» y «Cultivos por comunidad»', I11, 'En revisión')
fila('C14', '276 filas exceden la superficie declarada en más de 0,01 ha; 22 con componentes sin área; 61 vacías.',
     'Las 61 filas vacías son predios cuyas fichas no registran cultivos. Para los excedentes, la comparación '
     'válida es por predio: se suman los cultivos de todas las fichas de cada predio y se comparan con su '
     'superficie catastral. En las once comunidades, 117 predios declaran más de un 10 % por encima de lo que '
     'miden; 55 de ellos tienen varias fichas (herederos que declaran el mismo terreno). Otras causas: terreno '
     'arrendado fuera del predio y áreas estimadas en la entrevista. Se presenta además el área ajustada al predio '
     'como referencia, sin alterar lo declarado.',
     'Ejecutada para las 11 comunidades. Propuesta: la misma tabla de excedentes por predio para el padrón '
     'completo. ' + P6, I11, 'Sección 4; hojas «Sembrado vs predio» y «Predios que exceden»', I11, 'En revisión')
fila('C15', 'El cuadro comunitario suma 3.843 bovinos; los apartados 5 y 5.1 no están desarrollados.',
     'Aporte del catastro: la cifra de 3.843 bovinos se reproduce exactamente desde la base. Corresponde a los '
     'bovinos contados sin duplicar por titular: cuando un titular declara sus animales en varias de sus fichas, '
     'para cada categoría se toma el mayor valor entre ellas. Sumando todas las fichas, la base registra 4.055 '
     'cabezas declaradas. El detalle por categoría (vacas en producción, vacas secas, vaconas, terneros, terneras, '
     'toretes y toros) y por comunidad está en el informe de las once comunidades. ' + P6,
     'Ejecutada (catastro): bovinos y demás especies por comunidad, con las dos cifras. ' + PEND,
     I11, 'Sección 5; hojas «Bovinos por categoría» y «Detalle pecuario»', I11, '')
fila('C16', 'Depuración por máximos no reproducible sin llave personal; 3.092 campos de animales vacíos.',
     'Los 3.092 campos vacíos de X corresponden a predios cuyas fichas no tienen registros en la sección pecuaria. '
     'La depuración por máximos es reproducible con la cédula del titular como llave: el máximo por titular y '
     'especie da exactamente las cifras del Producto 6 (ver C15). La base guarda un registro por especie, cantidad '
     'y ficha, que permite armar la matriz por productor, predio y categoría. ' + P6, PEND,
     'GeoPackage, capa «animales»', '', I11, '')
fila('C18', 'La caracterización no acredita por sí sola necesidades ni viabilidad del riego; respaldos de '
            'calendarios, parámetros, balance, clima, oferta y áreas regables.', P6, PEND, PEND, PEND, PEND, '')
fila('§8-a', 'Contradicción de maíz en el sector alto: 0,00 ha en el cuadro sectorial frente a 13,94 ha en el '
             'subconjunto de once comunidades.',
     'La base registra 13,94 ha de maíz en las once comunidades, todas del Sector 1. El valor 0,00 corresponde al '
     'cuadro sectorial del Producto 6, que debe recalcularse desde la base. ' + P6, PEND, PEND, PEND, I11, '')
fila('§8-b', 'Identificar y vincular territorialmente los nueve puntos de suelo revisados.', P6, PEND, PEND, PEND,
     PEND, '')

# ── 9. Superficies ──────────────────────────────────────────────────────────
fila('§9-a', 'Áreas de X: 8.093,34 ha catastrales; 7.988,75 declaradas; 6.170,95 con riego; 1.817,80 sin riego. '
             'Definir cada concepto y fuente.',
     '7.988,75 / 6.170,95 / 1.817,80 ha son la superficie declarada de las 6.821 fichas con polígono. Con las 9 '
     'fichas sin polígono, la declarada es 7.992,88 ha (6.175,07 con riego y 1.817,81 sin riego). 8.093,34 ha es '
     'la superficie catastral: cada predio medido una vez por su polígono. Ninguna de ellas es área potencialmente '
     'regable.',
     'Propuesta: definición de cada superficie, con su fuente y universo, en el diccionario de datos.',
     'Diccionario de datos (v2)', 'Sección «Superficies»', '', 'En revisión')
fila('§9-b', 'Versiones de superficie irrigada: análisis previo 6.143,98 ha; informe ampliado 6.170,95 ha.',
     'No son dos versiones sino dos mediciones de la misma base y corte: 6.143,98 ha es la superficie con riego '
     'catastral (por polígono, ajustada donde lo declarado excede el predio) y 6.170,95 ha es la superficie con '
     'riego declarada en las fichas con polígono. No se sustituyen entre sí ni se homologan con área cultivada.',
     'Aclaración.', 'Diccionario de datos (v2)', 'Sección «Superficies»', '', 'Cerrada')
fila('§9-c', 'Diferencia catastral–declarada: informe ampliado 104,58 ha; resta de cifras publicadas 104,59 ha.',
     f'Valores sin redondear: superficie catastral {esn(CAT_M2, 2)} m²; declarada en fichas con polígono '
     f'{esn(DECL_M2, 2)} m²; diferencia {esn(CAT_M2 - DECL_M2, 2)} m² ({esn((CAT_M2 - DECL_M2) / 1e4, 4)} ha). '
     '104,58 ha es el valor correcto; 104,59 resulta de restar cifras ya redondeadas.',
     'Aclaración. Las superficies se publican en m² con dos decimales y se redondean a hectáreas solo al presentar.',
     'Diccionario de datos (v2)', 'Sección «Superficies»', '', 'Cerrada')
fila('§9-d', 'La tabla ampliada imprime «4.72 / 671 / 591 / 5». Confirmar el primer valor.',
     'En la base: 4.720 predios con riego, 671 mixtos, 591 sin riego y 5 sin dato = 5.987 predios. «4.72» es un '
     'error de formato de la tabla ampliada.', 'Aclaración.', '—', 'Capa «predios_investigados», campo '
     'condicion_riego', '', 'Cerrada')

# ── 4. Avances del oficio 0047, 4.1 y 11 ───────────────────────────────────
fila('§4-1', 'Socialización de propuesta y mapeo de actores (oficio 0047, p. 2).', SOC + ' Ver S01–S05.', PEND,
     PEND, PEND, PEND, '')
fila('§4-2', 'Línea base socioeconómica-productiva (oficio 0047, p. 2).',
     'Aporte del catastro: informe técnico consolidado del padrón (7 capítulos: perfil del titular, predio y acceso '
     'al agua, producción agropecuaria, servicios básicos, conocimiento y gobernanza, estructura del padrón y los '
     'tres sectores) e informes por comunidad y por sector, generados de la misma base con corte al 19-ago-2026. '
     + SOC + ' Metodología, fuentes, diagnóstico territorial y formato de la Guía MAATE.', PEND, PEND, PEND, PEND,
     '')
fila('§4-3', 'Catastro geoespacial y alfanumérico (oficio 0047, p. 3).',
     'Entregado el 18-sep-2026: SHP, CAD (DXF), GeoPackage con proyecto QGIS, diccionario de datos, enlace al '
     'geovisor, memoria técnica, manual de uso y porcentaje de avance. Las diferencias señaladas se responden en '
     'C01–C10, C17 y la sección 9.',
     'Propuesta: reentrega con tabla de relaciones ficha–titular–predio–polígono, código de ficha y de comunidad '
     'en las capas, versión Excel con claves como texto, catálogo de comunidades y fecha de corte en los metadatos.',
     REENTREGA, 'Carpeta 1 de la entrega', '—', 'En revisión')
fila('§4-4', 'Estructura e índice del modelo de gestión (oficio 0047, p. 4).', SOC + ' Ver S07.', PEND, PEND,
     PEND, PEND, '')
fila('§4-5', 'Socialización del proyecto de construcción (oficio 0047, p. 4).', SOC + ' Ver S08.', PEND, PEND,
     PEND, PEND, '')
fila('§4.1-a', 'Acreditar comunicación de remisión, fecha de recepción, inventario de archivos, versiones y '
               'responsables.',
     'Aporte del catastro: la entrega del 18-sep-2026 consta de 49 archivos en 6 carpetas numeradas, con guía de '
     'lectura. ' + ADM, PEND, PEND, PEND, PEND, '')
fila('§4.1-b', 'Revisión prevista para el 22-sep-2026 y planificaciones semanales.', ADM, PEND, PEND, PEND, PEND,
     '')
fila('§11-a', 'Documentos finales del Producto 5 conforme a los TDR y al formato de la Guía MAATE.',
     PEND + ' Consorcio, catastro y componente social: reestructurar los documentos finales al índice de la Guía '
     'MAATE citada en los TDR.', PEND, PEND, PEND, PEND, '')
fila('§11.1-b', 'Informes corregidos en formato editable y PDF, bases de cálculo, archivos geoespaciales y anexos, '
                'con inventario.', 'Propuesta del catastro: inventario único de la reentrega, archivo por archivo, '
     'con el código de observación que atiende cada uno. ' + ADM, PEND, PEND, PEND, '—', '')
fila('§11.1-c', 'Conciliación por sector y comunidad; tabla de relaciones ficha–usuario–predio–polígono; registro '
                'de altas, bajas, reclasificaciones y cambios de superficie.',
     'La base conserva una bitácora fechada de cada depuración y respaldos de la versión anterior a cada '
     'corrección.',
     'Propuesta: conciliación por comunidad (Anexo A1), tabla de relaciones y registro de altas, bajas, '
     'reclasificaciones y cambios de superficie extraído de la bitácora de depuración.',
     'Registro de cambios (nuevo); ' + REENTREGA, '', E1, 'En revisión')
fila('§11.1-e', 'Constancia de revisión conjunta y concordancia entre los Productos 5 y 6.',
     'Aporte del catastro: catálogo de comunidades, fecha de corte y definiciones de superficie comunes para ambos '
     'productos (C07, §7.1-b, sección 9). ' + ADM, PEND, PEND, PEND, PEND, '')
fila('§11.1-f', 'Cronograma de subsanación y planificación territorial.', ADM, PEND, PEND, PEND, PEND, '')
fila('§11.1-g', 'Matriz de conciliación de las 50 comunidades contra los padrones certificados de cada '
                'organización: usuarios, investigados, predios y pendientes, justificando cada diferencia.',
     'Se propone cruzar por cédula cada padrón certificado contra la base: usuarios del padrón investigados y no '
     'investigados, titulares investigados que no constan en el padrón y predios asociados, justificando cada '
     'diferencia. El cuadro por comunidad del Anexo A1 es la base de esa matriz. Su ejecución está sujeta a la '
     'entrega de los padrones certificados actualizados de cada organización y al alcance que se acuerde con la '
     'Administración del Contrato.',
     'Propuesta (ver respuesta).', '—', '—', E1, 'En revisión')
fila('§11.1-h', 'Oficio 049 (caracterización edáfica): se atenderá con la documentación completa del Producto 6.',
     P6, PEND, PEND, PEND, PEND, '')

# ── orden de lectura: S01–S08, C01–C18 y luego los puntos por sección ──────
SECC = ['§4-', '§4.1-', '§7.1-', '§8-', '§9-', '§11-', '§11.1-']


def orden(v):
    c = v[0]
    if c == 'Gral.':
        return (-1, 0, '')
    if c.startswith('S') and c[1:].isdigit():
        return (0, int(c[1:]), '')
    if c.startswith('S'):
        return (1, 0, c)
    if c.startswith('C'):
        return (2, 10.5 if c == 'C17' else int(c[1:]), '')   # C17 es de la sección 7, va tras C10
    pref = max((p for p in SECC if c.startswith(p)), key=len)
    return (3, SECC.index(pref), c)


# Títulos por sección (pedido de Armando, 11-oct: «¿a qué se refieren las demás
# respuestas?»). El informe trae observaciones con código (S, C) y otras escritas
# en el texto de sus secciones, sin código; estas se identifican con el número
# de sección y una letra.
SIN_CODIGO = ('OBSERVACIONES SIN CÓDIGO — El informe también plantea requerimientos en el texto de sus secciones '
              '{}, sin asignarles código. Deben responderse igual; aquí se identifican con el número de sección '
              'y una letra (por ejemplo, 7.1-a).')
TITULOS = [
    ('Gral.', 'DOCUMENTOS DE REFERENCIA CITADOS EN EL INFORME'),
    ('S', 'SECCIÓN 5 DEL INFORME — Expediente social (códigos S01 a S08). Responde el componente social.'),
    ('C6', 'SECCIÓN 6 DEL INFORME — Observaciones catastrales: agregación y universo (códigos C01 a C06). '
           'Responde el catastro.'),
    ('C7', 'SECCIÓN 7 DEL INFORME — Observaciones catastrales: conciliación y vínculos (códigos C07 a C10 y C17). '
           'Responde el catastro.'),
    ('C8', 'SECCIÓN 8 DEL INFORME — Articulación con el Producto 6 (códigos C11 a C16 y C18). Responde el '
           'agrónomo, con aporte del catastro.'),
    ('§4-', 'SECCIÓN 4 — Los cinco avances que pidió el oficio 0047.'),
    ('§4.1-', 'SECCIÓN 4.1 — Condiciones transversales. Responde la administración del contrato.'),
    ('§7.1-', 'SECCIÓN 7.1 — Archivos y documentación de revisión obligatoria (SHP, CAD, geovisor, corte). '
              'Responde el catastro.'),
    ('§8-', 'SECCIÓN 8 — Otros puntos del Producto 6. Responde el agrónomo.'),
    ('§9-', 'SECCIÓN 9 — Superficies y precisión de los resultados. Responde el catastro.'),
    ('§11', 'SECCIÓN 11 — Recomendaciones y contenido de la respuesta.'),
]
NUM_SECC = {'§4-': '4', '§4.1-': '4.1', '§7.1-': '7.1', '§8-': '8', '§9-': '9', '§11': '11'}


def clave_seccion(c):
    if c == 'Gral.':
        return 'Gral.'
    if c.startswith('S'):
        return 'S'
    if c.startswith('C'):
        n = 10.5 if c == 'C17' else int(c[1:])
        return 'C6' if n <= 6 else ('C7' if n <= 10.5 else 'C8')
    return max((p for p in NUM_SECC if c.startswith(p)), key=len)


F.sort(key=orden)

# ── Anexo C09: fichas por comunidad en el resumen R y en la tabla X ────────
import collections  # noqa: E402
from comunidades_canon import canonica  # noqa: E402


def _n(s):
    import unicodedata
    return unicodedata.normalize('NFKD', canonica(s) or '').encode('ascii', 'ignore').decode().upper().strip()


con = sqlite3.connect(gpkg)
X = collections.defaultdict(lambda: [0, 0])
for com, p, a in con.execute('select comunidad, fichas_principales, fichas_adicionales from predios_investigados'):
    X[_n(com)][0] += p or 0
    X[_n(com)][1] += a or 0
con.close()
R = collections.defaultdict(lambda: [0, 0])
idx = openpyxl.load_workbook(r'C:\Users\HP\OneDrive\Escritorio\FICHAS PDF POROTOG\INDICE DE FICHAS.xlsx',
                             read_only=True)
for r in list(idx.worksheets[0].iter_rows(values_only=True))[1:]:
    if r[2]:
        R[_n(r[1])][0 if r[6] == 'Principal' else 1] += 1
DIF = [(c, R[c], X[c]) for c in sorted(set(R) | set(X)) if R[c] != X[c]]
assert len(DIF) == 25, len(DIF)

fuente, ajuste = Font(name='Calibri', size=11), Alignment(wrap_text=True, vertical='top')


def anexo_c09(wb):
    an = wb.create_sheet('Anexo C09')
    cab = ['Comunidad', 'R principales', 'R adicionales', 'X principales', 'X adicionales',
           'Diferencia principales', 'Diferencia adicionales']
    for j, h in enumerate(cab, 1):
        c = an.cell(1, j, h); c.font = Font(name='Calibri', size=11, bold=True); c.alignment = ajuste
    for i, (c, r, x) in enumerate(DIF, 2):
        for j, v in enumerate([c, r[0], r[1], x[0], x[1], f'=D{i}-B{i}', f'=E{i}-C{i}'], 1):
            an.cell(i, j, v).font = fuente
    t = len(DIF) + 2
    an.cell(t, 1, 'Total 25 comunidades').font = Font(name='Calibri', size=11, bold=True)
    for j in range(2, 8):
        col = openpyxl.utils.get_column_letter(j)
        an.cell(t, j, f'=SUM({col}2:{col}{t - 1})').font = Font(name='Calibri', size=11, bold=True)
    an.cell(t + 2, 1, 'R: resumen de fichas (una fila por ficha). X: capa predios_investigados (una fila por '
                      'predio, asignado a la comunidad de su primera ficha). La diferencia neta es −9 fichas '
                      'principales: las 9 fichas sin polígono (C09).').font = Font(name='Calibri', size=10,
                                                                                    italic=True)
    an.column_dimensions['A'].width = 32
    for col in 'BCDEFG':
        an.column_dimensions[col].width = 14


def escribir(filas, salida):
    """Escribe las filas sobre una copia del modelo, con la hoja «Anexo C09»."""
    wb = openpyxl.load_workbook(MODELO)
    ws = wb.active
    ws.delete_rows(2, ws.max_row)                    # quita la fila de ejemplo
    titulos = dict(TITULOS)
    sin_codigo = [NUM_SECC[k] for k in dict.fromkeys(clave_seccion(v[0]) for v in filas) if k in NUM_SECC]
    titulo_fill = PatternFill('solid', fgColor='DDEBF7')
    i, previa, aviso_sin_codigo = 2, None, False

    def titulo(texto, tam=11):
        nonlocal i
        c = ws.cell(i, 1, texto)
        c.font = Font(name='Calibri', size=tam, bold=True); c.alignment = ajuste; c.fill = titulo_fill
        ws.merge_cells(start_row=i, start_column=1, end_row=i, end_column=8)
        ws.row_dimensions[i].height = 32 if len(texto) > 120 else 18
        i += 1

    for v in filas:
        sec = clave_seccion(v[0])
        if sec != previa:
            if sec in NUM_SECC and not aviso_sin_codigo:
                titulo(SIN_CODIGO.format(', '.join(sin_codigo[:-1]) + ' y ' + sin_codigo[-1]
                                         if len(sin_codigo) > 1 else sin_codigo[0]), 11)
                aviso_sin_codigo = True
            titulo(titulos[sec])
            previa = sec
        # «§» no se entiende fuera del equipo: en el código se quita y en el texto se dice «punto»
        v = [v[0].replace('§', '')] + [x.replace('§', 'punto ') if isinstance(x, str) else x for x in v[1:]]
        for j, x in enumerate(v, 1):
            c = ws.cell(i, j, x); c.font = fuente; c.alignment = ajuste
            if isinstance(x, str) and PEND in x:
                c.fill = AMARILLO
        ws.cell(i, 1).font = Font(name='Calibri', size=11, bold=True)
        i += 1
    for col, w in zip('ABCDEFGH', [10, 38, 70, 45, 30, 28, 26, 22]):
        ws.column_dimensions[col].width = w
    ws.freeze_panes = 'C2'
    ws.auto_filter.ref = f'A1:H{i - 1}'
    anexo_c09(wb)
    wb.calculation.fullCalcOnLoad = True
    wb.save(salida)
    aplicar_formatos(salida)


# ── 1. Matriz completa (todas las observaciones) ───────────────────────────
escribir(F, SALIDA)
print('OK', SALIDA, '|', len(F), 'observaciones |', sum(1 for v in F if any(PEND in str(x) for x in v)),
      'con celdas por completar')

# ── 2. Versión solo del componente catastral (pedido de Armando, 11-oct) ───
# Para mostrar al consorcio qué está atendido por el catastro. El estado usa el
# término del propio informe (11.2: «atendida»). Donde la respuesta está
# completa pero queda un ajuste de forma en la base entregada, se dice: ese
# ajuste va en la reentrega y no se presenta como hecho.
SALIDA_CAT = os.path.join(CARPETA, 'matriz_respuesta_octubre2026 - CATASTRO (atendido).xlsx')
AJUSTE = 'Atendida; ajuste de la entrega en la reentrega'
ESTADO_CAT = {
    'Gral.': 'Abierta: identificación de los dos documentos',
    'C01': 'Atendida', 'C02': 'Atendida', 'C06': 'Atendida', 'C08': 'Atendida',
    'C03': AJUSTE, 'C07': AJUSTE, 'C09': AJUSTE, 'C10': AJUSTE, 'C17': AJUSTE,
    'C04': 'Atendida; 116 cédulas en verificación de campo',
    'C05': 'Atendida; el porcentaje predial depende de la matriz de las 50 comunidades (§11.1-g)',
    '§4-3': AJUSTE, '§7.1-a': 'Atendida; por confirmar si se requiere .mpk', '§7.1-b': AJUSTE, '§7.1-c': AJUSTE,
    '§9-a': AJUSTE, '§9-b': 'Atendida', '§9-c': 'Atendida', '§9-d': 'Atendida',
    '§11.1-c': AJUSTE,
    '§11.1-g': 'Pendiente de insumo: padrones certificados',
}
GRAL_CAT = ('Esta versión reúne solo las observaciones del componente catastral (secciones 6, 7 y 9, y los '
            'puntos 4-3, 7.1, 11.1-c y 11.1-g). Las del componente social, del Producto 6 y de la administración '
            'del contrato se responden en la matriz completa. ')
cat = []
for v in F:
    if v[0] not in ESTADO_CAT:
        continue
    v = list(v)
    v[7] = ESTADO_CAT[v[0]]
    if v[0] == 'Gral.':
        v[2] = GRAL_CAT + v[2]
    if v[0] == '§7.1-a':
        v[3] = v[3].replace(PEND + ' Confirmar si se genera además el .mpk.',
                            'Se confirma con la Administración si se requiere además el .mpk.')
    # lo que le toca a otro componente no va en la versión del catastro
    v = [x.replace(' ' + P6, '').replace(P6, '') if isinstance(x, str) else x for x in v]
    assert not any(PEND in str(x) for x in v), v[0]
    cat.append(v)
assert len(cat) == len(ESTADO_CAT), (len(cat), len(ESTADO_CAT))
escribir(cat, SALIDA_CAT)
print('OK', SALIDA_CAT, '|', len(cat), 'observaciones del catastro')
