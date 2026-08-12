# Base declarada al Consejo Provincial y excedente registrado

**Para:** Armando — coordinación del proyecto
**Asunto:** las 6 fichas del 5 de agosto que quedan por encima de la base de 6.825
**Fecha:** 12 de agosto de 2026
**Fuente:** `data.gpkg` de QField sincronizado el 12/08/2026 a las 09:45, más el
historial del repositorio del padrón

---

## 1. La base declarada es la correcta

El número que se comunicó al Consejo Provincial —**4.305 predios principales y
2.520 adicionales, 6.825 en total**— coincide **exactamente** con el estado del
padrón al 4 de agosto. Se verificó reconstruyendo ese corte desde el archivo de
hoy: da 4.305 y 2.520, sin diferencia.

Conviene saber que el informe entregado ese mismo día decía **6.826**, un
predio adicional más. Esa ficha desapareció del padrón entre el 4 y el 12 de
agosto —se eliminó desde una tablet y la baja llegó en la sincronización— así
que **la cifra declarada es la buena y el informe del 4 de agosto es el que
tenía uno de más**, no al revés.

| | Declarado al Consejo | Informe del 4-ago | Padrón hoy |
|---|---:|---:|---:|
| Principales | 4.305 | 4.305 | 4.307 |
| Adicionales | 2.520 | 2.521 | 2.524 |
| **Total** | **6.825** | 6.826 | **6.831** |

---

## 2. Qué es exactamente el excedente

Son **6 fichas levantadas por Pablo Barrionuevo el 5 de agosto**, entre las
18:20 y las 18:59, en Otoncito y Pambamarquito:

| Clave catastral | Regante | Comunidad | Tipo | Hora | Superficie |
|---|---|---|---|---|---:|
| 1702540050092 | Sánchez Tandayamo Segundo Víctor | Otoncito | principal | 18:20 | 1.024 m² |
| 1702540050093 | Sánchez Tandayamo Segundo Víctor | Otoncito | adicional | 18:24 | 974 m² |
| 1702540140044 | Guaras Cobacango Luis Guido | Pambamarquito | adicional | 18:31 | 1.813 m² |
| 1702540050086 | Cholango Guaras Pedro | Otoncito | principal | 18:46 | 2.007 m² |
| 1702540050088 | Sánchez Tandayamo Rosa Elena | Otoncito | principal | 18:54 | 461 m² |
| 1702540050089 | Sánchez Tandayamo Rosa Elena | Otoncito | adicional | 18:59 | 399 m² |

Son 6 fichas de **4 titulares** —dos de ellos con un predio adicional además del
principal— y suman **0,67 hectáreas**. Sobre las 10.294,99 ha del padrón, el
excedente representa el **0,006 %**: no mueve ninguna cifra de superficie.

### Por qué el reparto cambia en +2 y +4, y no en +3 y +3

Además de las 6 fichas hubo **un cambio de clasificación**. La ficha
**1702550140041** (Guaras Cobacango Luis Guido, Cangahua Pungo), levantada por
Adriana Cuascota el 17 de junio como predio principal, fue reclasificada por
Pablo Barrionuevo el 5 de agosto como **predio adicional**.

El cambio tiene sentido: ese titular ya tenía su ficha principal levantada el 30
de julio (clave 1702540140027), así que Cangahua Pungo era un segundo predio
suyo, no una segunda persona. Por eso el padrón sube **+3 principales nuevos −1
reclasificado = +2 principales**, y **+3 adicionales nuevos +1 reclasificado =
+4 adicionales**.

---

## 3. Lo que hace falta decidir

**a) Confirmar el excedente.** Si se incorpora, la base para los estudios pasa a
4.307 + 2.524 = **6.831**, y así habría que comunicarlo al Consorcio. Los
informes que están hoy en la carpeta de entrega **ya se generaron con 6.831**
(se regeneraron el 12 de agosto a las 09:52, como último paso de la
sincronización), de modo que reflejan el padrón con el excedente incluido.

**b) Las 54 fichas con las áreas mal capturadas.** Todas de Pablo Barrionuevo,
del 24 al 30 de julio, en Pambamarca (32), Chaupiestancia (19), Pucará (2) y
Chinchinloma (1). En las 54 se repite el mismo número tres veces: área total,
área con riego y área sin riego son idénticas. El polígono del catastro confirma
el área total en 52 de las 54, así que lo que sobra es el campo de área sin
riego. Corregirlo —ponerlo en cero— quita **56,38 ha** duplicadas. **Falta que
Pablo Barrionuevo lo confirme** antes de tocar el dato.

**c) Tres predios adicionales quedaron sin ficha madre**, dos de ellos entre las
6 del 5 de agosto (1702540140044 y 1702540050089). No es descuido del técnico:
es un defecto del formulario de QField que ya está corregido en el proyecto pero
**todavía no se ha subido a las tablets**. Mientras no se suba, cada salida de
campo seguirá produciendo predios adicionales huérfanos: esa tarde, de 3
adicionales creados, 2 salieron sin madre.

El caso de Luis Guido Guaras Cobacango los reúne todos: tiene su ficha principal
del 30 de julio (que además está sin comunidad asignada y se resolverá en
oficina) y **dos predios adicionales que deberían colgar de ella, ambos sin
vincular** por este defecto.

---

## 4. Dos cosas más que conviene tener presentes

**La superficie bajo riego que se publica no es la suma directa de las fichas.**
El proceso que alimenta la web y los informes aplica una regla: cuando una ficha
no declara área con riego, le asigna toda el área del predio. El efecto es
grande —**1.209 ha** de diferencia— y va en un solo sentido:

| | Fichas de campo | Publicado en la web |
|---|---:|---:|
| Superficie total | 10.294,99 ha | 10.294,99 ha |
| Con riego | 7.769,71 ha | 8.978,86 ha |
| Sin riego | 2.579,44 ha | 1.372,50 ha |

Esa regla **contradice** el criterio que se acordó el 9 de agosto para la
revisión de campo, donde se decidió lo contrario: que un predio con el área sin
riego medida es un predio que no se riega. Conviene unificar el criterio antes
de que las dos cifras se citen en documentos distintos. **No se ha modificado
nada**: cambiarlo afecta a la web publicada y a todos los informes.

**El trabajo de campo pendiente bajó de 9.220 a 801 datos** al aplicar las
reglas de «no aplica» acordadas el 9 de agosto. Aparte quedan 67 fichas sin
comunidad, que se resuelven en oficina por cruce espacial y no requieren salida
de campo, y dos bloques a la espera de decisión: los datos de escritura de 38
fichas y las 492 fichas de ALPAKA, que son lotes de fraccionamiento y no
encuestas. El detalle está en `REVISION-CAMPO.xlsx`.
