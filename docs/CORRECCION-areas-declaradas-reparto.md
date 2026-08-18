# Corrección: el área declarada cuando el técnico dejó el default de QField

> Aplicada el **18 de agosto de 2026**. Script:
> `scripts/corregir_areas_declaradas_reparto.py`. Decisión de JAVIKO, revisada
> con Armando: no se vuelve a campo por esto, se corrige en oficina.

## El hallazgo

298 predios tenían varias fichas que, sumadas, declaraban más de lo que mide
su polígono catastral (1.766,17 ha de exceso). `corregir_areas_por_observacion.py`
(15-ago) ya había resuelto los que tenían el reparto completo escrito en
observaciones. Al mirar los 297 restantes de cerca aparecieron **tres grupos**:

| Grupo | Predios | Exceso | Qué es |
|---|---:|---:|---|
| **A — puro** | 112 | 197,79 ha | Todas las fichas declaran el polígono completo, ninguna tiene observación |
| **B — casi puro** | 132 | 1.209,79 ha | La mayoría declara el polígono completo, alguna trae un dato real |
| **C — mixto** | 54 | 358,59 ha | No hay patrón de "todos declaran el polígono" — ver abajo |

A y B son el mismo error: **QField pone por defecto el área del polígono
entero** cuando el técnico marca el punto sobre un predio compartido, y si no
se corrige a mano, cada ficha se queda con el 100% del predio en vez de la
parte que le toca. Confirmado con ejemplos concretos vistos en el mapa
(predio 1702520480104, Carrera: 2 fichas «adicional» creadas por
`AUTO-SECCION7`, ambas con 5.130 m² — el polígono completo, dos veces).

**El grupo C es un problema distinto**: varias fichas declaran valores que no
son ni el polígono ni una fracción razonable —una con 3.159% del predio, por
ejemplo— y sus observaciones dicen que esa persona tiene su terreno en **otra
clave catastral**. Quedaron enganchadas al predio equivocado (error de punto
GPS o de digitación), no mal divididas. **No lo toca este script**: se
arreglaría reasignando la clave, no repartiendo el área.

## La regla aplicada

Por cada ficha de un predio de los grupos A/B:

1. **Si su área ya es distinta del polígono** (no ronda el 100%), se asume
   dato real y no se toca.
2. **Si su área es ≈ el polígono** (el default sin corregir) y su observación
   trae un número que es claramente el suyo —con un marcador de pertenencia
   cerca («asignado», «corresponde», «lote», etc.) y sin mencionar otra
   clave catastral—, se usa ese número.
3. **Si no hay número propio recuperable**, la ficha entra al reparto: lo que
   sobra del polígono, descontando lo ya identificado en 1 y 2, se divide en
   partes iguales entre las fichas de este grupo.
4. **Si al final los valores no reconcilian con el polígono** (dentro de un
   15%) y no quedó ninguna ficha para el reparto —los números "reales" no
   suman lo que deberían, ni de más ni de menos—, el predio entero se
   descarta y se deja para revisar a mano. No se fuerza un cuadre falso.

Cada ficha corregida en los pasos 2 o 3 queda con una nota agregada a sus
observaciones: `[corregido 18-08-2026: dato de observacion|reparto
igualitario del predio, ver CORRECCION-areas-declaradas-reparto.md]`, para
que quien lea el dato después sepa que no es lo que el regante dijo
originalmente.

Al cambiar `area_total` se conserva la **proporción** de riego/sin-riego que
traía la ficha (si declaraba todo bajo riego, sigue todo bajo riego, sobre la
superficie nueva) — mismo criterio que `corregir_areas_por_observacion.py`.

### El bug que casi pasa desapercibido

La extracción de "el número que es mío" reusa la lógica de
`generar_auditoria_areas.num_del_texto`, pero esa función falla cuando el
texto menciona la palabra "pertenece" más de una vez con sentidos distintos:

> "el predio global **pertenece** a catorce propietarios [...] Área de Lote
> **Asignada** al Regante: 5.000 m², Lote 3"

`num_del_texto` se engancha con el primer "pertenece" (genérico, habla de los
14 propietarios) y elige el primer número después de esa posición —el
"50.000 m²" del lote sin fraccionar, no los 5.000 que sí son del regante—.
Este script busca el marcador de pertenencia **más cercano** a cada número, no
el primero del texto entero, y descarta el número si entre el marcador y él
aparece la mención a otra clave catastral (así se excluye el caso de
Quilumbaquin Farinango Rosa, cuya observación habla de su terreno en la clave
1702521000065, no en el predio que se estaba corrigiendo).

### El caso que reveló la necesidad del chequeo de reconciliación

El predio de Asociación Rosalía (los "cinco hermanos Cevallos Gordón",
1702550220015) es el ejemplo que motivó `corregir_areas_por_observacion.py`:
las cinco fichas traen su área en observaciones (12.500, 15.266, 14.420,
12.623 y 16.053 m²). Pero **esos cinco números solo suman 7,09 ha sobre un
polígono de 9,81 ha** — no reconcilian. La primera versión de este script los
aceptaba sin más, porque cada número individualmente parecía válido; el efecto
habría sido cambiar el predio de "sobra" a "falta" sin ninguna base. Se agregó
el chequeo de reconciliación y este predio (y otros 13 con el mismo problema)
quedó fuera, sin tocar.

## El resultado

| | |
|---|---:|
| Predios grupo A/B | 244 |
| **Se corrigieron** | **230** (574 fichas) |
| Descartados — no reconcilian, quedan para revisar a mano | 14 |
| Grupo C — no tocado, necesita revisar clave catastral | 54 |
| Fichas con dato real (ya distinto del default) | 5 |
| Fichas corregidas con su propio dato de observación | 38 |
| Fichas corregidas por reparto igualitario del resto | 536 |
| Superficie declarada que se quita | **1.312,27 ha** |

Quedan **68 predios sin resolver** en la pantalla de Auditoría de Áreas (14
descartados por no reconciliar + 54 del grupo C), sobre un exceso conjunto de
~717 ha. Esos 68 necesitan revisión caso por caso, no un script.

## Efecto en cifras publicadas

**La superficie catastral del sistema (8.092,45 ha) no se mueve** — se mide
sumando polígonos distintos del catastro, no fichas. **El conteo de fichas
tampoco cambia** (sigue en 6.830): esta corrección reescribe áreas, no crea ni
borra fichas, así que no dispara el aviso de la regla 11.

Lo que **sí puede moverse** al regenerar `generar_superficie_por_comunidad.py`
es `riego_ajustado_ha` (hoy 6.130,18 ha, cifra publicada): esa cifra ajusta el
riego declarado en proporción a lo que cabe en el polígono, y ahora hay menos
predios con exceso que ajustar. Ver el cálculo actualizado tras regenerar la
cadena completa.

## Cómo revertirlo

Respaldo tomado con la API de backup de SQLite (no `copy`), en
`Escritorio\CAYAMBE CATASTRO RIEGO\respaldos_qgs\2026-08-18\`:

```
data.gpkg.1413-antes-reparto-areas.bak
```

Para revertir, con QField cerrado y nadie sincronizando:

```bash
cp "respaldos_qgs/2026-08-18/data.gpkg.1413-antes-reparto-areas.bak" "$HOME/QField/cloud/porotog_levantamiento_offline/data.gpkg"
```

Y regenerar la cadena completa después, o los informes publicados seguirán
mostrando el estado corregido.

## Pendiente

* **68 predios sin resolver** (14 descartados + 54 del grupo C) — el grupo C
  necesita decidir qué hacer con las claves catastrales mal asignadas; los 14
  descartados necesitan que alguien revise a mano por qué sus observaciones no
  reconcilian con el polígono.
* Regenerar la cadena completa (`generar_superficie_por_comunidad.py` →
  `generar_auditoria_areas.py` → `generar_gpkg_cliente.py` →
  `generar_proyecto_qgis_cliente.py` → `generar_informe_consolidado.py` →
  `npm run build` → `firebase deploy`) para que la web y los informes reflejen
  esta corrección.
