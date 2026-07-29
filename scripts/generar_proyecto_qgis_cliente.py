# -*- coding: utf-8 -*-
"""
Genera el proyecto QGIS (.qgz) y el paquete .zip de entrega para el CONTRATANTE.

Se ejecuta DESPUÉS de generar_gpkg_cliente.py.

Qué produce
-----------
public/descargas/padron_riego_porotog.zip
    ├── padron_riego_porotog.gpkg     datos + simbología
    ├── padron_riego_porotog.qgz      proyecto listo para abrir
    └── LEEME.txt                     instrucciones para el cliente

Lo que aporta el proyecto sobre el GeoPackage suelto
----------------------------------------------------
* Relaciones 1:N — al clicar un predio se ven SUS fichas en una pestaña, y de cada
  ficha sus cultivos y animales. Así se resuelven los predios con varias fichas
  sin duplicar polígonos.
* Orden de capas, capa base satelital y encuadre inicial.
* Formularios por pestañas, en modo consulta.

Lo que deliberadamente NO lleva
-------------------------------
Ninguna expresión del proyecto de campo: sin aggregate(), sin ValueRelation, sin
defaults calculados, sin autonumeración. Todas las capas quedan de solo lectura.
"""
import os
import sqlite3
import sys
import zipfile
from datetime import datetime

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
TRABAJO = os.path.join(BASE, 'build_entrega')          # intermedios, no se publican
PUBLICO = os.path.join(BASE, 'public', 'descargas')    # solo el .zip que descarga el cliente
GPKG_NAME = 'padron_riego_porotog.gpkg'
GPKG = os.path.join(TRABAJO, GPKG_NAME)
QGZ = os.path.join(TRABAJO, 'padron_riego_porotog.qgz')
ZIP = os.path.join(PUBLICO, 'padron_riego_porotog.zip')

UTM17S_WKT = ('PROJCRS["WGS 84 / UTM zone 17S",BASEGEOGCRS["WGS 84",'
              'DATUM["World Geodetic System 1984",ELLIPSOID["WGS 84",6378137,298.257223563]],'
              'ID["EPSG",4326]],CONVERSION["UTM zone 17S",METHOD["Transverse Mercator"],'
              'PARAMETER["Latitude of natural origin",0],PARAMETER["Longitude of natural origin",-81],'
              'PARAMETER["Scale factor at natural origin",0.9996],'
              'PARAMETER["False easting",500000],PARAMETER["False northing",10000000]],'
              'CS[Cartesian,2],AXIS["easting",east],AXIS["northing",north],'
              'LENGTHUNIT["metre",1],ID["EPSG",32717]]')

# capa -> (id interno, título, ¿visible al abrir?)
CAPAS = [
    ('predios_investigados', 'predios_lyr', 'Predios investigados', True),
    ('comunidades', 'comunidades_lyr', 'Comunidades', False),
    ('sectores', 'sectores_lyr', 'Sectores de investigación', False),
    ('canales_riego', 'canales_lyr', 'Canales de riego', True),
    ('catastro_completo', 'catastro_lyr', 'Catastro rural completo', False),
]
# La capa de fichas lleva punto GPS (una capa con geometría siempre carga bien y
# de ella cuelga la pestaña "Fichas del predio"); va apagada porque el cliente
# consulta por predio, no por punto.
CAPAS.append(('fichas', 'fichas_lyr', 'Fichas de empadronamiento', False))

TABLAS = [
    ('cultivos', 'cultivos_lyr', 'Cultivos (Sección 4)'),
    ('animales', 'animales_lyr', 'Especies pecuarias (Sección 4)'),
]


def esc(s):
    return (str(s).replace('&', '&amp;').replace('<', '&lt;')
            .replace('>', '&gt;').replace('"', '&quot;'))


def columnas(cur, tabla):
    cur.execute('PRAGMA table_info("{}")'.format(tabla))
    return [c[1] for c in cur.fetchall() if c[1] not in ('fid', 'geom')]


def estilo_de(cur, tabla):
    """Reutiliza el QML ya embebido en el GeoPackage: una sola fuente de verdad."""
    cur.execute("SELECT styleQML FROM layer_styles WHERE f_table_name=?", (tabla,))
    r = cur.fetchone()
    if not r or not r[0]:
        return ''
    qml = r[0]
    ini = qml.find('<renderer-v2')
    fin = qml.find('</renderer-v2>')
    return qml[ini:fin + len('</renderer-v2>')] if ini >= 0 and fin > ini else ''


# ── Diseño del formulario ─────────────────────────────────────────────
# Los campos se agrupan en secciones con título en vez de caer en una lista
# plana. Cada entrada es (título del grupo, columnas, [campos]).
GRUPOS_PREDIO = [
    ('Identificación del predio', 2,
     ['clave_catastral', 'estado_predio', 'comunidad', 'sector_riego', 'parroquia']),
    ('Propiedad', 1, ['propietarios', 'propietario_catastro']),
    ('Fichas levantadas', 4,
     ['total_fichas', 'fichas_principales', 'fichas_adicionales', 'adicionales_pendientes']),
    ('Superficies y caudal', 2,
     ['area_catastro_m2', 'area_declarada_m2', 'area_riego_m2', 'caudal_ls']),
    ('Producción declarada', 1, ['cultivos_predio', 'animales_predio']),
]

GRUPOS_FICHA = [
    ('Regante', 2,
     ['apellidos', 'nombres', 'cedula', 'telefono_celular', 'telefono_casa',
      'nivel_instruccion']),
    ('Ubicación', 2,
     ['codigo_predio', 'clave_catastral', 'parroquia', 'comunidad', 'sector',
      'sector_comunidad', 'cota_msnm', 'tenencia_predio']),
    ('Tipo de ficha', 2, ['tipo_ficha', 'estado_investigacion', 'regante_principal']),
    ('Superficies', 3, ['area_total_m2', 'area_riego_m2', 'area_sin_riego_m2']),
    ('Riego', 3,
     ['canal', 'caudal_ls', 'caudal_tipo', 'frecuencia_riego', 'dias_riego',
      'horas_turno', 'metodo_gravedad_pct', 'metodo_aspersion_pct', 'metodo_goteo_pct']),
    ('Tarifa y servicios', 3,
     ['valor_tarifa', 'tipo_tarifa', 'tiene_reservorio', 'agua_consumo',
      'energia_electrica', 'material_construccion']),
    ('Organización', 2, ['org_riego', 'actividad_productiva']),
    ('Registro', 2, ['investigado_por', 'fecha_registro', 'foto_url', 'observaciones']),
]


def _grupos_xml(grupos, cols, sangria='          '):
    """Convierte la definición de grupos en contenedores de QGIS."""
    idx = {c: i for i, c in enumerate(cols)}
    out = []
    usados = set()
    for titulo, ncols, campos in grupos:
        presentes = [c for c in campos if c in idx]
        if not presentes:
            continue
        usados.update(presentes)
        campos_xml = "\n".join(
            '{s}    <attributeEditorField index="{i}" name="{c}" showLabel="1"/>'.format(
                s=sangria, i=idx[c], c=c) for c in presentes)
        out.append(
            '{s}  <attributeEditorContainer collapsed="0" columnCount="{n}" groupBox="1" '
            'name="{t}" showLabel="1" visibilityExpressionEnabled="0">\n{f}\n'
            '{s}  </attributeEditorContainer>'.format(
                s=sangria, n=ncols, t=esc(titulo), f=campos_xml))
    # cualquier campo no contemplado va a un grupo final, para no perderlo
    resto = [c for c in cols if c not in usados]
    if resto:
        campos_xml = "\n".join(
            '{s}    <attributeEditorField index="{i}" name="{c}" showLabel="1"/>'.format(
                s=sangria, i=idx[c], c=c) for c in resto)
        out.append(
            '{s}  <attributeEditorContainer collapsed="1" columnCount="2" groupBox="1" '
            'name="Otros datos" showLabel="1" visibilityExpressionEnabled="0">\n{f}\n'
            '{s}  </attributeEditorContainer>'.format(s=sangria, f=campos_xml))
    return "\n".join(out)


def maplayer(tabla, lid, titulo, cols, renderer, geom='Polygon', relaciones_tabs='', grupos=None):
    campos_xml = "\n".join(
        '      <field configurationFlags="NoFlag" name="{}"><editWidget type="TextEdit">'
        '<config><Option/></config></editWidget></field>'.format(c) for c in cols)
    editable = "\n".join('      <field editable="0" name="{}"/>'.format(c) for c in cols)
    alias = "\n".join(
        '      <alias field="{c}" index="{i}" name="{n}"/>'.format(
            c=c, i=i, n=esc(c.replace('_', ' ').capitalize()))
        for i, c in enumerate(cols))

    if relaciones_tabs or grupos:
        layout = 'tablayout'
        cuerpo = (_grupos_xml(grupos, cols) if grupos else "\n".join(
            '          <attributeEditorField index="{i}" name="{c}" showLabel="1"/>'.format(i=i, c=c)
            for i, c in enumerate(cols)))
        # OJO: <attributeEditorForm> debe ser hijo DIRECTO de <maplayer>, junto a
        # <editorlayout>. No existe ningún elemento <editformconfig> en el esquema
        # de los .qgs (ese es el nombre de la clase C++, no de la etiqueta XML);
        # si se envuelve ahí, QGIS no lo encuentra y muestra la lista plana.
        form = ('    <attributeEditorForm>\n'
                '        <attributeEditorContainer collapsed="0" columnCount="1" '
                'groupBox="0" name="{t}" showLabel="1" visibilityExpressionEnabled="0">\n'
                '{c}\n'
                '        </attributeEditorContainer>\n'
                '{r}'
                '    </attributeEditorForm>\n').format(
                    t='Datos del predio' if tabla == 'predios_investigados' else 'Ficha',
                    c=cuerpo, r=relaciones_tabs)
    else:
        layout = 'generatedlayout'
        form = ''

    return """  <maplayer type="vector" geometry="{gt}" hasScaleBasedVisibilityFlag="0" readOnly="1">
    <id>{lid}</id>
    <datasource>./{gp}|layername={t}</datasource>
    <layername>{titulo}</layername>
    <provider encoding="UTF-8">ogr</provider>
    <srs><spatialrefsys nativeFormat="Wkt">
      <wkt>{wkt}</wkt><proj4>+proj=utm +zone=17 +south +datum=WGS84 +units=m +no_defs</proj4>
      <srsid>3168</srsid><srid>32717</srid><authid>EPSG:32717</authid>
      <description>WGS 84 / UTM zone 17S</description><projectionacronym>utm</projectionacronym>
      <ellipsoidacronym>EPSG:7030</ellipsoidacronym><geographicflag>false</geographicflag>
    </spatialrefsys></srs>
{renderer}
    <fieldConfiguration>
{campos}
    </fieldConfiguration>
    <aliases>
{alias}
    </aliases>
    <editable>
{editable}
    </editable>
    <editorlayout>{layout}</editorlayout>
{form}  </maplayer>""".format(
        gt=geom, lid=lid, gp=GPKG_NAME, t=tabla,
        titulo=esc(titulo), wkt=esc(UTM17S_WKT), renderer=('    ' + renderer) if renderer else '',
        campos=campos_xml, alias=alias, editable=editable, layout=layout, form=form)


# Python de QGIS (OSGeo4W). Si está disponible, el .qgz se construye con la API
# oficial (construir_qgz_pyqgis.py), que además VERIFICA las relaciones releyendo
# el proyecto. El generador XML de más abajo queda solo como respaldo para
# máquinas sin QGIS.
PYQGIS_BAT = r"C:\OSGeo4W\bin\python-qgis.bat"


def construir_con_pyqgis():
    if not os.path.exists(PYQGIS_BAT):
        return False
    import subprocess
    script = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'construir_qgz_pyqgis.py')
    r = subprocess.run([PYQGIS_BAT, script], capture_output=True, text=True,
                       encoding='utf-8', errors='replace')
    salida = (r.stdout or '')
    ok = r.returncode == 0 and os.path.exists(QGZ) and 'VERIFICACION OK' in salida
    for linea in salida.strip().splitlines()[-8:]:
        print("  [PyQGIS] " + linea)
    if not ok:
        print("  [PyQGIS] falló (código {}); se usa el generador XML de respaldo".format(r.returncode))
    return ok


def main():
    if not os.path.exists(GPKG):
        print("ERROR: falta el GeoPackage. Ejecuta antes generar_gpkg_cliente.py")
        sys.exit(1)

    print("=" * 74)
    print(" PROYECTO QGIS Y PAQUETE DE ENTREGA")
    print("=" * 74)

    if construir_con_pyqgis():
        empaquetar()
        return

    con = sqlite3.connect(GPKG)
    cur = con.cursor()

    # ── relaciones 1:N ──
    relaciones = [
        ('rel_predio_fichas', 'Fichas de este predio', 'fichas_lyr', 'clave_catastral',
         'predios_lyr', 'clave_catastral'),
        ('rel_ficha_cultivos', 'Cultivos', 'cultivos_lyr', 'ficha_id', 'fichas_lyr', 'ficha_id'),
        ('rel_ficha_animales', 'Especies pecuarias', 'animales_lyr', 'ficha_id', 'fichas_lyr', 'ficha_id'),
    ]
    rel_xml = "\n".join(
        '    <relation id="{i}" name="{n}" referencingLayer="{rl}" referencedLayer="{dl}" '
        'strength="Association" providerKey="ogr">\n'
        '      <fieldRef referencingField="{rf}" referencedField="{df}"/>\n'
        '    </relation>'.format(i=i, n=esc(n), rl=rl, dl=dl, rf=rf, df=df)
        for i, n, rl, rf, dl, df in relaciones)

    capas_xml, tree_xml, orden = [], [], []

    # capas con geometría
    for tabla, lid, titulo, visible in CAPAS:
        cols = columnas(cur, tabla)
        tabs = ''
        if tabla == 'predios_investigados':
            tabs = ('        <attributeEditorContainer collapsed="0" columnCount="1" groupBox="0" '
                    'name="Fichas del predio" showLabel="1" visibilityExpressionEnabled="0">\n'
                    '          <attributeEditorRelation forceSuppressFormPopup="0" '
                    'name="rel_predio_fichas" nmRelationId="" relation="rel_predio_fichas" '
                    'showLabel="0"/>\n'
                    '        </attributeEditorContainer>\n')
        elif tabla == 'fichas':
            tabs = ''.join(
                '        <attributeEditorContainer collapsed="0" columnCount="1" groupBox="0" '
                'name="{n}" showLabel="1" visibilityExpressionEnabled="0">\n'
                '          <attributeEditorRelation forceSuppressFormPopup="0" name="{r}" '
                'nmRelationId="" relation="{r}" showLabel="0"/>\n'
                '        </attributeEditorContainer>\n'.format(n=n, r=r)
                for r, n in (('rel_ficha_cultivos', 'Cultivos'),
                             ('rel_ficha_animales', 'Especies pecuarias')))
        tipo = 'Point' if tabla == 'fichas' else ('Line' if tabla == 'canales_riego' else 'Polygon')
        grupos = (GRUPOS_PREDIO if tabla == 'predios_investigados'
                  else GRUPOS_FICHA if tabla == 'fichas' else None)
        capas_xml.append(maplayer(tabla, lid, titulo, cols, estilo_de(cur, tabla),
                                  geom=tipo, relaciones_tabs=tabs, grupos=grupos))
        tree_xml.append('    <layer-tree-layer checked="{c}" expanded="0" id="{i}" '
                        'name="{n}" providerKey="ogr" source="./{g}|layername={t}"/>'.format(
                            c='Qt::Checked' if visible else 'Qt::Unchecked',
                            i=lid, n=esc(titulo), g=GPKG_NAME, t=tabla))
        orden.append('      <item>{}</item>'.format(lid))

    # tablas sin geometría
    for tabla, lid, titulo in TABLAS:
        cols = columnas(cur, tabla)
        capas_xml.append(maplayer(tabla, lid, titulo, cols, '', geom='NoGeometry'))
        tree_xml.append('    <layer-tree-layer checked="Qt::Unchecked" expanded="0" id="{i}" '
                        'name="{n}" providerKey="ogr" source="./{g}|layername={t}"/>'.format(
                            i=lid, n=esc(titulo), g=GPKG_NAME, t=tabla))

    # Sin capa base: la declaración XYZ no cargaba en QGIS y solo estorbaba en el
    # panel. Si el cliente quiere fondo satelital lo agrega desde el navegador de
    # QGIS (XYZ Tiles), que es el camino normal.

    cur.execute("SELECT min_x,min_y,max_x,max_y FROM gpkg_contents WHERE table_name='predios_investigados'")
    ext = cur.fetchone()
    con.close()

    qgs = """<?xml version="1.0" encoding="UTF-8"?>
<qgis projectname="Padrón de Riego Guanguilquí–Porotog" version="3.36.0">
  <homePath path=""/>
  <title>Padrón de Usuarios — Sistema de Riego Comunitario Guanguilquí–Porotog</title>
  <projectCrs><spatialrefsys nativeFormat="Wkt">
    <wkt>{wkt}</wkt><srsid>3168</srsid><srid>32717</srid><authid>EPSG:32717</authid>
    <description>WGS 84 / UTM zone 17S</description><projectionacronym>utm</projectionacronym>
    <ellipsoidacronym>EPSG:7030</ellipsoidacronym><geographicflag>false</geographicflag>
  </spatialrefsys></projectCrs>
  <layer-tree-group>
{tree}
    <custom-order enabled="0">
{orden}
    </custom-order>
  </layer-tree-group>
  <mapcanvas name="theMapCanvas">
    <units>meters</units>
    <extent><xmin>{x0}</xmin><ymin>{y0}</ymin><xmax>{x1}</xmax><ymax>{y1}</ymax></extent>
    <destinationsrs><spatialrefsys nativeFormat="Wkt"><authid>EPSG:32717</authid>
      <description>WGS 84 / UTM zone 17S</description></spatialrefsys></destinationsrs>
  </mapcanvas>
  <projectlayers>
{capas}
  </projectlayers>
  <relations>
{rels}
  </relations>
  <projectMetadata>
    <title>Padrón de Usuarios — Riego Guanguilquí–Porotog</title>
    <abstract>Entrega cartográfica del padrón de usuarios. Solo consulta.</abstract>
    <author>Consorcio Cayambe SPT</author>
    <creation>{fecha}</creation>
  </projectMetadata>
</qgis>""".format(wkt=esc(UTM17S_WKT), tree="\n".join(tree_xml), orden="\n".join(orden),
                  capas="\n".join(capas_xml), rels=rel_xml,
                  x0=ext[0], y0=ext[1], x1=ext[2], y1=ext[3],
                  fecha=datetime.now().strftime('%Y-%m-%dT%H:%M:%S'))

    # validar antes de escribir
    import xml.etree.ElementTree as ET
    try:
        ET.fromstring(qgs)
        print("\n  XML del proyecto: válido")
    except ET.ParseError as e:
        print("\n  ERROR de XML: {}".format(e))
        sys.exit(2)

    with zipfile.ZipFile(QGZ, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr('padron_riego_porotog.qgs', qgs)
    print("  proyecto: {} ({:.0f} KB)".format(os.path.basename(QGZ), os.path.getsize(QGZ) / 1024))
    empaquetar()


def empaquetar():
    """Arma el .zip final (GeoPackage + .qgz + LEEME) en public/descargas."""
    leeme = """PADRÓN DE USUARIOS — SISTEMA DE RIEGO COMUNITARIO GUANGUILQUÍ–POROTOG
Entrega cartográfica para revisión en QGIS
Generado el {fecha}

CÓMO ABRIRLO
   Descomprima este archivo y abra "padron_riego_porotog.qgz" con QGIS 3.28 o
   superior. Las capas se cargan con su simbología y no hay que configurar nada.

QUÉ CONTIENE
   Predios investigados      CAPA PRINCIPAL. Predios con ficha de empadronamiento.
      naranja  = predio con ficha principal
      azul     = predio adicional ya investigado
      celeste  = predio adicional pendiente de la Sección 4 (producción)
      Para mostrar u ocultar cada color por separado, despliegue la flecha que
      está a la izquierda del nombre de la capa en el panel de Capas.
   Catastro rural completo   universo catastral de referencia
   Comunidades / Sectores    ámbito territorial del estudio
   Canales de riego          red de conducción

   Fichas de empadronamiento, Cultivos y Especies pecuarias son las capas de
   detalle. No hace falta abrirlas: alimentan las pestañas del formulario del
   predio. Vienen apagadas a propósito. Si le interesa, la capa de Fichas tiene
   el punto GPS donde se levantó cada ficha y puede encenderla.

CÓMO CONSULTAR UN PREDIO
   Active la herramienta Identificar y haga clic sobre un predio. Se abre un
   formulario con dos pestañas:
      "Datos del predio"    identificación, propiedad, fichas levantadas,
                            superficies y caudal
      "Fichas del predio"   el listado de las fichas de ese predio
   Seleccione una ficha de la lista y ábrala: verá los datos del regante, del
   riego y de la tarifa, y en sus propias pestañas los "Cultivos" (cada uno con
   su superficie y destino), las "Especies pecuarias" (con cantidades) y los
   "Predios adicionales del regante" — los otros predios que ese regante
   declaró, con acceso directo a cada uno.

   PREDIOS CON VARIAS FICHAS
   Un predio puede tener varias fichas, por herencia, copropiedad o porque
   corresponde a un terreno comunal con varias parcelas familiares. En el campo
   Propietarios se muestran los primeros nombres y el total; el listado completo
   está en la pestaña "Fichas del predio", y la producción de cada regante en su
   propia ficha.

   "Área catastro (m²)" es la superficie del polígono según el catastro.
   "Área declarada (m²)" es la suma de lo que reportaron las fichas del predio.

FOTOGRAFÍAS
   El campo "foto_url" de cada ficha enlaza a la imagen del predio. Requiere
   conexión a internet.

SISTEMA DE REFERENCIA
   EPSG:32717 — WGS 84 / UTM zona 17S. Las áreas y distancias se calculan en
   metros directamente.

NOTA
   Este paquete es de consulta: las capas están protegidas contra edición.
   Los datos corresponden al avance del levantamiento a la fecha indicada.

Consorcio Cayambe SPT — Prefectura de Pichincha
""".format(fecha=datetime.now().strftime('%d/%m/%Y'))

    os.makedirs(PUBLICO, exist_ok=True)
    with zipfile.ZipFile(ZIP, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        z.write(GPKG, GPKG_NAME)
        z.write(QGZ, os.path.basename(QGZ))
        z.writestr('LEEME.txt', leeme)

    mb = os.path.getsize(ZIP) / (1024 * 1024)
    print("\n" + "=" * 74)
    print(" PAQUETE LISTO: {}".format(ZIP))
    print(" {:.1f} MB comprimido (GeoPackage {:.1f} MB)".format(
        mb, os.path.getsize(GPKG) / (1024 * 1024)))
    print("=" * 74)


if __name__ == '__main__':
    main()
