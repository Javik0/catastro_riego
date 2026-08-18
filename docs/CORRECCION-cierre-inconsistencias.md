# Cierre de las inconsistencias de área y cultivo

> Aplicado el **18 de agosto de 2026**. Script:
> `scripts/cerrar_inconsistencias_areas.py`. Criterio de JAVIKO.

## El criterio que manda

Donde se puede **determinar que fue error del sistema** —el default de QField
que nadie corrigió, o el generador automático de fichas adicionales
(`AUTO-SECCION7`)— se corrige. Lo demás es **el dato que el regante confirmó
en campo** y **se respeta**, aunque parezca alto.

## Los tres pasos

### A — Duplicados del mismo cultivo dentro de una ficha

Los duplicados **exactos** (mismo tipo, misma superficie) ya estaban en 0 de
sesiones anteriores. Quedaban **6 casos** de mismo tipo con superficie
distinta, y **los creó la reclasificación de esta misma mañana**
(potrero/ladera → «Pasto no mejorado», cascajo → «Baldío»): una ficha que ya
tenía «Pasto no mejorado» y además un «Potrero» quedó con dos filas iguales.

Se **fusionaron sumando**, no se eliminó ninguna. Son dos pedazos reales y
distintos del mismo predio (una parte era ladera, la otra ya era pasto):
sumar **no infla** —el total de la ficha no se movió ni un metro— mientras que
eliminar habría perdido superficie declarada.

### B — Predios que declaraban más que su polígono

Por cada ficha: si su observación trae un número claramente suyo, se usa; el
resto del polígono se reparte en partes iguales entre las demás.

La diferencia con `corregir_areas_declaradas_reparto.py` (de esta misma
mañana) es el criterio de aceptación. Aquel exigía que los datos reconciliaran
con el polígono dentro de un 15 % y descartaba el predio si no —por eso dejó
fuera a los cinco hermanos Cevallos Gordón, cuyas observaciones suman 7,09 ha
sobre un polígono de 9,81—. **Ese chequeo era demasiado estricto**: el
objetivo es no inflar, y 7,09 sobre 9,81 no infla. Ahora solo se rechaza el
caso contrario, que los datos reales ya superen el polígono.

### C — Cultivos con la huella exacta del default

Filas cuya superficie coincide (±2 %) con el polígono catastral: es el número
que QField pone por defecto, no algo medido. Se recortan al área de su propia
ficha — un cultivo no puede ser más grande que el predio donde está.

## El resultado

| | antes | después |
|---|---:|---:|
| **Predios que declaran de más** | 68 | **4** |
| Exceso declarado | 453,90 ha | **2,42 ha** |
| Predios bien divididos | 326 | **378** |
| Superficie declarada del sistema | 8.467,62 ha | **7.992,88 ha** |
| Registros de cultivo | 13.626 | 13.620 |

Aplicado: 6 fusiones · 180 fichas de área · 24 filas de cultivo.

**La superficie catastral del sistema no se movió: 8.092,45 ha.** El conteo de
fichas tampoco (6.830). `riego_ajustado_ha` pasó de 6.133,06 a **6.144,26 ha**
(+0,18 %).

## Los 4 predios que quedan sin arreglo

No se pudieron cerrar porque los números que traen sus observaciones ya
superan el polígono — el extractor está leyendo algo que no es un área
(probablemente una clave catastral o un teléfono dentro del texto):

| Predio | Polígono | Lo que dicen las observaciones |
|---|---:|---:|
| `1702520790030` | 0,26 ha | 207,95 ha |
| `1702520840007` | 0,15 ha | 146,35 ha |
| `1702520280044` | 8,64 ha | 9,50 ha |
| `1702521040121` | 0,63 ha | 1,00 ha |

Los dos primeros son claramente lectura errónea del texto. Los dos últimos
exceden por poco y necesitan que alguien los mire.

## Lo que quedó sin tocar, a propósito

**342 fichas (678,70 ha) declaran sembrar más de lo que mide su ficha.** Subió
respecto de las 305 de antes de este cierre, y la razón es mecánica: al bajar
el área de 180 fichas más, sus cultivos —que no se tocaron— quedaron por
encima. Según el criterio de arriba, **eso es dato del regante y se respeta**:
sembrar en terreno arrendado fuera del predio propio es corriente en la zona.

De esas, **11** todavía tienen un cultivo que coincide con el polígono y
quedan marcadas «sin verificar» en la pantalla de Auditoría.

> **Decisión pendiente:** si se quisiera que ninguna ficha declare sembrar más
> de lo que mide, habría que recortar esas 342 al área de su ficha. Eso
> cerraría la inconsistencia visual, pero **borraría el terreno arrendado**,
> que es un dato real. No se hizo sin una instrucción explícita.

## Cómo revertirlo

Respaldo con la API de backup de SQLite, en
`Escritorio\CAYAMBE CATASTRO RIEGO\respaldos_qgs\2026-08-18\`:

```
data.gpkg.1618-antes-cierre-inconsistencias.bak
```

```bash
cp "respaldos_qgs/2026-08-18/data.gpkg.1618-antes-cierre-inconsistencias.bak" "$HOME/QField/cloud/porotog_levantamiento_offline/data.gpkg"
```

Y regenerar la cadena completa después.
