# -*- coding: utf-8 -*-
"""
Arma la REENTREGA (versión 2) del Producto 5 con los ajustes prometidos en la
matriz de respuesta al INFORME-JAFG-2026-002.

Principio: la v2 parte del GeoPackage TAL COMO SE ENTREGÓ el 18-sep-2026 y solo
AGREGA. Ninguna cifra se mueve: no se borran ni se fusionan fichas, no cambian
áreas ni conteos. Lo que cambia es cómo se presenta el dato:

  Capa predios_investigados (la «tabla X» del informe)
    - codigos_ficha: los códigos S-C-R-F de las fichas del predio (C04, C10).
    - codigo_comunidad / comunidad_oficial / sector: del catálogo de las 50
      comunidades (C07); «sector_riego» pasa a llamarse
      «sistema_riego_declarado», que es lo que contiene (7.1-c).
    - cultivos_predio y animales_predio con números en castellano.
  Capa fichas: codigo_comunidad, comunidad_oficial, sector_catalogo.
  Capa cultivos: donde el técnico llenó a la vez el tipo y el campo «otro»,
    manda el tipo y el «otro» pasa a cultivo_detalle (C17: el «500» era
    «Pasto no mejorado»).
  Tablas nuevas (atributos, sin geometría):
    - correspondencia_fichas: ficha, titular, cédula, comunidad, predio, si
      tiene polígono y marcas de revisión (C04, C09, C10, 11.1-c).
    - fichas_sin_poligono: las 9 fichas sin polígono y su causa (C09).
    - catalogo_comunidades: C01–C50 (C07).
    - registro_cambios: altas, bajas y cambios ficha por ficha desde el
      18-ago-2026 (inicio de la depuración) hasta la base entregada (11.1-c).
    - metadatos: fecha de corte, versión y cambios respecto de la v1 (7.1-b).
  SHP regenerado desde el GeoPackage v2; CAD sin cambios (la geometría es la
  misma); Excel con las claves como texto (C10, C17).

No toca la web ni la base de campo (QField se lee en solo lectura).
Uso:  python -X utf8 scripts/armar_reentrega_producto5.py
"""
import collections
import datetime as dt
import io
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import unicodedata
import zipfile

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
from comunidades_canon import canonica  # noqa: E402
from excel_compat import aplicar_formatos  # noqa: E402
from informe_estilo import FECHA_CORTE, esn  # noqa: E402

ESC = r'C:\Users\HP\OneDrive\Escritorio'
RAIZ = os.path.join(ESC, 'CAYAMBE CATASTRO RIEGO')
APP = os.path.join(RAIZ, 'padron-app')
ENTREGA_V1 = os.path.join(ESC, 'PRODUCTO 5 - ENTREGA 18-SEP-2026.zip')
DESTINO = os.path.join(ESC, 'PRODUCTO 5 - REENTREGA v2 (oct-2026)')
QFIELD = r'C:\Users\HP\QField\cloud\porotog_levantamiento_offline\data.gpkg'
ANTES_DEPURACION = os.path.join(RAIZ, 'respaldos_qgs', '2026-08-18', 'data.gpkg.1113-antes-campo-otro.bak')
OSGEO_ENV = r'C:\OSGeo4W\bin\o4w_env.bat'
VERSION = 'v2 (reentrega, octubre de 2026)'

C_BASE = '1 - BASE DE DATOS GEOESPACIAL DE LOS PREDIOS'
C_SHP = os.path.join(C_BASE, '1.1 - FORMATO SHP')
C_QGIS = os.path.join(C_BASE, '1.3 - PROYECTO QGIS')
C_XLS = os.path.join(C_BASE, '1.4 - TABLAS EN EXCEL')


def n(s):
    return ' '.join(unicodedata.normalize('NFKD', s or '').encode('ascii', 'ignore').decode().upper().split())


def ro(ruta):
    return sqlite3.connect('file:' + ruta.replace('\\', '/') + '?mode=ro', uri=True)


# ── 0. catálogo y datos auxiliares ─────────────────────────────────────────
def catalogo():
    ts = io.open(os.path.join(APP, 'src', 'lib', 'constants.ts'), encoding='utf-8').read()
    cat = {}
    for m in re.finditer(r"\{\s*n:\s*(\d+),\s*sector:\s*'([^']+)',\s*oficial:\s*'([^']+)',"
                         r"\s*datos:\s*'([^']+)'(,\s*oculta:\s*true)?\s*\}", ts):
        if not m.group(5):
            cat[n(canonica(m.group(4)))] = dict(num=int(m.group(1)), codigo=f'C{int(m.group(1)):02d}',
                                                sector=m.group(2), oficial=m.group(3), datos=m.group(4))
    assert len(cat) == 50, len(cat)
    return cat


# ── 1. copia de la entrega v1 ──────────────────────────────────────────────
def copiar_v1():
    if os.path.exists(DESTINO):
        shutil.rmtree(DESTINO)
    with zipfile.ZipFile(ENTREGA_V1) as z:
        raiz = z.namelist()[0].split('/')[0]
        for i in z.infolist():
            if i.filename.endswith('/'):
                continue
            rel = i.filename[len(raiz) + 1:]
            dst = os.path.join(DESTINO, rel.replace('/', os.sep))
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            with z.open(i) as f, open(dst, 'wb') as o:
                shutil.copyfileobj(f, o)
    return os.path.join(DESTINO, C_QGIS, 'padron_riego_porotog.gpkg')


# ── 2. GeoPackage v2 ───────────────────────────────────────────────────────
def registrar(con, tabla, descripcion):
    hoy = dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.000Z')
    con.execute('delete from gpkg_contents where table_name=?', (tabla,))
    con.execute("insert into gpkg_contents(table_name, data_type, identifier, description, last_change) "
                "values (?, 'attributes', ?, ?, ?)", (tabla, tabla, descripcion, hoy))
    con.execute('delete from gpkg_ogr_contents where table_name=?', (tabla,))
    con.execute('insert into gpkg_ogr_contents(table_name, feature_count) values (?, (select count(*) from "%s"))'
                % tabla, (tabla,))


def crear_tabla(con, tabla, cols, filas, descripcion):
    con.execute(f'drop table if exists "{tabla}"')
    con.execute(f'create table "{tabla}" (fid integer primary key autoincrement, '
                + ', '.join(f'"{c}" {t}' for c, t in cols) + ')')
    con.executemany(f'insert into "{tabla}" ({", ".join(chr(34) + c + chr(34) for c, _ in cols)}) '
                    f'values ({", ".join("?" * len(cols))})', filas)
    registrar(con, tabla, descripcion)


def ajustar_cultivos(con):
    """C17: donde se llenó el tipo y también el «otro», manda el tipo."""
    con.execute('alter table cultivos add column cultivo_detalle TEXT')
    q = ro(QFIELD)
    t = next(r[0] for r in q.execute("select name from sqlite_master where name like 'Cultivos_Agricolas%'"))
    casos = q.execute(f'select ficha_id, tipo_cultivo, tipo_cultivo_otro, superficie_m2 from "{t}" '
                      "where coalesce(trim(tipo_cultivo_otro),'')<>'' and "
                      "lower(trim(coalesce(tipo_cultivo,''))) not in ('otro','otros','')").fetchall()
    q.close()
    hechos = []
    for fid, tipo, otro, sup in casos:
        r = con.execute('select fid from cultivos where ficha_id=? and trim(cultivo)=? and abs(superficie_m2-?)<0.01',
                        (fid, otro.strip(), sup or 0)).fetchall()
        if len(r) == 1:
            con.execute('update cultivos set cultivo=?, cultivo_detalle=? where fid=?', (tipo, otro.strip(), r[0][0]))
            hechos.append((fid, otro.strip(), tipo))
    return hechos


def textos_predio(con):
    """Rehace cultivos_predio y animales_predio con números en castellano.
    Misma regla del generador: se agrupa por nombre en mayúsculas y se ordena
    de mayor a menor. Devuelve cuántos textos cambian además del formato."""
    fichas = collections.defaultdict(list)
    for fid, clave in con.execute('select ficha_id, clave_catastral from fichas order by fid'):
        fichas[(clave or '').strip()].append(fid)
    cult = collections.defaultdict(list)
    for fid, c, s in con.execute('select ficha_id, cultivo, superficie_m2 from cultivos order by fid'):
        cult[fid].append((c, s))
    anim = collections.defaultdict(list)
    for fid, e, c in con.execute('select ficha_id, especie, cantidad from animales order by fid'):
        anim[fid].append((e, c))
    cambios = 0
    for pfid, clave, ct, at in con.execute('select fid, clave_catastral, cultivos_predio, animales_predio '
                                           'from predios_investigados').fetchall():
        cs, ans = {}, {}
        for x in fichas.get(clave, []):
            for c, s in cult[x]:
                t = (c or '').strip()
                if t:
                    d = cs.setdefault(t.upper(), {'n': t.capitalize(), 's': 0.0}); d['s'] += s or 0
            for e, c in anim[x]:
                t = (e or '').strip()
                if t:
                    d = ans.setdefault(t.upper(), {'n': t.capitalize(), 'c': 0}); d['c'] += c or 0
        viejo_c = ', '.join('{} ({:.2f} ha)'.format(d['n'], d['s'] / 1e4) if d['s'] else d['n']
                            for d in sorted(cs.values(), key=lambda v: -v['s'])) or None
        nuevo_c = ', '.join('{} ({} ha)'.format(d['n'], esn(d['s'] / 1e4, 2)) if d['s'] else d['n']
                            for d in sorted(cs.values(), key=lambda v: -v['s'])) or None
        nuevo_a = ', '.join('{}: {}'.format(d['n'], esn(d['c'])) if d['c'] else d['n']
                            for d in sorted(ans.values(), key=lambda v: -v['c'])) or None
        if set((viejo_c or '').split(', ')) != set((ct or '').split(', ')):
            cambios += 1
        con.execute('update predios_investigados set cultivos_predio=?, animales_predio=? where fid=?',
                    (nuevo_c, nuevo_a, pfid))
    return cambios


def gpkg_v2(ruta, cat):
    con = sqlite3.connect(ruta)
    cod_fichas = collections.defaultdict(list)
    for clave, cod in con.execute('select clave_catastral, codigo_ficha from fichas order by codigo_ficha'):
        cod_fichas[(clave or '').strip()].append(cod)

    def de_cat(com):
        return cat.get(n(canonica(com or '')), {})

    # predios_investigados
    con.execute('alter table predios_investigados rename column sector_riego to sistema_riego_declarado')
    for c in ('codigos_ficha', 'codigo_comunidad', 'comunidad_oficial', 'sector', 'fecha_corte', 'version'):
        con.execute(f'alter table predios_investigados add column {c} TEXT')
    for fid, clave, com in con.execute('select fid, clave_catastral, comunidad from predios_investigados').fetchall():
        c = de_cat(com)
        con.execute('update predios_investigados set codigos_ficha=?, codigo_comunidad=?, comunidad_oficial=?, '
                    'sector=?, fecha_corte=?, version=? where fid=?',
                    (', '.join(cod_fichas.get(clave, [])), c.get('codigo'), c.get('oficial'), c.get('sector'),
                     FECHA_CORTE, VERSION, fid))
    # fichas
    for c in ('codigo_comunidad', 'comunidad_oficial', 'sector_catalogo'):
        con.execute(f'alter table fichas add column {c} TEXT')
    for fid, com in con.execute('select fid, comunidad from fichas').fetchall():
        c = de_cat(com)
        con.execute('update fichas set codigo_comunidad=?, comunidad_oficial=?, sector_catalogo=? where fid=?',
                    (c.get('codigo'), c.get('oficial'), c.get('sector'), fid))
    cult = ajustar_cultivos(con)
    textos = textos_predio(con)
    # estilos guardados: el campo renombrado
    con.execute("update layer_styles set styleQML=replace(styleQML,'\"sector_riego\"','\"sistema_riego_declarado\"'), "
                "styleSLD=replace(styleSLD,'sector_riego','sistema_riego_declarado') "
                "where f_table_name='predios_investigados'")
    # descripciones: corte y versión
    con.execute("update gpkg_contents set description = description || ' Corte: ' || ? || '. Versión: ' || ? || '.' "
                "where table_name in (select table_name from gpkg_contents)", (FECHA_CORTE, VERSION))
    con.commit()
    sin_comunidad = con.execute("select count(*) from predios_investigados where codigo_comunidad is null").fetchone()[0]
    return con, cult, textos, sin_comunidad


# ── 3. tablas nuevas ───────────────────────────────────────────────────────
def tablas_nuevas(con, cat):
    claves_pol = {r[0] for r in con.execute('select clave_catastral from predios_investigados')}
    fichas = con.execute('select ficha_id, codigo_ficha, tipo_ficha, ficha_madre_id, apellidos, nombres, cedula, '
                         'codigo_comunidad, comunidad_oficial, sector_catalogo, clave_catastral, observaciones, '
                         'fecha_registro, area_total_m2 from fichas order by codigo_ficha').fetchall()
    cod_de = {f[0]: f[1] for f in fichas}
    # duplicados de una misma entrevista: mismo titular (nombre), predio, día y área, ambas principales
    grupos = collections.defaultdict(list)
    for f in fichas:
        if f[2] == 'Ficha principal':
            grupos[(n(f'{f[4]} {f[5]}'), (f[10] or '').strip(), (f[12] or '')[:10], f[13])].append(f[1])
    dup = {c: g for g in grupos.values() if len(g) > 1 for c in g}
    # cédulas en verificación de campo (solicitud del 4-oct, lo que no se resolvió en oficina)
    en_campo = set()
    vf = os.path.join(RAIZ, 'CONTRATO Y FISCALIZACION', 'RESPUESTA OBSERVACIONES PRODUCTO 5',
                      'VERIFICACIONES EN OFICINA (7-oct-2026).xlsx')
    if os.path.exists(vf):
        import openpyxl
        ws = openpyxl.load_workbook(vf, read_only=True)['Solicitud 4-oct']
        for r in ws.iter_rows(min_row=5, values_only=True):
            if r[0] and 'requiere campo' in str(r[5] or ''):
                en_campo.add(r[0])
    filas, sinpol = [], []
    for (fid, cod, tipo, madre, ape, nom, ced, ccom, cofi, sec, clave, obs, fecha, area) in fichas:
        tiene = 'Sí' if (clave or '').strip() in claves_pol else 'No'
        marca = []
        if tiene == 'No':
            causa = ('Clave catastral del Distrito Metropolitano de Quito: el predio no está en el catastro del '
                     'cantón Cayambe.' if 'DMQ' in (obs or '').upper() or 'QUITO' in (obs or '').upper()
                     or (clave or '').startswith('1454') else
                     'La clave declarada no existe en el catastro del cantón; se confirma con el titular.')
            marca.append('Sin polígono: ' + causa)
            sinpol.append((cod, f'{ape} {nom}'.strip(), cofi, clave, area, causa))
        if cod in dup:
            otros = [c for c in dup[cod] if c != cod]
            marca.append('Posible registro duplicado de la misma entrevista (igual a ' + ', '.join(otros)
                         + '); se conserva')
        if cod in en_campo:
            marca.append('Cédula en verificación de campo')
        filas.append((cod, fid, tipo, cod_de.get(madre, ''), f'{ape or ""} {nom or ""}'.strip(), ced, ccom, cofi,
                      sec, clave, tiene, '; '.join(marca)))
    crear_tabla(con, 'correspondencia_fichas',
                [('codigo_ficha', 'TEXT'), ('ficha_id', 'TEXT'), ('tipo_ficha', 'TEXT'),
                 ('codigo_ficha_principal', 'TEXT'), ('titular', 'TEXT'), ('cedula', 'TEXT'),
                 ('codigo_comunidad', 'TEXT'), ('comunidad_oficial', 'TEXT'), ('sector', 'TEXT'),
                 ('clave_catastral', 'TEXT'), ('tiene_poligono', 'TEXT'), ('marcas_revision', 'TEXT')],
                filas, 'Relación ficha – titular – predio – polígono, una fila por ficha. Ningún registro se '
                       'elimina: las revisiones pendientes se marcan.')
    crear_tabla(con, 'fichas_sin_poligono',
                [('codigo_ficha', 'TEXT'), ('titular', 'TEXT'), ('comunidad_oficial', 'TEXT'),
                 ('clave_declarada', 'TEXT'), ('area_declarada_m2', 'REAL'), ('causa', 'TEXT')],
                sinpol, 'Fichas principales cuyo predio no tiene polígono en el catastro del cantón Cayambe.')
    # catálogo
    fpc = collections.Counter(r[0] for r in con.execute('select codigo_comunidad from fichas'))
    ppc = collections.Counter(r[0] for r in con.execute('select codigo_comunidad from predios_investigados'))
    crear_tabla(con, 'catalogo_comunidades',
                [('codigo_comunidad', 'TEXT'), ('numero', 'INTEGER'), ('comunidad_oficial', 'TEXT'),
                 ('nombre_en_la_base', 'TEXT'), ('sector', 'TEXT'), ('fichas', 'INTEGER'),
                 ('predios_con_poligono', 'INTEGER')],
                [(c['codigo'], c['num'], c['oficial'], c['datos'], c['sector'], fpc.get(c['codigo'], 0),
                  ppc.get(c['codigo'], 0)) for c in sorted(cat.values(), key=lambda c: c['num'])],
                'Catálogo de las 50 comunidades: código único, nombre oficial y nombre usado en la base.')
    return len(filas), len(sinpol), len(dup), len(en_campo & set(cod_de.values()))


def registro_cambios(con):
    """Altas, bajas y cambios ficha por ficha entre la base del 18-ago-2026 a las
    11:13 (antes de la depuración) y la base de campo actual (la de la entrega)."""
    a, b = ro(ANTES_DEPURACION), ro(QFIELD)
    tf = next(r[0] for r in b.execute("select name from sqlite_master where name like 'Fichas_Predios%' "
                                      "and type='table'"))
    tc = next(r[0] for r in b.execute("select name from sqlite_master where name like 'Cultivos_Agricolas%' "
                                      "and type='table'"))
    ta = next(r[0] for r in b.execute("select name from sqlite_master where name like 'Animales_Especies%' "
                                      "and type='table'"))
    campos = ['comunidad', 'clave_catastral', 'cod_poligono', 'parroquia', 'apellidos', 'nombres', 'cedula',
              'area_total', 'area_riego', 'area_sin_riego', 'es_ficha_hija', 'ficha_madre_id']

    def leer(c):
        return {r[0]: dict(zip(campos, r[1:])) for r in
                c.execute(f'select id, {", ".join(campos)} from "{tf}"')}

    def resumen(c, t, col):
        d = collections.defaultdict(lambda: [0, 0.0])
        for fid, v in c.execute(f'select ficha_id, {col} from "{t}"'):
            d[fid][0] += 1; d[fid][1] += v or 0
        return d
    fa, fb = leer(a), leer(b)
    ca, cb = resumen(a, tc, 'superficie_m2'), resumen(b, tc, 'superficie_m2')
    aa, ab = resumen(a, ta, 'cantidad'), resumen(b, ta, 'cantidad')
    a.close(); b.close()
    cod = dict(con.execute('select ficha_id, codigo_ficha from fichas').fetchall())

    def fmt(v):
        if isinstance(v, float):
            return esn(v, 2)
        return '' if v is None else str(v)

    def igual(x, y):
        if isinstance(x, (int, float)) and isinstance(y, (int, float)):
            return abs(x - y) < 0.005
        return (x or '') == (y or '') if not isinstance(x, (int, float)) else x == y
    filas = []
    for fid in sorted(set(fa) | set(fb), key=lambda i: cod.get(i, 'ZZZ' + i)):
        c = cod.get(fid, '(ficha retirada)')
        tit = lambda d: f"{d.get('apellidos') or ''} {d.get('nombres') or ''}".strip()  # noqa: E731
        if fid not in fb:
            filas.append((c, fid, tit(fa[fid]), 'Baja', 'ficha', 'existía', 'retirada')); continue
        if fid not in fa:
            filas.append((c, fid, tit(fb[fid]), 'Alta', 'ficha', '', 'nueva')); continue
        for k in campos:
            if not igual(fa[fid][k], fb[fid][k]):
                filas.append((c, fid, tit(fb[fid]), 'Modificación', k, fmt(fa[fid][k]), fmt(fb[fid][k])))
        for nombre, x, y, u in (('cultivos', ca, cb, 'm²'), ('animales', aa, ab, 'cabezas')):
            if x.get(fid, [0, 0])[0] != y.get(fid, [0, 0])[0] or abs(x.get(fid, [0, 0])[1] - y.get(fid, [0, 0])[1]) > 0.005:
                fv = lambda r: f'{r[0]} registros, {esn(r[1], 2 if u == "m²" else 0)} {u}'  # noqa: E731
                filas.append((c, fid, tit(fb[fid]), 'Modificación', nombre, fv(x.get(fid, [0, 0])),
                              fv(y.get(fid, [0, 0]))))
    crear_tabla(con, 'registro_cambios',
                [('codigo_ficha', 'TEXT'), ('ficha_id', 'TEXT'), ('titular', 'TEXT'), ('tipo_cambio', 'TEXT'),
                 ('campo', 'TEXT'), ('valor_antes', 'TEXT'), ('valor_despues', 'TEXT')],
                filas, 'Cambios ficha por ficha desde el 18-ago-2026 (antes de la depuración) hasta la base '
                       'entregada. Los valores originales se conservan en los respaldos.')
    return collections.Counter(f[3] for f in filas), collections.Counter(f[4] for f in filas)


def metadatos(con, resumen_cambios):
    filas = [
        ('Fecha de corte de la información', FECHA_CORTE),
        ('Versión', VERSION),
        ('Versión anterior', 'v1, entregada el 18 de septiembre de 2026'),
        ('Sistema de referencia', 'EPSG:32717 (WGS 84 / UTM zona 17 S)'),
        ('Fuente', 'Padrón de usuarios del sistema de riego Guanguilquí–Porotog (fichas de campo) y catastro '
                   'municipal del GAD Cayambe'),
        ('Qué cambia respecto de la v1', 'Solo se agrega: códigos de ficha y de comunidad, sector, fecha de corte '
         'y versión en las capas; «sector_riego» pasa a «sistema_riego_declarado»; tablas de correspondencia, '
         'fichas sin polígono, catálogo de comunidades y registro de cambios. Ninguna cifra cambia.'),
        ('Registro de cambios', resumen_cambios),
    ]
    crear_tabla(con, 'metadatos', [('elemento', 'TEXT'), ('valor', 'TEXT')], filas,
                'Fecha de corte, versión y cambios respecto de la entrega anterior.')


# ── 4. SHP y proyecto QGIS ─────────────────────────────────────────────────
def exportar_shp(gpkg):
    d = os.path.join(DESTINO, C_SHP)
    leeme = [f for f in os.listdir(d) if f.lower().endswith('.pdf')]
    for f in os.listdir(d):
        if f not in leeme:
            os.remove(os.path.join(d, f))
    con = sqlite3.connect(gpkg)
    capas = [r[0] for r in con.execute('select table_name from gpkg_contents')]
    con.close()
    con = sqlite3.connect(gpkg)
    for capa in capas:
        # El Shapefile corta los nombres a 10 caracteres. Los dos que la v1 ya
        # renombró se mantienen igual (TITULARES, PROP_CATAS) y los nuevos que
        # quedarían confusos llevan un nombre propio (ver el diccionario v2).
        cols = [r[1] for r in con.execute(f'pragma table_info("{capa}")') if r[1] != 'fid']
        alias = {c: SHP_ALIAS[c] for c in cols if c in SHP_ALIAS}
        sql = ''
        if alias:
            sel = ', '.join(f'{c} AS {alias[c]}' if c in alias else c for c in cols)
            sql = f'-dialect SQLite -sql "SELECT {sel} FROM {capa}" -nln {capa}'
        cmd = (f'call {OSGEO_ENV} && ogr2ogr -f "ESRI Shapefile" -lco ENCODING=UTF-8 "{d}" "{gpkg}" '
               f'{sql if sql else chr(34) + capa + chr(34)}')
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if r.returncode != 0:
            raise RuntimeError(f'ogr2ogr {capa}: {r.stderr[-400:]}')
    con.close()
    return capas


SHP_ALIAS = {
    'propietarios': 'TITULARES',              # igual que en la v1
    'propietario_catastro': 'PROP_CATAS',     # igual que en la v1
    'sistema_riego_declarado': 'SIST_RIEGO',
    'comunidad_oficial': 'COM_OFIC',
    'codigo_ficha_principal': 'COD_PRINC',
}


def ajustar_qgz():
    """El proyecto QGIS nombra el campo renombrado en su configuración."""
    qgz = os.path.join(DESTINO, C_QGIS, 'padron_riego_porotog.qgz')
    with zipfile.ZipFile(qgz) as z:
        ent = {i: z.read(i) for i in z.namelist()}
    for k in ent:
        if k.endswith('.qgs'):
            ent[k] = ent[k].replace(b'"sector_riego"', b'"sistema_riego_declarado"')
    with zipfile.ZipFile(qgz, 'w', zipfile.ZIP_DEFLATED) as z:
        for k, v in ent.items():
            z.writestr(k, v)


# ── 5. Excel con claves como texto ─────────────────────────────────────────
def excel(gpkg):
    import openpyxl
    from openpyxl.styles import Alignment, Font, PatternFill
    os.makedirs(os.path.join(DESTINO, C_XLS), exist_ok=True)
    ruta = os.path.join(DESTINO, C_XLS, 'TABLAS DE ATRIBUTOS v2.xlsx')
    con = sqlite3.connect(gpkg)
    wb = openpyxl.Workbook(); wb.remove(wb.active)
    hojas = [('Predios investigados', 'predios_investigados'), ('Fichas', 'fichas'),
             ('Correspondencia', 'correspondencia_fichas'), ('Fichas sin polígono', 'fichas_sin_poligono'),
             ('Catálogo comunidades', 'catalogo_comunidades'), ('Cultivos', 'cultivos'), ('Animales', 'animales'),
             ('Registro de cambios', 'registro_cambios'), ('Metadatos', 'metadatos')]
    texto = {'clave_catastral', 'clave_declarada', 'cedula', 'clave_predio_principal', 'codigos_ficha',
             'telefono_celular', 'telefono_casa'}
    for titulo, tabla in hojas:
        cols = [r[1] for r in con.execute(f'pragma table_info("{tabla}")') if r[1] not in ('geom', 'fid')]
        ws = wb.create_sheet(titulo)
        for j, c in enumerate(cols, 1):
            x = ws.cell(1, j, c); x.font = Font(name='Arial', bold=True, color='FFFFFF', size=10)
            x.fill = PatternFill('solid', fgColor='1F3864'); x.alignment = Alignment(wrap_text=True)
            ws.column_dimensions[openpyxl.utils.get_column_letter(j)].width = 22 if c not in (
                'cultivos_predio', 'animales_predio', 'marcas_revision', 'valor') else 50
        for i, fila in enumerate(con.execute(f'select {", ".join(chr(34) + c + chr(34) for c in cols)} '
                                             f'from "{tabla}"'), 2):
            for j, (c, v) in enumerate(zip(cols, fila), 1):
                x = ws.cell(i, j, '' if v is None else (str(v) if c in texto else v))
                x.font = Font(name='Arial', size=9)
                if c in texto:
                    x.number_format = '@'
        ws.freeze_panes = 'A2'
        ws.auto_filter.ref = ws.dimensions
    con.close()
    wb.save(ruta)
    aplicar_formatos(ruta)
    return ruta


def main():
    cat = catalogo()
    gpkg = copiar_v1()
    con, cult, textos, sin_com = gpkg_v2(gpkg, cat)
    print(f'Capas ajustadas · cultivos con tipo y «otro»: {len(cult)} {cult} · predios cuyo texto de cultivos '
          f'cambió además del formato: {textos} · predios sin comunidad de catálogo: {sin_com}')
    nf, nsp, ndup, ncampo = tablas_nuevas(con, cat)
    print(f'Correspondencia: {nf} fichas · sin polígono: {nsp} · duplicados marcados: {ndup} · '
          f'cédulas en campo marcadas: {ncampo}')
    tipos, campos = registro_cambios(con)
    res = ', '.join(f'{k}: {esn(v)}' for k, v in tipos.items())
    print('Registro de cambios:', dict(tipos), dict(campos))
    metadatos(con, f'{res} (detalle en la tabla registro_cambios)')
    con.commit(); con.execute('vacuum'); con.close()
    capas = exportar_shp(gpkg)
    print('SHP exportados:', capas)
    ajustar_qgz()
    print('Excel:', excel(gpkg))
    print('✔', DESTINO)


if __name__ == '__main__':
    main()
