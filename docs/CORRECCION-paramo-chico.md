# Corrección de la ficha levantada sobre el Páramo Chico

**Aplicada el 14 de agosto de 2026** · Registro técnico del cambio
Script: `scripts/corregir_ficha_paramo_chico.py`
Respaldo previo: `respaldos_qgs\2026-08-14\data.gpkg.1308-antes-paramo-chico.bak`

---

## Qué estaba mal

La ficha **S-C-P001** de **AIGAJE QUINATOA SILVIA ESTELA** (cédula 1726801069,
comunidad LA LIBERTAD) estaba levantada sobre la clave catastral `1702606901`,
que no es su predio.

Según la ficha catastral del GADM Cayambe —consultada por Armando Proaño el 13
de agosto de 2026, con copia de los oficios en su poder— esa clave es:

> **PÁRAMO CHICO** · Tipo de predio: «Polígono Especial de Colindancia»
> Observaciones: *«REVERSIÓN DEL PARAMO CHICO AL ESTADO A PARTIR DE LA COTA 3680
> M SNM OFICIO Nº 269-JACR-2018 INSPECCIÓN Nº 422 DEL 26/09/2018»*

Con la clave se arrastró la superficie del polígono: la ficha declaraba
**3.237.394 m² (323,74 ha)**, enteros como superficie bajo riego, a 3.740 msnm.

El predio que el catastro sí tiene a nombre de la titular, con su nombre y su
cédula, es `1702521020106`, de **3.073,78 m²**:

| clave | área | titular según el catastro |
|---|---:|---|
| 1702606901 | 3.237.394 m² | *(sin titular — PÁRAMO CHICO, del Estado)* |
| 1702521020106 | 3.073,78 m² | AIGAJE QUINATOA SILVIA ESTHELA · 1726801069 |

## Cómo se comprobó

Los cultivos de la propia ficha venían duplicados, distinguibles por
`ref_area_predio`:

| cultivo | superficie | ref_area_predio | |
|---|---:|---:|---|
| Cebolla | 1.000 m² | 3.073,78 | el predio real |
| Pasto no mejorado | 2.073,78 m² | 3.073,78 | el predio real |
| Cebolla | 3.237.394 m² | 3.237.394 | escalado al páramo |
| Pasto no mejorado | 500 m² | 3.237.394 | escalado al páramo |

Los dos primeros **suman exactamente** el polígono catastrado a su nombre. Esa
es la prueba: la producción real de la titular son 1.000 m² de cebolla y
2.073,78 m² de pasto.

La ficha adicional que colgaba de ella (`{ab2d02fb-…}`) era **ese mismo predio**
`1702521020106`, con copia de los dos cultivos reales y `ref_area_predio` en
cero — la recuperación de la Sección 7 los escribió en las dos fichas.

## Qué se hizo

1. La ficha principal pasó a la clave `1702521020106`, con `area_total` y
   `area_riego` de 3.073,78 m² y `area_sin_riego` en cero. Se mantuvo la
   proporción que traía: declaraba todo su terreno regado.
2. Se eliminaron los dos registros de cultivo escalados al páramo.
3. Se eliminó la ficha adicional duplicada y sus dos cultivos copia.
4. Se dejó constancia en el campo `observaciones` de la ficha, **sin cifras**:
   `corregir_areas_por_observacion.py` lee números de ese campo para repartir
   superficies entre copropietarios y no debe encontrar nada que confunda.

**No se tocó:** el caudal (31,5 l/s, que es la moda de LA LIBERTAD — 105 de 154
fichas— así que el caudal del sistema no se mueve), ni los animales, ni ningún
dato de la encuesta. **La titular sigue en el padrón como regante.**

## Qué se movió en las cifras

| | Antes | Después |
|---|---:|---:|
| Fichas | 6.831 | 6.830 |
| Predios adicionales | 2.524 | 2.523 |
| Regantes | 4.307 | 4.307 |
| Superficie total (plataforma) | 10.196,51 ha | 9.872,77 ha |
| Con riego (plataforma) | 7.633,76 ha | 7.310,02 ha |
| Superficie empadronada (informes) | 8.211,78 ha | 7.888,35 ha |
| Con riego (informes) | 6.431,60 ha | 6.109,83 ha |
| Cebolla | 984,7 ha | 660,9 ha |
| Superficie cultivada | 7.527 ha | 7.203 ha |
| Caudal del sistema | 950 l/s | 950 l/s |

## Efecto en la cartografía de la represa

El área de proyecto de la represa cae sobre este predio en 31,69 ha (49,8 % de
la obra). Antes de la corrección eso se leía como «media represa sobre el predio
de una regante»; **con el dato corregido, la obra no toca ningún predio del
padrón**: se levanta sobre el páramo que ya es del Estado.

Por eso `scripts/represa/06_capas_padron.py` dejó de cruzar el límite contra los
predios investigados y pasó a cruzarlo contra el **catastro rural completo**: si
solo mirara lo investigado, la pantalla diría «no hay nada» y sería engañoso.

Resultado publicado:

| predio | dentro del proyecto | condición |
|---|---:|---|
| 1702606901 — PÁRAMO CHICO | 31,69 ha | Predio del Estado |
| 1702605313 | 31,49 ha | **sin consultar al GADM** |
| 1702300178 | 0,04 ha | sin consultar |
| 1702300173 | 0,03 ha | sin consultar |
| *sin predio catastrado* | 0,34 ha | |

## Qué queda pendiente

1. **Consultar al GADM la condición del predio `1702605313`**, que ocupa la otra
   mitad del vaso (31,49 ha, el 4,8 % de un predio de ~656 ha) y no tiene ficha.
   Si también es del Estado, la represa se levanta íntegramente sobre suelo
   público y eso conviene dejarlo escrito en el informe.
2. **Avisar a Armando del cambio de conteo**: declaró 6.825 al Consejo
   Provincial y el padrón queda en 6.830 (regla 11 del proyecto).
3. Revisar el otro caso detectado de paso: la clave `1702520680109`
   (CHIMARRO LANCHIMBA SILVIA BEATRIZ) declara **87,67 ha de cultivo sobre un
   predio de 0,88 ha**. Es un caso distinto y probablemente de campo.

## Cómo revertirlo

Restaurar el respaldo indicado arriba sobre
`C:\Users\HP\QField\cloud\porotog_levantamiento_offline\data.gpkg` y volver a
correr la cadena de regeneración. El script es idempotente: si se ejecuta de
nuevo sobre un padrón ya corregido, detecta que la ficha apunta al predio real y
no hace nada.
