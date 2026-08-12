# -*- coding: utf-8 -*-
"""
Corrige las fichas donde el área sin riego repite el área total del predio.

Qué problema resuelve
---------------------
Hay 54 fichas en las que `area_total`, `area_riego` y `area_sin_riego` traen
**el mismo número tres veces**. Todas son del mismo técnico (`jvk-editor5`) y de
la misma semana (24 al 30 de julio de 2026): es un patrón de captura, no 54
predios raros.

El efecto es que el predio se cuenta dos veces —entero con riego y entero sin
riego— y la superficie del padrón deja de cuadrar:

    area_riego + area_sin_riego = 10.349,15 ha
    area_total                  = 10.294,99 ha   →  56,38 ha de más

Se midió sobre las 6.831 fichas: **estas 54 son la única fuente de descuadre del
padrón**. Las otras 6.774 cuadran, y 3 más quedan cortas por no declarar ninguno
de los dos campos (2,22 ha, caso distinto que este script no toca).

Qué hace y por qué así
----------------------
Deja `area_total` intacta —el polígono del catastro la confirma— y pone en cero
**uno** de los otros dos campos:

    --direccion riego       el predio NO se riega      → area_riego = 0
    --direccion sin-riego   el predio SE RIEGA entero  → area_sin_riego = 0
    --direccion auto        decide ficha por ficha, según el canal (ver abajo)

Cuál de los dos era la única duda de fondo, y **la resolvió Armando el 12 de
agosto de 2026** mirando las fichas en el mapa:

    PAMBAMARCA     — «casi todos los adicionales están SOBRE el canal,
                      no tienen riego»
    CHAUPIESTANCIA — «todos están BAJO el canal, deben tener riego»

O sea que no hay una respuesta única para las 54: depende de dónde caiga el
predio respecto al canal Guanguilquí. El canal riega por gravedad, así que lo
que queda por encima de su cota no recibe agua por mucho que esté al lado.

Cómo lo decide `--direccion auto`
---------------------------------
Para cada ficha busca las `--vecinos` fichas más cercanas que **sí declaran
riego** y compara su cota con la mediana de esas vecinas. Si está más de
`--umbral` metros por encima, es que quedó sobre el canal.

No se usa la cota del canal directamente porque la capa `ramales_riego.geojson`
es 2D: no trae cotas. Los regantes vecinos son una referencia mejor, porque son
predios que de hecho reciben agua en ese punto del sistema.

El resultado reproduce lo que dijo Armando sin habérselo dicho al programa:

    PAMBAMARCA      22 sobre  ·  8 bajo     («casi todos»)
    CHAUPIESTANCIA   1 sobre  · 17 bajo     («todos»)

y el corte sale limpio: en Pambamarca las de arriba están a +40 m o más de sus
vecinas regantes y las de abajo a +25 m o menos, sin casos en la franja del
medio. Aun así el script imprime la diferencia de cada ficha para que se pueda
revisar, y marca las que quedan cerca del umbral.

Por qué hacía falta preguntar
-----------------------------
Los demás campos de la ficha apuntaban a que ninguna se riega:

    señales de riego (frecuencia, canal, días de turno, método, caudal,
    reservorio o tarifa) presentes en...
        las 54 fichas       →     1 de 54   (1,9 %)
        el resto del padrón → 6.731 de 6.777 (99 %)

Pero eso admitía dos lecturas opuestas —que no se rieguen, o que esa semana la
sección quedara sin llenar— y la respuesta resultó ser «depende de cuál».

Lo que NO hace
--------------
No toca la regla de exportación. Si además se cambia `export_geojson.py:582`
por la regla de cuadre, el resultado publicado es el mismo; pero esta corrección
hace falta igual, porque el `data.gpkg` es lo que viaja al cliente en el
GeoPackage y lo que ven los técnicos en QField.

Uso
---
    "C:\\OSGeo4W\\bin\\python-qgis.bat" -X utf8 scripts/corregir_areas_sin_riego.py
    "C:\\OSGeo4W\\bin\\python-qgis.bat" -X utf8 scripts/corregir_areas_sin_riego.py --aplicar

Sin `--aplicar` **no escribe nada**: lista las fichas y muestra el efecto (regla
7 del proyecto). Con `--aplicar` respalda antes de tocar nada, usando la API de
backup de SQLite —no una copia plana, que sale incompleta si hay `-wal`
pendiente— y deja el respaldo fuera de la carpeta que sincroniza QFieldCloud.

Antes de correrlo con --aplicar
-------------------------------
1. Que Armando o Pablo validen en el mapa la lista que imprime `--direccion
   auto`, sobre todo las fichas marcadas como límite.
2. Que Armando lo apruebe: mueve una cifra de superficie, y pidió aprobar
   cualquier cambio sobre la base declarada al Consejo Provincial.
3. Ventana coordinada: que nadie esté sincronizando desde una tablet.
"""
import argparse
import json
import os
import sqlite3
import sys
import time

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
GPKG = os.path.join(os.path.expanduser('~'), 'QField', 'cloud',
                    'porotog_levantamiento_offline', 'data.gpkg')
CATASTRO = os.path.join(BASE, 'public', 'geo', 'catastro_geo.geojson')
RAIZ_RESPALDOS = (r"C:\Users\HP\OneDrive\Escritorio\CAYAMBE CATASTRO RIEGO"
                  r"\respaldos_qgs")

TABLA = 'Fichas_Predios_880eb10d_d887_4fc6_99a2_8af3ac63877e'

# El patrón: los tres campos con el mismo valor, y ese valor distinto de cero.
# Se compara con tolerancia de medio metro porque son reales, no enteros.
PATRON = ("area_total IS NOT NULL AND area_total <> 0 "
          "AND ABS(area_total - COALESCE(area_riego,0)) < 0.5 "
          "AND ABS(area_total - COALESCE(area_sin_riego,0)) < 0.5")

TOLERANCIA_CATASTRO = 0.20   # 20 % de diferencia contra el polígono


def ha(m2):
    return '{:,.2f}'.format(m2 / 10000.0).replace(',', 'X').replace('.', ',').replace('X', '.')


def respaldo_sqlite(origen, etiqueta):
    """Copia consistente con la API de backup de SQLite, fuera de QFieldCloud."""
    carpeta = os.path.join(RAIZ_RESPALDOS, time.strftime('%Y-%m-%d'))
    os.makedirs(carpeta, exist_ok=True)
    destino = os.path.join(carpeta, '{}.{}-{}.bak'.format(
        os.path.basename(origen), time.strftime('%H%M'), etiqueta))
    src = sqlite3.connect(origen)
    dst = sqlite3.connect(destino)
    with dst:
        src.backup(dst)
    dst.close()
    src.close()
    return destino


def mediana(v):
    v = sorted(v)
    n = len(v)
    return v[n // 2] if n % 2 else (v[n // 2 - 1] + v[n // 2]) / 2.0


def clasificar_por_canal(cur, t, umbral, k):
    """Sobre o bajo el canal, comparando con las fichas regantes de al lado.

    Devuelve {clave_catastral: (veredicto, cota, cota_vecinas, diferencia)}.
    El canal riega por gravedad: lo que queda por encima de su cota no recibe
    agua. Como la capa del canal no trae cotas, se usan de referencia los
    predios vecinos que sí declaran riego, que es una referencia mejor: son
    predios que de hecho reciben agua en ese punto del sistema.
    """
    V = "({0} IS NOT NULL AND TRIM(CAST({0} AS TEXT)) NOT IN ('','None','NULL'))"
    NZ = "({0} IS NOT NULL AND CAST({0} AS REAL) <> 0)"
    riega = "({} OR {} OR {} OR {} OR {})".format(
        V.format('frecuencia_riego'), V.format('canal'), NZ.format('dias_riego'),
        NZ.format('caudal_valor'), NZ.format('metodo_gravedad_pct'))
    sel = ("SELECT COALESCE(clave_catastral,''), COALESCE(cota_msnm,0), "
           "COALESCE(coord_x_utm,0), COALESCE(coord_y_utm,0) FROM {}")

    cur.execute((sel + " WHERE {} AND NOT ({})").format(t, riega, PATRON))
    regantes = [r for r in cur.fetchall() if r[1] and r[2] and r[3]]
    cur.execute((sel + " WHERE {}").format(t, PATRON))
    objetivo = [r for r in cur.fetchall() if r[1] and r[2] and r[3]]

    fallo = {}
    for clave, cota, x, y in objetivo:
        cerca = sorted(((x - r[2]) ** 2 + (y - r[3]) ** 2, r[1])
                       for r in regantes)[:k]
        if not cerca:
            continue
        ref = mediana([c for _, c in cerca])
        dif = cota - ref
        fallo[clave] = ('riego' if dif > umbral else 'sin-riego', cota, ref, dif)
    return fallo, len(regantes)


def areas_del_catastro():
    """Área del polígono por clave catastral, si el archivo está disponible."""
    if not os.path.exists(CATASTRO):
        return {}
    try:
        with open(CATASTRO, encoding='utf-8') as f:
            datos = json.load(f)
    except Exception as e:
        print("   aviso: no se pudo leer el catastro ({})".format(e))
        return {}
    # El geojson del catastro trae los nombres recortados a 10 caracteres, como
    # los deja la conversión desde shapefile: `clave_cata` y `area_predi`.
    areas = {}
    for ft in datos.get('features', []):
        p = ft.get('properties') or {}
        clave = str(p.get('clave_cata') or p.get('clave_catastral') or '').strip()
        if not clave:
            continue
        for campo in ('area_predi', 'area_m2', 'area', 'Shape_Area'):
            if p.get(campo):
                try:
                    areas[clave] = float(p[campo])
                except (TypeError, ValueError):
                    pass
                break
    return areas


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--aplicar', action='store_true',
                    help='escribe en el data.gpkg (sin esto solo simula)')
    ap.add_argument('--direccion', choices=('sin-riego', 'riego', 'auto'),
                    help='que campo se pone en cero. riego = el predio no se '
                         'riega; sin-riego = se riega entero; auto = decide por '
                         'ficha segun quede sobre o bajo el canal.')
    ap.add_argument('--umbral', type=float, default=25.0,
                    help='metros por encima de las vecinas regantes para darlo '
                         'por sobre el canal (por defecto 25)')
    ap.add_argument('--vecinos', type=int, default=15,
                    help='cuantas fichas regantes cercanas se usan de referencia')
    args = ap.parse_args()

    print("=" * 78)
    print(" CORRECCION DE AREA SIN RIEGO DUPLICADA" +
          ("  [APLICAR]" if args.aplicar else "  [SIMULACION - no escribe nada]"))
    print("=" * 78)

    if not os.path.exists(GPKG):
        print("ERROR: no se encuentra el data.gpkg:\n  {}".format(GPKG))
        return 1

    con = sqlite3.connect(GPKG)
    cur = con.cursor()
    t = '"{}"'.format(TABLA)

    # ── estado del padrón antes ──
    cur.execute("SELECT COUNT(*), SUM(COALESCE(area_total,0)), "
                "SUM(COALESCE(area_riego,0)), SUM(COALESCE(area_sin_riego,0)) "
                "FROM {}".format(t))
    n_all, s_tot, s_rie, s_sin = cur.fetchone()
    print("\n  padron: {:,} fichas".format(n_all))
    print("     area total declarada : {:>10} ha".format(ha(s_tot)))
    print("     con riego            : {:>10} ha".format(ha(s_rie)))
    print("     sin riego            : {:>10} ha".format(ha(s_sin)))
    print("     riego + sin riego    : {:>10} ha   <-- excede el total en {} ha"
          .format(ha(s_rie + s_sin), ha(s_rie + s_sin - s_tot)))

    # ── las fichas afectadas ──
    cur.execute(
        "SELECT COALESCE(clave_catastral,''), "
        "TRIM(COALESCE(apellidos,'') || ' ' || COALESCE(nombres,'')), "
        "COALESCE(comunidad,'(sin comunidad)'), COALESCE(creado_por,''), "
        "SUBSTR(CAST(fecha_creacion AS TEXT),1,10), COALESCE(area_total,0) "
        "FROM {} WHERE {} ORDER BY 3, 1".format(t, PATRON))
    fichas = cur.fetchall()

    if not fichas:
        print("\n  No hay fichas con este patron. Nada que corregir.")
        con.close()
        return 0

    catastro = areas_del_catastro()
    print("\n  {} fichas con el area repetida tres veces".format(len(fichas)))
    print("  cruce contra el catastro: {}".format(
        "{:,} claves con area de poligono".format(len(catastro)) if catastro
        else "no disponible (no se pudo leer catastro_geo.geojson)"))

    dudosas = []
    print("\n  {:<15} {:<30} {:<18} {:>10}  {}".format(
        'CLAVE', 'REGANTE', 'COMUNIDAD', 'AREA (ha)', 'CATASTRO'))
    print("  " + "-" * 92)
    for clave, nombre, com, tec, fecha, area in fichas:
        marca = ''
        if catastro:
            ref = catastro.get(clave.strip())
            if ref is None:
                marca = 'sin poligono'
            elif area > 0 and abs(ref - area) / area > TOLERANCIA_CATASTRO:
                marca = 'NO CONFIRMA ({} ha)'.format(ha(ref))
                dudosas.append((clave, nombre, area, ref))
            else:
                marca = 'ok'
        print("  {:<15} {:<30} {:<18} {:>10}  {}".format(
            clave or '—', (nombre or '—')[:30], com[:18], ha(area), marca))

    # ── quién y cuándo, para que Pablo lo reconozca ──
    cur.execute("SELECT COALESCE(creado_por,'(vacio)'), COUNT(*), "
                "MIN(SUBSTR(CAST(fecha_creacion AS TEXT),1,10)), "
                "MAX(SUBSTR(CAST(fecha_creacion AS TEXT),1,10)) "
                "FROM {} WHERE {} GROUP BY 1".format(t, PATRON))
    print("\n  quien las levanto:")
    for tec, n, d1, d2 in cur.fetchall():
        print("     {:<16} {:>3} fichas   del {} al {}".format(tec, n, d1, d2))

    # ── ¿esos predios se riegan? lo dicen los demás campos de la ficha ──
    V = "({0} IS NOT NULL AND TRIM(CAST({0} AS TEXT)) NOT IN ('','None','NULL'))"
    NZ = "({0} IS NOT NULL AND CAST({0} AS REAL) <> 0)"
    RIEGA = "({} OR {} OR {} OR {} OR {} OR {} OR {})".format(
        V.format('frecuencia_riego'), V.format('canal'), NZ.format('dias_riego'),
        NZ.format('caudal_valor'), NZ.format('metodo_gravedad_pct'),
        NZ.format('metodo_aspersion_pct'), NZ.format('valor_tarifa'))
    cur.execute("SELECT COUNT(*) FROM {} WHERE {} AND {}".format(t, PATRON, RIEGA))
    con_señal = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*), SUM(CASE WHEN {} THEN 1 ELSE 0 END) FROM {} "
                "WHERE NOT ({})".format(RIEGA, t, PATRON))
    n_resto, señal_resto = cur.fetchone()

    print("\n  ¿ESTOS PREDIOS SE RIEGAN? (frecuencia, canal, dias de turno,")
    print("  caudal, metodo, tarifa — cualquier senal sirve)")
    print("     estas {} fichas    : {:>5} con alguna senal  ({:.1f} %)"
          .format(len(fichas), con_señal, 100.0 * con_señal / len(fichas)))
    print("     resto del padron   : {:>5} de {:,}          ({:.0f} %)"
          .format(señal_resto, n_resto, 100.0 * señal_resto / n_resto))
    print("     -> el padron entero declara riego y estas no. Eso APUNTA a que no")
    print("        se riegan, pero tambien puede ser que la seccion quedara sin")
    print("        llenar esa semana. Son lecturas opuestas y deciden donde van")
    print("        {} ha. Por eso hace falta --direccion.".format(ha(sum(f[5] for f in fichas))))

    sobra = sum(f[5] for f in fichas)

    # ── clasificación por el canal (lo que resolvió Armando) ──
    fallo, n_reg = clasificar_por_canal(cur, t, args.umbral, args.vecinos)
    print("\n  SOBRE O BAJO EL CANAL (referencia: {:,} fichas regantes; "
          "{} vecinas por ficha, umbral {:.0f} m)".format(n_reg, args.vecinos, args.umbral))
    print("     Armando, 12-ago: Pambamarca «casi todos SOBRE el canal, no tienen")
    print("     riego»; Chaupiestancia «todos BAJO el canal, deben tener riego».\n")
    print("     {:<15} {:<16} {:>6} {:>8} {:>7}  {}".format(
        'CLAVE', 'COMUNIDAD', 'COTA', 'VECINAS', 'DIF', 'VEREDICTO'))
    print("     " + "-" * 74)
    resumen, limite = {}, []
    ha_riego = ha_sin = 0.0
    for clave, nombre, com, tec, fecha, area in fichas:
        v = fallo.get(clave.strip())
        if not v:
            print("     {:<15} {:<16} {:>6} {:>8} {:>7}  sin cota o sin coordenadas"
                  .format(clave, com[:16], '—', '—', '—'))
            continue
        direccion, cota, ref, dif = v
        etq = 'SOBRE -> no riega' if direccion == 'riego' else 'BAJO  -> si riega'
        cerca = abs(dif - args.umbral) <= 10
        resumen[etq] = resumen.get(etq, 0) + 1
        if direccion == 'riego':
            ha_riego += area
        else:
            ha_sin += area
        if cerca:
            limite.append((clave, com, dif, etq))
        print("     {:<15} {:<16} {:>6.0f} {:>8.0f} {:>+7.0f}  {}{}"
              .format(clave, com[:16], cota, ref, dif, etq,
                      '  <-- al limite' if cerca else ''))

    print("\n     reparto: " + " · ".join("{} {}".format(v, k)
                                          for k, v in sorted(resumen.items())))

    print("\n  EFECTO DE LA CORRECCION:")
    print("     --direccion auto   (lo que dijo Armando, ficha por ficha)")
    print("        con riego {} -> {} ha".format(ha(s_rie), ha(s_rie - ha_riego)))
    print("        sin riego {} -> {} ha".format(ha(s_sin), ha(s_sin - ha_sin)))
    print("        suma      {} -> {} ha   (cuadra con el area total)"
          .format(ha(s_rie + s_sin), ha(s_rie + s_sin - sobra)))
    print("     --direccion riego      todas sin riego : con riego {} ha"
          .format(ha(s_rie - sobra)))
    print("     --direccion sin-riego  todas regadas   : sin riego {} ha"
          .format(ha(s_sin - sobra)))

    if limite:
        print("\n  {} ficha(s) cerca del umbral, conviene mirarlas en el mapa:"
              .format(len(limite)))
        for clave, com, dif, etq in limite:
            print("     - {} ({}) {:+.0f} m -> {}".format(clave, com[:16], dif, etq))

    if dudosas:
        # Antes de mandar a nadie a revisar: cuando varias fichas comparten la
        # misma clave son copropietarios, y cada uno declara SU parte del
        # predio. Si las partes suman el poligono, no hay nada que revisar.
        por_clave = {}
        for clave, nombre, area, ref in dudosas:
            d = por_clave.setdefault(clave, {'suma': 0.0, 'ref': ref, 'quienes': []})
            d['suma'] += area
            d['quienes'].append(nombre)
        compartidos, revisar = [], []
        for clave, d in por_clave.items():
            if len(d['quienes']) > 1 and d['ref'] > 0 and \
                    abs(d['suma'] - d['ref']) / d['ref'] <= TOLERANCIA_CATASTRO:
                compartidos.append((clave, d))
            else:
                revisar.append((clave, d))

        for clave, d in compartidos:
            print("\n  El catastro no cuadra con una ficha suelta de {}, pero si con "
                  "la suma:".format(clave))
            print("     {} fichas declaran {} ha entre todas y el poligono mide {} ha."
                  .format(len(d['quienes']), ha(d['suma']), ha(d['ref'])))
            print("     Son copropietarios repartiendose el predio: {}."
                  .format(', '.join(n[:28] for n in d['quienes'])))
            print("     No hay nada que revisar aqui; la correccion les aplica igual.")

        if revisar:
            print("\n  !! {} ficha(s) que el catastro NO respalda: revisar aparte."
                  .format(sum(len(d['quienes']) for _, d in revisar)))
            print("     En estas el problema puede ser el area_total, no el sin riego.")
            for clave, d in revisar:
                print("     - {} {} · declara {} ha · poligono {} ha"
                      .format(clave, ', '.join(n[:28] for n in d['quienes']),
                              ha(d['suma']), ha(d['ref'])))
            print("     Aun asi el cuadre las corrige igual: se respeta lo declarado")
            print("     en riego y el sin riego se ajusta. El area_total dudosa es un")
            print("     problema distinto, que no arregla este script.")

    if not args.aplicar or not args.direccion:
        print("\n  " + "=" * 74)
        if args.aplicar and not args.direccion:
            print("  NO SE ESCRIBIO NADA: falta --direccion.")
            print("  Sin saber si esos predios se riegan, la correccion seria una")
            print("  moneda al aire entre dos columnas. Preguntar a Pablo primero.")
        else:
            print("  SIMULACION: no se escribio nada.")
            print("  Para aplicarlo:  --aplicar --direccion auto")
            print("  Antes: que Armando valide en el mapa las fichas marcadas al")
            print("  limite, apruebe el cambio de superficie, y que nadie este")
            print("  sincronizando desde una tablet.")
        print("  " + "=" * 74)
        con.close()
        return 0 if not args.aplicar else 2

    # ── aplicar ──
    # En `auto` cada ficha lleva su propia direccion; en los otros modos, todas
    # la misma.
    if args.direccion == 'auto':
        plan = {c: v[0] for c, v in fallo.items()}
        faltan = [f[0] for f in fichas if f[0].strip() not in plan]
        if faltan:
            print("\n  NO SE ESCRIBIO NADA: {} ficha(s) sin cota o sin coordenadas, "
                  "que 'auto' no puede clasificar.".format(len(faltan)))
            print("  Resolverlas a mano o usar una direccion explicita: {}"
                  .format(', '.join(faltan)))
            con.close()
            return 2
        print("\n  direccion: auto — {} sin riego, {} regadas"
              .format(sum(1 for d in plan.values() if d == 'riego'),
                      sum(1 for d in plan.values() if d == 'sin-riego')))
    else:
        plan = {f[0].strip(): args.direccion for f in fichas}
        campo = 'area_sin_riego' if args.direccion == 'sin-riego' else 'area_riego'
        print("\n  direccion: {} para las {} ->  {} = 0"
              .format(args.direccion, len(fichas), campo))
    con.close()
    print("\n  respaldando antes de tocar nada...")
    destino = respaldo_sqlite(GPKG, 'antes-areas-' + args.direccion)
    print("     {}".format(destino))

    con = sqlite3.connect(GPKG)
    cur = con.cursor()
    # Los triggers del índice espacial llaman a ST_IsEmpty, que SQLite puro no
    # trae. Se retiran mientras dura el UPDATE y se recrean tal cual.
    cur.execute("SELECT name, sql FROM sqlite_master "
                "WHERE type='trigger' AND tbl_name=?", (TABLA,))
    triggers = cur.fetchall()
    for nombre, _ in triggers:
        cur.execute('DROP TRIGGER IF EXISTS "{}"'.format(nombre))
    try:
        tocadas = 0
        for clave, direccion in plan.items():
            col = 'area_sin_riego' if direccion == 'sin-riego' else 'area_riego'
            cur.execute("UPDATE {} SET {} = 0 WHERE {} AND TRIM(COALESCE("
                        "clave_catastral,'')) = ?".format(t, col, PATRON), (clave,))
            tocadas += cur.rowcount
    finally:
        for _, sql in triggers:
            if sql:
                cur.execute(sql)
    con.commit()
    cur.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    con.close()
    print("     {} fichas actualizadas · {} triggers espaciales recreados"
          .format(tocadas, len(triggers)))

    # ── verificación releyendo del disco ──
    con = sqlite3.connect(GPKG)
    cur = con.cursor()
    cur.execute("SELECT COUNT(*) FROM {} WHERE {}".format(t, PATRON))
    quedan = cur.fetchone()[0]
    cur.execute("SELECT SUM(COALESCE(area_total,0)), SUM(COALESCE(area_riego,0)), "
                "SUM(COALESCE(area_sin_riego,0)) FROM {}".format(t))
    v_tot, v_rie, v_sin = cur.fetchone()
    con.close()

    print("\n  VERIFICACION (releyendo del disco):")
    print("     fichas con el patron    : {}".format(quedan))
    print("     area total              : {} ha".format(ha(v_tot)))
    print("     con riego + sin riego   : {} ha".format(ha(v_rie + v_sin)))
    print("     descuadre               : {} ha".format(ha(v_rie + v_sin - v_tot)))
    ok = quedan == 0 and abs((v_rie + v_sin) - v_tot) < 10000
    print("\n  {}".format("CORRECCION APLICADA Y VERIFICADA" if ok
                          else "!! REVISAR: el resultado no es el esperado"))
    print("\n  Siguiente paso: regenerar y publicar (npm run build + firebase deploy)")
    print("  para que la web y los informes recojan el cambio.")
    print("=" * 78)
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
