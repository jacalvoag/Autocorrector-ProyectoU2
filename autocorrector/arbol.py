"""Árbol de búsqueda a partir de la traza real de A*.

Elige qué estados mostrar y dónde colocarlos. No dibuja nada: lo usan la
vista interactiva de la interfaz y el exportador a imagen.
"""

from dataclasses import dataclass

from autocorrector.astar import Expansion, Resultado

LIMITE_PREDETERMINADO = 12


@dataclass(frozen=True)
class Nodo:
    estado: str
    padre: str | None
    operacion: str | None
    g: int
    h: int
    orden: int  # Paso en que A* lo expandió; la meta va después del último.
    tipo: str  # inicio, ruta, meta o explorado

    @property
    def f(self) -> int:
        return self.g + self.h


def seleccionar_nodos(
    resultado: Resultado,
    traza: list[Expansion] | tuple[Expansion, ...],
    limite: int = LIMITE_PREDETERMINADO,
) -> dict[str, Nodo]:
    """Los primeros estados expandidos más todos los de la ruta."""
    # Con límite de niveles una palabra podría expandirse dos veces (con
    # distinto costo y número de pasos); el árbol dibuja la primera.
    por_estado: dict[str, Expansion] = {}
    for expansion in traza:
        por_estado.setdefault(expansion.estado, expansion)

    en_ruta = {paso.destino for paso in resultado.ruta}
    meta = resultado.sugerencia if resultado.estado == "sugerida" else None
    nodos: dict[str, Nodo] = {}

    def tipo_de(estado: str, padre: str | None) -> str:
        if padre is None:
            return "inicio"
        if estado == meta:
            return "meta"
        if estado in en_ruta:
            return "ruta"
        return "explorado"

    for expansion in list(traza)[:limite]:
        if expansion.estado in nodos:
            continue

        nodos[expansion.estado] = Nodo(
            expansion.estado,
            expansion.padre,
            expansion.operacion,
            expansion.g,
            expansion.h,
            expansion.orden,
            tipo_de(expansion.estado, expansion.padre),
        )

    g = 0
    for paso in resultado.ruta:
        g += paso.costo
        expansion = por_estado.get(paso.destino)
        nodos[paso.destino] = Nodo(
            paso.destino,
            paso.origen,
            paso.operacion,
            g,
            expansion.h if expansion else 0,
            expansion.orden if expansion else len(traza) + 1,
            tipo_de(paso.destino, paso.origen),
        )

    return nodos


def posiciones(nodos: dict[str, Nodo]) -> dict[str, tuple[int, float]]:
    """Columna (profundidad) y fila de cada nodo, de izquierda a derecha.

    Las hojas ocupan filas seguidas y cada padre queda a la altura media de
    sus hijos.
    """
    hijos: dict[str, list[str]] = {estado: [] for estado in nodos}
    raices = []

    # Las ramas del camino elegido van primero (arriba) para que siempre se
    # vean; el resto conserva el orden en que A* las expandió.
    def prioridad(nodo: Nodo) -> tuple[int, int]:
        return (0 if nodo.tipo in ("ruta", "meta") else 1, nodo.orden)

    for nodo in sorted(nodos.values(), key=prioridad):
        if nodo.padre in nodos:
            hijos[nodo.padre].append(nodo.estado)
        else:
            raices.append(nodo.estado)

    resultado: dict[str, tuple[int, float]] = {}
    siguiente_fila = [0.0]

    def colocar(estado: str, profundidad: int) -> float:
        if hijos[estado]:
            filas = [colocar(hijo, profundidad + 1) for hijo in hijos[estado]]
            fila = (filas[0] + filas[-1]) / 2
        else:
            fila = siguiente_fila[0]
            siguiente_fila[0] += 1

        resultado[estado] = (profundidad, fila)
        return fila

    for raiz in raices:
        colocar(raiz, 0)

    return resultado


def pasos(nodos: dict[str, Nodo]) -> list[Nodo]:
    """Nodos en el orden en que A* los fue alcanzando."""
    return sorted(nodos.values(), key=lambda n: n.orden)
