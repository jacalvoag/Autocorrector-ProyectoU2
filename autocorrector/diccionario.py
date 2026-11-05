from collections.abc import Mapping
from pathlib import Path

from autocorrector.teclados import ALFABETO

RUTA_PREDETERMINADA = Path(__file__).parent / "datos" / "palabras.txt"


class Diccionario(frozenset):
    """Conjunto de palabras que además recuerda qué tan usada es cada una.

    Se comporta como un ``frozenset`` normal; ``frecuencias`` solo se
    consulta para desempatar sugerencias de igual costo. Una palabra sin
    frecuencia cuenta como 0.
    """

    frecuencias: Mapping[str, float]

    def __new__(
        cls,
        palabras=(),
        frecuencias: Mapping[str, float] | None = None,
    ):
        instancia = super().__new__(cls, palabras)
        instancia.frecuencias = dict(frecuencias or {})
        return instancia


def _es_numero(texto: str) -> bool:
    try:
        float(texto)
    except ValueError:
        return False

    return True


def cargar_diccionario(
    ruta: Path = RUTA_PREDETERMINADA,
) -> Diccionario:
    """Lee las palabras del archivo, con su frecuencia opcional.

    Cada línea es ``palabra frecuencia`` (el archivo generado) o una o más
    palabras sin frecuencia, separadas por espacios. La
    frecuencia es un número positivo (en el archivo generado, la escala
    Zipf de wordfreq: más alto significa más usada).
    """
    contenido = ruta.read_text(encoding="utf-8")
    palabras: set[str] = set()
    frecuencias: dict[str, float] = {}

    for linea in contenido.splitlines():
        campos = linea.split()

        # "palabra 4.25" lleva frecuencia; cualquier otra línea son palabras.
        frecuencia = None

        if len(campos) == 2 and _es_numero(campos[1]):
            frecuencia = float(campos[1])
            campos = campos[:1]

            if not frecuencia > 0:
                raise ValueError(f"Frecuencia no positiva para {campos[0]}")

        for palabra in campos:
            if not 1 <= len(palabra) <= 6:
                raise ValueError(f"Longitud no admitida: {palabra}")

            if any(letra not in ALFABETO for letra in palabra):
                raise ValueError(f"Caracteres no admitidos: {palabra}")

            if palabra in palabras:
                raise ValueError(f"Palabra repetida: {palabra}")

            palabras.add(palabra)

            if frecuencia is not None:
                frecuencias[palabra] = frecuencia

    if not palabras:
        raise ValueError("El diccionario está vacío.")

    return Diccionario(palabras, frecuencias)
