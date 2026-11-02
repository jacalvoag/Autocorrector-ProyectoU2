# Revisión de la propuesta contra el repositorio

Revisión hecha el 2 de noviembre de 2026 sobre `main` (commit `31d6c9d`) y
la rama `feat/interfaz-flet`. Para cada requisito se comprobó el
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
| 4 | Vecindad calculada desde la posición de las teclas, sin `if` letra por letra; diagonales incluidas | `Distribucion.son_vecinas` usa la distancia entre coordenadas (umbral 1.25 al cuadrado, que incluye la diagonal de filas desfasadas media tecla). `test_vecindad_depende_de_las_posiciones` | El profesor habló de una "tabla de cercanías". Hoy se calcula al momento, con el mismo resultado. Si se quiere mostrar una tabla explícita, se puede precalcular una matriz 26×26 al cargar cada teclado | José | Cumple (ver ajuste) |
| 5 | Costos: vecina 1, no vecina 2, inserción 2, eliminación 2, intercambio 1 | `_sucesores` en `astar.py`; `test_ruta_y_costos` | Ninguno | José | Cumple |
| 6 | Estados de 1 a 6 letras | La inserción se limita a 6, pero `_sucesores("q", ...)` genera la cadena vacía al eliminar la única letra | No generar eliminaciones cuando la palabra tiene una letra y agregar una prueba | José | Discrepa |
| 7 | Heurística: mínimo sobre el diccionario de `max(2 × diferencia de longitudes, letras faltantes)` | `heuristica()` en `astar.py` devuelve 0, 1 o 2 según firmas de letras. Se verificó que es admisible y consistente, así que A* sigue siendo óptimo | No es la fórmula de la propuesta y es débil: `xyzxyz` expande 287,694 estados y tarda unos 90 s sin límite. Hay que decidir entre implementar la fórmula original o cambiar la propuesta y justificar la cota. No se debe decir que se implementó literalmente | José (decisión del equipo) | Discrepa |
| 8 | A* devuelve la corrección de costo mínimo | `test_compara_con_costo_uniforme` compara contra costo uniforme; ejemplos: gstp→gato (2), hoal→hola (1), cssa→casa (1) | Ninguno | José | Cumple |
| 9 | Vocabulario en español | `datos/palabras.txt`, 19,151 palabras de 1 a 6 letras sin tildes ni ñ, con fuentes citadas | Ninguno | José | Cumple |
| 10 | Al presionar espacio se procesa la palabra y el espacio no llega al algoritmo | `Controlador.actualizar_entrada`; `test_el_espacio_no_llega_al_algoritmo` | Ninguno | Rafael | Cumple |
| 11 | Palabra válida: se conserva y no se ejecuta A* | `test_palabra_valida_no_ofrece_reemplazo` | Ninguno | Rafael | Cumple |
| 12 | Sugerencia con palabra, costo, ruta y métricas; reemplazo solo al pulsar Aceptar | Panel de resultado en `interfaz.py`; `test_aceptar_reemplaza`, `test_rechazar_conserva_original`, `test_flujo_completo_con_teclas_en_pantalla` | Ninguno | Rafael | Cumple |
| 13 | Resultado incompleto sin presentarlo como óptimo | La interfaz no muestra costo ni sugerencia y solo ofrece conservar la original. `test_resultado_incompleto_no_tiene_costo` | Ninguno | Rafael | Cumple |
| 14 | Validación de entrada (vacía, más de 6 letras, tildes, ñ, mayúsculas, otros caracteres, espacios repetidos, pegado) | `validar_palabra` y `_procesar`; `test_entradas_invalidas`, `test_espacios_repetidos`, `test_texto_pegado_procesa_solo_la_primera_palabra` | Ninguno | Rafael | Cumple |
| 15 | Teclado dibujado en sus posiciones reales y con teclas pulsables | `_dibujar_teclado` coloca cada letra en `(x, y)` de la distribución; `test_teclado_usa_las_posiciones_de_la_distribucion`, `test_teclas_en_pantalla` | Ninguno | Rafael | Cumple |
| 16 | La búsqueda corre fuera del manejador de entrada y se ignoran resultados viejos | `page.run_thread`; cada búsqueda guarda número, palabra y teclado. `test_resultado_tardio_tras_cambiar_palabra`, `test_resultado_tardio_tras_cambiar_teclado`, `test_busqueda_vieja_no_pisa_a_la_nueva` | `buscar_correccion` no se puede cancelar; un resultado viejo se ignora, pero su hilo sigue hasta terminar o agotar el presupuesto | Rafael / José | Cumple (ver ajuste) |
| 17 | Diccionario y teclados se cargan una sola vez | Se cargan en `Aplicacion.__init__` | `buscar_correccion` reconstruye el índice de la heurística con todo el diccionario en cada llamada; convendría hacerlo una vez | José | Pendiente |
| 18 | Métricas de rendimiento visibles | Costo, estados expandidos, frontera máxima y tiempo en la CLI y en la interfaz | La comparación con costo uniforme solo existe en una prueba. Para la exposición convendría mostrarla en la interfaz o en la CLI | Rafael / José | Pendiente |
| 19 | Visualización del recorrido de búsqueda (PNG o animación) | No existe | Queda fuera del alcance inicial. Si se hace, debe salir de los eventos reales de A* y separar estados explorados de la ruta final | Por definir | Pendiente |
| 20 | Las posiciones de las teclas representan el teclado real | En `qwerty.json` la tercera fila empieza en 1.5 y la segunda en 0.5. Con eso la V queda justo debajo de la G y la B no cuenta como vecina de la G (distancia al cuadrado 2 > 1.25). En un teclado físico la fila de abajo se desplaza cerca de media tecla, y G tiene como vecinas a V y B | Revisar los desplazamientos (`inicio`) de QWERTY, AZERTY y Dvorak contra un teclado real y ajustar las pruebas de vecindad | José | Discrepa |

## Presupuesto de búsqueda (`max_estados`)

La interfaz usa `MAX_ESTADOS = 400_000` (en `controlador.py`). El valor se
eligió midiendo 152 palabras del diccionario con errores al azar
(sustitución, inserción, eliminación o intercambio) en QWERTY, AZERTY,
Dvorak y un teclado aleatorio con semilla 7:

| Presupuesto | Incompletas con 1 error | Incompletas con 2 errores | Tiempo máximo |
|---|---|---|---|
| 20,000 | 3 de 94 | 21 de 58 | 0.14 s |
| 50,000 | 0 de 94 | 8 de 58 | 0.40 s |
| 100,000 | 0 de 94 | 3 de 58 | 0.64 s |
| 200,000 | 0 de 94 | 1 de 58 | 1.12 s |
| 400,000 | 0 de 94 | 0 de 58 | 3.09 s |

Con 200,000 se cortaba "gstp" en el teclado aleatorio de semilla 2026,
que necesita unos 307,000 estados para llegar a "aspe" con costo 4. Por eso
se subió a 400,000. Con ese límite una entrada sin sentido como `xyzxyz`
termina como incompleta en unos 3.3 s en lugar de 90 s.

Los tiempos se midieron en el contenedor de desarrollo (Linux,
Python 3.13). En Windows hay que repetir la medición; si la ventana tarda
demasiado, el valor se baja en `controlador.py` sin tocar el núcleo.

Si José implementa una heurística más informada (punto 7), este
presupuesto se puede reducir.

## Pendientes antes de fusionar

- José: corregir los puntos 6 y 20, decidir el punto 7 y, si es posible, el 17.
- Rafael y José: probar el flujo completo en Windows con Python 3.12 y
  Flet 1.0.5 y repetir la medición del presupuesto.
- Revisar juntos el pull request antes de fusionar.
