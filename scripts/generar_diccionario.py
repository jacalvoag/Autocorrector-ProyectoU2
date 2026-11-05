import hashlib
import math
import re
import unicodedata
from pathlib import Path

from spylls.hunspell import Dictionary
from wordfreq import iter_wordlist, word_frequency

RAIZ = Path(__file__).resolve().parents[1]
FUENTE = RAIZ / "fuentes" / "es_MX"
SALIDA = RAIZ / "autocorrector" / "datos" / "palabras.txt"

CARACTERES_ORIGINALES = re.compile(r"[a-záéíóúüñ]{1,6}\Z")
CARACTERES_FINALES = re.compile(r"[a-z]{1,6}\Z")

# Escala Zipf de wordfreq: log10 de las apariciones por mil millones de
# palabras. 2.5 son unas 316 apariciones por mil millones (una cada tres
# millones de palabras); por debajo hay sobre todo formas verbales raras y
# términos que ningún usuario espera como sugerencia.
ZIPF_MINIMO = 2.5

# De una o dos letras solo se conservan palabras del español de uso general.
# El diccionario ortográfico también acepta letras sueltas, notas musicales,
# siglas y símbolos (d, ap, km, pp, ...), que no son sugerencias razonables.
PALABRAS_CORTAS = frozenset(
    "a e o u y "
    "al as ay ah da de di do eh el en es fa fe ha he ir ja la le lo me mi "
    "ni no oh oi os pi se si so su te ti tu uf uh un uy va ve vi ya yo".split()
)

# Abreviaturas, siglas y palabras de otros idiomas o nombres propios que el
# diccionario ortográfico acepta y wordfreq registra, pero que no son
# palabras del español común.
EXCLUIDAS = frozenset(
    # Abreviaturas y siglas
    "abc adv aes art avda ayto cfr cgo cta cte dpto dto etc gta hna hno hnos "
    "ibid imp impr incl inst ing izq lda ldo lic loc ltda max mtro nro num "
    "pag pags pbro pdte pta ptas pts pza rae rdo rep rev rte sic sig soc sra "
    "sres srta sta stas sto tpo trad univ vta vto xto prof prov ues "
    # Palabras de otros idiomas
    "too roo loo mee pee yes ice box bree bren chii grey gray frey hall "
    "lady peer plus tell time true watt watts tops sets sexy sexys bytes "
    "crack hobby kappa kanji punks rocks shows okupas "
    # Nombres propios
    "adan jaen luis juan paul iran peru cuba java york troy henry weber "
    "kelvin newton gil ben bey hab kan kas coa cok jhs jau lui sao nao hao "
    "dix".split()
)


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
    frecuencias: dict[str, float] = {}
    descartadas = {"corta": 0, "excluida": 0, "rara": 0}

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

        if not CARACTERES_FINALES.fullmatch(normalizada):
            continue

        # "esta" y "está" se escriben igual sin tilde: sus usos se suman.
        frecuencias[normalizada] = frecuencias.get(
            normalizada, 0.0
        ) + word_frequency(original, "es")

    palabras: dict[str, float] = {}

    for palabra, frecuencia in frecuencias.items():
        zipf = math.log10(frecuencia * 1e9)

        if len(palabra) <= 2 and palabra not in PALABRAS_CORTAS:
            descartadas["corta"] += 1
        elif palabra in EXCLUIDAS:
            descartadas["excluida"] += 1
        elif zipf < ZIPF_MINIMO:
            descartadas["rara"] += 1
        else:
            palabras[palabra] = round(zipf, 2)

    if not palabras:
        raise RuntimeError("No se generó ninguna palabra.")

    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    SALIDA.write_text(
        "".join(
            f"{palabra} {palabras[palabra]:.2f}\n"
            for palabra in sorted(palabras)
        ),
        encoding="utf-8",
    )

    resumen = hashlib.sha256(SALIDA.read_bytes()).hexdigest()
    print(f"Palabras generadas: {len(palabras)}")
    print(
        f"Descartadas: {descartadas['corta']} cortas, "
        f"{descartadas['excluida']} excluidas, {descartadas['rara']} raras"
    )
    print(f"SHA-256: {resumen}")
    print(f"Archivo: {SALIDA}")


if __name__ == "__main__":
    main()