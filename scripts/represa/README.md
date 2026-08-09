# Cartografía de la represa de Porotog

Cómo se convirtieron los tres planos PDF del Consorcio CCSPT en capas
georreferenciadas, un modelo de terreno y la pantalla `/represa` de la web.

Escrito el 6 de agosto de 2026.

---

## Por qué hizo falta todo esto

Los planos (`CARTOGRAFIA REPRESA/CCSPT-GEN-AMB-PL-DT-100{0,1,2}-R1.pdf`) salieron
de AutoCAD Civil 3D 2026. **No son GeoPDF**: no traen sistema de coordenadas ni
georreferencia, así que ningún SIG los ubica solo. Pero sí traen el dibujo como
geometría vectorial, y el plano 1000 incluye una tabla con las coordenadas UTM
de los 29 vértices del límite de proyecto. De ahí sale todo lo demás.

Dos obstáculos que condicionaron el enfoque:

1. **GDAL solo ve una parte del dibujo.** Abre estos PDF y expone 15 capas, las
   que quedaron marcadas como *optional content group*. El límite de proyecto,
   los bancos de materiales y las obras se dibujaron sin esa marca y GDAL no los
   ve. Por eso `02_extraer_pdf.py` interpreta el PDF por su cuenta: recupera 55
   capas CAD, y de las que no tienen nombre las separa por color.
2. **Las tablas de coordenadas no son texto.** AutoCAD las vectorizó (usan fuente
   SHX), así que no hay nada que leer por software. La tabla del límite se
   transcribió a mano y se validó contra el área que declara el propio plano.

---

## La cadena de scripts

Se ejecutan en orden desde `padron-app/`, con el Python de OSGeo4W (trae GDAL,
pyproj y shapely). `pypdf` está instalado aparte en `~/.pylibs/carto` para no
tocar el entorno de QGIS.

```bash
PYTHONUTF8=1 /c/OSGeo4W/bin/python-qgis.bat -X utf8 scripts/represa/01_recortar_curvas_5m.py
PYTHONUTF8=1 /c/OSGeo4W/bin/python-qgis.bat -X utf8 scripts/represa/02_extraer_pdf.py
PYTHONUTF8=1 /c/OSGeo4W/bin/python-qgis.bat -X utf8 scripts/represa/03_georreferenciar.py
PYTHONUTF8=1 /c/OSGeo4W/bin/python-qgis.bat -X utf8 scripts/represa/04_generar_capas.py
PYTHONUTF8=1 /c/OSGeo4W/bin/python-qgis.bat -X utf8 scripts/represa/05_modelo_terreno.py
```

| Script | Qué hace | Salida |
|---|---|---|
| `01_recortar_curvas_5m.py` | Recorta las curvas de nivel del cantón a la zona | `curvas_5m_zona.gpkg` (2,7 MB de 71 MB) |
| `02_extraer_pdf.py` | Interpreta los PDF: geometría, capas CAD, colores, textos | `plano_100{0,1,2}.gpkg` |
| `03_georreferenciar.py` | Calcula la transformación a UTM 17S y la valida | `georref_1000.json` |
| `04_generar_capas.py` | Aplica la transformación y exporta las capas | `public/geo/represa/*.geojson` + `represa_utm.gpkg` |
| `05_modelo_terreno.py` | Interpola el modelo de terreno y la malla 3D | `dem_represa.tif` + `terreno.json` |
| `06_capas_padron.py` | Predios por sector y huella, para dar la escala | `predios_por_sector.geojson` + `sectores_huella.geojson` + `magnitud.json` |
| `07_validar_contra_consorcio.py` | Contrasta nuestra reconstrucción contra la geometría oficial | informe por consola |

Los intermedios van a `CARTOGRAFIA REPRESA/procesado/` (fuera del repo).

---

## Qué tan fiable es la georreferenciación

**RMS 0,216 m** sobre 19 vértices de control. Tres comprobaciones, dos de ellas
independientes entre sí:

| Comprobación | Resultado |
|---|---|
| Escala que resulta del ajuste | 1:1.998 · el plano declara **1:2.000** |
| Área del polígono transcrito | 635.548 m² · el plano declara **636.016 m²** (0,07 %) |
| Curvas del levantamiento contra las curvas regionales de 5 m | mediana **3,4 m**, p90 16,9 m, sobre 708 puntos |

La tercera es la que más pesa: contrasta contra una cartografía que no tiene
ninguna relación con estos planos. Si la georreferenciación estuviera desplazada,
daría decenas o cientos de metros.

El ajuste es una **similitud** (escala uniforme + rotación + traslación), que es
lo físicamente correcto para un plano CAD. Se ajusta también una afín de 6
parámetros como control: si mejorara mucho el residual sería señal de que el
plano tiene dos escalas o de que hay puntos mal emparejados. No es el caso
(0,185 m contra 0,216 m).

El emparejamiento de puntos de control es **robusto a errores** (RANSAC
exhaustivo sobre las 351 parejas posibles). Hizo falta: con mínimos cuadrados a
secas, un solo rótulo mal identificado llevaba el RMS de centímetros a 201 m.

---

## El GeoPackage del consorcio (`GIS POROTOG.gpkg`, recibido el 7-ago-2026)

**Llegó incompleto.** El archivo pesa 17 MB pero casi todo es un proyecto QGIS
embebido: define **50 capas CAD** y todas apuntan a un `./POROTOG.gpkg` **que no
vino**. De datos propios trae 43 geometrías sueltas.

Aun así sirvió para lo más importante que se podía hacer con él:

### Validación contra la geometría oficial

Dos de esas capas (`01-01-CAPTACION$0$CA-0.05` y `03-01-TANQUE$0$CH-0.05`)
también las reconstruimos nosotros desde el PDF, y vienen en UTM real. Comparadas
vértice a vértice (`07_validar_contra_consorcio.py`):

| | |
|---|---|
| Vértices comparados | **431** |
| Distancia mediana | **0,144 m** |
| Media | 0,196 m |
| Percentil 90 | 0,475 m |
| Máxima | 0,695 m |

Es la comprobación más fuerte de todas las que se hicieron, porque contrasta
contra la geometría original salida del CAD del consorcio, no contra el plano.
**Confirma el RMS de 0,216 m** obtenido por otra vía: la reconstrucción desde PDF
es correcta a nivel de centímetros.

### Lo que falta pedir: `POROTOG.gpkg`

Es el archivo con los datos de esas 50 capas. Lo que resolvería:

1. **Las cotas de las curvas de nivel.** El proyecto define
   `C3D-Superficie_cotas` como capa de **textos** y las geometrías del archivo
   son **3D**. Es decir: allí la altura sí es un dato, no un rótulo dibujado.
   Eso desbloquea el modelo de terreno con precisión de obra, que es la
   limitación principal de todo este trabajo.
2. **Dieciséis capas que no están en los tres PDF que recibimos**, algunas con
   peso ambiental y de obra:
   `LIMITE DE ESCOMBRERA`, `TOP-AREA CAMPAMENTO`, `TOP-CAPTACION`, `TOP-CAUCE`,
   `TOP-AGUA`, `TOP-OJO DE AGUA`, `TOP-ALCANTARILLA`, `TOP-TANQUE`,
   `TOP-TUBO AGUA`, `TOP-PISCINA`, `TOP-CAJA`, `TOP-BORDILLO`,
   `TOP-LIND CERCA VIVA`, `TOP-POSTE DE LUZ`, `TOP-PUENTE`, `TOP-CONSTRUCCIÓN`.
3. **Georreferenciación de origen** (EPSG:32717), sin pasar por nuestra
   reconstrucción.

Detalle menor pero conviene decírselo: en su proyecto los nombres de capa con
tilde están mal codificados (`TOP-CONSTRUCCIÃ“N` en vez de `TOP-CONSTRUCCIÓN`),
un UTF-8 leído como latin-1 en algún paso de la conversión desde AutoCAD.

---

## Hallazgo: error en la tabla del consorcio

**La fila 23 de la tabla del plano `CCSPT-GEN-AMB-PL-DT-1000-R1` está
equivocada.**

|  | Norte | Este |
|---|---|---|
| Dice la tabla | 9.982.773,250 | 820.757,241 |
| Según el dibujo del propio plano | 9.983.977,666 | 818.592,180 |

Está 2.478 m fuera de sitio, al sureste. Se demuestra sin salir del plano:

- Con el valor de la tabla, el polígono se cruza consigo mismo y da
  **338.163 m²**, contra los **636.016 m²** que el plano declara en su recuadro.
- Sin ese vértice, el área da 635.548 m²: faltan 467,7 m².
- Con la coordenada deducida del dibujo, da 635.947 m² — a **69 m²** de lo
  declarado (0,011 %).

Las 28 filas restantes son correctas: proyectadas sobre el plano, todas caen
sobre el límite dibujado a menos de 2 m.

**Las capas publicadas usan la coordenada corregida**, y eso queda anotado en las
propiedades de `limite_proyecto.geojson` para que nadie la herede sin enterarse.
Conviene reportárselo al consorcio: es un error en su entregable.

---

## Limitaciones que hay que conocer

**El modelo de terreno tiene la resolución vertical de la cartografía regional
(5 m), no la del levantamiento.** Las curvas de 1 m del consorcio están
georreferenciadas y se publican, pero **su cota no se pudo determinar**: en el
PDF la altura está escrita al lado de cada curva y AutoCAD vectorizó esos
rótulos. Se intentó deducirla muestreando el modelo regional, y solo 50 de 575
curvas quedaron determinadas sin ambigüedad; el resto cae a mitad de camino
entre dos valores posibles y se descartó en vez de inventarles una cota.

**El datum vertical del levantamiento no es verificable con lo que hay.** Como
la cota se lee del propio modelo regional, comparar ambas fuentes sería circular.

**La superficie de los bancos de materiales es una estimación.** El plano los
dibuja como sombreado hexagonal, sin contorno: se agrupó el sombreado por
cercanía a su rótulo y se tomó la envolvente convexa. Da 17,27 + 8,40 + 14,79 ha.
No es el polígono topográfico del consorcio.

**Nada de esto sirve para medir volúmenes de obra ni para catastro legal.** Es
cartografía de referencia y de análisis.

---

## Lo que conviene pedirle al consorcio

Resolvería de golpe las tres limitaciones anteriores:

1. **La superficie de Civil 3D** (LandXML, raster o los puntos XYZ del
   levantamiento). Las capas del PDF se llaman `C3D-Superficie_*`, así que esa
   superficie existe. Con ella el modelo de terreno pasa a tener precisión de
   obra y el 3D deja de apoyarse en cartografía regional.
2. **El DWG original**, que evita todo el trabajo de reconstrucción desde PDF.
3. **La corrección de la fila 23** de la tabla de coordenadas.

---

## La escala del proyecto

La obra sola no dice nada: 63,6 ha en medio del páramo. Lo que la mide es verla
contra el sistema de riego al que va a servir, y por eso la pantalla trae también
los predios del padrón pintados por sector, su huella y la red de canales.

| | |
|---|---|
| Represa | **63,6 ha** |
| Superficie bajo riego | **6.081 ha** |
| Predios investigados | **6.825** |
| Canales de riego existentes | **41,5 km** |
| Por cada hectárea de represa | **96 ha regadas** |

| Sector | Predios | Superficie de riego |
|---|---|---|
| Sector 1 | 3.229 | 3.019 ha |
| Sector 2 | 2.271 | 1.555 ha |
| Sector 3 | 1.154 | 1.507 ha |
| Sin asignar | 171 | — |

El predio investigado más cercano está a **2,83 km** de la represa, así que ambas
cosas caben en un mismo encuadre; el botón «Ver todo» del panel alterna entre la
obra y el sistema completo.

Estas capas van **solo en el mapa 2D**. En el visor 3D no aparecen: el modelo de
terreno cubre 2 x 2,4 km alrededor de la presa y los predios caen fuera, así que
allí no aportarían nada.

Sobre el sector de cada predio: sale del campo `sector_investigacion` de la
ficha (5.707 casos) y, cuando viene vacío, se resuelve mirando dentro de qué
polígono de `sectores.geojson` cae el punto (947 más). Los 171 que no caen en
ninguno quedan como «Sin asignar» en gris — no se les inventa un sector. La
regla de canonización **no se reimplementa aquí**: vive en `comunidades_canon.py`
y en el script que genera esa capa.

---

## La pantalla web

`/represa`, restringida a los roles `admin` y `tecnico` en `App.tsx`
(`RoleProtectedRoute`), igual que Reportes. El cliente (Consorcio) no entra ni
escribiendo la URL, y el enlace tampoco le aparece en el menú.

- `src/components/represa/RepresaPage.tsx` — mapa 2D con las capas
- `src/components/represa/TerrenoVista3D.tsx` — visor 3D del relieve (Three.js)

Tres decisiones de rendimiento, por si alguien las toca:

- **Las capas se descargan solo al encenderlas.** Con todo activo son ~2,5 MB.
- **El mapa usa `preferCanvas`.** Las obras del plano son más de 3.000 trazos; en
  SVG eso son 3.000 nodos en el DOM y el mapa se arrastra al hacer zoom.
- **Three.js va en carga diferida, en dos niveles** (la página y el visor). Si se
  importara normal, sus ~600 KB los descargaría también el cliente, que ni
  siquiera puede abrir esta pantalla. Se ve en el build: `TerrenoVista3D` sale
  como un chunk aparte de 558 KB.

---

## Reglas que se respetaron

- **No se tocó el GPKG de curvas de nivel del proyecto de QField.** Se abre en
  solo lectura y `01_recortar_curvas_5m.py` aborta si alguien apunta la salida
  dentro de `~/QField/`: lo que quede ahí, QFieldSync se lo lleva a las tablets.
  (Aparte: esa capa son 71 MB de todo el cantón viajando a cada tablet. Sustituirla
  por el recorte las aligeraría, pero es un cambio en el proyecto de campo y hay
  que hacerlo con ventana coordinada, no de pasada.)
- **`pypdf` se instaló aislado** en `~/.pylibs/carto`, no en el Python de QGIS.
- **No se tocó producción.** El deploy es aparte y requiere `npm run build`
  antes de `firebase deploy` (publica `dist/`).
