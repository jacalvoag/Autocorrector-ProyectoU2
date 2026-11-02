from dataclasses import dataclass
from functools import lru_cache
from heapq import heappop, heappush
from typing import Literal

from autocorrector.teclados import ALFABETO, Distribucion


@dataclass(frozen=True)
class Paso:
    origen: str
    destino: str
    operacion: str
    costo: int


@dataclass(frozen=True)
class Resultado:
    estado: Literal["valida", "sugerida", "incompleta"]
    original: str
    sugerencia: str | None
    costo: int | None
    ruta: tuple[Paso, ...]
    expandidos: int
    frontera_maxima: int


def _validar_entrada(palabra: str) -> None:
    if not 1 <= len(palabra) <= 6:
        raise ValueError("La palabra debe tener de 1 a 6 letras.")

    if any(letra not in ALFABETO for letra in palabra):
        raise ValueError("Solo se admiten letras minúsculas a-z.")


def _sucesores(palabra: str, teclado: Distribucion):
    generados: set[str] = set()

    for i, original in enumerate(palabra):
        for nueva in ALFABETO:
            if nueva == original:
                continue

            destino = palabra[:i] + nueva + palabra[i + 1:]

            if destino not in generados:
                generados.add(destino)
                costo = 1 if teclado.son_vecinas(original, nueva) else 2
                yield destino, "sustitucion", costo

    if len(palabra) < 6:
        for i in range(len(palabra) + 1):
            for letra in ALFABETO:
                destino = palabra[:i] + letra + palabra[i:]

                if destino not in generados:
                    generados.add(destino)
                    yield destino, "insercion", 2

    for i in range(len(palabra)):
        destino = palabra[:i] + palabra[i + 1:]

        if destino not in generados:
            generados.add(destino)
            yield destino, "eliminacion", 2

    for i in range(len(palabra) - 1):
        if palabra[i] == palabra[i + 1]:
            continue

        destino = (
            palabra[:i]
            + palabra[i + 1]
            + palabra[i]
            + palabra[i + 2:]
        )

        if destino not in generados:
            generados.add(destino)
            yield destino, "intercambio", 1


def _reconstruir(meta: str, anteriores: dict[str, Paso]) -> tuple[Paso, ...]:
    ruta: list[Paso] = []

    while meta in anteriores:
        paso = anteriores[meta]
        ruta.append(paso)
        meta = paso.origen

    ruta.reverse()
    return tuple(ruta)


def buscar_correccion(
    palabra: str,
    teclado: Distribucion,
    diccionario: frozenset[str],
    *,
    max_estados: int | None = None,
) -> Resultado:
    _validar_entrada(palabra)

    if not diccionario:
        raise ValueError("El diccionario no puede estar vacío.")

    if max_estados is not None and max_estados < 1:
        raise ValueError("max_estados debe ser positivo.")

    if palabra in diccionario:
        return Resultado("valida", palabra, palabra, 0, (), 0, 0)

    # Se agrupan metas con las mismas letras, sin considerar su orden.
    firmas = {"".join(sorted(meta)) for meta in diccionario}
    firmas_sin_una: dict[int, set[str]] = {}

    for firma in firmas:
        indice = firmas_sin_una.setdefault(len(firma), set())

        for i in range(len(firma)):
            indice.add(firma[:i] + firma[i + 1:])

    @lru_cache(maxsize=100_000)
    def heuristica(estado: str) -> int:
        firma = "".join(sorted(estado))

        if firma in firmas:
            return 0

        indice = firmas_sin_una.get(len(firma), set())

        if any(
            firma[:i] + firma[i + 1:] in indice
            for i in range(len(firma))
        ):
            return 1

        return 2

    # La cola prioriza f, luego g y finalmente la palabra.
    frontera: list[tuple[int, int, str]] = [
        (heuristica(palabra), 0, palabra)
    ]
    mejor_g = {palabra: 0}
    anteriores: dict[str, Paso] = {}

    mejor_meta: str | None = None
    costo_meta: int | None = None
    expandidos = 0
    frontera_maxima = 1

    while frontera:
        f, g, estado = heappop(frontera)

        if g != mejor_g[estado]:
            continue  # Entrada obsoleta de la cola.

        if costo_meta is not None and f > costo_meta:
            break  # Ya no puede aparecer otra meta de ese costo.

        if estado in diccionario:
            if (
                costo_meta is None
                or g < costo_meta
                or (
                    g == costo_meta
                    and (mejor_meta is None or estado < mejor_meta)
                )
            ):
                mejor_meta = estado
                costo_meta = g

            continue

        expandidos += 1

        for destino, operacion, costo in _sucesores(estado, teclado):
            nuevo_g = g + costo

            if nuevo_g >= mejor_g.get(destino, float("inf")):
                continue

            if (
                max_estados is not None
                and destino not in mejor_g
                and len(mejor_g) >= max_estados
            ):
                return Resultado(
                    "incompleta",
                    palabra,
                    None,
                    None,
                    (),
                    expandidos,
                    frontera_maxima,
                )

            mejor_g[destino] = nuevo_g
            anteriores[destino] = Paso(
                estado, destino, operacion, costo
            )
            nuevo_f = nuevo_g + heuristica(destino)
            heappush(frontera, (nuevo_f, nuevo_g, destino))

        frontera_maxima = max(frontera_maxima, len(frontera))

    if mejor_meta is None or costo_meta is None:
        raise RuntimeError("No se encontró una palabra alcanzable.")

    return Resultado(
        "sugerida",
        palabra,
        mejor_meta,
        costo_meta,
        _reconstruir(mejor_meta, anteriores),
        expandidos,
        frontera_maxima,
    )