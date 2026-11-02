"""Exporta a PNG el árbol de búsqueda de A* con matplotlib.

Sirve para generar figuras (por ejemplo para el reporte) desde la consola:

    python -m autocorrector.cli nmovte --grafo grafo.png

En la interfaz el mismo árbol se muestra de forma interactiva.
"""

from io import BytesIO

from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
from matplotlib.lines import Line2D

from autocorrector.arbol import (
    LIMITE_PREDETERMINADO,
    Nodo,
    posiciones,
    seleccionar_nodos,
)
from autocorrector.astar import Expansion, Resultado

__all__ = ["Nodo", "dibujar_busqueda", "seleccionar_nodos"]

AZUL = "#1565C0"
AZUL_SUAVE = "#E3F2FD"
VERDE = "#2E7D32"
VERDE_SUAVE = "#E8F5E9"
GRIS = "#B0BEC5"
GRIS_SUAVE = "#ECEFF1"
TEXTO = "#263238"
TEXTO_SECUNDARIO = "#455A64"

ESTILOS = {
    "inicio": (AZUL_SUAVE, AZUL, TEXTO),
    "ruta": ("#FFFFFF", AZUL, TEXTO),
    "meta": (VERDE_SUAVE, VERDE, TEXTO),
    "explorado": (GRIS_SUAVE, GRIS, TEXTO_SECUNDARIO),
}


def dibujar_busqueda(
    resultado: Resultado,
    traza: list[Expansion],
    limite: int = LIMITE_PREDETERMINADO,
) -> bytes:
    """Devuelve una imagen PNG del árbol de búsqueda."""
    nodos = seleccionar_nodos(resultado, traza, limite)
    lugar = posiciones(nodos)
    columnas = max(c for c, _ in lugar.values()) + 1
    filas = max(f for _, f in lugar.values()) + 1

    figura = Figure(figsize=(0.8 + 2.6 * columnas, 1.6 + 0.62 * filas), dpi=110)
    FigureCanvasAgg(figura)
    ejes = figura.add_axes((0.02, 0.12, 0.96, 0.80))
    ejes.set_axis_off()

    pasos_ruta = {(paso.origen, paso.destino): paso for paso in resultado.ruta}

    for nodo in nodos.values():
        if nodo.padre not in lugar:
            continue

        x1, y1 = lugar[nodo.padre]
        x2, y2 = lugar[nodo.estado]
        paso = pasos_ruta.get((nodo.padre, nodo.estado))
        ejes.plot(
            [x1 + 0.17, x2 - 0.17],
            [-y1, -y2],
            color=AZUL if paso else GRIS,
            linewidth=3 if paso else 1.2,
            zorder=1,
        )

        if paso:
            ejes.text(
                (x1 + x2) / 2,
                -(y1 + y2) / 2 + 0.25,
                f"+{paso.costo}",
                color=AZUL,
                fontsize=11,
                fontweight="bold",
                ha="center",
                zorder=3,
            )

    for nodo in nodos.values():
        x, y = lugar[nodo.estado]
        fondo, borde, color = ESTILOS[nodo.tipo]
        ejes.text(
            x,
            -y,
            f"{nodo.estado}\n{nodo.g}+{nodo.h}={nodo.f}",
            ha="center",
            va="center",
            fontsize=10,
            fontfamily="monospace",
            fontweight="normal" if nodo.tipo == "explorado" else "bold",
            color=color,
            zorder=2,
            bbox={
                "boxstyle": "round,pad=0.4",
                "facecolor": fondo,
                "edgecolor": borde,
                "linewidth": 1 if nodo.tipo == "explorado" else 2,
            },
        )

    ejes.set_xlim(-0.5, columnas - 0.5)
    ejes.set_ylim(-(filas - 0.5), 0.5)

    mostrados = min(limite, len(traza))
    figura.suptitle(
        f"Recorrido de A*: primeros {mostrados} de {len(traza)} estados "
        "expandidos y la ruta final (cada nodo: g+h=f)",
        fontsize=11,
        color=TEXTO,
        x=0.02,
        ha="left",
    )
    # La leyenda va fuera del área del árbol para no tapar ningún nodo.
    figura.legend(
        handles=[
            Line2D([], [], color=AZUL, linewidth=3, label="Ruta elegida"),
            Line2D([], [], color=GRIS, linewidth=1.2, label="Explorado y descartado"),
            Line2D([], [], marker="s", linestyle="", markersize=10,
                   markerfacecolor=VERDE_SUAVE, markeredgecolor=VERDE,
                   label="Meta"),
        ],
        loc="lower center",
        ncol=3,
        fontsize=9,
        frameon=False,
    )

    salida = BytesIO()
    figura.savefig(salida, format="png", bbox_inches="tight", facecolor="white")
    return salida.getvalue()
