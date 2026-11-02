import unittest
from heapq import heappop, heappush

import random

from autocorrector.astar import (
    _sucesores,
    buscar_correccion,
    heuristica_directa,
    indice_heuristica,
)
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


class TestPropuesta(unittest.TestCase):
    """Ajustes para que el núcleo coincida con la propuesta registrada."""

    @classmethod
    def setUpClass(cls):
        cls.teclados = cargar_distribuciones()
        cls.diccionario = cargar_diccionario()
        cls.indice = indice_heuristica(cls.diccionario)

    def test_ejemplo_de_la_propuesta(self):
        vocabulario = frozenset({"gato", "gasto", "gota", "pato"})

        # A "gstp" le faltan la a y la o para formar "gato": h = 2.
        self.assertEqual(indice_heuristica(vocabulario).calcular("gstp"), 2)

        resultado = buscar_correccion(
            "gstp", self.teclados["qwerty"], vocabulario
        )
        self.assertEqual((resultado.sugerencia, resultado.costo), ("gato", 2))

    def test_no_se_genera_la_palabra_vacia(self):
        for palabra in ("q", "ab", "gato", "gatito"):
            with self.subTest(palabra=palabra):
                destinos = [
                    destino
                    for destino, _, _ in _sucesores(
                        palabra, self.teclados["qwerty"]
                    )
                ]

                self.assertNotIn("", destinos)
                self.assertTrue(all(1 <= len(d) <= 6 for d in destinos))

    def test_indice_coincide_con_la_formula(self):
        azar = random.Random(2026)
        letras = "abcdefghijklmnopqrstuvwxyz"
        estados = [
            "".join(azar.choice(letras) for _ in range(azar.randint(1, 6)))
            for _ in range(150)
        ] + azar.sample(sorted(self.diccionario), 50)

        for estado in estados:
            with self.subTest(estado=estado):
                self.assertEqual(
                    self.indice.calcular(estado),
                    heuristica_directa(estado, self.diccionario),
                )

    def test_heuristica_admisible(self):
        casos = [
            ("gstp", frozenset({"gato", "gasto", "gota", "pato"})),
            ("gtao", frozenset({"gato"})),
            ("perro", frozenset({"pero", "pera"})),
            ("cssa", frozenset({"casa", "cosa"})),
            ("al", frozenset({"ala", "sal"})),
        ]

        for teclado in self.teclados.values():
            for inicio, metas in casos:
                with self.subTest(teclado=teclado.nombre, inicio=inicio):
                    self.assertLessEqual(
                        indice_heuristica(metas).calcular(inicio),
                        costo_uniforme(inicio, metas, teclado),
                    )

    def test_heuristica_consistente(self):
        teclado = self.teclados["qwerty"]

        for estado in ("gstp", "hoal", "xyzxyz", "q", "cssa", "prro"):
            for destino, _, costo in _sucesores(estado, teclado):
                with self.subTest(estado=estado, destino=destino):
                    self.assertLessEqual(
                        self.indice.calcular(estado),
                        costo + self.indice.calcular(destino),
                    )

    def test_indice_se_construye_una_vez(self):
        self.assertIs(
            indice_heuristica(self.diccionario),
            indice_heuristica(self.diccionario),
        )


if __name__ == "__main__":
    unittest.main()