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

Cómo se organiza y por qué
--------------------------
Por **comunidad**, no por técnico ni por fecha: las salidas de campo se planifican
por zona, y lo que decide si vale la pena ir a un sitio es cuánto queda pendiente
allí. Dentro de cada comunidad van las fichas concretas con su código.

Los pendientes se separan en dos clases, porque no cuestan lo mismo:

* **Puntuales** (comunidad, cédula, caudal, tenencia…): son pocos y se arreglan
  ficha por ficha. Van listados uno a uno, con nombre y código.
* **Masivos** (servicios básicos): son miles y listarlos no ayudaría a nadie. Van
  como recuento por comunidad, que es lo que sirve para decidir la ruta.

Lo que este documento NO pide
-----------------------------
Hay campos vacíos en el 100 % de las fichas (`informante`, `consentimiento`).
Un campo que nadie llenó nunca no es trabajo de campo pendiente: es un campo que
no está en el formulario o que se decidió no usar. Aparece señalado como
pregunta para la dirección del proyecto, no como tarea para los técnicos.

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


# (campo, etiqueta, condicion, ¿se lista ficha por ficha?)
PENDIENTES = [
    ('comunidad', 'Sin comunidad asignada', VACIO.format('comunidad'), True),
    ('cedula', 'Sin cédula', VACIO.format('cedula'), True),
    ('caudal_valor', 'Sin caudal registrado', vacio_num('caudal_valor'), True),
    ('tenencia_predio', 'Sin tenencia del predio', VACIO.format('tenencia_predio'), True),
    ('nivel_instruccion', 'Sin nivel de instrucción', VACIO.format('nivel_instruccion'), True),
    ('area_riego', 'Sin área de riego', vacio_num('area_riego'), True),
    ('agua_consumo', 'Sin agua de consumo', VACIO.format('agua_consumo'), False),
    ('energia_electrica', 'Sin energía eléctrica', VACIO.format('energia_electrica'), False),
    ('material_construccion', 'Sin material de construcción',
     VACIO.format('material_construccion'), False),
    ('telefono_celular', 'Sin teléfono', VACIO.format('telefono_celular'), False),
    ('foto_predio', 'Sin foto del predio', VACIO.format('foto_predio'), False),
]

LIMITE_LISTADO = 60      # fichas por bloque antes de cortar el listado

# Comunidades cuyas fichas NO son encuestas de campo. Mandar a alguien a
# «completarlas» seria trabajo perdido, y es justo lo que sugeriria una lista de
# campos vacios: aparecen al 100 % en todo porque nunca fueron una entrevista.
NO_SON_ENCUESTAS = {
    'ALPAKA': ('son lotes de fraccionamiento cargados en bloque, no fichas '
               'levantadas en campo (ver REPORTE-PENDIENTES.md)'),
}


def num(n):
    """Separador de miles en español: 6.831, no 6,831."""
    return '{:,}'.format(int(n)).replace(',', '.')


def consultar(ds, sql):
    res = ds.ExecuteSQL(sql, dialect='SQLITE')
    filas = [[ft.GetField(i) for i in range(ft.GetFieldCount())] for ft in res]
    ds.ReleaseResultSet(res)
    return filas


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
    w("2. En el detalle de cada comunidad tienes las fichas con su **código** y el "
      "nombre del regante: búscalas en QField por ese código.")
    w("3. Completa lo que falte **en la ficha existente**. No crees una ficha nueva: "
      "se duplicaría el predio.")
    w("4. Si el dato no se puede obtener (el regante no está, no quiere darlo, el "
      "predio ya no se riega), anótalo en **observaciones** de la propia ficha. Un "
      "campo vacío no distingue entre «falta preguntar» y «no aplica»; una nota sí.\n")
    w("---\n")
    w("## Resumen\n")
    w("| Qué falta | En todas las fichas | Solo principales | Cómo se aborda |")
    w("|---|---:|---:|---|")

    conteos = {}
    for campo, etq, cond, listar in PENDIENTES:
        n_t = consultar(ds, "SELECT COUNT(*) FROM {} WHERE {}".format(t, cond))[0][0]
        n_p = consultar(ds, "SELECT COUNT(*) FROM {} WHERE {} AND {}"
                        .format(t, cond, PRINCIPALES))[0][0]
        conteos[campo] = (n_t, n_p)
        modo = 'ficha por ficha' if listar else 'por comunidad'
        if n_t:
            w("| {} | {} | {} | {} |".format(etq, num(n_t), num(n_p), modo))
        print("      {:32s} {:5,} ({:,} principales)".format(etq, n_t, n_p))

    w("")
    w("> Las **fichas hijas** son los predios adicionales de la Sección 7: heredan "
      "los datos del predio madre, así que a ellas no se les exige la encuesta "
      "completa. Por eso importa sobre todo la columna de principales.\n")
    w("---\n")

    # ── pendientes puntuales, por comunidad ──
    w("## Pendientes puntuales\n")
    w("Son pocos y se resuelven ficha por ficha. Van agrupados por comunidad.\n")

    for campo, etq, cond, listar in PENDIENTES:
        if not listar or not conteos[campo][1]:
            continue
        w("### {} — {} fichas principales\n".format(etq, num(conteos[campo][1])))

        filas = consultar(ds,
            "SELECT COALESCE(NULLIF(TRIM(comunidad),''),'(sin comunidad)') com, "
            "COALESCE(codigo_final,'') cod, "
            "TRIM(COALESCE(apellidos,'') || ' ' || COALESCE(nombres,'')) nombre, "
            "COALESCE(clave_catastral,'') clave, COALESCE(creado_por,'') tec "
            "FROM {} WHERE {} AND {} ORDER BY com, cod"
            .format(t, cond, PRINCIPALES))

        por_com = {}
        for com, cod, nombre, clave, tec in filas:
            por_com.setdefault(com, []).append((cod, nombre, clave, tec))

        for com in sorted(por_com):
            fichas = por_com[com]
            aviso = NO_SON_ENCUESTAS.get(com.strip().upper())
            w("**{}**{} — {} ficha{}\n".format(
                com, ' ⚠️' if aviso else '', num(len(fichas)),
                's' if len(fichas) != 1 else ''))
            if aviso:
                # la misma advertencia que en la tabla por comunidad: aquí también
                # hay que verla, o alguien sale a buscar fichas que no son encuestas
                w("> ⚠️ {}. Consultar con dirección antes de intervenirlas.\n"
                  .format(aviso[0].upper() + aviso[1:]))
            w("| Código | Regante | Clave catastral | Levantó |")
            w("|---|---|---|---|")
            for cod, nombre, clave, tec in fichas[:LIMITE_LISTADO]:
                w("| {} | {} | {} | {} |".format(cod or '—', nombre or '—',
                                                 clave or '—', tec or '—'))
            if len(fichas) > LIMITE_LISTADO:
                w("| … | _y {} fichas más en esta comunidad_ | | |"
                  .format(num(len(fichas) - LIMITE_LISTADO)))
            w("")
        w("---\n")

    # ── pendientes masivos: recuento por comunidad ──
    w("## Encuesta incompleta, por comunidad\n")
    w("Los servicios básicos y la foto del predio faltan en miles de fichas: "
      "listarlas una a una no ayudaría a planificar. Lo que sirve es saber "
      "**dónde** se concentran.\n")
    w("La columna que manda es la última: si en una comunidad falta mucho de "
      "todo, conviene una visita completa; si falta poco y disperso, se resuelve "
      "aprovechando otra salida.\n")

    filas = consultar(ds,
        "SELECT COALESCE(NULLIF(TRIM(comunidad),''),'(sin comunidad)') com, "
        "COUNT(*) total, "
        "SUM(CASE WHEN {} THEN 1 ELSE 0 END) agua, "
        "SUM(CASE WHEN {} THEN 1 ELSE 0 END) luz, "
        "SUM(CASE WHEN {} THEN 1 ELSE 0 END) material, "
        "SUM(CASE WHEN {} THEN 1 ELSE 0 END) foto "
        "FROM {} WHERE {} GROUP BY com ORDER BY agua DESC, total DESC"
        .format(VACIO.format('agua_consumo'), VACIO.format('energia_electrica'),
                VACIO.format('material_construccion'), VACIO.format('foto_predio'),
                t, PRINCIPALES))

    w("| Comunidad | Fichas | Sin agua | Sin luz | Sin material | Sin foto | Pendiente |")
    w("|---|---:|---:|---:|---:|---:|---:|")
    avisos = []
    for com, tot, agua, luz, mat, foto in filas:
        if not (agua or luz or mat or foto):
            continue
        pct = 100.0 * (agua + luz + mat) / (3.0 * tot) if tot else 0
        clave = com.strip().upper()
        if clave in NO_SON_ENCUESTAS:
            avisos.append((com, tot, NO_SON_ENCUESTAS[clave]))
            w("| {} ⚠️ | {} | {} | {} | {} | {} | _ver nota_ |"
              .format(com, num(tot), num(agua), num(luz), num(mat), num(foto)))
            continue
        marca = '🔴' if pct >= 66 else ('🟠' if pct >= 33 else '🟡')
        w("| {} | {} | {} | {} | {} | {} | {} {:.0f} % |"
          .format(com, num(tot), num(agua), num(luz), num(mat), num(foto), marca, pct))
    w("")

    # Aviso destacado: sin esto, la tabla manda a completar fichas que nunca
    # fueron una entrevista, y son cientos.
    for com, tot, motivo in avisos:
        w("> ⚠️ **{}: no salir a completar estas {} fichas.** No están vacías por "
          "descuido — {}. Aparecen aquí porque el criterio de este documento es "
          "«campo vacío», y en su caso ese criterio no significa trabajo "
          "pendiente. Antes de tocarlas hace falta una decisión de dirección "
          "sobre qué se hace con ellas.\n".format(com, num(tot), motivo))

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

    print("\n  guardado: {} ({:,.0f} KB)"
          .format(os.path.relpath(SALIDA, BASE), os.path.getsize(SALIDA) / 1024))
    print("=" * 74)
    return 0


if __name__ == '__main__':
    sys.exit(main())
