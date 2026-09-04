# -*- coding: utf-8 -*-
"""
Construye el proyecto QGIS (.qgz) de entrega al contratante usando la API de
QGIS (PyQGIS), no XML artesanal.

POR QUÉ ASÍ: dos intentos de escribir el .qgs a mano fallaron en detalles del
esquema (elementos inventados, ubicación de <relations>, atributos de los
widgets). Con la API el propio QGIS escribe el proyecto, así que el resultado
es por construcción lo que QGIS espera; y al final este script lo RELEE y
verifica que las relaciones sean válidas antes de dar el visto bueno.

SE EJECUTA con el Python de QGIS (no con el Python normal):
  "C:\\OSGeo4W\\bin\\python-qgis.bat" scripts/construir_qgz_pyqgis.py
Normalmente lo invoca generar_proyecto_qgis_cliente.py, no hace falta llamarlo
a mano.

Modelo de consulta que arma (todo de solo lectura):
  clic en un predio -> pestañas: Datos del predio | Fichas del predio
  abrir una ficha   -> pestañas: Ficha | Cultivos | Especies pecuarias |
                        Predios adicionales del regante (autorrelación por
                        ficha_madre_id: los otros predios que declaró)
"""
import os
import sys

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
GPKG = os.path.join(BASE, 'build_entrega', 'padron_riego_porotog.gpkg')
QGZ = os.path.join(BASE, 'build_entrega', 'padron_riego_porotog.qgz')

from qgis.core import (  # noqa: E402  (el entorno lo da python-qgis.bat)
    QgsApplication, QgsProject, QgsVectorLayer, QgsRelation,
    QgsEditFormConfig, QgsAttributeEditorContainer, QgsAttributeEditorField,
    QgsAttributeEditorRelation, QgsCoordinateReferenceSystem,
    QgsFillSymbol, QgsLineSymbol, QgsMarkerSymbol,
    QgsRuleBasedRenderer, QgsCategorizedSymbolRenderer, QgsRendererCategory,
    QgsSingleSymbolRenderer, QgsReferencedRectangle, QgsRectangle,
    QgsAttributeTableConfig, QgsFeatureRequest,
    QgsProperty, QgsSymbolLayer,
)
from qgis.PyQt.QtGui import QColor  # noqa: E402


# ── paletas ───────────────────────────────────────────────────────────
# Mismos colores que el mapa web, para que el cliente vea lo mismo en ambos.
COLOR_PREDIO = {
    'Investigado':           ('#f97316', '#ea580c'),   # tomate: tiene ficha principal
    'Adicional investigado': ('#3b82f6', '#2563eb'),   # azul
    'Adicional pendiente':   ('#7dd3fc', '#0ea5e9'),   # celeste: falta Sección 4
    'Sin ficha':             ('#cbd5e1', '#94a3b8'),
}
COLOR_SECTOR = {
    'Sector 1': '#8b5cf6',
    'Sector 2': '#06b6d4',
    'Sector 3': '#10b981',
}
# Condición de riego del predio — mismos colores que la vista de riego de la
# web (3-sep-2026). Los mixtos, igual que en la web, llevan degradado
# tomate→verde según su % regado (ver simbologia_riego); el amarillo de aquí
# es solo el color de la LEYENDA de esa regla.
COLOR_RIEGO = {
    'Con riego': '#22c55e',
    'Mixto (riega una parte)': '#facc15',
    'Sin riego': '#c2410c',
    'Sin dato': '#94a3b8',
}
# 12 tonos bien diferenciados que se van rotando entre las 46 comunidades
PALETA_COMUNIDADES = [
    '#e6194b', '#3cb44b', '#ffe119', '#4363d8', '#f58231', '#911eb4',
    '#42d4f4', '#f032e6', '#bfef45', '#fabed4', '#469990', '#dcbeff',
]


def relleno(hex_fill, hex_borde, opacidad=0.45, ancho=0.26):
    s = QgsFillSymbol.createSimple({
        'color': hex_fill, 'outline_color': hex_borde,
        'outline_width': str(ancho), 'style': 'solid', 'outline_style': 'solid'})
    s.setOpacity(opacidad)
    return s

# ── diseño de los formularios ─────────────────────────────────────────
GRUPOS_PREDIO = [
    ('Identificación del predio', 2,
     ['clave_catastral', 'estado_predio', 'comunidad', 'sector_riego', 'parroquia']),
    ('Propiedad', 1, ['propietarios', 'propietario_catastro']),
    ('Fichas levantadas', 4,
     ['total_fichas', 'fichas_principales', 'fichas_adicionales', 'adicionales_pendientes']),
    ('Superficies y caudal', 2,
     ['area_catastro_m2', 'area_declarada_m2', 'area_riego_m2', 'area_sin_riego_m2',
      'condicion_riego', 'riego_pct', 'caudal_comunidad_ls']),
    # 'cultivos_predio' / 'animales_predio' (texto resumido) quedan en la tabla de
    # atributos para consulta rápida, pero en el formulario se reemplazan por las
    # pestañas "Cultivos del predio" / "Animales del predio" (tabla real, con
    # cantidades y de qué ficha viene cada registro): así se ven exactamente con
    # el mismo tratamiento que "Fichas del predio", en vez de texto plano.
]
GRUPOS_FICHA = [
    ('Regante', 2,
     ['apellidos', 'nombres', 'cedula', 'telefono_celular', 'telefono_casa',
      'nivel_instruccion']),
    ('Tipo de ficha', 2, ['tipo_ficha', 'estado_investigacion', 'regante_principal']),
    ('Ubicación', 2,
     ['codigo_predio', 'clave_catastral', 'parroquia', 'comunidad', 'sector',
      'sector_comunidad', 'cota_msnm', 'tenencia_predio']),
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

ALIAS = {
    'clave_catastral': 'Clave catastral', 'estado_predio': 'Estado del predio',
    'sector_riego': 'Sector de riego', 'propietario_catastro': 'Propietario según catastro',
    'area_catastro_m2': 'Área catastro (m²)', 'area_declarada_m2': 'Área declarada (m²)',
    'area_riego_m2': 'Área con riego (m²)', 'area_sin_riego_m2': 'Área sin riego (m²)',
    'area_total_m2': 'Área total (m²)',
    # En la ficha el técnico anotó el caudal que recibe SU COMUNIDAD, así que el
    # mismo valor se repite en todas las fichas de esa comunidad y NO debe
    # sumarse. El alias lo dice explícitamente para que nadie lo agregue.
    'caudal_ls': 'Caudal declarado (l/s) — es el de la comunidad, no sumar',
    'caudal_comunidad_ls': 'Caudal de la comunidad (l/s)',
    'condicion_riego': 'Condición de riego',
    'riego_pct': 'Riega (% del área declarada)',
    'caudal_total_ls': 'Caudal de la comunidad (l/s)',
    'total_fichas': 'Total de fichas', 'fichas_principales': 'Fichas principales',
    'fichas_adicionales': 'Fichas adicionales', 'adicionales_pendientes': 'Adicionales pendientes',
    'cultivos_predio': 'Cultivos del predio', 'animales_predio': 'Animales del predio',
    'telefono_celular': 'Teléfono celular', 'telefono_casa': 'Teléfono de casa',
    'nivel_instruccion': 'Nivel de instrucción', 'codigo_predio': 'Código del predio',
    'sector_comunidad': 'Sector en la comunidad', 'cota_msnm': 'Cota (msnm)',
    'tenencia_predio': 'Tenencia del predio', 'tipo_ficha': 'Tipo de ficha',
    'estado_investigacion': 'Estado de investigación', 'regante_principal': 'Regante principal',
    'caudal_tipo': 'Tipo de caudal', 'frecuencia_riego': 'Frecuencia de riego',
    'dias_riego': 'Días de riego', 'horas_turno': 'Horas por turno',
    'metodo_gravedad_pct': 'Gravedad (%)', 'metodo_aspersion_pct': 'Aspersión (%)',
    'metodo_goteo_pct': 'Goteo (%)', 'valor_tarifa': 'Tarifa ($)', 'tipo_tarifa': 'Tipo de tarifa',
    'tiene_reservorio': 'Tiene reservorio', 'agua_consumo': 'Agua de consumo',
    'energia_electrica': 'Energía eléctrica', 'material_construccion': 'Material de construcción',
    'org_riego': 'Organización de riego', 'actividad_productiva': 'Actividad productiva',
    'investigado_por': 'Investigado por', 'fecha_registro': 'Fecha de registro',
    'foto_url': 'Fotografía (enlace)', 'observaciones': 'Observaciones',
    'superficie_m2': 'Superficie (m²)', 'es_principal': 'Cultivo principal',
    'destino': 'Destino', 'cultivo': 'Cultivo', 'especie': 'Especie', 'cantidad': 'Cantidad',
    'area_predi_m2': 'Área catastral (m²)', 'tiene_ficha': 'Tiene ficha',
    'propietario': 'Propietario', 'comunidad': 'Comunidad', 'parroquia': 'Parroquia',
    'cedula': 'Cédula', 'apellidos': 'Apellidos', 'nombres': 'Nombres', 'sector': 'Sector',
    'canal': 'Canal', 'nombre': 'Nombre', 'ficha_madre_id': 'ID ficha madre',
    'ficha_id': 'ID de ficha', 'propietarios': 'Propietarios', 'regante': 'Regante',
    'clave_predio_principal': 'Clave (si es del dueño)',
}


def alias_de(campo):
    return ALIAS.get(campo, campo.replace('_', ' ').capitalize())


def aplicar_alias(vl):
    for i, f in enumerate(vl.fields()):
        vl.setFieldAlias(i, alias_de(f.name()))


def simbologia_predios(vl):
    """Reglas por estado del predio, con los mismos colores del mapa web."""
    raiz = QgsRuleBasedRenderer.Rule(None)
    for estado, (f, b) in COLOR_PREDIO.items():
        r = QgsRuleBasedRenderer.Rule(relleno(f, b))
        r.setLabel(estado)
        r.setFilterExpression('"estado_predio" = \'{}\''.format(estado))
        raiz.appendChild(r)
    vl.setRenderer(QgsRuleBasedRenderer(raiz))


def simbologia_riego(vl):
    """Reglas por condición de riego, con los colores de la web. Los MIXTOS no
    llevan color plano: el relleno se calcula por expresión con un degradado
    tomate→verde claro según `riego_pct` (rango 5–95 %, el mismo criterio y
    los mismos RGB que usa colorMixto() en la vista de riego del mapa web)."""
    raiz = QgsRuleBasedRenderer.Rule(None)
    for etiqueta, color in COLOR_RIEGO.items():
        r = QgsRuleBasedRenderer.Rule(relleno(color, color, 0.50, 0.4))
        r.setLabel(etiqueta)
        r.setFilterExpression('"condicion_riego" = \'{}\''.format(etiqueta))
        if etiqueta.startswith('Mixto'):
            t = 'clamp((coalesce("riego_pct",50)-5)/90.0, 0, 1)'
            expr = ('color_rgb( round(249+(134-249)*{t}), '
                    'round(115+(239-115)*{t}), round(22+(172-22)*{t}) )').format(t=t)
            r.symbol().symbolLayer(0).setDataDefinedProperty(
                QgsSymbolLayer.PropertyFillColor, QgsProperty.fromExpression(expr))
        raiz.appendChild(r)
    vl.setRenderer(QgsRuleBasedRenderer(raiz))


def simbologia_categorizada(vl, campo, colores=None, opacidad=0.35, borde_grueso=False):
    """Un color por valor del campo (comunidad, sector...)."""
    valores = sorted({str(f[campo]) for f in vl.getFeatures() if f[campo]})
    cats = []
    for i, v in enumerate(valores):
        c = (colores or {}).get(v) or PALETA_COMUNIDADES[i % len(PALETA_COMUNIDADES)]
        sym = relleno(c, c, opacidad, 0.8 if borde_grueso else 0.4)
        # el borde va opaco para que el límite se lea aunque el relleno sea tenue
        sym.symbolLayer(0).setStrokeColor(QColor(c))
        cats.append(QgsRendererCategory(v, sym, v))
    vl.setRenderer(QgsCategorizedSymbolRenderer(campo, cats))


def tabla_atributos_ordenada(vl, primeras):
    """Deja las columnas más útiles al inicio: la tabla se usa para analizar."""
    cfg = QgsAttributeTableConfig()
    cfg.update(vl.fields())
    columnas = list(cfg.columns())
    orden = {n: i for i, n in enumerate(primeras)}
    columnas.sort(key=lambda c: (orden.get(c.name, 999), c.name))
    cfg.setColumns(columnas)
    vl.setAttributeTableConfig(cfg)


def armar_formulario(vl, grupos, pestanas_rel):
    """grupos: secciones de la primera pestaña. pestanas_rel: [(titulo, relId, modo)]
    modo: 'tabla' muestra los registros relacionados como lista; 'formulario' abre
    ficha a ficha."""
    cfg = vl.editFormConfig()
    cfg.setLayout(QgsEditFormConfig.TabLayout)
    raiz = cfg.invisibleRootContainer()
    raiz.clear()

    tab = QgsAttributeEditorContainer(
        'Datos del predio' if grupos is GRUPOS_PREDIO else 'Ficha', raiz)
    tab.setIsGroupBox(False)
    for titulo, ncol, campos in grupos:
        g = QgsAttributeEditorContainer(titulo, tab)
        g.setIsGroupBox(True)
        g.setColumnCount(ncol)
        for c in campos:
            idx = vl.fields().indexOf(c)
            if idx >= 0:
                g.addChildElement(QgsAttributeEditorField(c, idx, g))
        tab.addChildElement(g)
    raiz.addChildElement(tab)

    for titulo, rel_id, modo in pestanas_rel:
        t = QgsAttributeEditorContainer(titulo, raiz)
        t.setIsGroupBox(False)
        rel = QgsAttributeEditorRelation(rel_id, t)
        # view_mode 0 = tabla (lista de registros), 1 = formulario (uno a uno).
        # Cultivos y animales se leen mejor como tabla: se comparan cantidades.
        try:
            conf = dict(rel.relationEditorConfiguration())
            conf['view_mode'] = 0 if modo == 'tabla' else 1
            rel.setRelationEditorConfiguration(conf)
        except Exception as e:
            print('  aviso: no se pudo fijar el modo de "{}": {}'.format(titulo, e))
        t.addChildElement(rel)
        raiz.addChildElement(t)

    vl.setEditFormConfig(cfg)


def main():
    app = QgsApplication([], False)
    app.initQgis()

    proyecto = QgsProject.instance()
    proyecto.setTitle('Padrón de Usuarios — Sistema de Riego Comunitario Guanguilquí–Porotog')
    proyecto.setCrs(QgsCoordinateReferenceSystem('EPSG:32717'))
    raiz = proyecto.layerTreeRoot()

    capas = {}

    def cargar(tabla, nombre, visible, expandida=False, clave=None):
        # `clave` permite cargar la misma tabla dos veces (p.ej. la simbología
        # de riego sobre predios_investigados) sin pisar la entrada de `capas`
        # que usan las relaciones.
        vl = QgsVectorLayer('{}|layername={}'.format(GPKG, tabla), nombre, 'ogr')
        if not vl.isValid():
            print('ERROR: no carga la capa', tabla)
            sys.exit(2)
        # La simbología se construye aquí con la API, no con loadDefaultStyle():
        # el estilo del GeoPackage no siempre se aplica y las capas salían con el
        # color aleatorio que asigna QGIS.
        vl.setReadOnly(True)           # entregable de consulta
        aplicar_alias(vl)
        proyecto.addMapLayer(vl, False)
        nodo = raiz.addLayer(vl)
        nodo.setItemVisibilityChecked(visible)
        nodo.setExpanded(expandida)
        capas[clave or tabla] = vl
        return vl

    # orden del panel = orden de carga
    # (La capa 'Comunidades' —dissolve— se retiró el 3-sep-2026: decisión de
    # JAVIKO; el límite territorial lo da 'Límites de comunas (oficial)'.)
    predios = cargar('predios_investigados', 'Predios investigados', True, expandida=True)
    riego = cargar('predios_investigados', 'Condición de riego (con/sin/mixto)',
                   False, expandida=True, clave='condicion_riego')
    comunas_ofi = cargar('comunas_oficiales', 'Límites de comunas (oficial)', False)
    sectores = cargar('sectores', 'Sectores de investigación', False)
    canales = cargar('canales_riego', 'Canales de riego', True)
    fichas = cargar('fichas', 'Fichas de empadronamiento (detalle)', False)
    catastro = cargar('catastro_completo', 'Catastro rural completo', False)
    cultivos = cargar('cultivos', 'Cultivos (detalle)', False)
    animales = cargar('animales', 'Especies pecuarias (detalle)', False)

    # ── simbología ────────────────────────────────────────────────────
    simbologia_predios(predios)
    # Condición de riego: una regla por clase (cada una se prende y apaga desde
    # el panel de Capas) y los mixtos con degradado por % regado, como la web.
    simbologia_riego(riego)
    # Una categoría por comuna: así se prende y apaga cada una por separado
    # desde el panel de Capas. Va tenue porque es límite de referencia, no el
    # ámbito investigado.
    simbologia_categorizada(comunas_ofi, 'comuna', opacidad=0.18, borde_grueso=True)
    simbologia_categorizada(sectores, 'sector', COLOR_SECTOR, opacidad=0.25, borde_grueso=True)
    catastro.setRenderer(QgsSingleSymbolRenderer(
        relleno('#e2e8f0', '#94a3b8', 0.18, 0.16)))
    canales.setRenderer(QgsSingleSymbolRenderer(
        QgsLineSymbol.createSimple({'line_color': '#38bdf8', 'line_width': '0.7'})))
    fichas.setRenderer(QgsSingleSymbolRenderer(QgsMarkerSymbol.createSimple({
        'name': 'circle', 'color': '#2563eb', 'outline_color': '#ffffff',
        'outline_width': '0.2', 'size': '1.6'})))

    # ── tabla de atributos lista para analizar ────────────────────────
    orden_predios = [
        'clave_catastral', 'estado_predio', 'comunidad', 'sector_riego', 'parroquia',
        'propietarios', 'total_fichas', 'area_catastro_m2', 'area_declarada_m2',
        'area_riego_m2', 'area_sin_riego_m2', 'condicion_riego', 'riego_pct',
        'caudal_comunidad_ls', 'cultivos_predio', 'animales_predio']
    tabla_atributos_ordenada(predios, orden_predios)
    tabla_atributos_ordenada(riego, orden_predios)
    tabla_atributos_ordenada(fichas, [
        'apellidos', 'nombres', 'cedula', 'tipo_ficha', 'estado_investigacion',
        'clave_catastral', 'comunidad', 'parroquia', 'area_total_m2', 'area_riego_m2',
        'caudal_ls', 'regante_principal'])
    tabla_atributos_ordenada(cultivos,
        ['clave_catastral', 'regante', 'cultivo', 'superficie_m2', 'es_principal', 'destino'])
    tabla_atributos_ordenada(animales,
        ['clave_catastral', 'regante', 'especie', 'cantidad', 'destino'])

    # ── relaciones ────────────────────────────────────────────────────
    def relacion(rid, nombre, hija, campo_hijo, madre, campo_madre):
        r = QgsRelation()
        r.setId(rid)
        r.setName(nombre)
        r.setReferencingLayer(capas[hija].id())   # tabla hija (muchos)
        r.setReferencedLayer(capas[madre].id())   # tabla madre (uno)
        r.addFieldPair(campo_hijo, campo_madre)
        if not r.isValid():
            print('ERROR: relación inválida', rid)
            sys.exit(3)
        proyecto.relationManager().addRelation(r)
        return r

    relacion('rel_predio_fichas', 'Fichas de este predio',
             'fichas', 'clave_catastral', 'predios_investigados', 'clave_catastral')
    relacion('rel_ficha_cultivos', 'Cultivos de la ficha',
             'cultivos', 'ficha_id', 'fichas', 'ficha_id')
    relacion('rel_ficha_animales', 'Especies pecuarias de la ficha',
             'animales', 'ficha_id', 'fichas', 'ficha_id')
    # autorrelación: los predios adicionales que declaró este regante
    relacion('rel_ficha_adicionales', 'Predios adicionales del regante',
             'fichas', 'ficha_madre_id', 'fichas', 'ficha_id')
    # Estas dos relaciones NO se usan en el formulario del predio (ver mas abajo),
    # pero se dejan declaradas: sirven para analisis en la tabla de atributos y
    # para uniones espaciales, sin costo alguno en la interfaz.
    # Se relacionan por 'clave_predio_principal' y no por 'clave_catastral': ese
    # campo solo se llena cuando la ficha dueña del registro es PRINCIPAL, asi la
    # produccion que otro regante declaro sobre la misma tierra como "predio
    # adicional" (Seccion 7) no se mezcla con la del dueño.
    relacion('rel_predio_cultivos', 'Cultivos del predio',
             'cultivos', 'clave_predio_principal', 'predios_investigados', 'clave_catastral')
    relacion('rel_predio_animales', 'Animales del predio',
             'animales', 'clave_predio_principal', 'predios_investigados', 'clave_catastral')

    # ── formularios ───────────────────────────────────────────────────
    # El formulario del predio NO lleva pestañas de produccion. En los predios
    # comunales (335 con varias fichas principales) esa vista agregaba los
    # cultivos de todos los regantes del poligono y se leia como si fueran del
    # mismo dueño, repitiendo lo que ya se ve dentro de cada ficha. La produccion
    # se consulta donde tiene sentido: en la ficha de cada regante.
    armar_formulario(capas['predios_investigados'], GRUPOS_PREDIO,
                     [('Fichas del predio', 'rel_predio_fichas', 'formulario')])
    armar_formulario(capas['fichas'], GRUPOS_FICHA,
                     [('Cultivos', 'rel_ficha_cultivos', 'tabla'),
                      ('Especies pecuarias', 'rel_ficha_animales', 'tabla'),
                      ('Predios adicionales del regante', 'rel_ficha_adicionales', 'tabla')])

    # ── encuadre inicial: al abrir se ve el área de estudio, sin zoom manual ──
    predios.updateExtents()
    ext = QgsRectangle(predios.extent())
    ext.scale(1.05)
    proyecto.viewSettings().setDefaultViewExtent(
        QgsReferencedRectangle(ext, proyecto.crs()))
    print('encuadre inicial: {:.0f},{:.0f} a {:.0f},{:.0f}'.format(
        ext.xMinimum(), ext.yMinimum(), ext.xMaximum(), ext.yMaximum()))

    if os.path.exists(QGZ):
        os.remove(QGZ)
    if not proyecto.write(QGZ):
        print('ERROR: no se pudo escribir', QGZ)
        sys.exit(4)
    print('proyecto escrito:', QGZ)

    # ── verificación: RELEER el proyecto como lo hará el cliente ──────
    proyecto.clear()
    p2 = QgsProject.instance()
    if not p2.read(QGZ):
        print('ERROR: el proyecto no se puede releer')
        sys.exit(5)
    print('capas al releer:', len(p2.mapLayers()))
    fallo = False
    for r in p2.relationManager().relations().values():
        madre = r.referencedLayer().featureCount() if r.referencedLayer() else -1
        print('  relacion {:<24} valida={} (madre: {} filas)'.format(
            r.id(), r.isValid(), madre))
        fallo |= not r.isValid()

    # la simbología y el encuadre deben haber sobrevivido al guardado
    ve = p2.viewSettings().defaultViewExtent()
    print('  encuadre guardado: {}'.format(
        'si' if not ve.isNull() and ve.width() > 0 else 'NO <-- abriria en blanco'))
    fallo |= ve.isNull() or ve.width() <= 0
    for vl in p2.mapLayers().values():
        rnd = vl.renderer() if hasattr(vl, 'renderer') else None
        if rnd is None:
            continue
        tipo = rnd.type()
        n = (len(rnd.categories()) if tipo == 'categorizedSymbol'
             else len(rnd.rootRule().children()) if tipo == 'RuleRenderer' else 1)
        print('  {:<38} {:<18} {} clases'.format(vl.name(), tipo, n))
        if vl.name() == 'Predios investigados' and (tipo != 'RuleRenderer' or n != 4):
            fallo = True
        # la capa de riego debe salir con sus 4 reglas (una por clase)
        if vl.name().startswith('Condición de riego') and (tipo != 'RuleRenderer' or n != 4):
            fallo = True
    # prueba funcional: el predio de CARRERA con 11 fichas
    for vl in p2.mapLayers().values():
        if vl.name() == 'Predios investigados':
            expr = "\"clave_catastral\" = '1702520500001'"
            from qgis.core import QgsFeatureRequest
            feats = list(vl.getFeatures(QgsFeatureRequest().setFilterExpression(expr)))
            if feats:
                for rid, etiqueta in (('rel_predio_fichas', 'fichas'),
                                     ('rel_predio_cultivos', 'cultivos'),
                                     ('rel_predio_animales', 'animales')):
                    rel = p2.relationManager().relation(rid)
                    hijas = list(rel.getRelatedFeatures(feats[0]))
                    print('  prueba: predio 1702520500001 -> {} {} relacionados'.format(
                        len(hijas), etiqueta))
                    fallo |= len(hijas) == 0
        # prueba del caso "mixto": predio con ficha principal + ficha adicional
        # compartiendo clave. Sus cultivos NO deben mezclarse.
        if vl.name() == 'Predios investigados':
            expr2 = "\"clave_catastral\" = '1702521010056'"
            feats2 = list(vl.getFeatures(QgsFeatureRequest().setFilterExpression(expr2)))
            if feats2:
                relc = p2.relationManager().relation('rel_predio_cultivos')
                cults = list(relc.getRelatedFeatures(feats2[0]))
                regs = {f['regante'] for f in cults}
                print('  prueba mixto: predio 1702521010056 (principal+adicional) -> '
                      '{} cultivos, regantes: {}'.format(len(cults), regs))
                # solo debe aparecer el dueño (SOPALO ACERO CARLOS SEGUNDO), no la
                # adicional (ACERO ACERO MARIA PETRONA)
                fallo |= any('PETRONA' in (r or '') for r in regs)
                fallo |= not any('SOPALO' in (r or '') for r in regs)
    app.exitQgis()
    if fallo:
        print('VERIFICACION FALLIDA')
        sys.exit(6)
    print('VERIFICACION OK')


if __name__ == '__main__':
    main()
