# Cuatro fichas fuera del límite de comunas de Cayambe

> Detectado el **18 de agosto de 2026** al cerrar las fichas sin comunidad.
> Identificadas por JAVIKO en QGIS contra el catastro rural.

## Qué son

Cuatro fichas del padrón cuyo predio **no está dentro de ninguna comuna del
cantón Cayambe**. Al cruzarlas contra la capa oficial (`comunas_cy.shp`)
quedan fuera de todos los polígonos, y su comunidad de riego más cercana está
a casi un kilómetro — demasiado para atribuírsela.

Consultando el catastro rural en QGIS aparece a qué pertenecen:
**CANGAHUA – SAN MIGUEL DE MOYABAMBA**, que **no es ninguna de las 50
comunidades del padrón**.

| Clave catastral | Regante | Comunidad más cercana |
|---|---|---:|
| `1702521700003` | FARINANGO TANDAYAMO JOSE MIGUEL | Loma Gorda, a 905 m |
| `1702521660058` | FARINANGO TANDAYAMO JOSE MIGUEL | Pucará, a 962 m |
| `1702521700004` | ACERO FARINANGO JUAN MIGUEL | Loma Gorda, a 1.021 m |
| `1702521660059` | ACERO CHIQUIMBA SEGUNDO JUAN | Pucará, a 1.070 m |

Son **dos personas con dos predios cada una** (Farinango Tandayamo y Acero
Farinango/Chiquimba).

## Por qué no se les asigna comunidad

Ponerles la comunidad más cercana sería inventar el dato: están a casi un
kilómetro, fuera del territorio de esa comunidad y fuera del límite comunal
del cantón. Y «San Miguel de Moyabamba» no puede escribirse en el campo porque
no es una comunidad del sistema de riego — el padrón solo admite las 50 que
existen, y añadir una nueva es una decisión que no corresponde tomar aquí.

## Qué hay que decidir

Son regantes reales, con ficha levantada, que reciben agua del sistema. La
pregunta es cómo se registran:

1. **Crear la comunidad «San Miguel de Moyabamba»** en el padrón, si el sistema
   efectivamente le entrega agua y la junta la reconoce como tal.
2. **Adscribirlas a la comunidad que las administra** —Loma Gorda o Pucará—
   aunque su predio esté fuera del territorio, si es esa junta la que les da el
   agua y les cobra.
3. **Dejarlas sin comunidad**, documentadas como está aquí, y que figuren
   aparte en los informes.

Ninguna se puede resolver desde el dato: hace falta saber **quién les entrega
el agua y quién les cobra la tarifa**, que es lo que define la pertenencia a
una comunidad de riego.

## Efecto mientras tanto

Las cuatro **cuentan con normalidad** en el total de fichas (6.830), en
cultivos, animales, encuestas y superficie. Lo único es que **no aparecen en
ninguna tabla por comunidad**, así que la suma de las 50 comunidades queda 4
fichas por debajo del total del padrón. Es la misma razón por la que las tablas
por comunidad nunca cuadran exactamente con el total del sector.
