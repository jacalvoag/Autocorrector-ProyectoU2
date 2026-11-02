# Autocorrector de palabras con A*

Proyecto académico de escritorio desarrollado en Python.

El usuario escribe una palabra de 1 a 6 letras minúsculas (`a-z`).
Al pulsar espacio, la aplicación conserva la palabra si pertenece al
diccionario. En caso contrario, A* busca una sugerencia de costo mínimo
según la distribución de teclado seleccionada. El usuario decide si
acepta el reemplazo.

## Tecnologías

- Python 3.12
- Flet 1.0.5
- Diccionario local y fijo

## Organización del trabajo

- Núcleo: distribuciones, diccionario, búsqueda A*, pruebas y ejecución
  por consola.
- Interfaz: aplicación Flet (`autocorrector/interfaz.py`), estado de la
  interacción (`autocorrector/controlador.py`) y sus pruebas
  (`tests/test_interfaz.py`).

## Estado

El núcleo y la interfaz Flet están integrados. Los puntos pendientes
y las diferencias con la propuesta están en `docs/revision_propuesta.md`.

## Diccionario

El archivo `autocorrector/datos/palabras.txt` se genera con
`scripts/generar_diccionario.py`. Incluye formas del vocabulario español de
wordfreq 3.1.1 verificadas con el diccionario ortográfico es_MX de
LibreOffice. Se conservan únicamente palabras de 1 a 6 letras dentro del
alfabeto a-z; las tildes se eliminan y las palabras con ñ se excluyen.

El archivo generado queda versionado y se utiliza sin conexión a internet.
Su cobertura depende de las fuentes; no se presenta como una lista de todas
las palabras existentes en español.

# Fuentes del diccionario

- Diccionario ortográfico español de México (`es_MX.aff` y `es_MX.dic`):
  proyecto RLA-ES, distribuido por LibreOffice. Autor inicial:
  Santiago Bosio y colaboradores.
  https://github.com/LibreOffice/dictionaries/tree/master/es
  La licencia original se conserva en `es_MX/LICENSE.md`.

- Candidatos de palabras: `wordfreq` 3.1.1, de Robyn Speer.
  https://github.com/rspeer/wordfreq
  Sus datos se distribuyen bajo CC BY-SA 4.0; consultar el NOTICE del
  proyecto: https://github.com/rspeer/wordfreq/blob/master/NOTICE.md

Modificaciones realizadas: selección de formas verificadas por es_MX,
exclusión de ñ y otros caracteres fuera del alfabeto acordado,
eliminación de tildes, límite de seis letras, eliminación de duplicados
y orden alfabético.

## Instalación

Desde la raíz del repositorio, con Python 3.12:

```powershell
python -m pip install -r requirements.txt
```

## Ejecutar la interfaz gráfica

```powershell
python -m autocorrector.interfaz
```

Se abre una ventana de escritorio donde se puede:

- Elegir QWERTY, AZERTY, Dvorak o cualquier otro JSON que se agregue a
  `autocorrector/distribuciones/`.
- Generar un teclado aleatorio. Si se escribe una semilla, se repite la
  misma distribución; si se deja vacía, se genera una y se muestra.
- Escribir con el teclado físico o con las teclas en pantalla, que se
  dibujan en las posiciones de la distribución activa. Al pasar el cursor
  sobre una tecla se ven sus vecinas.
- Presionar espacio para revisar la palabra. Si no está en el
  diccionario se muestra la sugerencia, el costo, la ruta de operaciones,
  los estados expandidos, la frontera máxima y el tiempo. La ruta se
  dibuja como una cadena de estados desde el inicio hasta la meta, con la
  operación y el costo en cada arista y las letras que cambian
  resaltadas. Las letras de las sustituciones también se marcan en el
  teclado.
- Aceptar el cambio o rechazarlo para conservar la palabra original.

La búsqueda corre en un hilo aparte con un presupuesto de 400,000 estados
(`MAX_ESTADOS` en `autocorrector/controlador.py`). Si se agota, la
interfaz lo indica y no presenta la palabra como corrección óptima. Si
la palabra o el teclado cambian mientras se busca, el resultado anterior
se descarta. La elección del presupuesto y la revisión contra la
propuesta están en `docs/revision_propuesta.md`.

## Probar el agente

Desde la raíz del repositorio:

```powershell
python -m autocorrector.cli gstp --teclado qwerty
python -m autocorrector.cli gatp --teclado aleatorio --semilla 2026
python -m unittest discover -s tests -v
```

La consola muestra sugerencia, costo, ruta, estados expandidos,
frontera máxima y tiempo. El estado `incompleta` no garantiza
una sugerencia óptima.

## Contrato para la interfaz Flet

La interfaz carga una vez los teclados con `cargar_distribuciones()` y
las palabras con `cargar_diccionario()`. Al terminar una palabra con
espacio, elimina ese espacio y llama a:

```python
buscar_correccion(palabra, teclado, diccionario, max_estados=...)
```

El resultado tiene `estado`, `sugerencia`, `costo`, `ruta`,
`expandidos` y `frontera_maxima`:

- `valida`: conserva la palabra; A* no se ejecutó.
- `sugerida`: muestra la sugerencia y espera Aceptar o Rechazar.
- `incompleta`: informa que no hay una sugerencia óptima garantizada.

La búsqueda debe ejecutarse fuera del manejador de entrada. La
interfaz asociará cada resultado con la palabra y distribución que
originaron esa búsqueda para ignorar respuestas tardías.