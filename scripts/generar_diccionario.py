import hashlib
import re
import unicodedata
from pathlib import Path

from spylls.hunspell import Dictionary
from wordfreq import iter_wordlist

RAIZ = Path(__file__).resolve().parents[1]
FUENTE = RAIZ / "fuentes" / "es_MX"
SALIDA = RAIZ / "autocorrector" / "datos" / "palabras.txt"

CARACTERES_ORIGINALES = re.compile(r"[a-záéíóúüñ]{1,6}\Z")
CARACTERES_FINALES = re.compile(r"[a-z]{1,6}\Z")


def normalizar(palabra: str) -> str:
    descompuesta = unicodedata.normalize("NFD", palabra)

    return "".join(
        caracter
        for caracter in descompuesta
        if not unicodedata.combining(caracter)
    )


def main() -> None:
    ruta_diccionario = FUENTE / "es_MX"

    if not ruta_diccionario.with_suffix(".aff").is_file():
        raise FileNotFoundError("Falta fuentes/es_MX/es_MX.aff")

    if not ruta_diccionario.with_suffix(".dic").is_file():
        raise FileNotFoundError("Falta fuentes/es_MX/es_MX.dic")

    corrector = Dictionary.from_files(str(ruta_diccionario))
    palabras: set[str] = set()

    for candidata in iter_wordlist("es"):
        original = unicodedata.normalize("NFC", candidata.lower())

        if not CARACTERES_ORIGINALES.fullmatch(original):
            continue

        # La ñ queda fuera del alfabeto acordado; no se cambia por n.
        if "ñ" in original:
            continue

        if not corrector.lookup(original):
            continue

        normalizada = normalizar(original)

        if CARACTERES_FINALES.fullmatch(normalizada):
            palabras.add(normalizada)

    if not palabras:
        raise RuntimeError("No se generó ninguna palabra.")

    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    SALIDA.write_text(
        "\n".join(sorted(palabras)) + "\n",
        encoding="utf-8",
    )

    resumen = hashlib.sha256(SALIDA.read_bytes()).hexdigest()
    print(f"Palabras generadas: {len(palabras)}")
    print(f"SHA-256: {resumen}")
    print(f"Archivo: {SALIDA}")


if __name__ == "__main__":
    main()