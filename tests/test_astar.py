import unittest
from heapq import heappop, heappush

from autocorrector.astar import _sucesores, buscar_correccion
from autocorrector.diccionario import cargar_diccionario
from autocorrector.teclados import cargar_distribuciones


def costo_uniforme(inicio, metas, teclado):
    frontera = [(0, inicio)]
    mejor = {inicio: 0}

    while frontera:
        costo, estado = heappop(frontera)

        if costo != mejor[estado]:
            continue

        if estado in metas:
            return costo

        for destino, _, costo_operacion in _sucesores(estado, teclado):
            nuevo = costo + costo_operacion

            if nuevo < mejor.get(destino, float("inf")):
                mejor[destino] = nuevo
                heappush(frontera, (nuevo, destino))

    raise AssertionError("La meta debería ser alcanzable.")


class TestAStar(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.teclados = cargar_distribuciones()

    def test_palabra_valida(self):
        resultado = buscar_correccion(
            "gato",
            self.teclados["qwerty"],
            frozenset({"gato"}),
        )

        self.assertEqual(resultado.estado, "valida")
        self.assertEqual(resultado.expandidos, 0)

    def test_desempate_alfabetico(self):
        resultado = buscar_correccion(
            "gatp",
            self.teclados["qwerty"],
            frozenset({"gato", "gatl"}),
        )

        self.assertEqual(resultado.sugerencia, "gatl")
        self.assertEqual(resultado.costo, 1)

    def test_ruta_y_costos(self):
        resultado = buscar_correccion(
            "gtao",
            self.teclados["qwerty"],
            frozenset({"gato"}),
        )

        self.assertEqual(resultado.sugerencia, "gato")
        self.assertEqual(resultado.ruta[0].operacion, "intercambio")
        self.assertEqual(
            resultado.costo,
            sum(paso.costo for paso in resultado.ruta),
        )

    def test_compara_con_costo_uniforme(self):
        casos = [
            ("gatp", frozenset({"gato", "gatl"})),
            ("gtao", frozenset({"gato"})),
            ("gat", frozenset({"gato"})),
            ("gato", frozenset({"gat"})),
            ("gstp", frozenset({"gato"})),
        ]

        for teclado in self.teclados.values():
            for inicio, metas in casos:
                with self.subTest(teclado=teclado.nombre, inicio=inicio):
                    resultado = buscar_correccion(inicio, teclado, metas)

                    self.assertEqual(
                        resultado.costo,
                        costo_uniforme(inicio, metas, teclado),
                    )

    def test_limite_informa_busqueda_incompleta(self):
        resultado = buscar_correccion(
            "gatp",
            self.teclados["qwerty"],
            frozenset({"gato"}),
            max_estados=1,
        )

        self.assertEqual(resultado.estado, "incompleta")
        self.assertIsNone(resultado.sugerencia)

    def test_diccionario_real(self):
        palabras = cargar_diccionario()
        resultado = buscar_correccion(
            "gstp",
            self.teclados["qwerty"],
            palabras,
        )

        self.assertEqual(resultado.estado, "sugerida")
        self.assertIn(resultado.sugerencia, palabras)

    def test_entrada_invalida(self):
        for palabra in ("", "ÁRBOL", "gáto", "perrito", "gato "):
            with self.subTest(palabra=palabra):
                with self.assertRaises(ValueError):
                    buscar_correccion(
                        palabra,
                        self.teclados["qwerty"],
                        frozenset({"gato"}),
                    )


if __name__ == "__main__":
    unittest.main()