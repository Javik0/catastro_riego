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
**uno** de los otros dos campos. Cuál de los dos es la única decisión de fondo, y
el script no la toma solo: hay que pasarla con `--direccion`.

    --direccion sin-riego   el predio SE RIEGA entero  → area_sin_riego = 0
    --direccion riego       el predio NO se riega      → area_riego = 0

**Por qué no se decide sola.** El catastro confirma cuánto mide el predio, pero
no dice si se riega. Y los demás campos de la ficha apuntan a que NO:

    señales de riego (frecuencia, canal, días de turno, método, caudal,
    reservorio o tarifa) presentes en...
        las 54 fichas      →   1 de 54   (1,9 %)
        el resto del padrón → 6.731 de 6.777 (99 %)

Un predio del sistema sin ningún dato de riego es raro; 53 seguidos, del mismo
técnico y la misma semana, no son 53 casos raros. Pero eso admite dos lecturas
opuestas: o esos predios de verdad no se riegan, o en esa semana la sección de
riego quedó sin llenar. **Solo quien hizo el levantamiento puede decirlo**, y de
ahí depende en qué columna van 56,38 ha.

Mientras no se aclare, el script se niega a escribir.

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
1. Que Pablo Barrionuevo diga si esos 54 predios se riegan o no. De su respuesta
   sale el `--direccion`, y sin eso la corrección es una moneda al aire.
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
    ap.add_argument('--direccion', choices=('sin-riego', 'riego'),
                    help='que campo se pone en cero. sin-riego = el predio se '
                         'riega entero; riego = el predio no se riega. Lo tiene '
                         'que confirmar quien hizo el levantamiento.')
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
    print("\n  EFECTO SEGUN LA DIRECCION QUE SE ELIJA:")
    print("     --direccion sin-riego  (se riegan enteros)")
    print("        con riego {} ha (igual) · sin riego {} -> {} ha"
          .format(ha(s_rie), ha(s_sin), ha(s_sin - sobra)))
    print("     --direccion riego      (no se riegan)")
    print("        con riego {} -> {} ha · sin riego {} ha (igual)"
          .format(ha(s_rie), ha(s_rie - sobra), ha(s_sin)))
    print("     en los dos casos la suma queda en {} ha y cuadra con el area total"
          .format(ha(s_rie + s_sin - sobra)))

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
            print("  Para aplicarlo: --aplicar --direccion {sin-riego|riego}")
            print("  Antes: respuesta de Pablo sobre si esos predios se riegan,")
            print("  aprobacion de Armando y que nadie este sincronizando.")
        print("  " + "=" * 74)
        con.close()
        return 0 if not args.aplicar else 2

    # ── aplicar ──
    campo = 'area_sin_riego' if args.direccion == 'sin-riego' else 'area_riego'
    print("\n  direccion elegida: {}  ->  {} = 0".format(args.direccion, campo))
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
        cur.execute("UPDATE {} SET {} = 0 WHERE {}".format(t, campo, PATRON))
        tocadas = cur.rowcount
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
