from dataclasses import dataclass
from functools import lru_cache
from heapq import heappop, heappush
from itertools import combinations
from typing import Literal

from autocorrector.teclados import ALFABETO, Distribucion


@dataclass(frozen=True)
class Paso:
    origen: str
    destino: str
    operacion: str
    costo: int


@dataclass(frozen=True)
class Expansion:
    """Un estado que A* sacó de la frontera, en el orden en que lo hizo.

    Sirve para dibujar el recorrido real de la búsqueda: no se reconstruye
    a partir de la ruta final.
    """

    orden: int
    estado: str
    padre: str | None
    operacion: str | None
    g: int
    h: int


@dataclass(frozen=True)
class Resultado:
    estado: Literal["valida", "sugerida", "incompleta", "sin_correccion"]
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

    # Los estados tienen de 1 a 6 letras: no se elimina la única letra.
    if len(palabra) > 1:
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


def _submulticonjuntos(palabra: str) -> set[str]:
    """Todas las combinaciones de letras de la palabra, sin orden."""
    letras = "".join(sorted(palabra))
    return {
        "".join(combinacion)
        for tamano in range(len(letras) + 1)
        for combinacion in combinations(letras, tamano)
    }


class IndiceHeuristica:
    """Calcula la heurística de la propuesta en tiempo constante por estado.

    h(n) = mínimo, sobre todas las palabras w del diccionario, de
    max(2 * |len(n) - len(w)|, letras de w que faltan en n).

    Las letras faltantes se cuentan con repetición: a "gstp" le faltan
    la "a" y la "o" para formar "gato". Para una longitud fija de w, faltan
    len(w) menos las letras que n y w tienen en común, así que basta con
    conocer el mayor número de letras en común con alguna palabra de esa
    longitud. El índice guarda, para cada combinación de letras, las
    longitudes de las palabras que la contienen.
    """

    def __init__(self, diccionario: frozenset[str]) -> None:
        self.longitudes = sorted({len(palabra) for palabra in diccionario})
        self._contenidas: dict[str, int] = {}

        for palabra in diccionario:
            bit = 1 << len(palabra)

            for combinacion in _submulticonjuntos(palabra):
                self._contenidas[combinacion] = (
                    self._contenidas.get(combinacion, 0) | bit
                )

        self._por_letras = lru_cache(maxsize=200_000)(self._calcular_por_letras)

    def calcular(self, estado: str) -> int:
        # h solo depende de qué letras tiene el estado, no de su orden.
        return self._por_letras("".join(sorted(estado)))

    def _calcular_por_letras(self, letras: str) -> int:
        largo = len(letras)
        mejor = None
        pendientes = set(self.longitudes)

        # Se revisan primero las combinaciones más grandes: la primera que
        # aparece para una longitud es la que más letras comparte.
        for tamano in range(largo, -1, -1):
            if mejor is not None and all(
                max(2 * abs(largo - longitud), longitud - tamano) >= mejor
                for longitud in pendientes
            ):
                break  # Ninguna longitud pendiente puede mejorar el valor.

            for combinacion in set(combinations(letras, tamano)):
                mascara = self._contenidas.get("".join(combinacion), 0)

                for longitud in [l for l in pendientes if mascara >> l & 1]:
                    pendientes.discard(longitud)
                    valor = max(
                        2 * abs(largo - longitud), longitud - tamano
                    )

                    if mejor is None or valor < mejor:
                        mejor = valor

            if not pendientes:
                break

        return mejor if mejor is not None else 0


@lru_cache(maxsize=4)
def indice_heuristica(diccionario: frozenset[str]) -> IndiceHeuristica:
    """Construye el índice una sola vez por diccionario."""
    return IndiceHeuristica(diccionario)


def heuristica_directa(estado: str, diccionario: frozenset[str]) -> int:
    """Fórmula de la propuesta aplicada palabra por palabra (para pruebas)."""

    def faltantes(meta: str) -> int:
        restantes = list(estado)
        cuenta = 0

        for letra in meta:
            if letra in restantes:
                restantes.remove(letra)
            else:
                cuenta += 1

        return cuenta

    return min(
        max(2 * abs(len(estado) - len(meta)), faltantes(meta))
        for meta in diccionario
    )


def _reconstruir(
    meta: str,
    nivel: int,
    anteriores: dict[tuple[str, int], Paso],
    nivel_por_paso: int,
) -> tuple[Paso, ...]:
    """Camina hacia atrás desde la meta. Cada paso baja un nivel si se limita."""
    ruta: list[Paso] = []
    clave = (meta, nivel)

    while clave in anteriores:
        paso = anteriores[clave]
        ruta.append(paso)
        clave = (paso.origen, clave[1] - nivel_por_paso)

    ruta.reverse()
    return tuple(ruta)


def buscar_correccion(
    palabra: str,
    teclado: Distribucion,
    diccionario: frozenset[str],
    *,
    max_estados: int | None = None,
    max_niveles: int | None = None,
    traza: list[Expansion] | None = None,
) -> Resultado:
    """Busca con A* la corrección de menor costo.

    ``max_niveles`` limita cuántas operaciones puede tener la corrección.
    Dentro de ese límite el resultado sigue siendo el de menor costo. Si
    ninguna palabra del diccionario se alcanza con tantas operaciones o
    menos, el estado es ``sin_correccion``. Sin límite (``None``) la
    búsqueda se comporta como antes.

    Si se pasa una lista en ``traza``, se agrega un ``Expansion`` por cada
    estado expandido, en orden. No cambia el resultado de la búsqueda.
    """
    _validar_entrada(palabra)

    if not diccionario:
        raise ValueError("El diccionario no puede estar vacío.")

    if max_estados is not None and max_estados < 1:
        raise ValueError("max_estados debe ser positivo.")

    if max_niveles is not None and max_niveles < 1:
        raise ValueError("max_niveles debe ser positivo.")

    if palabra in diccionario:
        return Resultado("valida", palabra, palabra, 0, (), 0, 0)

    heuristica = indice_heuristica(diccionario).calcular
    limitar = max_niveles is not None
    # Con límite, el estado de la búsqueda es (palabra, nivel): una palabra
    # puede alcanzarse barata pero con muchas operaciones, o cara pero con
    # pocas, y las dos rutas importan. Sin límite el nivel siempre es 0.
    sube = 1 if limitar else 0

    # La cola prioriza f, luego g y finalmente la palabra.
    frontera: list[tuple[int, int, str, int]] = [
        (heuristica(palabra), 0, palabra, 0)
    ]
    mejor_g = {(palabra, 0): 0}
    anteriores: dict[tuple[str, int], Paso] = {}
    # Pares (g, nivel) vigentes de cada palabra; uno desplaza a otro si
    # cuesta igual o menos y usa igual o menos niveles.
    vigentes: dict[str, list[tuple[int, int]]] = {palabra: [(0, 0)]}

    mejor_meta: str | None = None
    nivel_meta = 0
    costo_meta: int | None = None
    expandidos = 0
    frontera_maxima = 1

    while frontera:
        f, g, estado, nivel = heappop(frontera)

        if mejor_g.get((estado, nivel)) != g:
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
                nivel_meta = nivel
                costo_meta = g

            continue

        expandidos += 1

        if traza is not None:
            llegada = anteriores.get((estado, nivel))
            traza.append(
                Expansion(
                    expandidos,
                    estado,
                    llegada.origen if llegada else None,
                    llegada.operacion if llegada else None,
                    g,
                    heuristica(estado),
                )
            )

        nuevo_nivel = nivel + sube

        for destino, operacion, costo in _sucesores(estado, teclado):
            nuevo_g = g + costo

            if limitar:
                # En el último nivel solo sirve una palabra del diccionario.
                if nuevo_nivel == max_niveles and destino not in diccionario:
                    continue

                if any(
                    g0 <= nuevo_g and n0 <= nuevo_nivel
                    for g0, n0 in vigentes.get(destino, ())
                ):
                    continue

                nuevo_h = heuristica(destino)

                # Cada operación cuesta 2 como máximo: si faltan al menos
                # h de costo, hacen falta al menos h/2 operaciones.
                if (nuevo_h + 1) // 2 > max_niveles - nuevo_nivel:
                    continue
            else:
                if nuevo_g >= mejor_g.get((destino, 0), float("inf")):
                    continue

                nuevo_h = heuristica(destino)

            clave = (destino, nuevo_nivel)

            if (
                max_estados is not None
                and clave not in mejor_g
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

            if limitar:
                restantes = []

                for g0, n0 in vigentes.get(destino, ()):
                    if nuevo_g <= g0 and nuevo_nivel <= n0:
                        mejor_g.pop((destino, n0), None)
                    else:
                        restantes.append((g0, n0))

                restantes.append((nuevo_g, nuevo_nivel))
                vigentes[destino] = restantes

            mejor_g[clave] = nuevo_g
            anteriores[clave] = Paso(estado, destino, operacion, costo)
            heappush(frontera, (nuevo_g + nuevo_h, nuevo_g, destino, nuevo_nivel))

        frontera_maxima = max(frontera_maxima, len(frontera))

    if mejor_meta is None or costo_meta is None:
        if limitar:
            return Resultado(
                "sin_correccion",
                palabra,
                None,
                None,
                (),
                expandidos,
                frontera_maxima,
            )

        raise RuntimeError("No se encontró una palabra alcanzable.")

    return Resultado(
        "sugerida",
        palabra,
        mejor_meta,
        costo_meta,
        _reconstruir(mejor_meta, nivel_meta, anteriores, sube),
        expandidos,
        frontera_maxima,
    )
