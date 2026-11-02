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
- Interfaz: aplicación Flet y conexión con el núcleo terminado.

## Estado

Proyecto en desarrollo. Cada módulo se integrará cuando tenga sus
pruebas y pueda ejecutarse.

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