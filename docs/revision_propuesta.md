# Revisión de la propuesta contra el repositorio

Revisión hecha el 2 de noviembre de 2026 sobre `main` (commit `31d6c9d`) y
la rama de la interfaz. Los puntos 4, 6, 7, 17 y 20 se ajustaron después en
la rama `rafael-nucleo-propuesta` para que el núcleo siga la propuesta. Para cada requisito se comprobó el
comportamiento con la CLI, las pruebas o la interfaz, no solo lo que dice
el README.

Estados usados: **Cumple**, **Pendiente** (falta hacerlo) y
**Discrepa** (está hecho, pero distinto a la propuesta).

## Matriz de conformidad

| # | Requisito de la propuesta | Evidencia | Ajuste necesario | Responsable | Estado |
|---|---|---|---|---|---|
| 1 | Más de dos distribuciones de teclado (observación del profesor) | `distribuciones/` trae QWERTY, AZERTY y Dvorak; `test_se_cargan_las_tres_distribuciones` | Ninguno | José | Cumple |
| 2 | La distribución es configurable y se pueden agregar otras | `cargar_distribuciones()` lee todos los JSON de la carpeta; `test_descubre_un_archivo_nuevo`. La interfaz arma el selector con lo que encuentra | Ninguno | José / Rafael | Cumple |
| 3 | Teclado aleatorio repetible | `generar_aleatoria(base, semilla)`; la interfaz genera una y muestra la semilla, y la CLI la repite con `--semilla`. `test_aleatorio_con_semilla_es_repetible` | Ninguno | José / Rafael | Cumple |
| 4 | Vecindad calculada desde la posición de las teclas con una tabla de cercanías, sin `if` letra por letra; dos teclas son vecinas si su diferencia de fila y de columna es como máximo 1, con diagonales | `generar_tabla_cercanias` arma la tabla al crear cada `Distribucion` y `son_vecinas` solo la consulta. `test_tabla_de_cercanias`, `test_vecindad_segun_la_propuesta` | Antes se usaba distancia euclidiana con umbral 1.25 al cuadrado; se cambió a la regla de la propuesta | José / Rafael | Cumple |
| 5 | Costos: vecina 1, no vecina 2, inserción 2, eliminación 2, intercambio 1 | `_sucesores` en `astar.py`; `test_ruta_y_costos` | Ninguno | José | Cumple |
| 6 | Estados de 1 a 6 letras | `_sucesores` ya no elimina la única letra; la inserción se limita a 6. `test_no_se_genera_la_palabra_vacia` | Ninguno | José / Rafael | Cumple |
| 7 | Heurística: mínimo sobre el diccionario de `max(2 × diferencia de longitudes, letras faltantes)` | `IndiceHeuristica` en `astar.py` calcula exactamente esa fórmula (letras faltantes con repetición). `test_indice_coincide_con_la_formula` la compara con la fórmula aplicada palabra por palabra; `test_heuristica_admisible`, `test_heuristica_consistente` y `test_ejemplo_de_la_propuesta` (h(gstp) = 2 con el vocabulario de la propuesta) | Ninguno. La versión anterior devolvía 0, 1 o 2 según firmas de letras | José / Rafael | Cumple |
| 8 | A* devuelve la corrección de costo mínimo | `test_compara_con_costo_uniforme` compara contra costo uniforme; ejemplos: gstp→gato (2), hoal→hola (1), cssa→casa (1) | Ninguno | José | Cumple |
| 9 | Vocabulario en español | `datos/palabras.txt`, 19,151 palabras de 1 a 6 letras sin tildes ni ñ, con fuentes citadas | Ninguno | José | Cumple |
| 10 | Al presionar espacio se procesa la palabra y el espacio no llega al algoritmo | `Controlador.actualizar_entrada`; `test_el_espacio_no_llega_al_algoritmo` | Ninguno | Rafael | Cumple |
| 11 | Palabra válida: se conserva y no se ejecuta A* | `test_palabra_valida_no_ofrece_reemplazo` | Ninguno | Rafael | Cumple |
| 12 | Sugerencia con palabra, costo, ruta y métricas; reemplazo solo al pulsar Aceptar | Panel de resultado en `interfaz.py`; `test_aceptar_reemplaza`, `test_rechazar_conserva_original`, `test_flujo_completo_con_teclas_en_pantalla` | Ninguno | Rafael | Cumple |
| 13 | Resultado incompleto sin presentarlo como óptimo | La interfaz no muestra costo ni sugerencia y solo ofrece conservar la original. `test_resultado_incompleto_no_tiene_costo` | Ninguno | Rafael | Cumple |
| 14 | Validación de entrada (vacía, más de 6 letras, tildes, ñ, mayúsculas, otros caracteres, espacios repetidos, pegado) | `validar_palabra` y `_procesar`; `test_entradas_invalidas`, `test_espacios_repetidos`, `test_texto_pegado_procesa_solo_la_primera_palabra` | Ninguno | Rafael | Cumple |
| 15 | Teclado dibujado en sus posiciones reales y con teclas pulsables | `_dibujar_teclado` coloca cada letra en `(x, y)` de la distribución; `test_teclado_usa_las_posiciones_de_la_distribucion`, `test_teclas_en_pantalla` | Ninguno | Rafael | Cumple |
| 16 | La búsqueda corre fuera del manejador de entrada y se ignoran resultados viejos | `page.run_thread`; cada búsqueda guarda número, palabra y teclado. `test_resultado_tardio_tras_cambiar_palabra`, `test_resultado_tardio_tras_cambiar_teclado`, `test_busqueda_vieja_no_pisa_a_la_nueva` | `buscar_correccion` no se puede cancelar; un resultado viejo se ignora, pero su hilo sigue hasta terminar o agotar el presupuesto | Rafael / José | Cumple (ver ajuste) |
| 17 | Diccionario, teclados e índice de la heurística se preparan una sola vez | La interfaz carga diccionario y teclados en `Aplicacion.__init__`; `indice_heuristica` guarda el índice por diccionario (0.26 s la primera vez). `test_indice_se_construye_una_vez` | Ninguno | José / Rafael | Cumple |
| 18 | Métricas de rendimiento visibles | Costo, estados expandidos, frontera máxima y tiempo en la CLI y en la interfaz | La comparación con costo uniforme solo existe en una prueba. Para la exposición convendría mostrarla en la interfaz o en la CLI | Rafael / José | Pendiente |
| 19 | Visualización del recorrido de búsqueda | `buscar_correccion` acepta `traza` y agrega un `Expansion` por cada estado expandido. `arbol.py` elige y acomoda los nodos; la interfaz los muestra en un grafo interactivo (paso a paso, animación, clic en un nodo) y `visualizacion.py` exporta la misma figura a PNG con matplotlib (`cli.py --grafo`). `tests/test_visualizacion.py` | Ninguno | Rafael | Cumple |
| 20 | Las posiciones de las teclas representan el teclado real | Las filas empiezan en 0, 0.25 y 0.75 en QWERTY, AZERTY y Dvorak, como en un teclado físico. En QWERTY la G tiene como vecinas a T, Y, F, H, V y B | Ninguno. Antes las filas empezaban en 0, 0.5 y 1.5 y la B no contaba como vecina de la G | José / Rafael | Cumple |
| 21 | Límite de niveles de la corrección: la búsqueda no sigue combinando palabras sin parar (observación después de la exposición: un límite de 2 o 3 niveles) | `buscar_correccion(..., max_niveles=)`. La interfaz y la CLI usan `MAX_NIVELES = 3`. Si ninguna palabra queda a tantos cambios o menos, el estado es `sin_correccion` y la palabra se conserva. `TestLimiteDeNiveles`, `test_sin_correccion_cercana_conserva_la_entrada` | Ninguno. Antes solo existía el presupuesto de estados, que no limita cuánto se aleja la sugerencia | Rafael | Cumple |

## Presupuesto de búsqueda (`max_estados`)

La interfaz usa `MAX_ESTADOS = 200_000` (en `controlador.py`). El valor se
eligió midiendo 152 palabras del diccionario con errores al azar
(sustitución, inserción, eliminación o intercambio) en QWERTY, AZERTY,
Dvorak y un teclado aleatorio con semilla 7, ya con la heurística y la
vecindad de la propuesta:

| Presupuesto | Incompletas con 1 error | Incompletas con 2 errores | Tiempo máximo |
|---|---|---|---|
| 100,000 | 0 de 94 | 3 de 58 | 0.61 s |
| 200,000 | 0 de 94 | 0 de 58 | 0.99 s |
| 400,000 | 0 de 94 | 0 de 58 | 0.90 s |

Con 200,000 todas las palabras medidas terminan completas. Sin límite de
niveles, una entrada sin sentido como `xyzxyz` se corta como incompleta en
unos 1.4 s; con el límite de 3 niveles de la interfaz termina como sin
corrección en unos 0.5 s.

En la versión anterior del núcleo se necesitaban 400,000 estados y el peor
caso tardaba 3.1 s. La mejora viene sobre todo de calcular la heurística
con un índice que se arma una sola vez y se consulta por combinación de
letras.

Los tiempos se midieron en el contenedor de desarrollo (Linux,
Python 3.13). Si en Windows la ventana tarda demasiado, el valor se baja
en `controlador.py`.

## Límite de niveles (`max_niveles`)

Un nivel es una operación (sustituir, insertar, eliminar o intercambiar).
`buscar_correccion(..., max_niveles=3)` solo acepta correcciones de hasta
3 operaciones, y dentro de ese límite sigue devolviendo la de menor costo.
La interfaz y la CLI lo usan con `MAX_NIVELES = 3` (en `controlador.py`);
en la CLI se cambia con `--max-niveles N` y `0` lo quita.

Cómo funciona:

- El estado de la búsqueda pasa a ser `(palabra, nivel)`. Una palabra puede
  alcanzarse barata pero con muchas operaciones, o cara pero con pocas, y
  las dos rutas importan. Una ruta descarta a otra de la misma palabra solo
  si cuesta igual o menos y usa igual o menos niveles.
- En el último nivel solo se generan palabras del diccionario, porque ya no
  se podrían expandir.
- Como cada operación cuesta 2 como máximo, una palabra con `h` de costo
  restante necesita al menos `h / 2` operaciones más. Si no caben en los
  niveles que quedan, se descarta. La heurística sigue siendo admisible, así
  que esta poda no pierde ninguna corrección posible.
- Si ninguna palabra del diccionario queda a `max_niveles` operaciones o
  menos, el resultado es `sin_correccion`: no hay sugerencia, costo ni ruta,
  y la interfaz conserva la palabra escrita. Es distinto de `incompleta`,
  que quiere decir que se agotó el presupuesto de estados antes de saber si
  había corrección.

Por qué 3: los tres casos del reporte necesitan exactamente 3 operaciones.
Con 2, `nmovte` se corrige a `monte` (costo 4) y `cyqrot` en Dvorak queda
sin corrección. Con palabras cortas, 3 cambios ya pueden alterar casi toda la
palabra; si hiciera falta, el límite puede depender del largo.

Medición con 144 palabras del diccionario con 1, 2 y 3 errores al azar
(48 de cada una, repartidas entre QWERTY, AZERTY, Dvorak y un teclado
aleatorio con semilla 7), comparando con la búsqueda sin límite:

- Con 1 y 2 errores, las 96 sugerencias son idénticas.
- Con 3 errores, 43 de 48 son idénticas, 4 eran incompletas sin límite y
  ahora se resuelven, y 1 cambia de palabra con el mismo costo (`crup` en 4
  operaciones contra `echa` en 3).
- Tiempo máximo de una búsqueda: 3.31 s sin límite y 0.53 s con límite.
- Frontera máxima media: 43,491 sin límite y 6,967 con límite.

Los tres casos del reporte con el límite de 3 (estados expandidos y
frontera máxima, contra la búsqueda sin límite):

- `nmovte` en QWERTY: 524 y 10,472 (antes 542 y 50,751).
- `cyqrot` en Dvorak: 215 y 7,365 (antes 266 y 26,366).
- `gstp` en la aleatoria con semilla 2026: 321 y 16,811 (antes 348 y 52,219).

La corrección y el costo de los tres son los mismos. La prueba
`test_coincide_con_la_referencia_sin_podas` compara el resultado contra una
búsqueda de costo uniforme sobre `(palabra, nivel)` sin heurística ni podas.

## Pendientes

- Revisar juntos la rama `rafael-nucleo-propuesta` antes de pasarla a
  `main`, porque cambia el núcleo (vecindad, heurística y posiciones de
  las teclas).
- Punto 18: decidir si se muestra la comparación con costo uniforme en la
  interfaz o en la CLI para la exposición.
