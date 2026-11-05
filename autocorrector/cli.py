import argparse
import secrets
import sys
from time import perf_counter

from autocorrector.astar import buscar_correccion
from autocorrector.controlador import MAX_NIVELES, limite_por_largo, texto_cambios
from autocorrector.diccionario import cargar_diccionario
from autocorrector.teclados import cargar_distribuciones, generar_aleatoria


def main(argv: list[str] | None = None) -> int:
    teclados = cargar_distribuciones()

    parser = argparse.ArgumentParser(
        description="Prueba por consola del autocorrector con A*."
    )
    parser.add_argument("palabra", help="Palabra de 1 a 6 letras a-z.")
    parser.add_argument(
        "--teclado",
        choices=[*teclados, "aleatorio"],
        default="qwerty",
    )
    parser.add_argument(
        "--semilla",
        type=int,
        help="Semilla para reproducir un teclado aleatorio.",
    )
    parser.add_argument(
        "--max-estados",
        type=int,
        help="Presupuesto opcional; puede producir una búsqueda incompleta.",
    )
    parser.add_argument(
        "--max-niveles",
        type=int,
        default=None,
        help=(
            "Operaciones máximas de la corrección. Sin esta opción depende "
            "del largo de la palabra (1-2 letras: 1; 3-4: 2; 5-6: "
            f"{MAX_NIVELES}). Con 0 no hay límite."
        ),
    )

    parser.add_argument(
        "--grafo",
        metavar="ARCHIVO.png",
        help="Guarda una imagen del árbol de búsqueda (requiere matplotlib).",
    )

    argumentos = parser.parse_args(argv)

    if argumentos.teclado == "aleatorio":
        semilla = (
            argumentos.semilla
            if argumentos.semilla is not None
            else secrets.randbits(32)
        )
        teclado = generar_aleatoria(teclados["qwerty"], semilla)
    else:
        if argumentos.semilla is not None:
            parser.error("--semilla solo se usa con --teclado aleatorio")

        teclado = teclados[argumentos.teclado]

    if argumentos.max_niveles is not None and argumentos.max_niveles < 0:
        parser.error("--max-niveles no puede ser negativo")

    max_niveles = argumentos.max_niveles

    if max_niveles is None:
        max_niveles = limite_por_largo(len(argumentos.palabra))

    diccionario = cargar_diccionario()

    try:
        inicio = perf_counter()
        traza = []
        resultado = buscar_correccion(
            argumentos.palabra,
            teclado,
            diccionario,
            max_estados=argumentos.max_estados,
            max_niveles=max_niveles or None,
            traza=traza,
        )
        segundos = perf_counter() - inicio
    except ValueError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2

    print(f"Teclado: {teclado.nombre}")
    print(f"Palabras en el diccionario: {len(diccionario)}")
    print(f"Entrada: {resultado.original}")
    print(
        "Límite de cambios: "
        + ("sin límite" if not max_niveles else str(max_niveles))
    )
    print(f"Estado: {resultado.estado}")

    if resultado.estado == "valida":
        print("La palabra ya pertenece al diccionario.")
    elif resultado.estado == "incompleta":
        print("No se puede garantizar una sugerencia óptima.")
    elif resultado.estado == "sin_correccion":
        print(
            "No hay una palabra del diccionario a "
            f"{texto_cambios(max_niveles)} o menos."
        )
    else:
        print(f"Sugerencia: {resultado.sugerencia}")
        print(f"Costo mínimo: {resultado.costo}")
        print("Ruta:")

        for paso in resultado.ruta:
            print(
                f"  {paso.origen} -> {paso.destino} "
                f"({paso.operacion}, costo {paso.costo})"
            )

    print(f"Estados expandidos: {resultado.expandidos}")
    print(f"Frontera máxima: {resultado.frontera_maxima}")
    print(f"Tiempo de búsqueda: {segundos:.4f} s")

    if argumentos.grafo and resultado.estado != "valida":
        from pathlib import Path

        from autocorrector.visualizacion import dibujar_busqueda

        Path(argumentos.grafo).write_bytes(dibujar_busqueda(resultado, traza))
        print(f"Grafo guardado en {argumentos.grafo}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())