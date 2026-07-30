# Cómo se calcula el caudal del sistema

**Decisión tomada el 2026-07-30.** Este documento explica por qué el caudal NO se
suma ficha por ficha, y dónde vive el cálculo. Si alguien vuelve a sumar la
columna `caudal_valor`, obtendrá un número físicamente imposible.

---

## El problema

La ficha de campo pregunta *"¿cuánto caudal recibe?"* y el técnico anota el
caudal que recibe **la comunidad entera**, no la parte del regante. Ese mismo
valor queda repetido en todas las fichas de esa comunidad.

Sumar la columna es como preguntarle a cada una de las 120 personas de una casa
"¿cuánta luz consume esta casa?", que las 120 respondan "50 dólares", y concluir
que la casa consume 6.000 dólares.

Ese error daba **169.282 l/s** para el sistema Guanguilquí–Porotog. El valor
real es **949 l/s**.

## La regla acordada

| Caso | Cómo se obtiene el caudal |
|---|---|
| Comunidad con caudal comunal | La **moda** de lo declarado en sus fichas (el valor que más se repite). Es lo que anotaron la mayoría de los técnicos, así que es el dato de la llave comunal. |
| ALPAKA y MONTESERIN BAJO | El valor del **acta de campo** (18,5 y 14,65 l/s). En estas dos repartimos el caudal comunal entre las fichas durante la carga, así que su moda ya no representa la llave y la moda daría un número equivocado. |
| Ficha `caudal_tipo = 'Recibe individual'` | **Sí se suma**, porque ahí cada regante tiene su propia concesión y su propio valor. |

Caudal del sistema = suma de las comunidades (una vez cada una) + suma de las
individuales.

Al 2026-07-30: 46 comunidades → 732,71 l/s · 110 individuales → 216,65 l/s ·
**sistema 949,36 l/s**.

## Dónde vive el cálculo

`scripts/export_geojson.py` → `calcular_caudal_por_comunidad()` es la **única**
fuente. Escribe `public/geo/caudal_por_comunidad.json`, que incluye el origen de
cada valor (`acta de campo` o `moda (412 de 939 fichas)`) para que sea auditable.

Todo lo demás **lee** ese archivo, nunca recalcula:

| Consumidor | Qué muestra |
|---|---|
| `scripts/generar_capas_sectores_comunidades.py` | `caudal_total_ls` de comunidades.geojson y sectores.geojson |
| `scripts/generar_gpkg_cliente.py` | campo `caudal_comunidad_ls` de los predios del entregable |
| `src/components/map/MapPrintComposerPage.tsx` | el caudal del sistema en la composición para impresión |

## Trampa a evitar: el nombre de la comunidad

Los técnicos escriben la comunidad a mano, así que el mismo lugar aparece como
`IZACATA GRANDE`, `INSACATA`, `MONTESERÍN BAJO` o `MONTESERIN BAJO`.

Cuando cada script normalizaba el nombre a su manera, las claves no coincidían y
el caudal se perdía **en silencio**: Monteserrín Bajo y el grupo Izacata
quedaron en 0 l/s sin que nada fallara.

Por eso existe **`scripts/comunidades_canon.py`**: una sola función `canonica()`
que todos importan. Para corregir una escritura se edita `CORRECCIONES_COM` **en
ese archivo y en ninguno otro**.

## El descuadre esperado de 16,18 l/s

La suma de las 46 comunidades del mapa da 933,18 l/s, no 949,36. La diferencia
no es un error, son fichas que el mapa no puede dibujar:

- 11 fichas `Recibe individual` descartadas por discrepancia con el catastro → 11,38 l/s
- 6 fichas `Recibe individual` sin comunidad asignada → 4,80 l/s

`generar_capas_sectores_comunidades.py` imprime este cuadre en cada corrida
(`🔎 Cuadre de caudal…`). Si la diferencia crece o aparece una comunidad en 0 l/s,
el script lo avisa — no hay que descubrirlo revisando el mapa.

## Qué revisar si el número cambia

1. ¿Aparecen comunidades nuevas mal escritas? → agregar a `CORRECCIONES_COM`.
2. ¿Alguna comunidad quedó en 0 l/s? → el script lo avisa; casi siempre es el nombre.
3. ¿La moda de una comunidad se ve rara? → mirar el campo `origen` en
   `caudal_por_comunidad.json`; si dice `moda (5 de 300 fichas)` los técnicos no
   están de acuerdo y hay que pedir el acta.
