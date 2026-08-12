# -*- coding: utf-8 -*-
"""
Documento de revisión de campo — qué le falta a cada ficha, comunidad por comunidad.

Para qué sirve y en qué se diferencia de lo que ya hay
-----------------------------------------------------
En `docs/` ya existen tres documentos de revisión, y este NO los reemplaza:

* `REVISION-observaciones-con-clave.md` — los predios que un regante mencionó en
  observaciones y hay que regularizar (31 por levantar, 78 por revisar, 28 con
  la clave mal escrita).
* `REVISION-AREAS-fichas-a-verificar.md` — las 148 fichas cuya área declarada no
  cuadra con el polígono del catastro.
* `REPORTE-PENDIENTES.md` — todo lo abierto del proyecto, agrupado por quién lo
  resuelve (dirección, oficina o campo).

Los tres nacen de un análisis concreto. Falta lo más simple y lo que más se
necesita antes de una salida: **qué campos están vacíos, en qué fichas, y en qué
comunidad están**. Eso es lo que arma este documento, leyendo el `data.gpkg` de
QField en el momento en que se ejecuta.

Un campo vacío NO es siempre un pendiente
-----------------------------------------
Es la corrección de fondo del 9 de agosto de 2026. La primera versión contaba
como pendiente todo campo vacío y salían **9.220** filas, cuando el trabajo real
de campo es **801**. La diferencia no era trabajo: eran respuestas legítimas
contadas como omisiones, y con eso se planificaban salidas que no hacían falta.

Las reglas que distinguen «falta preguntar» de «no aplica» las decidió el
cliente (Armando, coordinación) el 9 de agosto de 2026 y están en `REGLAS`, más
abajo. **No se cambian sin consultarle**: cada una tiene detrás una razón de
terreno, no un criterio técnico.

Cómo se organiza y por qué
--------------------------
Por **comunidad**, no por técnico ni por fecha: las salidas de campo se planifican
por zona, y lo que decide si vale la pena ir a un sitio es cuánto queda pendiente
allí. Dentro de cada comunidad van las fichas concretas con su código.

Lo que este documento separa del trabajo de campo
-------------------------------------------------
* **Oficina** — lo que se resuelve sin salir: las fichas sin comunidad se
  asignan por traslape espacial, porque todas tienen coordenadas.
* **En espera** — lo que depende de una decisión de dirección: la tenencia del
  predio y las fichas de ALPAKA, que no son encuestas.
* **Nunca llenado** — `informante`, `consentimiento`: vacíos en el 100 % de las
  fichas. Un campo que nadie llenó nunca no es trabajo de campo pendiente.

Cómo se ejecuta
---------------
Necesita `osgeo`, que en esta máquina solo está en el Python de OSGeo4W::

    "C:\\OSGeo4W\\bin\\python-qgis.bat" -X utf8 scripts/generar_revision_campo.py

(El Python del PATH no trae `osgeo`; el de OSGeo4W no trae `python-docx`. Por eso
`md_a_docx.py` se corre con el otro.)

Salida
------
docs/REVISION-CAMPO.md
"""
import os
import sys
from datetime import datetime

from osgeo import ogr

ogr.UseExceptions()

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
GPKG = os.path.join(os.path.expanduser('~'), 'QField', 'cloud',
                    'porotog_levantamiento_offline', 'data.gpkg')
SALIDA = os.path.join(BASE, 'docs', 'REVISION-CAMPO.md')

CAPA = 'Fichas_Predios_880eb10d_d887_4fc6_99a2_8af3ac63877e'

# Una ficha es «principal» si no es hija. Las hijas (Sección 7) heredan del
# predio madre y no se les exige la encuesta completa.
PRINCIPALES = ("(es_ficha_hija IS NULL OR es_ficha_hija NOT IN "
               "('1','true','SI','Si','si'))")

VACIO = "({0} IS NULL OR TRIM(CAST({0} AS TEXT))='' OR CAST({0} AS TEXT) IN ('None','NULL'))"


def vacio_num(campo):
    """Para campos numéricos, el 0 también cuenta como sin dato."""
    return "({0} IS NULL OR CAST({0} AS REAL)=0)".format(campo)


def lleno(campo):
    return "NOT " + VACIO.format(campo)


def lleno_num(campo):
    """Lo contrario de `vacio_num`: para un número, 0 no es dato.

    Ojo: no vale usar `lleno()` con un campo numérico. Un 0.0 pasa el filtro de
    texto (`CAST(0.0 AS TEXT)` es '0.0', que no está vacío) y contaría como si
    tuviera dato.
    """
    return "({0} IS NOT NULL AND CAST({0} AS REAL)<>0)".format(campo)


# ─────────────────────────────────────────────────────────────────────────────
#  REGLAS DE «NO APLICA» — decididas por el cliente el 9 de agosto de 2026
#  ═══════════════════════════════════════════════════════════════════════
#  NO CAMBIAR NINGUNA SIN CONSULTAR CON EL CLIENTE. Cada una responde a algo
#  que pasa en terreno, y quitarla vuelve a inflar el trabajo de campo con
#  fichas que están bien.
#
#  1. FOTO DEL PREDIO — fuera del reporte. «Esa condición se eliminó desde el
#     inicio» (textual). Eran 3.413 pendientes que nunca existieron.
#
#  2. VIVIENDA (agua, luz, material) — si `material_construccion` está vacío,
#     NO HAY CONSTRUCCIÓN, y entonces los tres campos vacíos son la respuesta
#     correcta. Solo es pendiente la ficha «a medias»: material declarado pero
#     sin agua o sin luz.
#     Por qué el material y no un «tiene_construccion»: ese campo existe en la
#     ficha web (Firestore) pero NO en el `data.gpkg` ni en el `.qgs` de QField,
#     que es de donde sale este documento. Se comprobó que sirve de indicador:
#     de las 1.559 principales sin material, NINGUNA tiene `material_constr_otro`
#     lleno, así que no hay construcciones escondidas en el campo «otro».
#
#  3. ÁREA DE RIEGO en 0 — no es pendiente si `area_sin_riego` tiene valor: el
#     predio existe y está medido, simplemente no se riega. De 141, hay 137 así.
#
#  4. CAUDAL vacío — no es pendiente de campo si la ficha tiene comunidad: el
#     caudal se hereda de la comuna, no se mide ficha a ficha
#     (ver `docs/METODOLOGIA-CAUDAL.md`). De 168, hay 138 con comunidad.
#
#  5. COMUNIDAD vacía — no es trabajo de campo: se resuelve en oficina por
#     traslape espacial. Va en su propia sección.
#
#  6. CÉDULA y TELÉFONO — se mantienen como pendientes. «Dejar el dato que se
#     reporta que falta, para cédula y otros campos que no se pudo obtener»
#     (textual).
#
#  7. TENENCIA del predio — en espera: el cliente la revisa después de la
#     depuración. Va en su propia sección, no en la ruta de campo.
# ─────────────────────────────────────────────────────────────────────────────

CON_CONSTRUCCION = lleno('material_construccion')

# (campo, etiqueta, condicion, ¿se lista ficha por ficha?)
#
# Las etiquetas son parte del contrato con el Excel: la nota que escribe el
# revisor se guarda como «id|etiqueta». Cambiar un texto de aquí le borra las
# notas a ese bloque en la siguiente regeneración.
PENDIENTES = [
    ('cedula', 'Sin cédula', VACIO.format('cedula'), True),
    ('telefono_celular', 'Sin teléfono', VACIO.format('telefono_celular'), True),
    ('nivel_instruccion', 'Sin nivel de instrucción',
     VACIO.format('nivel_instruccion'), True),
    # regla 4: solo si tampoco hay comunidad de la que heredarlo
    ('caudal_valor', 'Sin caudal registrado',
     '{} AND {}'.format(vacio_num('caudal_valor'), VACIO.format('comunidad')), True),
    # regla 3: solo si tampoco está medida el área sin riego
    ('area_riego', 'Sin área de riego',
     '{} AND {}'.format(vacio_num('area_riego'), vacio_num('area_sin_riego')), True),
    # regla 2: solo las fichas «a medias», con construcción declarada
    ('agua_consumo', 'Sin agua de consumo',
     '{} AND {}'.format(CON_CONSTRUCCION, VACIO.format('agua_consumo')), True),
    ('energia_electrica', 'Sin energía eléctrica',
     '{} AND {}'.format(CON_CONSTRUCCION, VACIO.format('energia_electrica')), True),
]

# Cómo se contaba antes del 9-ago-2026: todo campo vacío era un pendiente.
# Se conserva para poder explicar la diferencia en el propio documento. Sin
# esto, la caída de 9.220 a 801 parece que alguien borró trabajo.
CRITERIO_ANTERIOR = [
    VACIO.format('comunidad'), VACIO.format('cedula'),
    vacio_num('caudal_valor'), VACIO.format('tenencia_predio'),
    VACIO.format('nivel_instruccion'), vacio_num('area_riego'),
    VACIO.format('agua_consumo'), VACIO.format('energia_electrica'),
    VACIO.format('material_construccion'), VACIO.format('telefono_celular'),
    VACIO.format('foto_predio'),
]

# El descuento de cada regla, en datos (no en fichas): una ficha a la que se le
# dejaron de pedir dos cosas descuenta dos. Así la resta cuadra con el total
# anterior, y `main()` lo comprueba en cada ejecución.
DESCUENTOS = [
    ('Foto del predio', 'regla 1',
     [VACIO.format('foto_predio')],
     'La condición se eliminó desde el inicio del levantamiento.'),
    ('Predios sin construcción', 'regla 2',
     [VACIO.format('material_construccion'),
      '{} AND {}'.format(VACIO.format('material_construccion'),
                         VACIO.format('agua_consumo')),
      '{} AND {}'.format(VACIO.format('material_construccion'),
                         VACIO.format('energia_electrica'))],
     'Sin material de construcción no hay vivienda: agua y luz vacías son la '
     'respuesta correcta, no una omisión. El material deja de pedirse porque '
     'es el indicador, no un dato faltante.'),
    ('Predio medido que no se riega', 'regla 3',
     ['{} AND {}'.format(vacio_num('area_riego'), lleno_num('area_sin_riego'))],
     'El área sin riego está medida: el predio existe y no se riega. No falta '
     'ir a medirlo.'),
    ('Caudal heredado de la comuna', 'regla 4',
     ['{} AND {}'.format(vacio_num('caudal_valor'), lleno('comunidad'))],
     'El caudal no se mide ficha por ficha, se hereda de la comuna '
     '(`METODOLOGIA-CAUDAL.md`).'),
    ('Comunidad — se resuelve en oficina', 'regla 5',
     [VACIO.format('comunidad')],
     'Se asigna por traslape espacial; todas tienen coordenadas.'),
    ('Tenencia — en espera del cliente', 'regla 7',
     [VACIO.format('tenencia_predio')],
     'La coordinación las revisa después de la depuración.'),
]

# Lo que sí falta pero no lo resuelve el técnico en campo.
OFICINA = ('comunidad', 'Sin comunidad asignada', VACIO.format('comunidad'))
EN_ESPERA = ('tenencia_predio', 'Sin tenencia del predio',
             VACIO.format('tenencia_predio'))

# Aclaraciones que van bajo el título de un bloque, cuando el nombre del campo
# se presta a que alguien haga el trabajo equivocado.
NOTA_BLOQUE = {
    'caudal_valor':
        'No hay que ir a medir ningún caudal. Son las mismas fichas de «Se '
        'resuelve en oficina»: al asignarles comunidad heredan el caudal de la '
        'comuna y este bloque se vacía solo.',
    'agua_consumo':
        'Solo las fichas con material de construcción declarado. Donde no hay '
        'construcción, el campo vacío es la respuesta correcta.',
    'energia_electrica':
        'Solo las fichas con material de construcción declarado. Donde no hay '
        'construcción, el campo vacío es la respuesta correcta.',
    'area_riego':
        'Solo las que tampoco tienen medida el área sin riego. Si el predio '
        'está medido y no se riega, ya está completo.',
}

LIMITE_LISTADO = 60      # fichas por bloque antes de cortar el listado

# Comunidades cuyas fichas NO son encuestas de campo. Mandar a alguien a
# «completarlas» seria trabajo perdido, y es justo lo que sugeriria una lista de
# campos vacios: aparecen al 100 % en todo porque nunca fueron una entrevista.
# Desde el 9-ago-2026 no se cuentan como pendiente de campo (decision de JAVIKO):
# quedan registradas aparte, a la espera de que la direccion decida que se hace.
NO_SON_ENCUESTAS = {
    'ALPAKA': ('son lotes de fraccionamiento cargados en bloque, no fichas '
               'levantadas en campo (ver REPORTE-PENDIENTES.md)'),
}

# Filtro SQL que deja fuera esas comunidades.
ES_ENCUESTA = "UPPER(TRIM(COALESCE(comunidad,''))) NOT IN ({})".format(
    ', '.join("'{}'".format(c) for c in sorted(NO_SON_ENCUESTAS)))

# El universo del trabajo de campo: fichas principales que además son encuestas.
DE_CAMPO = '{} AND {}'.format(PRINCIPALES, ES_ENCUESTA)


def num(n):
    """Separador de miles en español: 6.831, no 6,831."""
    return '{:,}'.format(int(n)).replace(',', '.')


def consultar(ds, sql):
    res = ds.ExecuteSQL(sql, dialect='SQLITE')
    filas = [[ft.GetField(i) for i in range(ft.GetFieldCount())] for ft in res]
    ds.ReleaseResultSet(res)
    return filas


def contar(ds, t, cond, universo=None):
    return consultar(ds, "SELECT COUNT(*) FROM {} WHERE {} AND {}"
                     .format(t, cond, universo or DE_CAMPO))[0][0]


def fichas_de(ds, t, cond, universo=None, extra=''):
    """Las fichas que cumplen una condición, ordenadas por comunidad y clave."""
    return consultar(ds,
        "SELECT COALESCE(NULLIF(TRIM(comunidad),''),'(sin comunidad)') com, "
        "COALESCE(clave_catastral,'') clave, "
        "TRIM(COALESCE(apellidos,'') || ' ' || COALESCE(nombres,'')) nombre, "
        "COALESCE(cedula,'') ced, COALESCE(creado_por,'') tec{extra} "
        "FROM {t} WHERE {cond} AND {uni} ORDER BY com, clave"
        .format(t=t, cond=cond, uni=universo or DE_CAMPO, extra=extra))


def main():
    print("=" * 74)
    print(" DOCUMENTO DE REVISION DE CAMPO")
    print("=" * 74)

    if not os.path.exists(GPKG):
        print("ERROR: no se encuentra el data.gpkg de QField:\n  {}".format(GPKG))
        return 1

    ds = ogr.Open(GPKG, 0)          # SOLO LECTURA: es la fuente de campo
    if ds is None:
        print("ERROR: no se pudo abrir el GeoPackage.")
        return 1
    t = '"{}"'.format(CAPA)

    total = consultar(ds, "SELECT COUNT(*) FROM {}".format(t))[0][0]
    principales = consultar(ds, "SELECT COUNT(*) FROM {} WHERE {}"
                            .format(t, PRINCIPALES))[0][0]
    hijas = total - principales
    encuestas = consultar(ds, "SELECT COUNT(*) FROM {} WHERE {}"
                          .format(t, DE_CAMPO))[0][0]
    corte = consultar(ds, "SELECT MAX(fecha_creacion) FROM {}".format(t))[0][0]
    corte = (corte or '')[:10]

    print("\n  fichas: {:,} ({:,} principales, {:,} hijas) — corte {}"
          .format(total, principales, hijas, corte))

    L = []
    w = L.append
    w("# Revisión de campo — Padrón Guanguilquí–Porotog\n")
    w("**Última ficha registrada:** {}  ".format(corte))
    w("**Documento generado:** {}  ".format(datetime.now().strftime('%d/%m/%Y')))
    w("**Para:** equipo técnico de campo\n")
    w("Este documento sale de leer el `data.gpkg` de QField tal como está hoy. "
      "Dice qué campos quedaron vacíos, en qué fichas y en qué comunidad, para "
      "poder planificar la salida por zona.\n")
    w("> **Un campo vacío no siempre es un pendiente.** Desde el 9 de agosto de "
      "2026 este documento aplica las reglas de «no aplica» que acordó la "
      "coordinación del proyecto: un predio sin construcción no tiene por qué "
      "declarar agua ni luz, un predio medido y sin riego no tiene área de "
      "riego, y el caudal se hereda de la comuna. Lo que dejó de contarse y por "
      "qué está al final, en «Qué ya no se cuenta como pendiente».\n")
    w("No repite lo que ya está en otros documentos. Antes de salir a campo, "
      "revisar también:\n")
    w("| Documento | Qué contiene |")
    w("|---|---|")
    w("| `REVISION-observaciones-con-clave.md` | Predios que el regante mencionó "
      "en observaciones: 31 por levantar, 78 por revisar, 28 con la clave mal escrita |")
    w("| `REVISION-AREAS-fichas-a-verificar.md` | 148 fichas cuya área declarada "
      "no cuadra con el polígono del catastro |")
    w("| `REPORTE-PENDIENTES.md` | Todo lo abierto del proyecto, por responsable |")
    w("")
    w("---\n")
    w("## Cómo usar esta lista\n")
    w("1. Busca tu comunidad en la tabla de abajo y mira cuánto queda pendiente ahí.")
    w("2. En el detalle de cada comunidad tienes las fichas por **clave catastral** "
      "y nombre del regante: búscalas en QField por la clave catastral.")
    w("")
    w("> ⚠️ **No busques por el «código» de la ficha.** El campo `codigo_final` no "
      "identifica nada: vale `S-C-P001` en 5.529 de las 6.831 fichas, porque es el "
      "valor por defecto del formulario y casi nunca se cambió. La clave catastral "
      "sí está en todas las fichas y es la que sirve para encontrarlas.\n")
    w("3. Completa lo que falte **en la ficha existente**. No crees una ficha nueva: "
      "se duplicaría el predio.")
    w("4. Si el dato no se puede obtener (el regante no está, no quiere darlo, el "
      "predio ya no se riega), anótalo en **observaciones** de la propia ficha. Un "
      "campo vacío no distingue entre «falta preguntar» y «no aplica»; una nota sí.\n")
    w("---\n")
    w("## Resumen\n")
    w("Sobre las **{} fichas principales** que son encuestas de campo "
      "(de {} fichas en total: {} son hijas de la Sección 7 y {} son de ALPAKA, "
      "que no son encuestas).\n"
      .format(num(encuestas), num(total), num(hijas), num(principales - encuestas)))
    w("| Qué falta | Fichas | Cómo se aborda |")
    w("|---|---:|---|")

    conteos = {}
    total_campo = 0
    for campo, etq, cond, listar in PENDIENTES:
        n_p = contar(ds, t, cond)
        conteos[campo] = n_p
        total_campo += n_p
        if n_p:
            w("| {} | {} | ficha por ficha |".format(etq, num(n_p)))
        print("      {:32s} {:5,}".format(etq, n_p))

    w("| **Total de trabajo de campo** | **{}** | |".format(num(total_campo)))
    w("")
    w("Cada fila de la tabla es un dato faltante, no una ficha: una misma ficha "
      "puede aparecer en dos bloques.\n")
    w("> Las **fichas hijas** son los predios adicionales de la Sección 7: heredan "
      "los datos del predio madre, así que a ellas no se les exige la encuesta "
      "completa. Por eso este documento mira solo las principales.\n")
    w("---\n")

    # ── pendientes puntuales, por comunidad ──
    w("## Pendientes de campo\n")
    w("Se resuelven ficha por ficha, en QField. Van agrupados por comunidad para "
      "poder armar la ruta.\n")

    for campo, etq, cond, listar in PENDIENTES:
        if not listar or not conteos[campo]:
            continue
        w("### {} — {} fichas\n".format(etq, num(conteos[campo])))
        if campo in NOTA_BLOQUE:
            w("> {}\n".format(NOTA_BLOQUE[campo]))

        por_com = {}
        for com, clave, nombre, ced, tec in fichas_de(ds, t, cond):
            por_com.setdefault(com, []).append((clave, nombre, ced, tec))

        for com in sorted(por_com):
            fichas = por_com[com]
            w("**{}** — {} ficha{}\n".format(
                com, num(len(fichas)), 's' if len(fichas) != 1 else ''))
            w("| Clave catastral | Regante | Cédula | Levantó |")
            w("|---|---|---|---|")
            for clave, nombre, ced, tec in fichas[:LIMITE_LISTADO]:
                w("| {} | {} | {} | {} |".format(clave or '—', nombre or '—',
                                                 ced or '—', tec or '—'))
            if len(fichas) > LIMITE_LISTADO:
                w("| … | _y {} fichas más en esta comunidad_ | | |"
                  .format(num(len(fichas) - LIMITE_LISTADO)))
            w("")
        w("---\n")

    # ── dónde se concentra el trabajo ──
    n_ofi = contar(ds, t, OFICINA[2], PRINCIPALES)
    w("## Dónde se concentra el trabajo\n")
    w("Para decidir la ruta: qué comunidades justifican una salida y cuáles se "
      "resuelven aprovechando otra.\n")

    columnas = [
        ('Contacto', ['cedula', 'telefono_celular']),
        ('Encuesta', ['nivel_instruccion', 'caudal_valor', 'area_riego']),
        ('Vivienda', ['agua_consumo', 'energia_electrica']),
    ]
    campo_a_cond = {c: cond for c, _, cond, _ in PENDIENTES}

    def suma_datos(condiciones):
        """Cuenta datos faltantes, no fichas: una ficha a la que le faltan dos
        cosas suma dos. Así las tres columnas suman exactamente el total."""
        return ' + '.join("SUM(CASE WHEN {} THEN 1 ELSE 0 END)".format(c)
                          for c in condiciones)

    sel = ["COALESCE(NULLIF(TRIM(comunidad),''),'(sin comunidad)') com",
           "COUNT(*) total"]
    for _, campos in columnas:
        sel.append(suma_datos([campo_a_cond[c] for c in campos]))
    # fichas con al menos un pendiente: aquí sí se cuentan fichas
    cualquiera = ' OR '.join(cond for _, _, cond, _ in PENDIENTES)
    sel.append("SUM(CASE WHEN {} THEN 1 ELSE 0 END)".format(cualquiera))
    sel.append(suma_datos([cond for _, _, cond, _ in PENDIENTES]))

    filas = consultar(ds, "SELECT {} FROM {} WHERE {} GROUP BY com "
                          "ORDER BY 7 DESC, 2 DESC".format(', '.join(sel), t, DE_CAMPO))

    # Esta tabla es con la que se arma la ruta: en el Word tiene que salir
    # entera aunque se pase de `--max-filas` (ver `md_a_docx.py`).
    w("<!-- tabla-completa -->")
    w("| Comunidad | Fichas | Con pendientes | Contacto | Encuesta | Vivienda | Datos por completar |")
    w("|---|---:|---:|---:|---:|---:|---:|")
    for com, tot, contacto, enc, viv, con_pend, datos in filas:
        if not datos:
            continue
        pct = 100.0 * con_pend / tot if tot else 0
        marca = '🔴' if pct >= 50 else ('🟠' if pct >= 20 else '🟡')
        w("| {} | {} | {} {} ({:.0f} %) | {} | {} | {} | {} |"
          .format(com, num(tot), marca, num(con_pend), pct,
                  num(contacto), num(enc), num(viv), num(datos)))
    w("")
    w("«Fichas» es cuántas hay en la comunidad y «con pendientes» a cuántas les "
      "falta algo; las dos son **fichas**. Contacto, Encuesta y Vivienda cuentan "
      "**datos** —una ficha a la que le faltan dos cosas suma dos— y por eso "
      "suman exactamente la última columna.\n")
    w("> La fila **(sin comunidad)** son las {} fichas de la sección siguiente. "
      "Todavía no se pueden asignar a ninguna ruta: primero hay que resolverlas "
      "en oficina. Al hacerlo se caen solos los {} pendientes de caudal, porque "
      "el caudal se hereda de la comuna.\n".format(num(n_ofi), num(conteos['caudal_valor'])))
    w("---\n")

    # ── oficina ──
    con_coord = contar(ds, t, "{} AND coord_x_utm IS NOT NULL AND coord_x_utm <> 0"
                       .format(OFICINA[2]), PRINCIPALES)
    w("## Se resuelve en oficina, no en campo\n")
    w("**{} fichas principales sin comunidad asignada.** No hay que ir a "
      "preguntarle a nadie: **{} de las {} tienen coordenadas**, así que la "
      "comunidad sale de un cruce espacial — el punto de la ficha dentro del "
      "polígono de la capa de comunidades.\n"
      .format(num(n_ofi), num(con_coord), num(n_ofi)))
    w("El cruce ya está resuelto en código: `scripts/represa/06_capas_padron.py` "
      "hace exactamente eso (punto dentro de polígono de `sectores.geojson`) y "
      "sirve de referencia para asignarlas.\n")
    w("> ⚠️ El cruce tiene que ser **espacial, nunca por nombre**. Hay nombres "
      "iguales que designan sitios distintos: la comuna «Asociación Porotog» del "
      "shapefile oficial corresponde a nuestra *Asociación 17 de Junio*, mientras "
      "que nuestra *Asociación Porotog* cae en «San Vicente de Porotog».\n")

    filas = fichas_de(ds, t, OFICINA[2], PRINCIPALES,
                      extra=", COALESCE(coord_x_utm,0) x, COALESCE(coord_y_utm,0) y")
    w("| Clave catastral | Regante | Cédula | Levantó | X (UTM 17S) | Y (UTM 17S) |")
    w("|---|---|---|---|---:|---:|")
    for _com, clave, nombre, ced, tec, x, y in filas[:LIMITE_LISTADO]:
        w("| {} | {} | {} | {} | {} | {} |"
          .format(clave or '—', nombre or '—', ced or '—', tec or '—',
                  '{:,.0f}'.format(x).replace(',', '.') if x else '— sin coordenada',
                  '{:,.0f}'.format(y).replace(',', '.') if y else '—'))
    if len(filas) > LIMITE_LISTADO:
        w("| … | _y {} fichas más_ | | | | |"
          .format(num(len(filas) - LIMITE_LISTADO)))
    w("")
    w("---\n")

    # ── en espera de una decisión ──
    w("## En espera de una decisión\n")
    w("No entran en la ruta de campo hasta que la coordinación del proyecto "
      "resuelva qué hacer con ellas.\n")

    n_ten = contar(ds, t, EN_ESPERA[2], PRINCIPALES)
    w("### Tenencia del predio — {} fichas\n".format(num(n_ten)))
    w("Los datos de escritura quedan en espera: el cliente los revisa **después** "
      "de la depuración, para no mandar a preguntar dos veces.\n")

    for com, mot in sorted(NO_SON_ENCUESTAS.items()):
        n_f = consultar(ds, "SELECT COUNT(*) FROM {} WHERE {} AND "
                            "UPPER(TRIM(COALESCE(comunidad,'')))='{}'"
                        .format(t, PRINCIPALES, com))[0][0]
        detalle = []
        n_datos = 0
        for campo, etq, cond, _ in PENDIENTES:
            n_c = consultar(ds, "SELECT COUNT(*) FROM {} WHERE {} AND {} AND "
                                "UPPER(TRIM(COALESCE(comunidad,'')))='{}'"
                            .format(t, cond, PRINCIPALES, com))[0][0]
            if n_c:
                detalle.append((etq, n_c))
                n_datos += n_c
        w("### {} — {} fichas, {} datos vacíos\n"
          .format(com, num(n_f), num(n_datos)))
        w("**No salir a completarlas.** No están vacías por descuido: {}. Contarlas "
          "como pendiente de campo mandaría a los técnicos a levantar encuestas "
          "que nunca existieron, así que desde el 9 de agosto de 2026 quedan fuera "
          "del conteo y registradas aquí.\n".format(mot))
        if detalle:
            w("| Qué está vacío | Fichas |")
            w("|---|---:|")
            for etq, n_c in detalle:
                w("| {} | {} |".format(etq, num(n_c)))
            w("")
        w("Antes de tocarlas hace falta una decisión de dirección sobre qué se "
          "hace con ellas.\n")

    w("---\n")

    # ── qué ya no se cuenta ──
    anterior = sum(contar(ds, t, c, PRINCIPALES) for c in CRITERIO_ANTERIOR)
    w("## Qué ya no se cuenta como pendiente\n")
    w("Las reglas las decidió la coordinación del proyecto el **9 de agosto de "
      "2026**. Esta tabla existe para que quede claro de dónde sale la "
      "diferencia con las versiones anteriores del documento, que contaban como "
      "pendiente todo campo vacío. Cada línea es un descuento en **datos**: una "
      "ficha a la que se le dejaron de pedir dos cosas descuenta dos.\n")
    w("| | Datos | Por qué |")
    w("|---|---:|---|")
    w("| **Como se contaba antes** | **{}** | Todo campo vacío era un pendiente |"
      .format(num(anterior)))
    quitado = 0
    for etq, regla, condiciones, motivo in DESCUENTOS:
        n_q = sum(contar(ds, t, c, PRINCIPALES) for c in condiciones)
        quitado += n_q
        w("| − {} _({})_ | −{} | {} |".format(etq, regla, num(n_q), motivo))
    n_alpaka = sum(
        consultar(ds, "SELECT COUNT(*) FROM {} WHERE {} AND {} AND NOT {}"
                  .format(t, cond, PRINCIPALES, ES_ENCUESTA))[0][0]
        for _, _, cond, _ in PENDIENTES)
    quitado += n_alpaka
    w("| − ALPAKA — en espera de dirección | −{} | No son encuestas: lotes de "
      "fraccionamiento cargados en bloque |".format(num(n_alpaka)))
    w("| **Trabajo de campo real** | **{}** | Lo que sí hay que ir a preguntar |"
      .format(num(total_campo)))
    w("")

    # Red de seguridad: si mañana alguien toca una regla y la resta deja de
    # cuadrar, el documento estaría explicando una diferencia que no existe.
    if anterior - quitado != total_campo:
        w("> ⚠️ **Aviso para quien mantiene este documento:** la resta no cuadra "
          "({} − {} = {}, pero el trabajo de campo da {}). Alguna regla cambió "
          "sin actualizar la tabla de descuentos en `generar_revision_campo.py`.\n"
          .format(num(anterior), num(quitado), num(anterior - quitado),
                  num(total_campo)))
        print("\n  *** AVISO: la reconciliacion no cuadra: {} - {} = {} != {}"
              .format(anterior, quitado, anterior - quitado, total_campo))

    w("Ninguna ficha se borró ni se dio por buena: lo que cambió es qué cuenta "
      "como pendiente. Los datos descontados siguen vacíos en el `data.gpkg`, y "
      "los que dependen de una decisión están listados arriba, en «Se resuelve "
      "en oficina» y «En espera de una decisión».\n")
    w("> Antes de aplicar la regla 2 se comprobó que el material de construcción "
      "sirve de indicador: de las fichas principales sin material, **ninguna** "
      "tiene lleno el campo `material_constr_otro`. No hay viviendas escondidas "
      "detrás de un «otro material».\n")
    w("**Cédula y teléfono se mantienen** como pendientes aunque muchos no se "
      "puedan obtener: la coordinación pidió expresamente dejar constancia del "
      "dato que falta.\n")
    w("---\n")

    # ── campos que nadie llenó nunca ──
    w("## Para la dirección del proyecto, no para campo\n")
    nunca = []
    for campo, etq in [('informante', 'Informante'),
                       ('consentimiento_inform', 'Consentimiento informado')]:
        n = consultar(ds, "SELECT COUNT(*) FROM {} WHERE {}"
                      .format(t, VACIO.format(campo)))[0][0]
        if n >= total:
            nunca.append(etq)
    if nunca:
        w("Estos campos están vacíos en **las {} fichas, sin excepción**: "
          "{}.\n".format(num(total), ', '.join('`%s`' % x for x in nunca)))
        w("Un campo que no se llenó ni una sola vez no es trabajo pendiente de "
          "campo: o no está en el formulario de QField, o se decidió no usarlo. "
          "Pedir que se completen ahora significaría volver a visitar a los "
          "{} regantes. **Es una decisión de dirección**, y conviene tomarla "
          "antes de que alguien los dé por perdidos en el informe.\n"
          .format(num(principales)))
    else:
        w("_Sin campos en esta situación._\n")

    w("---\n")
    w("## Casos que no se arreglan llenando un campo\n")
    w("Están documentados en `REPORTE-PENDIENTES.md`; se repiten aquí porque "
      "tocan trabajo de campo:\n")
    w("- **Dos fichas con el mismo identificador de QField** (José Rafael Coyago "
      "Chicaiza y Marco Rafael Coyago Alquinga, mismo predio en Santa Marianita "
      "de Pingulmí). Hay que confirmar en campo si son dos copropietarios o una "
      "ficha duplicada, y cuál queda.")
    w("- **491 fichas de ALPAKA** con tarifas de 672 y 308 USD mensuales, cuando "
      "la mediana del sistema es 3 USD. Están excluidas de los informes hasta "
      "que se confirme si es error de digitación o el dato es real.")
    w("- **Granja avícola de Asociación Rosalía**: seis titulares declaran 10.000 "
      "gallinas cada uno sobre el mismo predio. 60.000 aves excluidas.")
    w("- **Avellaneda, Hernán Timpe y Hacienda San Francisco**: su caudal coincide "
      "exacto con el de su comunidad de origen. Si tuvieran llave propia, el "
      "sistema pasaría de 950 a 1.021 l/s.\n")

    ds = None

    os.makedirs(os.path.dirname(SALIDA), exist_ok=True)
    with open(SALIDA, 'w', encoding='utf-8') as f:
        f.write('\n'.join(L))

    print("\n  trabajo de campo        : {:,} datos".format(total_campo))
    print("  se resuelve en oficina  : {:,} fichas sin comunidad".format(n_ofi))
    print("  en espera de decision   : {:,} de tenencia".format(n_ten))
    print("  ya no cuenta como pendiente: {:,} datos".format(quitado))
    print("\n  guardado: {} ({:,.0f} KB)"
          .format(os.path.relpath(SALIDA, BASE), os.path.getsize(SALIDA) / 1024))
    print("=" * 74)
    return 0


if __name__ == '__main__':
    sys.exit(main())
