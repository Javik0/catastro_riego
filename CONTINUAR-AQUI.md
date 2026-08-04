# Punto de continuación — Padrón Guanguilquí–Porotog

> Escrito el 4 de agosto de 2026 al cerrar la sesión anterior por límite de
> contexto. **Este archivo es el punto de partida del siguiente chat.**

---

## Qué hay que hacer ahora (en orden)

### 1. Publicar la sincronización del 4 de agosto ← EMPEZAR POR AQUÍ

Los técnicos sincronizaron y el `data.gpkg` local ya tiene datos nuevos, pero
**la web y los informes siguen mostrando el corte del 31 de julio**.

| | Publicado (31 jul) | En el gpkg (4 ago) |
|---|---|---|
| Fichas | 6.823 | **6.826** |
| Principales | 4.301 | **4.305** |
| Cultivos | 12.984 | **13.782** (+798) |
| Animales | 9.819 | **9.836** |
| Adicionales pendientes | 577 | **115** ← avanzaron mucho |

Comandos, en este orden (desde `padron-app/`):

```bash
python -X utf8 scripts/export_geojson.py
python -X utf8 scripts/generar_capas_sectores_comunidades.py
python -X utf8 scripts/generar_gpkg_cliente.py
python -X utf8 scripts/generar_proyecto_qgis_cliente.py
npm run build
firebase deploy --only hosting
python -X utf8 scripts/generar_informe_consolidado.py
python -X utf8 scripts/generar_anexo_operadores.py
```

Luego **verificar contra producción** (no contra los archivos locales) y copiar
los informes a `Escritorio\INFORME ENCUESTA REGANTES\`.

Qué vigilar al correrlo:
- El aviso `⚠ N comunidades con caudal heredado` debe seguir apareciendo.
- El cuadre de las capas debe quedar en **−11,38 l/s** (son 11 fichas
  individuales discrepantes). Si cambia mucho, revisar antes de publicar.
- Los informes toman la fecha de corte sola, de la última ficha del gpkg.

### 2. Las capas de límites de comunas

`comunas_cy.zip` ya llegó completo y **está extraído en `capas_recibidas/`**.
(El `LIMITES_COMUNAS_PS.dwg.xml` anterior estaba vacío y el otro era solo
metadata; ese camino está descartado.)

Qué contiene:
- Shapefile de **polígonos**, 117 registros, **WGS 84 / UTM 17S** (nuestro CRS)
- Extensión E 798.192–837.434 / N 9.987.106–10.022.096 → **cubre nuestra zona**
- El nombre de la comuna está en el campo **`TEXT`** (los demás campos son
  basura de la conversión desde AutoCAD: ENTITY, HANDLE, LAYER, COLOR…)

**Hallazgo a resolver:** son las comunas de **todo el cantón Cayambe**, no solo
las del sistema. De nuestras 51 comunidades, **solo 20 cruzan por nombre**:

```
ASOCIACION POROTOG, CARRERA, CHAMBITOLA, CHINCHINLOMA, COCHAPAMBA, EL MANZANO,
IZACATA, LA CANDELARIA, LA LIBERTAD, LARCACHACA, MILAGRO, OTONCITO, PAMBAMARCA,
PAMBAMARQUITO, PITANA ALTO, PUCARA, SAN ANTONIO, SAN JOSE,
SANTA MARIANITA DE PINGULMI, SANTA ROSA DE PINGULMI
```

Las 31 restantes (ALPAKA, las asociaciones, COMUNA POROTOG, CANGAHUA PUNGO…) no
tienen polígono con ese nombre. Antes de sustituir nada, **comparar estos
límites oficiales contra los que ya generamos** por dissolve de los predios
(`public/geo/comunidades.geojson`) y reportar cuánto difieren. Puede que algunas
sean sectores dentro de una comuna mayor, o que tengan otro nombre en el
shapefile.

Armando espera aviso cuando estén subidas las capas.

---

## Estado del proyecto

### Web y entregables — al día salvo la sincronización del 4 ago
- Producción: https://invs-riego-comunitario.web.app
- Deploy: **siempre `npm run build` antes** de `firebase deploy` (publica `dist/`)
- Verificar **contra la URL**, nunca contra los archivos locales

### Informes — 6 capítulos + consolidado + anexo, todos regenerables
En `Escritorio\INFORME ENCUESTA REGANTES\` (archivo 0 = el consolidado).
Se regeneran con `generar_informe_consolidado.py`, que llama a los seis.

### QField — el proyecto de campo está al día
Pestaña «➕ PREDIO ADICIONAL», encuesta precargada, desplegable de comunidad
numerado 01–50. Los técnicos ya lo tienen.

---

## Reglas que NO hay que romper

1. **Nunca `current_value()`** en un FilterExpression de QField: escribe NULL al
   guardar. Borró 375 fichas una vez y 553 comunidades otra.
2. **Nunca una expresión en el `Value`** de un ValueRelation: QGIS la evalúa,
   QField no — mostraba «Sector 3» repetido 50 veces. Debe ser un nombre de
   columna real.
3. **El caudal no se suma ficha a ficha.** Fuente única:
   `public/geo/caudal_por_comunidad.json`. Ver `docs/METODOLOGIA-CAUDAL.md`.
4. **El nombre de comunidad se canoniza solo en** `scripts/comunidades_canon.py`.
   Si cada script normaliza a su manera, el dato se pierde en silencio.
5. **Los respaldos van fuera de la carpeta de QFieldCloud** —
   `scripts/respaldo_seguro.py`. Si quedan dentro, QFieldSync los sube.
6. **Personas ≠ predios.** Para escolaridad/conocimiento se usan las fichas
   principales; para superficie/producción, todas. Nunca se suman los universos.
7. Los scripts que escriben en el `data.gpkg` **simulan por defecto** y solo
   escriben con `--aplicar`. Los triggers espaciales del GeoPackage hay que
   retirarlos y recrearlos (usan `ST_IsEmpty`, que SQLite puro no trae).

---

## Pendientes de terceros

**Los coordina JAVIKO — no requieren acción técnica hasta que respondan:**

1. **491 fichas de ALPAKA** con tarifas de 672 y 308 USD «mensuales» (mediana
   del sistema: 3 USD). Excluidas del informe.
2. **Granja avícola de Asociación Rosalía**: seis titulares declaran 10.000
   gallinas cada uno sobre el mismo predio. 60.000 aves excluidas.
3. **Avellaneda, Hernán Timpe y Hda. San Francisco**: su caudal coincide exacto
   con el de su comunidad de origen. Son 71,5 l/s. Si tuvieran llave propia, el
   sistema pasaría de 950 a 1.021 l/s.
4. **Servicios básicos**: registrado al 68 %, en levantamiento.

**Trabajo de campo pendiente:**
- 31 predios por levantar y 17 por marcar, en
  `docs/REVISION-observaciones-con-clave.md`
- 148 fichas con áreas dudosas, en `docs/REVISION-AREAS-fichas-a-verificar.md`
- 111 fichas sin comunidad (66 principales necesitan verificación en campo)

**Sin resolver desde hace tiempo:**
- Punto 4 de la nota de Armando: «visualizar en QGIS y QField con los atributos
  de la ficha» — nunca se aclaró qué espera.

---

## Datos del entorno

```
data.gpkg    C:\Users\HP\QField\cloud\porotog_levantamiento_offline\data.gpkg
proyecto     ...\POROTOG LEVANTAMIENTO_qfield_cloud.qgs
repo         padron-app  ·  github.com/Javik0/catastro_riego  ·  rama main
PyQGIS       C:\OSGeo4W\bin\python-qgis.bat
respaldos    Escritorio\CAYAMBE CATASTRO RIEGO\respaldos_qgs\AAAA-MM-DD\
informes     Escritorio\INFORME ENCUESTA REGANTES\
```

Python en Windows: usar `PYTHONUTF8=1` y `-X utf8`, o los emojis de los scripts
rompen la consola.
