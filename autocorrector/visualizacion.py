"""Dibujo del árbol de búsqueda de A* con matplotlib.

El árbol sale de la traza real de la búsqueda (los estados en el orden en
que A* los expandió), no de la ruta final. Se muestran los primeros estados
expandidos y, además, todos los de la ruta, para que se vea qué exploró A*
y por dónde llegó a la corrección.
"""

from dataclasses import dataclass
from io import BytesIO

from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
from matplotlib.lines import Line2D

from autocorrector.astar import Expansion, Resultado

LIMITE_PREDETERMINADO = 15

AZUL = "#1565C0"
AZUL_SUAVE = "#E3F2FD"
VERDE = "#2E7D32"
VERDE_SUAVE = "#E8F5E9"
GRIS = "#B0BEC5"
GRIS_SUAVE = "#ECEFF1"
TEXTO = "#263238"
TEXTO_SECUNDARIO = "#455A64"


@dataclass(frozen=True)
class Nodo:
    estado: str
    padre: str | None
    g: int
    h: int
    orden: int  # Orden de expansión; la meta, que no se expande, va al final.
    tipo: str  # inicio, ruta, meta o explorado


def seleccionar_nodos(
    resultado: Resultado,
    traza: list[Expansion],
    limite: int = LIMITE_PREDETERMINADO,
) -> dict[str, Nodo]:
    """Elige qué estados dibujar: los primeros expandidos más la ruta."""
    por_estado = {expansion.estado: expansion for expansion in traza}
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

    for expansion in traza[:limite]:
        nodos[expansion.estado] = Nodo(
            expansion.estado,
            expansion.padre,
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
            g,
            expansion.h if expansion else 0,
            expansion.orden if expansion else len(traza) + 1,
            tipo_de(paso.destino, paso.origen),
        )

    return nodos


def _posiciones(nodos: dict[str, Nodo]) -> dict[str, tuple[float, float]]:
    """Árbol de izquierda a derecha: x = profundidad, y = hojas en orden."""
    hijos: dict[str, list[str]] = {estado: [] for estado in nodos}
    raices = []

    for nodo in sorted(nodos.values(), key=lambda n: n.orden):
        if nodo.padre in nodos:
            hijos[nodo.padre].append(nodo.estado)
        else:
            raices.append(nodo.estado)

    posiciones: dict[str, tuple[float, float]] = {}
    siguiente_hoja = [0.0]

    def colocar(estado: str, profundidad: int) -> float:
        if not hijos[estado]:
            y = siguiente_hoja[0]
            siguiente_hoja[0] += 1
        else:
            ys = [colocar(hijo, profundidad + 1) for hijo in hijos[estado]]
            y = sum(ys) / len(ys)

        posiciones[estado] = (float(profundidad), -y)
        return y

    for raiz in raices:
        colocar(raiz, 0)

    return posiciones


def dibujar_busqueda(
    resultado: Resultado,
    traza: list[Expansion],
    limite: int = LIMITE_PREDETERMINADO,
) -> bytes:
    """Devuelve una imagen PNG del árbol de búsqueda."""
    nodos = seleccionar_nodos(resultado, traza, limite)
    posiciones = _posiciones(nodos)
    profundidad = max(x for x, _ in posiciones.values()) if posiciones else 0
    hojas = -min(y for _, y in posiciones.values()) + 1 if posiciones else 1

    figura = Figure(
        figsize=(3.0 + 2.6 * profundidad, max(3.5, 0.48 * hojas + 1.4)),
        dpi=110,
    )
    FigureCanvasAgg(figura)
    ejes = figura.add_subplot()
    ejes.set_axis_off()

    pasos_ruta = {(paso.origen, paso.destino): paso for paso in resultado.ruta}

    for nodo in nodos.values():
        if nodo.padre not in posiciones:
            continue

        x1, y1 = posiciones[nodo.padre]
        x2, y2 = posiciones[nodo.estado]
        paso = pasos_ruta.get((nodo.padre, nodo.estado))
        ejes.plot(
            [x1, x2],
            [y1, y2],
            color=AZUL if paso else GRIS,
            linewidth=3 if paso else 1.2,
            zorder=1,
        )

        if paso:
            ejes.text(
                (x1 + x2) / 2,
                (y1 + y2) / 2 + 0.18,
                f"+{paso.costo}",
                color=AZUL,
                fontsize=10,
                fontweight="bold",
                ha="center",
                zorder=3,
            )

    estilos = {
        "inicio": (AZUL_SUAVE, AZUL, TEXTO),
        "ruta": ("#FFFFFF", AZUL, TEXTO),
        "meta": (VERDE_SUAVE, VERDE, TEXTO),
        "explorado": (GRIS_SUAVE, GRIS, TEXTO_SECUNDARIO),
    }

    for nodo in nodos.values():
        x, y = posiciones[nodo.estado]
        fondo, borde, color = estilos[nodo.tipo]
        ejes.text(
            x,
            y,
            f"{nodo.estado}\n{nodo.g}+{nodo.h}={nodo.g + nodo.h}",
            ha="center",
            va="center",
            fontsize=10 if nodo.tipo == "explorado" else 11,
            fontfamily="monospace",
            fontweight="normal" if nodo.tipo == "explorado" else "bold",
            color=color,
            zorder=2,
            bbox={
                "boxstyle": "round,pad=0.35",
                "facecolor": fondo,
                "edgecolor": borde,
                "linewidth": 2 if nodo.tipo != "explorado" else 1,
            },
        )

    ejes.set_xlim(-0.6, profundidad + 0.6)
    ejes.set_ylim(-hojas + 0.4, 0.8)

    mostrados = min(limite, len(traza))
    ejes.set_title(
        f"Recorrido de A*: primeros {mostrados} de {len(traza)} estados "
        "expandidos y la ruta final (cada nodo: g+h=f)",
        fontsize=11,
        color=TEXTO,
        loc="left",
    )
    ejes.legend(
        handles=[
            Line2D([], [], color=AZUL, linewidth=3, label="Ruta elegida"),
            Line2D([], [], color=GRIS, linewidth=1.2, label="Explorado y descartado"),
            Line2D([], [], marker="s", linestyle="", markersize=10,
                   markerfacecolor=VERDE_SUAVE, markeredgecolor=VERDE,
                   label="Meta"),
        ],
        loc="lower right",
        fontsize=9,
        frameon=False,
    )

    salida = BytesIO()
    figura.savefig(salida, format="png", bbox_inches="tight", facecolor="white")
    return salida.getvalue()
