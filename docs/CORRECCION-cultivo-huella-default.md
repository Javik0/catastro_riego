# Corrección: el cultivo que se quedó con el área vieja

> Aplicada el **18 de agosto de 2026**, misma sesión que
> `corregir_areas_declaradas_reparto.py`. Script:
> `scripts/corregir_cultivo_huella_default.py`.

## El hallazgo

Al revisar en la pantalla de Auditoría el resultado del reparto de áreas de
esta misma tarde, apareció un problema que ese script no cubría: en varias
fichas donde **hoy se corrigió `area_total`** (porque el técnico había dejado
el default de QField — el polígono completo, repetido en cada ficha que
comparte el predio), **el cultivo se quedó con el valor viejo**.

El caso que lo destapó, revisado con JAVIKO: predio `1702521000064` (Carrera),
5 fichas **adicionales de 5 personas sin relación entre sí** —cada una con su
propio predio principal en otro lugar—, las 5 creadas por `AUTO-SECCION7` en
el mismo segundo (2026-07-19 22:34:32) y completadas por el mismo técnico
(`jvk-editor3`). El área de las 5 se corrigió hoy a 7.730 m² cada una
(38.649 ÷ 5). Pero Roberto Farinango Tugulinago seguía con «Pasto no
mejorado: 38.649,46 m²» — el polígono completo, sin dividir. La pantalla
decía que sembraba «9,7 veces su predio»: no era que sembrara de más, es que
su cultivo nunca se actualizó cuando se corrigió el área.

Verificado en la app (búsqueda por clave catastral en `/fichas`): los 5
registros existen, con coordenadas distintas (repartidas en anillo alrededor
del mismo polígono, tal como hace `generar_fichas_hijas.py` cuando varias
fichas hijas caen en un mismo predio), confirmando que no es un artefacto de
consulta.

## Por qué esto sí se corrige con la misma certeza que el área

Un cultivo no puede ser más grande que el predio donde está sembrado. Si hoy
ya se estableció —con la prueba de `corregir_areas_declaradas_reparto.py`—
cuál es el área real de una ficha, un cultivo que siga diciendo el área
**vieja** (la de antes de dividir) es, por definición, imposible: no cabe. Se
recorta al área nueva de esa misma ficha. No es una cifra inventada: es la
misma que ya se corrigió hoy, aplicada al campo que faltaba.

## Qué NO se corrigió

Las fichas donde el cultivo coincide con el polígono pero **el área de esa
ficha nunca se corrigió** (no hay predio compartido, es la única ficha en su
clave) siguen sin tocarse: ahí no hay una corrección de hoy con la que
alinear el cultivo. Son del orden de 1.600 fichas adicionales, detectadas
pero no corregidas — quedan marcadas «sin verificar» en la pantalla de
Auditoría (`generar_auditoria_areas.py`, campo `coincide_poligono`), no
corregidas.

## El resultado

| | |
|---|---:|
| Fichas corregidas | 67 |
| Superficie de cultivo que se quita | 187,40 ha |

Solo se tocó `superficie_m2` de la fila de cultivo que coincidía con el
polígono viejo. Cuando una ficha tenía más de un cultivo, las demás filas no
se tocaron.

## Efecto en cifras publicadas

Reduce `superficie cultivada` (capítulo de Producción). No afecta a la
superficie catastral del sistema ni al conteo de fichas.

## Cómo revertirlo

Respaldo con la API de backup de SQLite, en
`Escritorio\CAYAMBE CATASTRO RIEGO\respaldos_qgs\2026-08-18\`:

```
data.gpkg.1555-antes-cultivo-huella-default.bak
```

```bash
cp "respaldos_qgs/2026-08-18/data.gpkg.1555-antes-cultivo-huella-default.bak" "$HOME/QField/cloud/porotog_levantamiento_offline/data.gpkg"
```

Y regenerar la cadena completa después.
