import importlib.util
import unittest

from autocorrector.astar import buscar_correccion
from autocorrector.diccionario import cargar_diccionario
from autocorrector.teclados import cargar_distribuciones

HAY_MATPLOTLIB = importlib.util.find_spec("matplotlib") is not None


class TestTraza(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.teclados = cargar_distribuciones()
        cls.diccionario = cargar_diccionario()

    def buscar(self, palabra, **opciones):
        traza = []
        resultado = buscar_correccion(
            palabra,
            self.teclados["qwerty"],
            self.diccionario,
            traza=traza,
            **opciones,
        )
        return resultado, traza

    def test_traza_no_cambia_el_resultado(self):
        sin_traza = buscar_correccion(
            "nmovte", self.teclados["qwerty"], self.diccionario
        )
        con_traza, _ = self.buscar("nmovte")

        self.assertEqual(sin_traza, con_traza)

    def test_una_entrada_por_estado_expandido(self):
        resultado, traza = self.buscar("nmovte")

        self.assertEqual(len(traza), resultado.expandidos)
        self.assertEqual([e.orden for e in traza], list(range(1, len(traza) + 1)))

    def test_empieza_en_la_palabra_escrita(self):
        _, traza = self.buscar("gstp")

        self.assertEqual(traza[0].estado, "gstp")
        self.assertIsNone(traza[0].padre)
        self.assertEqual(traza[0].g, 0)

    def test_la_ruta_sale_de_los_estados_expandidos(self):
        resultado, traza = self.buscar("nmovte")
        expandidos = {e.estado for e in traza}

        for paso in resultado.ruta:
            self.assertIn(paso.origen, expandidos)

    def test_cada_padre_se_expandio_antes(self):
        _, traza = self.buscar("cssa")
        orden = {e.estado: e.orden for e in traza}

        for expansion in traza[1:]:
            self.assertLess(orden[expansion.padre], expansion.orden)

    def test_f_nunca_baja_en_la_ruta(self):
        resultado, traza = self.buscar("nmovte")
        por_estado = {e.estado: e for e in traza}
        valores = [
            por_estado[p.origen].g + por_estado[p.origen].h
            for p in resultado.ruta
        ]

        self.assertEqual(valores, sorted(valores))

    def test_traza_en_busqueda_incompleta(self):
        resultado, traza = self.buscar("xyzxyz", max_estados=500)

        self.assertEqual(resultado.estado, "incompleta")
        self.assertEqual(len(traza), resultado.expandidos)


@unittest.skipUnless(HAY_MATPLOTLIB, "matplotlib no está instalado")
class TestDibujo(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.teclados = cargar_distribuciones()
        cls.diccionario = cargar_diccionario()

    def resolver(self, palabra, **opciones):
        traza = []
        resultado = buscar_correccion(
            palabra,
            self.teclados["qwerty"],
            self.diccionario,
            traza=traza,
            **opciones,
        )
        return resultado, traza

    def test_genera_png(self):
        from autocorrector.visualizacion import dibujar_busqueda

        resultado, traza = self.resolver("nmovte")
        imagen = dibujar_busqueda(resultado, traza)

        self.assertTrue(imagen.startswith(b"\x89PNG"))

    def test_incluye_ruta_y_primeros_expandidos(self):
        from autocorrector.visualizacion import seleccionar_nodos

        resultado, traza = self.resolver("nmovte")
        nodos = seleccionar_nodos(resultado, traza, limite=10)

        for paso in resultado.ruta:
            self.assertIn(paso.destino, nodos)

        for expansion in traza[:10]:
            self.assertIn(expansion.estado, nodos)

        self.assertEqual(nodos["nmovte"].tipo, "inicio")
        self.assertEqual(nodos["nombre"].tipo, "meta")
        self.assertEqual(nodos["nmobte"].tipo, "ruta")

    def test_arbol_conectado(self):
        from autocorrector.visualizacion import seleccionar_nodos

        resultado, traza = self.resolver("gstp")
        nodos = seleccionar_nodos(resultado, traza)

        for nodo in nodos.values():
            if nodo.tipo != "inicio":
                self.assertIn(nodo.padre, nodos)

    def test_dibuja_busqueda_incompleta(self):
        from autocorrector.visualizacion import dibujar_busqueda, seleccionar_nodos

        resultado, traza = self.resolver("xyzxyz", max_estados=500)
        nodos = seleccionar_nodos(resultado, traza)

        self.assertNotIn("meta", {n.tipo for n in nodos.values()})
        self.assertTrue(dibujar_busqueda(resultado, traza).startswith(b"\x89PNG"))


@unittest.skipUnless(HAY_MATPLOTLIB, "matplotlib no está instalado")
class TestGrafoEnControlador(unittest.TestCase):
    def test_vista_trae_el_grafo(self):
        from autocorrector.controlador import Controlador

        pendientes = []
        controlador = Controlador(
            cargar_distribuciones(),
            cargar_diccionario(),
            ejecutar=pendientes.append,
        )
        controlador.actualizar_entrada("gstp ")
        pendientes.pop()()
        vista = controlador.vista()

        self.assertEqual(vista.fase, "sugerida")
        self.assertTrue(vista.grafo.startswith(b"\x89PNG"))

        controlador.aceptar()
        self.assertIsNone(controlador.vista().grafo)

    def test_error_al_dibujar_no_rompe_la_correccion(self):
        from autocorrector.controlador import Controlador

        def falla(*args):
            raise RuntimeError("sin dibujo")

        pendientes = []
        controlador = Controlador(
            cargar_distribuciones(),
            cargar_diccionario(),
            ejecutar=pendientes.append,
            graficar=falla,
        )
        controlador.actualizar_entrada("gstp ")
        pendientes.pop()()
        vista = controlador.vista()

        self.assertEqual(vista.resultado.sugerencia, "gato")
        self.assertIsNone(vista.grafo)


if __name__ == "__main__":
    unittest.main()
