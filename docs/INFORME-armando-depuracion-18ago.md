# Depuración del padrón: lo hecho y lo que hay que decidir

**Para:** Armando Proaño — coordinación del proyecto
**Fecha:** 18 de agosto de 2026
**Asunto:** cierre de la depuración de inconsistencias, y cuatro decisiones que no se pueden tomar desde la oficina
**Fuente:** `data.gpkg` sincronizado el 12/08/2026 · corte de los datos: 5 de agosto de 2026

---

## 1. Lo primero, porque es lo que importa para el Consorcio

**El padrón sigue en 6.830 fichas.** No se incorporó ni se eliminó ninguna.

**La superficie del sistema pasó de 8.092,45 a 8.093,34 hectáreas.** Son
**0,89 ha más (+0,01 %)**, y la razón es concreta: tres fichas tenían mal
escrita su clave catastral y no se cruzaban con ningún predio, así que su
terreno no sumaba. Al encontrar la clave correcta —el predio está a nombre del
mismo regante en el catastro— esos predios entraron a la cuenta.

Se comunica por la regla acordada: cualquier movimiento de superficie o del
número de fichas se informa, aunque sea mínimo.

---

## 2. Qué se depuró

Todo el trabajo fue sobre **el dato que declararon los regantes**, no sobre la
medición del territorio. Cada corrección tiene su respaldo del archivo original
y su documento explicando cómo revertirla.

| | antes | ahora |
|---|---:|---:|
| Predios donde varias fichas declaran más que su polígono | 298 | **4** |
| Hectáreas declaradas de más | 1.766,17 | **2,42** |
| Predios con el reparto correcto | 326 | **377** |
| Fichas sin comunidad asignada | 23 | **4** |
| Claves catastrales que no existían | 11 | **8** (6 son correctas, del DMQ) |

### De dónde venía el problema

La mayor parte no era error de los regantes ni de los técnicos en el campo,
sino del formulario: **QField pone por defecto el área del polígono completo**
cuando el técnico marca el punto sobre un predio. Si el predio es compartido y
nadie corrige ese valor a mano, cada ficha se queda declarando el terreno
entero. Con once personas sobre un mismo predio, el padrón "sumaba" once veces
la misma superficie.

Donde el técnico había anotado el reparto real en el campo de observaciones, se
usó ese dato. Donde no, se repartió el polígono entre las fichas. **Lo que el
regante declaró sobre su producción y su familia no se tocó.**

### También se corrigió

* **La escritura de los cultivos y especies.** La arveja aparecía escrita de
  ocho formas distintas y salía como ocho cultivos diferentes en el informe.
* **Las fichas sin comunidad.** De 23 quedaron 4. Doce se resolvieron
  revisándolas una por una sobre el mapa.
* **Las correcciones que envió el técnico** el 18 de agosto: material de
  construcción, tenencia y el género de las observaciones —donde una plantilla
  en femenino se había quedado sin ajustar en 20 fichas—.

---

## 3. Las cuatro decisiones que hacen falta

Ninguna se puede resolver mirando el dato: las cuatro dependen de algo que solo
usted o la junta pueden confirmar.

### a) Cuatro regantes fuera del límite de Cayambe

Cuatro fichas —dos personas con dos predios cada una— caen **fuera de todas las
comunas del cantón**. Según el catastro rural pertenecen a
**Cangahua – San Miguel de Moyabamba**, que no es ninguna de las 50 comunidades
del sistema. La comunidad más cercana está a casi un kilómetro.

| Clave catastral | Regante |
|---|---|
| `1702521700003` | Farinango Tandayamo José Miguel |
| `1702521660058` | Farinango Tandayamo José Miguel |
| `1702521700004` | Acero Farinango Juan Miguel |
| `1702521660059` | Acero Chiquimba Segundo Juan |

**Lo que hay que saber: quién les entrega el agua y quién les cobra la tarifa.**
Eso define a qué comunidad pertenecen. Las salidas posibles son crear la
comunidad, adscribirlas a Loma Gorda o Pucará, o dejarlas registradas aparte.

### b) 342 fichas que declaran sembrar más de lo que mide su predio

Suman **678,70 ha** de más. En la mayoría el exceso es pequeño y **puede ser
terreno arrendado fuera del predio propio**, que es práctica corriente en la
zona — es decir, no sería un error sino un dato real que el formulario no sabe
distinguir.

**Lo que hay que decidir: si el terreno arrendado se registra como parte del
sistema o se deja fuera del análisis de producción.** Si se registra, el
formulario necesita un campo que distinga «sembrado en mi predio» de «sembrado
en terreno de otro».

### c) 118 regantes de Monteserrín Bajo sin superficie asignada

En el predio de la hacienda del Sr. Coloma (809 ha) hay **122 fichas**: cuatro
cargan toda la superficie y **118 figuran con 0 m²**. Se registraron a partir
del listado de la factura de agua, a pedido de la comunidad.

Son regantes reconocidos, con derecho al agua, pero **sin una parcela asignada
dentro del predio**. No es un error de cálculo, pero conviene que quede claro
si esa es la situación real o si hace falta levantar el reparto.

### d) Dos claves catastrales que no se pudieron ubicar

* **Umaquinga Andrango Virgilio** (La Libertad) — su punto cae dentro de un
  predio que ya pertenece a otra familia, y su observación menciona una
  superficie (1.423,23 m²) que no coincide con nada del predio.
* **Ulcuango Imbago Melchor** (La Libertad) — su punto cae sobre un solar
  urbano de 113 m² que sí está a su nombre, pero su ficha declara 22.000 m² de
  riego: el técnico levantó la ficha en su casa del pueblo, no en el terreno.

Las dos necesitan una visita o una llamada para confirmar cuál es el predio.

---

## 4. Lo que no se tocó, a propósito

* **Lo que declaró cada regante sobre su producción**, salvo donde el propio
  técnico pidió corregirlo.
* **Las 8 fichas de Asociación Rosalía con clave del Distrito Metropolitano de
  Quito**: su clave es correcta, pertenece a otro catastro. Cuentan con
  normalidad en el padrón; lo único que no aportan es superficie catastral,
  porque su polígono no está en el catastro de Cayambe.
* **Los datos que el técnico pidió añadir y ya constaban** —pasto, cebada,
  cebolla en tres fichas—: se comprobó uno por uno antes de tocarlos.

---

## 5. Estado de la entrega

Todo el material está regenerado con los datos de hoy y publicado:

* **Web** — `https://invs-riego-comunitario.web.app`
* **Descarga para QGIS** — GeoPackage con predios investigados, catastro
  completo, fichas, comunidades, límites comunales oficiales del GAD, sectores
  y canales
* **Los seis capítulos del informe, el consolidado, el anexo de operadores y
  sus Excel** — en la carpeta de entrega
* **Revisión de campo** — 774 datos pendientes, en 45 comunidades

**El informe se puede generar y entregar cuando usted lo indique.** Las cuatro
decisiones de arriba no lo bloquean: afectan a la calidad del dato declarado,
no a la superficie ni al conteo de fichas que se entrega al Consorcio.
