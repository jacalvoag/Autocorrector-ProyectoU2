import json
import random
from dataclasses import dataclass, field
from pathlib import Path

ALFABETO = "abcdefghijklmnopqrstuvwxyz"
# Según la propuesta, dos teclas son vecinas si su diferencia de fila y
# de columna es como máximo 1, lo que incluye las diagonales.
DIFERENCIA_MAXIMA_VECINA = 1.0


@dataclass(frozen=True)
class Distribucion:
    nombre: str
    posiciones: dict[str, tuple[float, float]]
    # Tabla de cercanías: para cada letra, las letras vecinas. Se genera
    # una vez a partir de las posiciones y el agente solo la consulta.
    cercanias: dict[str, frozenset[str]] = field(
        init=False, repr=False, compare=False
    )

    def __post_init__(self) -> None:
        if set(self.posiciones) != set(ALFABETO):
            raise ValueError(
                "La distribución debe contener exactamente las letras a-z."
            )

        if len(set(self.posiciones.values())) != 26:
            raise ValueError("Dos letras ocupan la misma posición.")

        object.__setattr__(
            self, "cercanias", generar_tabla_cercanias(self.posiciones)
        )

    def son_vecinas(self, primera: str, segunda: str) -> bool:
        return segunda in self.cercanias[primera]


def generar_tabla_cercanias(
    posiciones: dict[str, tuple[float, float]],
) -> dict[str, frozenset[str]]:
    """Vecinas de cada letra: diferencia de fila y de columna de 1 o menos."""
    tabla: dict[str, frozenset[str]] = {}

    for letra, (x1, y1) in posiciones.items():
        tabla[letra] = frozenset(
            otra
            for otra, (x2, y2) in posiciones.items()
            if otra != letra
            and abs(x1 - x2) <= DIFERENCIA_MAXIMA_VECINA
            and abs(y1 - y2) <= DIFERENCIA_MAXIMA_VECINA
        )

    return tabla


def cargar_distribucion(ruta: Path) -> Distribucion:
    datos = json.loads(ruta.read_text(encoding="utf-8"))
    posiciones: dict[str, tuple[float, float]] = {}

    for numero_fila, fila in enumerate(datos["filas"]):
        inicio = float(fila["inicio"])

        for columna, letra in enumerate(fila["teclas"]):
            # El guion representa una posición ocupada por otra tecla.
            if letra == "-":
                continue

            if letra not in ALFABETO or letra in posiciones:
                raise ValueError(
                    f"Letra inválida o repetida en {ruta.name}: {letra}"
                )

            posiciones[letra] = (inicio + columna, float(numero_fila))

    return Distribucion(
        nombre=datos["nombre"],
        posiciones=posiciones,
    )


def cargar_distribuciones(
    carpeta: Path | None = None,
) -> dict[str, Distribucion]:
    if carpeta is None:
        carpeta = Path(__file__).parent / "distribuciones"

    distribuciones = {
        ruta.stem: cargar_distribucion(ruta)
        for ruta in sorted(carpeta.glob("*.json"))
    }

    if not distribuciones:
        raise ValueError(f"No hay distribuciones en {carpeta}")

    return distribuciones


def generar_aleatoria(
    base: Distribucion,
    semilla: int,
) -> Distribucion:
    """Reubica las 26 letras en las posiciones de la distribución base."""
    letras = list(ALFABETO)
    random.Random(semilla).shuffle(letras)

    posiciones_disponibles = [
        base.posiciones[letra] for letra in ALFABETO
    ]

    return Distribucion(
        nombre=f"Aleatoria (semilla {semilla})",
        posiciones=dict(
            zip(letras, posiciones_disponibles, strict=True)
        ),
    )