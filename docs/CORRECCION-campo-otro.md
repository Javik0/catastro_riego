# Corrección: el campo libre «Otros» de cultivos y animales

> Aplicada el **18 de agosto de 2026**. Script: `scripts/depurar_campo_otro.py`.
> Aprobada por JAVIKO ese mismo día (bloques A + B + C).

## El hallazgo

La depuración del 15 de agosto (`depurar_cultivos_y_animales.py`) unificó la
escritura de `tipo_cultivo` (37 → 19 tipos) y de `especie` (31 → 15). Quedó algo
fuera: cuando el técnico elige **«Otros»** en el formulario y escribe el nombre a
mano, ese texto va a otro campo — `tipo_cultivo_otro` / `especie_otro` — que
**nunca se depuró**.

No es un campo interno. `generar_capitulo_produccion.py:118` lo publica tal cual
en el capítulo que se entrega al consorcio y en `Produccion_Agropecuaria.xlsx`.
La arveja estaba escrita de **once maneras** contando mayúsculas —ARBEJA,
ARVERJA, ALBERJA, ARVEJA, ALVERJA, ARBERJA, ARBEJAS, ATBEJA…— y salía como once
cultivos distintos.

El daño no era solo una lista sucia. El agrupador del informe busca la palabra
`arveja` dentro del nombre, así que **51 de las 57 filas de arveja caían en
«Otros cultivos»** en lugar de «Cereales y leguminosas». Lo mismo con la alfalfa
mal escrita, que no llegaba a «Pastos», y con los patrones, que no llegaban a
«Flores».

## Qué se hizo

| bloque | registros | qué |
|---|---:|---|
| **A** escritura | 231 | Cada variante a un nombre canónico, en formato Título y sin espacios sobrantes. **No** cambia superficies, cantidades ni tipos. |
| **B** categoría existente | 48 | El texto libre ya era una opción del catálogo: «Otros»+CHOCHO → Chocho, +CEBADA, +TRIGO, +HORTALIZAS. En animales: borrego y chivo → *Ovejas / Cabras*; caballo y burro → *Equinos*; yunta → *Vacas en producción*. |
| **C** texto redundante | 3 | «Vacas en producción» + «VACAS» al lado: se vació el campo libre. |
| **!** no coincide | 10 | **No se tocaron.** Ver abajo. |

Como el bloque B dejó 8 fichas con la misma especie repetida, se corrió después
`depurar_cultivos_y_animales.py --aplicar`, que fusionó 7 sumando y retiró 1
copia exacta (−2 cabezas).

## El resultado

| | antes | después |
|---|---:|---:|
| Nombres de cultivo distintos en el entregable | 80 | **57** |
| Especies distintas | 38 | **25** |
| Grupo «Otros cultivos» del informe | 78,90 ha | **62,24 ha** |
| Registros de cultivo | 13.626 | 13.626 |
| Superficie cultivada | 7.088,98 ha | **7.088,98 ha** |
| Registros de animales | 9.662 | 9.654 |
| Cabezas | 169.473 | 169.471 |

**Ninguna cifra del padrón se movió** salvo las 2 cabezas de la copia exacta: no
cambia el conteo de fichas ni la superficie del sistema, así que esta corrección
**no activa el aviso a Armando de la regla 11**. Las 16,66 ha que salen de «Otros
cultivos» no desaparecen: se reparten a Cereales (+11,4), Pastos (+3,5) y Flores
(+1,6), que es donde debían estar.

## Actualización del 18-ago (misma tarde): uso del suelo reclasificado

JAVIKO decidió, viendo la lista de arriba: POTRERO, LADERA y PENDUENTE no son un
cultivo, son cobertura del terreno igual que «Pasto no mejorado» — ahí van.
CASCAJO y TERRENO PREPARADO (con y sin «para arar») van a «Baldío», que ya es
categoría del catálogo. Se aplicó extendiendo el diccionario del bloque B
(`CATALOGO_CULTIVO` en `depurar_campo_otro.py`) y corriendo de nuevo el script
con `--con-catalogo` — 19 registros, ninguna superficie cambia de sitio dentro
del padrón, solo de categoría:

| | filas | superficie |
|---|---:|---:|
| POTRERO + LADERA + PENDUENTE → Pasto no mejorado | 16 | 13,79 ha |
| CASCAJO + TERRENO PREPARADO (2 variantes) → Baldío | 3 | 2,85 ha |

Respaldo de este segundo paso: `data.gpkg.1157-antes-campo-otro.bak` (contiene
el estado A+B+C+fusión del primer paso, antes de esta reclasificación).

**RESERVORIO (3 filas, 0,40 ha) y HUERTO (1 fila) siguen sin decidir a
propósito**: un reservorio es infraestructura, no uso agrícola del suelo, y no
hay una categoría de «infraestructura» en el catálogo; un huerto podría ser
cultivo real (huerto familiar mixto) y clasificarlo como no-cultivo sería un
error en el sentido contrario.

## Lo que quedó fuera a propósito

* **ZAMBO y ZAPALLO no se unieron** (143 y 101 filas): el técnico los distinguió
  y no hay base para decidir que son lo mismo.
* **10 registros donde el campo libre no coincide con el tipo elegido**, que hay
  que verificar en campo porque no se sabe cuál de los dos datos vale:

  | tipo | texto libre | superficie |
  |---|---|---:|
  | Pasto no mejorado | «500» | 2.910,44 m² |
  | Pasto mejorado | «Cebolla» | 8.000,00 m² |
  | Cebolla | «Habas,cebolla y papas» | 7.298,17 m² |
  | Papas | «Habas y potrero» | 9.298,17 m² |
  | Pasto no mejorado | «Bosque» | 7.798,17 m² |
  | Pasto no mejorado | «POTRERO» | 3.500,00 m² |
  | Trigo | «AVENA» | 1.000,00 y 1.629,85 m² |
  | Frutales | «Aguacate» / «Árbol de aguacate» | 500,00 y 2.000,00 m² |

## Cómo revertirlo

Los respaldos se tomaron con la API de backup de SQLite (no `copy`: el `-wal`
dejaría la copia incompleta), en
`Escritorio\CAYAMBE CATASTRO RIEGO\respaldos_qgs\2026-08-18\`:

| archivo | estado que contiene |
|---|---|
| `data.gpkg.1113-antes-campo-otro.bak` | **antes de todo** — el punto al que hay que volver |
| `data.gpkg.1115-antes-depurar-cultivos.bak` | después de A+B+C, antes de fusionar los repetidos |

Para revertir por completo, con QField cerrado y nadie sincronizando:

```bash
cp "respaldos_qgs/2026-08-18/data.gpkg.1113-antes-campo-otro.bak" "$HOME/QField/cloud/porotog_levantamiento_offline/data.gpkg"
```

Y después regenerar la cadena, o los informes publicados seguirán mostrando el
estado corregido.

## Cómo evitar que vuelva

Esto se reproduce en cada campaña: el campo libre no tiene validación en QField.
Dos caminos, ninguno aplicado todavía:

1. Volver a correr este script después de cada sincronización, antes de generar
   informes. Es barato y no requiere tocar el formulario.
2. Añadir al catálogo del formulario las opciones que la gente escribe siempre
   —**arveja, zambo, zapallo, avena, alfalfa**, que son 418 de las 531 filas de
   «Otros»— para que dejen de pasar por el campo libre. Cambia el esquema, así
   que va entre campañas, no en medio de una.
