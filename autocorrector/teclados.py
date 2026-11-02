import json
import random
from dataclasses import dataclass
from pathlib import Path

ALFABETO = "abcdefghijklmnopqrstuvwxyz"
DISTANCIA_VECINA_CUADRADA = 1.25


@dataclass(frozen=True)
class Distribucion:
    nombre: str
    posiciones: dict[str, tuple[float, float]]

    def __post_init__(self) -> None:
        if set(self.posiciones) != set(ALFABETO):
            raise ValueError(
                "La distribución debe contener exactamente las letras a-z."
            )

        if len(set(self.posiciones.values())) != 26:
            raise ValueError("Dos letras ocupan la misma posición.")

    def son_vecinas(self, primera: str, segunda: str) -> bool:
        if primera == segunda:
            return False

        x1, y1 = self.posiciones[primera]
        x2, y2 = self.posiciones[segunda]

        distancia_cuadrada = (x1 - x2) ** 2 + (y1 - y2) ** 2
        return distancia_cuadrada <= DISTANCIA_VECINA_CUADRADA


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