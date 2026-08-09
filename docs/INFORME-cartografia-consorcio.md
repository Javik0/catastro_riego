# Cartografía de la represa de Porotog — estado y solicitud de información

**Proyecto:** Estudio definitivo de la presa del río Porotog para los sistemas de riego Guanguilquí y Porotog · Parroquia Cangahua, cantón Cayambe  
**Asunto:** Resultado del procesamiento de la cartografía entregada y pedido de un archivo faltante  
**Fecha:** 9 de agosto de 2026

---

## En una página

Recibimos la cartografía del proyecto en dos entregas: primero tres planos en
PDF y después un GeoPackage. Con ellas construimos las capas digitales de la
represa y las incorporamos al visor del padrón de regantes.

El resultado es bueno: **la cartografía quedó ubicada sobre el terreno con una
exactitud de 15 a 20 centímetros**, y así lo confirman tres comprobaciones
distintas e independientes entre sí.

Quedan dos cosas por resolver, ninguna grave, ambas del lado del consorcio:

1. **Falta un archivo.** El GeoPackage enviado contiene el proyecto de trabajo
   (la lista de las 50 capas y cómo se dibujan), pero no los datos de esas capas:
   apuntan a un archivo `POROTOG.gpkg` que no venía en el envío.
2. **Hay un error en la tabla de coordenadas del plano del límite de proyecto**,
   en el vértice 23. Está probado con los datos del propio plano.

---

## Qué se recibió y qué se hizo con ello

### Primera entrega: tres planos en PDF

Los planos `CCSPT-GEN-AMB-PL-DT-1000`, `1001` y `1002` son dibujos vectoriales
salidos de AutoCAD Civil 3D. Contienen todo el dibujo, pero **no llevan
información de ubicación geográfica**: un programa de mapas no sabe dónde
colocarlos en el terreno.

Para ubicarlos se usó la tabla de coordenadas UTM que el propio plano 1000
incluye, la de los 29 vértices del límite de proyecto. Con esos puntos se calculó
la correspondencia entre el dibujo y el terreno real, y con ella se convirtió
todo el contenido de los planos a coordenadas geográficas: límite de proyecto,
bancos de materiales, eje de presa, túnel, captación, tanque disipador, canal,
vertedero, rápida, curvas de nivel, río, caminos y puntos de control GNSS.

### Segunda entrega: el GeoPackage `GIS POROTOG.gpkg`

Este archivo llegó **incompleto**. Pesa 17 MB, pero casi todo ese peso es el
proyecto de QGIS guardado dentro: la lista de las 50 capas del levantamiento y
la forma en que se representan. Los datos de esas capas no venían — todas
apuntan a un archivo `./POROTOG.gpkg` que no estaba en el envío.

De información propia, el archivo trae 43 elementos sueltos de geometría.

---

## Lo que sí permitió comprobar

Aunque incompletos, esos 43 elementos resultaron muy valiosos, porque dos de sus
capas (`01-01-CAPTACION` y `03-01-TANQUE`) son capas que nosotros ya habíamos
reconstruido a partir de los PDF. Al venir en coordenadas reales, permitieron
comparar nuestra reconstrucción contra el original.

**Resultado de la comparación, sobre 431 vértices:**

| Medida | Valor |
|---|---|
| Diferencia mediana | **0,144 m** |
| Diferencia media | 0,196 m |
| Percentil 90 | 0,475 m |
| Diferencia máxima | 0,695 m |

En términos prácticos: las capas que generamos a partir de los planos coinciden
con la geometría original del consorcio con una diferencia típica de **14
centímetros**, y en el peor caso 70 centímetros.

Esta comprobación se suma a otras dos que ya se habían hecho:

| Comprobación | Resultado |
|---|---|
| Escala deducida del cálculo frente a la escala declarada en el plano | 1:1.998 frente a 1:2.000 |
| Área del límite calculada frente al área declarada en el plano | 635.548 m² frente a 636.016 m² (0,07 % de diferencia) |
| Contraste con la cartografía regional de curvas de nivel de 5 m | 3,4 m de diferencia mediana en 708 puntos |

Las tres apuntan a lo mismo por caminos distintos. **La cartografía está
correctamente ubicada.**

---

## Punto a corregir: el vértice 23 del límite de proyecto

La tabla de coordenadas del plano `CCSPT-GEN-AMB-PL-DT-1000-R1` tiene un error en
la fila 23:

| | Norte | Este |
|---|---|---|
| Lo que dice la tabla | 9.982.773,250 | 820.757,241 |
| Donde el propio plano lo dibuja | 9.983.977,666 | 818.592,180 |

La diferencia es de **2.478 metros**, hacia el sureste.

No es una interpretación: se demuestra con los datos del mismo plano.

- Usando el valor de la tabla, el polígono del límite **se cruza consigo mismo** y
  encierra 338.163 m².
- El plano declara, en su propio recuadro, un área de **636.016 m²**.
- Quitando ese vértice, el área da 635.548 m²: faltan 468 m², que es justamente
  el pequeño saliente que el vértice 23 forma en el dibujo.
- Sustituyéndolo por la coordenada que se lee del dibujo, el área cierra en
  635.947 m², a **69 m² del valor declarado** (0,011 % de diferencia).

Las 28 filas restantes de la tabla son correctas: proyectadas sobre el plano,
todas caen sobre la línea del límite con menos de 2 m de separación.

**Mientras tanto**, nuestras capas usan la coordenada corregida, y así queda
anotado en las propiedades de la capa para que nadie la utilice sin saberlo. Se
solicita la confirmación o corrección oficial por parte del consorcio.

---

## Lo que se solicita

### 1. El archivo `POROTOG.gpkg`

Es el archivo de datos que las 50 capas del proyecto enviado están buscando. Como
el proyecto lo referencia con ruta relativa (`./POROTOG.gpkg`), todo indica que
está en la misma carpeta y quedó fuera del envío por descuido.

**Por qué importa.** Resolvería la limitación principal que hoy tiene el trabajo:

> Las curvas de nivel del levantamiento tienen equidistancia de 1 metro, mucho
> más detalle que la cartografía regional disponible. Sin embargo, en los PDF la
> altura de cada curva está **dibujada como rótulo**, no guardada como dato: al
> exportar desde AutoCAD, esos números se convirtieron en trazos. Un programa
> puede dibujarlos, pero no leerlos.
>
> En el proyecto enviado se ve que en el archivo faltante la altura **sí es un
> dato**: la capa `C3D-Superficie_cotas` está declarada como capa de textos y las
> geometrías son tridimensionales.

Con ese archivo, el modelo digital del terreno pasaría de apoyarse en cartografía
regional de 5 metros a tener la precisión del levantamiento de la obra.

Sirve igualmente cualquiera de estas alternativas, en orden de preferencia:

1. `POROTOG.gpkg` (el que el proyecto busca).
2. La superficie de Civil 3D exportada como **LandXML**, o como raster de
   terreno, o los puntos del levantamiento en XYZ.
3. El **DWG** original.

### 2. Dieciséis capas que no están en los planos recibidos

El proyecto enviado las declara, pero no aparecen en ninguno de los tres PDF.
Varias tienen peso ambiental y de obra:

`LIMITE DE ESCOMBRERA` · `TOP-AREA CAMPAMENTO` · `TOP-CAPTACION` · `TOP-CAUCE` ·
`TOP-AGUA` · `TOP-OJO DE AGUA` · `TOP-ALCANTARILLA` · `TOP-TANQUE` ·
`TOP-TUBO AGUA` · `TOP-PISCINA` · `TOP-CAJA` · `TOP-BORDILLO` ·
`TOP-LIND CERCA VIVA` · `TOP-POSTE DE LUZ` · `TOP-PUENTE` · `TOP-CONSTRUCCIÓN`

El límite de escombrera y el área de campamento son especialmente relevantes para
la evaluación ambiental y para el análisis de afectación a predios.

### 3. Confirmación del vértice 23

Según lo expuesto más arriba.

---

## Observación menor

En el proyecto enviado, los nombres de capa que llevan tilde están mal
codificados: aparece `TOP-CONSTRUCCIÃ“N` donde debería decir `TOP-CONSTRUCCIÓN`.
Es un problema de codificación de caracteres en algún paso de la conversión desde
AutoCAD. No afecta a la geometría, pero conviene revisarlo antes de que esos
nombres pasen a los entregables finales.

---

## Estado actual del trabajo

La cartografía de la represa ya está incorporada al visor del padrón de regantes,
en una vista de uso interno del equipo consultor. Incluye el límite de proyecto,
los bancos de materiales, las obras, el área protegida del Parque Nacional
Cayambe Coca, la hidrografía, los caminos y las curvas de nivel, junto con una
vista tridimensional del relieve de la zona de presa.

Sobre esa misma vista se superponen los datos del padrón —los 6.825 predios
investigados agrupados por sector y los 41,5 km de canales— lo que permite ver la
obra en relación con el sistema al que servirá:

| | |
|---|---|
| Superficie del proyecto de la represa | 63,6 ha |
| Superficie bajo riego del sistema | 6.081 ha |
| Predios investigados | 6.825 |
| Por cada hectárea de represa | **96 hectáreas regadas** |

Todo el procesamiento es reproducible y está documentado. Cuando llegue el
archivo faltante, la actualización de las capas y del modelo de terreno es
inmediata.
