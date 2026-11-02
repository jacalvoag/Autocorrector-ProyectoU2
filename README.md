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

`autocorrector/datos/palabras.txt` contiene 160 palabras seleccionadas
para el alcance académico del proyecto. Solo admite letras minúsculas
`a-z` y palabras de hasta seis letras. Por esta simplificación, palabras
que normalmente llevan tilde se escriben sin ella. La lista es fija
durante cada ejecución y se puede ampliar mediante un cambio versionado.