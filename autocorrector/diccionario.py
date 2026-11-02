from pathlib import Path

from autocorrector.teclados import ALFABETO

RUTA_PREDETERMINADA = Path(__file__).parent / "datos" / "palabras.txt"


def cargar_diccionario(
    ruta: Path = RUTA_PREDETERMINADA,
) -> frozenset[str]:
    contenido = ruta.read_text(encoding="utf-8")
    palabras: set[str] = set()

    for palabra in contenido.split():
        if not 1 <= len(palabra) <= 6:
            raise ValueError(f"Longitud no admitida: {palabra}")

        if any(letra not in ALFABETO for letra in palabra):
            raise ValueError(f"Caracteres no admitidos: {palabra}")

        if palabra in palabras:
            raise ValueError(f"Palabra repetida: {palabra}")

        palabras.add(palabra)

    if not palabras:
        raise ValueError("El diccionario está vacío.")

    return frozenset(palabras)