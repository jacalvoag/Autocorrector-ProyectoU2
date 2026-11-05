import unittest
from heapq import heappop, heappush

import random

from autocorrector.astar import (
    _sucesores,
    buscar_correccion,
    heuristica_directa,
    indice_heuristica,
)
from autocorrector.diccionario import Diccionario, cargar_diccionario
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


def costo_uniforme_con_niveles(inicio, metas, teclado, niveles):
    """Referencia sin heurística ni podas: costo uniforme sobre (palabra, nivel).

    Devuelve (meta, costo) con la meta más barata (a igual costo, la más
    frecuente y luego la alfabética), o (None, None).
    """
    frecuencias = getattr(metas, "frecuencias", {})

    def preferencia(palabra):
        return (-frecuencias.get(palabra, 0), palabra)

    frontera = [(0, inicio, 0)]
    mejor = {(inicio, 0): 0}
    meta = None
    costo_meta = None

    while frontera:
        costo, estado, nivel = heappop(frontera)

        if mejor.get((estado, nivel)) != costo:
            continue

        if costo_meta is not None and costo > costo_meta:
            break

        if estado in metas:
            if (
                costo_meta is None
                or costo < costo_meta
                or (
                    costo == costo_meta
                    and preferencia(estado) < preferencia(meta)
                )
            ):
                meta, costo_meta = estado, costo

            continue

        if nivel >= niveles:
            continue

        for destino, _, costo_operacion in _sucesores(estado, teclado):
            nuevo = costo + costo_operacion

            if nuevo < mejor.get((destino, nivel + 1), float("inf")):
                mejor[(destino, nivel + 1)] = nuevo
                heappush(frontera, (nuevo, destino, nivel + 1))

    return meta, costo_meta


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

    def test_desempate_por_frecuencia(self):
        # Mismo costo: gatl (alfabética) contra gato (más usada).
        vocabulario = Diccionario(
            {"gato", "gatl"}, {"gato": 5.2, "gatl": 1.1}
        )

        resultado = buscar_correccion(
            "gatp", self.teclados["qwerty"], vocabulario
        )

        self.assertEqual(resultado.sugerencia, "gato")
        self.assertEqual(resultado.costo, 1)

    def test_frecuencia_no_supera_al_costo(self):
        # gatl cuesta menos aunque se use poquísimo: el costo manda.
        vocabulario = Diccionario(
            {"gatl", "gatos"}, {"gatl": 0.5, "gatos": 6.0}
        )

        resultado = buscar_correccion(
            "gatp", self.teclados["qwerty"], vocabulario
        )

        self.assertEqual(resultado.sugerencia, "gatl")

    def test_misma_frecuencia_desempata_alfabeticamente(self):
        vocabulario = Diccionario(
            {"gato", "gatl"}, {"gato": 3.0, "gatl": 3.0}
        )

        resultado = buscar_correccion(
            "gatp", self.teclados["qwerty"], vocabulario
        )

        self.assertEqual(resultado.sugerencia, "gatl")

    def test_frecuencia_con_limite_de_niveles(self):
        vocabulario = Diccionario(
            {"gato", "gatl"}, {"gato": 5.2, "gatl": 1.1}
        )

        resultado = buscar_correccion(
            "gatp", self.teclados["qwerty"], vocabulario, max_niveles=2
        )

        self.assertEqual(resultado.sugerencia, "gato")

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


class TestLimiteDeNiveles(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.teclados = cargar_distribuciones()
        cls.diccionario = cargar_diccionario()

    def test_limite_invalido(self):
        with self.assertRaises(ValueError):
            buscar_correccion(
                "gstp",
                self.teclados["qwerty"],
                self.diccionario,
                max_niveles=0,
            )

    def test_limite_no_cambia_una_ruta_que_cabe(self):
        sin_limite = buscar_correccion(
            "nmovte", self.teclados["qwerty"], self.diccionario
        )
        con_limite = buscar_correccion(
            "nmovte", self.teclados["qwerty"], self.diccionario, max_niveles=3
        )

        self.assertEqual(con_limite.sugerencia, "nombre")
        self.assertEqual(con_limite.costo, sin_limite.costo)
        self.assertEqual(con_limite.ruta, sin_limite.ruta)
        self.assertLessEqual(con_limite.frontera_maxima, sin_limite.frontera_maxima)

    def test_casos_del_reporte_con_limite_de_tres(self):
        casos = [
            ("nmovte", "qwerty", "nombre"),
            ("cyqrot", "dvorak", "cierto"),
            ("cyqrot", "qwerty", "cuarto"),
            ("gstp", "qwerty", "gato"),
        ]

        for palabra, clave, esperada in casos:
            with self.subTest(palabra=palabra, teclado=clave):
                resultado = buscar_correccion(
                    palabra,
                    self.teclados[clave],
                    self.diccionario,
                    max_niveles=3,
                )

                self.assertEqual(resultado.sugerencia, esperada)

    def test_sin_correccion_cuando_no_alcanzan_los_niveles(self):
        resultado = buscar_correccion(
            "cyqrot",
            self.teclados["dvorak"],
            self.diccionario,
            max_niveles=2,
        )

        self.assertEqual(resultado.estado, "sin_correccion")
        self.assertIsNone(resultado.sugerencia)
        self.assertIsNone(resultado.costo)
        self.assertEqual(resultado.ruta, ())

    def test_con_menos_niveles_la_sugerencia_puede_ser_otra(self):
        resultado = buscar_correccion(
            "nmovte", self.teclados["qwerty"], self.diccionario, max_niveles=2
        )

        self.assertEqual(resultado.sugerencia, "norte")
        self.assertEqual(resultado.costo, 4)
        self.assertEqual(len(resultado.ruta), 2)

    def test_ruta_barata_con_mas_pasos_contra_cara_con_menos(self):
        # abc a cba: tres intercambios cuestan 3; dos sustituciones lejanas, 4.
        metas = frozenset({"cba"})
        teclado = self.teclados["qwerty"]
        esperado = {None: (3, 3), 3: (3, 3), 2: (4, 2)}

        for niveles, (costo, pasos) in esperado.items():
            with self.subTest(niveles=niveles):
                resultado = buscar_correccion(
                    "abc", teclado, metas, max_niveles=niveles
                )

                self.assertEqual(resultado.costo, costo)
                self.assertEqual(len(resultado.ruta), pasos)

        uno = buscar_correccion("abc", teclado, metas, max_niveles=1)
        self.assertEqual(uno.estado, "sin_correccion")

    def test_la_ruta_respeta_el_limite_y_encadena(self):
        for niveles in (1, 2, 3):
            resultado = buscar_correccion(
                "gstp",
                self.teclados["qwerty"],
                self.diccionario,
                max_niveles=niveles,
            )

            if resultado.estado != "sugerida":
                continue

            self.assertLessEqual(len(resultado.ruta), niveles)
            actual = "gstp"

            for paso in resultado.ruta:
                self.assertEqual(paso.origen, actual)
                actual = paso.destino

            self.assertEqual(actual, resultado.sugerencia)

    def test_coincide_con_la_referencia_sin_podas(self):
        generador = random.Random(11)
        palabras = sorted(p for p in self.diccionario if 3 <= len(p) <= 6)
        teclados = [
            self.teclados["qwerty"],
            self.teclados["azerty"],
            self.teclados["dvorak"],
        ]
        comprobados = 0

        while comprobados < 14:
            palabra = generador.choice(palabras)
            posicion = generador.randrange(len(palabra))
            palabra = (
                palabra[:posicion]
                + generador.choice("abcdefghijklmnopqrstuvwxyz")
                + palabra[posicion + 1:]
            )

            if palabra in self.diccionario:
                continue

            teclado = generador.choice(teclados)
            niveles = generador.choice((2, 3))
            resultado = buscar_correccion(
                palabra, teclado, self.diccionario, max_niveles=niveles
            )
            meta, costo = costo_uniforme_con_niveles(
                palabra, self.diccionario, teclado, niveles
            )

            if meta is None:
                self.assertEqual(resultado.estado, "sin_correccion")
            else:
                self.assertEqual(
                    (resultado.sugerencia, resultado.costo), (meta, costo)
                )

            comprobados += 1

    def test_el_limite_respeta_el_presupuesto_de_estados(self):
        resultado = buscar_correccion(
            "xyzxyz",
            self.teclados["qwerty"],
            self.diccionario,
            max_estados=500,
            max_niveles=3,
        )

        self.assertEqual(resultado.estado, "incompleta")


if __name__ == "__main__":
    unittest.main()