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

    def test_traza_con_limite_de_niveles(self):
        resultado, traza = self.buscar("nmovte", max_niveles=3)

        self.assertEqual(resultado.sugerencia, "nombre")
        self.assertEqual(len(traza), resultado.expandidos)
        self.assertEqual(len({e.estado for e in traza}), len(traza))
        self.assertTrue(all(e.g <= 2 * (3 - 1) for e in traza))

    def test_traza_en_busqueda_sin_correccion(self):
        resultado, traza = self.buscar("xyzxyz", max_niveles=3)

        self.assertEqual(resultado.estado, "sin_correccion")
        self.assertEqual(len(traza), resultado.expandidos)

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

    def test_dibuja_busqueda_sin_correccion(self):
        from autocorrector.visualizacion import dibujar_busqueda, seleccionar_nodos

        resultado, traza = self.resolver("xyzxyz", max_niveles=3)
        nodos = seleccionar_nodos(resultado, traza)

        self.assertEqual(resultado.estado, "sin_correccion")
        self.assertNotIn("meta", {n.tipo for n in nodos.values()})
        self.assertTrue(dibujar_busqueda(resultado, traza).startswith(b"\x89PNG"))

    def test_dibuja_busqueda_incompleta(self):
        from autocorrector.visualizacion import dibujar_busqueda, seleccionar_nodos

        resultado, traza = self.resolver("xyzxyz", max_estados=500)
        nodos = seleccionar_nodos(resultado, traza)

        self.assertNotIn("meta", {n.tipo for n in nodos.values()})
        self.assertTrue(dibujar_busqueda(resultado, traza).startswith(b"\x89PNG"))


class TestTrazaEnControlador(unittest.TestCase):
    def test_vista_trae_la_traza(self):
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
        self.assertEqual(len(vista.traza), vista.resultado.expandidos)
        self.assertEqual(vista.traza[0].estado, "gstp")

        controlador.aceptar()
        self.assertEqual(controlador.vista().traza, ())


HAY_FLET = importlib.util.find_spec("flet") is not None


class PaginaFalsa:
    def __init__(self):
        self.tareas = []

    def add(self, *controles):
        pass

    def update(self, *controles):
        pass

    def run_thread(self, tarea, *args):
        tarea(*args)

    def run_task(self, tarea, *args):
        self.tareas.append((tarea, args))


@unittest.skipUnless(HAY_FLET, "Flet no está instalado")
class TestGrafoInteractivo(unittest.TestCase):
    def setUp(self):
        from autocorrector.interfaz import GrafoBusqueda

        teclados = cargar_distribuciones()
        self.traza = []
        self.resultado = buscar_correccion(
            "nmovte", teclados["qwerty"], cargar_diccionario(), traza=self.traza
        )
        self.pagina = PaginaFalsa()
        self.grafo = GrafoBusqueda(self.pagina)
        self.grafo.mostrar(self.resultado, tuple(self.traza))

    def tarjetas(self):
        return [c for c in self.grafo.area.controls if isinstance(c.data, str)]

    def test_empieza_mostrando_el_resultado_final(self):
        estados = {t.data for t in self.tarjetas()}

        self.assertIn("nombre", estados)
        self.assertIn("nmovte", estados)
        self.assertIn("es una palabra válida", self.grafo.explicacion.value)

    def test_paso_a_paso_en_orden_real(self):
        self.grafo.ir(1)
        self.assertEqual([t.data for t in self.tarjetas()], ["nmovte"])

        self.grafo.ir(3)
        esperados = [e.estado for e in self.traza[:3]]
        self.assertEqual([t.data for t in self.tarjetas()], esperados)
        self.assertIn(f"Paso {self.traza[2].orden}", self.grafo.explicacion.value)

    def test_los_limites_no_se_salen(self):
        self.grafo.ir(0)
        self.assertEqual(self.grafo._paso, 1)

        self.grafo.ir(999)
        self.assertEqual(self.grafo._paso, len(self.grafo._pasos))

    def test_clic_en_un_nodo_explica_ese_nodo(self):
        self.grafo.seleccionar("nmobte")

        self.assertIn("«nmobte»", self.grafo.explicacion.value)
        self.assertIn("cambiar una letra", self.grafo.explicacion.value)

    def test_reproducir_agenda_la_animacion(self):
        self.grafo._alternar()

        self.assertEqual(len(self.pagina.tareas), 1)
        self.assertEqual(self.grafo._paso, 0)
        self.assertEqual(self.grafo.boton_reproducir.content, "Pausar")

        self.grafo._alternar()
        self.assertEqual(self.grafo.boton_reproducir.content, "Reproducir")

    def test_la_animacion_avanza_hasta_el_final(self):
        import asyncio

        self.grafo.ir(len(self.grafo._pasos) - 2)
        self.grafo._reproduciendo = True
        self.grafo._generacion += 1

        async def sin_espera(segundos):
            return None

        original = asyncio.sleep
        asyncio.sleep = sin_espera
        try:
            asyncio.run(self.grafo._animar(self.grafo._generacion))
        finally:
            asyncio.sleep = original

        self.assertEqual(self.grafo._paso, len(self.grafo._pasos))
        self.assertFalse(self.grafo._reproduciendo)

    def test_misma_busqueda_conserva_el_paso(self):
        self.grafo.ir(2)
        self.grafo.mostrar(self.resultado, tuple(self.traza))

        self.assertEqual(self.grafo._paso, 2)


if __name__ == "__main__":
    unittest.main()
