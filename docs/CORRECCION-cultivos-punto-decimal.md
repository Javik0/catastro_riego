# Corrección de un cultivo digitado con el punto decimal corrido

**Aplicada el 14 de agosto de 2026** · Registro técnico del cambio
Script: `scripts/corregir_cultivo_punto_decimal.py`
Respaldo previo: `respaldos_qgs\2026-08-14\data.gpkg.1356-antes-punto-decimal.bak`

Complementa a [`CORRECCION-paramo-chico.md`](CORRECCION-paramo-chico.md), del
mismo día pero de otra naturaleza: aquella era un predio mal asignado, esta es
una tecla.

---

## Qué estaba mal

| | |
|---|---:|
| Ficha | CHIMARRO LANCHIMBA SILVIA BEATRIZ · cédula 1725967051 |
| Clave catastral | 1702520680109 · comunidad SAN ANTONIO |
| Levantada por | `jvk-editor5`, 23 de julio de 2026 |
| Área del predio | 8.767,33 m² (riego 7.000 + sin riego 1.767,33 — **cuadra**) |
| Cultivo declarado | Pasto no mejorado, **876.733,00 m²** |

`876733` es `8767.33` sin el punto: **cien veces exactas** el área del propio
predio. El predio está bien, la ficha está bien y las superficies de riego
cuadran entre sí; lo único mal es ese registro de cultivo.

## Qué se hizo

Se dividió entre cien: **8.767,33 m²**. El resultado es el predio entero
sembrado de pasto, que es lo que la ficha decía desde el principio.

La regla del script no es «arreglar esta ficha», sino **corregir todo registro
de cultivo cuya superficie sea cien veces el área del predio de su ficha, dentro
del 1 %**. Ese cuadre hasta la segunda cifra es lo que distingue un punto
decimal de una superficie declarada de más: si fuera terreno arrendado, no
coincidiría con el área del predio. Hoy hay un solo caso; en la próxima
sincronización el script vuelve a mirar.

## Qué se movió

| | Antes | Después |
|---|---:|---:|
| Superficie cultivada (informes) | 7.203 ha | **7.116 ha** |
| Pasto no mejorado | 3.215,7 ha | **3.128,6 ha** |
| Proporción de pastos sobre lo cultivado | 55,3 % | 57,2 % |
| Superficie de los predios | — | **sin cambio** |
| Fichas y regantes | — | **sin cambio** |

## Lo que NO se tocó, y hay que decidir

Al medirlo aparecieron **153 fichas que declaran más superficie sembrada que la
que su predio mide**, con **261,32 ha de exceso** sobre las 7.116 ha cultivadas
(un 3,7 %).

| Desborde | Fichas | Exceso |
|---|---:|---:|
| ×100 — punto decimal | 1 | 86,80 ha ← **corregida** |
| ×10 | 3 | 23,58 ha |
| ×2 a ×9 | 53 | 70,18 ha |
| ×1,1 a ×2 | 89 | 42,88 ha |

Las peores, para empezar por ahí:

| clave | titular | factor | predio |
|---|---|---:|---:|
| 1702520680035 | ACERO CUMBAL SEGUNDO TEODORO | ×36,5 | 191,64 m² |
| 1702520680002 | ASCANTA AIGAJE JUAN VICENTE | ×23,5 | 424,69 m² |
| 1702510090009 | PINEIDA CAIZA ELVIA BEATRIZ | ×23,1 | 1.315,00 m² |
| 1702520990033 | FARINANGO UMAQUINGA ALEJO | ×23,0 | 3.000,00 m² |
| 1702521470022 | IMBAQUINGO LANCHIMBA JOSE MANUEL | ×20,2 | 13.168,17 m² |
| 1702540220002 | COMUNA JURIDICA CHAUPIESTANCIA | ×11,7 | 1.278,52 m² |
| 1702520270345 | COYAGO COYAGO FREDDY GERARDO | ×11,0 | 869,00 m² |

**Ninguna se tocó**, y no por prudencia excesiva: sembrar en terreno arrendado
fuera del predio propio es una práctica normal en la zona, así que un cultivo
mayor que el predio no es necesariamente un error. Distinguir un caso del otro
es criterio del cliente o trabajo de campo, no aritmética.

Para volver a listarlas en cualquier momento, sin escribir nada:

```
"C:\OSGeo4W\bin\python-qgis.bat" -X utf8 scripts/corregir_cultivo_punto_decimal.py
```

## Cómo revertirlo

Restaurar el respaldo indicado arriba y regenerar. El script es idempotente: si
se ejecuta de nuevo sobre un padrón ya corregido, el registro ya no cumple la
regla del ×100 y no lo vuelve a tocar.
