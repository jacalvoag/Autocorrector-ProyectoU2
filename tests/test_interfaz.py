import importlib.util
import unittest

from autocorrector.astar import buscar_correccion
from autocorrector.astar import Paso
from autocorrector.controlador import (
    CLAVE_ALEATORIA,
    MAX_NIVELES,
    Controlador,
    letras_sustituidas,
    posiciones_cambiadas,
    validar_palabra,
)
from autocorrector.diccionario import cargar_diccionario
from autocorrector.teclados import cargar_distribuciones, generar_aleatoria

HAY_FLET = importlib.util.find_spec("flet") is not None


class EjecutorManual:
    """Guarda las búsquedas para decidir en la prueba cuándo terminan."""

    def __init__(self):
        self.pendientes = []

    def __call__(self, tarea):
        self.pendientes.append(tarea)

    def correr_todas(self):
        while self.pendientes:
            self.pendientes.pop(0)()


class TestControlador(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.teclados = cargar_distribuciones()
        cls.diccionario = cargar_diccionario()

    def setUp(self):
        self.ejecutor = EjecutorManual()
        self.cambios = 0
        self.controlador = Controlador(
            self.teclados,
            self.diccionario,
            ejecutar=self.ejecutor,
            al_cambiar=self._contar_cambio,
        )

    def _contar_cambio(self):
        self.cambios += 1

    def escribir(self, texto):
        self.controlador.actualizar_entrada(texto)
        self.ejecutor.correr_todas()
        return self.controlador.vista()

    def test_palabra_valida_no_ofrece_reemplazo(self):
        vista = self.escribir("gato ")

        self.assertEqual(vista.fase, "escribiendo")
        self.assertIsNone(vista.resultado)
        self.assertEqual(vista.texto, ("gato",))
        self.assertEqual(vista.palabra, "")
        self.assertEqual(self.ejecutor.pendientes, [])

    def test_error_de_una_tecla_usa_resultado_del_nucleo(self):
        vista = self.escribir("gatp ")
        esperado = buscar_correccion(
            "gatp", self.teclados["qwerty"], self.diccionario
        )

        self.assertEqual(vista.fase, "sugerida")
        self.assertEqual(vista.resultado.sugerencia, esperado.sugerencia)
        self.assertEqual(vista.resultado.costo, esperado.costo)
        self.assertEqual(vista.resultado.ruta, esperado.ruta)
        self.assertIsNotNone(vista.segundos)

    def test_transposicion(self):
        vista = self.escribir("hoal ")

        self.assertEqual(vista.resultado.sugerencia, "hola")
        self.assertEqual(vista.resultado.costo, 1)
        self.assertEqual(vista.resultado.ruta[0].operacion, "intercambio")

    def test_el_espacio_no_llega_al_algoritmo(self):
        recibidas = []

        def buscar(palabra, *args, **kwargs):
            recibidas.append(palabra)
            return buscar_correccion(palabra, *args, **kwargs)

        controlador = Controlador(
            self.teclados, self.diccionario, self.ejecutor, buscar=buscar
        )
        controlador.actualizar_entrada("gstp ")
        self.ejecutor.correr_todas()

        self.assertEqual(recibidas, ["gstp"])

    def test_aceptar_reemplaza(self):
        self.escribir("gstp ")
        self.controlador.aceptar()
        vista = self.controlador.vista()

        self.assertEqual(vista.texto, ("gato",))
        self.assertEqual(vista.palabra, "")
        self.assertEqual(vista.fase, "escribiendo")

    def test_rechazar_conserva_original(self):
        self.escribir("gstp ")
        self.controlador.rechazar()

        self.assertEqual(self.controlador.vista().texto, ("gstp",))

    def test_aceptar_sin_sugerencia_no_hace_nada(self):
        self.controlador.aceptar()
        self.controlador.rechazar()

        self.assertEqual(self.controlador.vista().texto, ())

    def test_entradas_invalidas(self):
        casos = {
            "HOLA ": "minúsculas",
            "canción ": "tildes",
            "niño ": "ñ",
            "hola1 ": "no está permitido",
            "palabras ": "máximo es 6",
        }

        for entrada, fragmento in casos.items():
            with self.subTest(entrada=entrada):
                vista = self.escribir(entrada)

                self.assertEqual(vista.tipo_aviso, "error")
                self.assertIn(fragmento, vista.aviso)
                self.assertEqual(vista.fase, "escribiendo")
                self.assertEqual(vista.palabra, entrada.strip())
                self.assertEqual(self.ejecutor.pendientes, [])

    def test_espacios_repetidos(self):
        vista = self.escribir("   ")

        self.assertEqual(vista.tipo_aviso, "error")
        self.assertEqual(vista.palabra, "")
        self.assertEqual(vista.texto, ())

    def test_texto_pegado_procesa_solo_la_primera_palabra(self):
        vista = self.escribir("hola mundo azul ")

        self.assertEqual(vista.texto, ("hola",))
        self.assertIn("mundo azul", vista.aviso)

    def test_teclas_en_pantalla(self):
        for letra in "gstp":
            self.controlador.pulsar_tecla(letra)

        self.controlador.borrar()
        self.controlador.pulsar_tecla("p")
        self.controlador.pulsar_espacio()
        self.ejecutor.correr_todas()

        self.assertEqual(self.controlador.vista().resultado.original, "gstp")

    def test_cambio_de_teclado_afecta_la_correccion(self):
        qwerty = self.escribir("gstp ").resultado
        self.controlador.rechazar()

        self.controlador.seleccionar_teclado("dvorak")
        dvorak = self.escribir("gstp ").resultado

        self.assertEqual((qwerty.sugerencia, qwerty.costo), ("gato", 2))
        self.assertEqual((dvorak.sugerencia, dvorak.costo), ("este", 3))
        self.assertEqual(self.controlador.vista().teclado.nombre, "Dvorak")

    def test_teclado_desconocido(self):
        with self.assertRaises(ValueError):
            self.controlador.seleccionar_teclado("colemak")

    def test_aleatorio_con_semilla_es_repetible(self):
        self.controlador.generar_aleatorio(2026)
        vista = self.controlador.vista()
        esperado = generar_aleatoria(self.teclados["qwerty"], 2026)

        self.assertEqual(vista.clave_teclado, CLAVE_ALEATORIA)
        self.assertEqual(vista.semilla, 2026)
        self.assertEqual(vista.teclado.posiciones, esperado.posiciones)

        self.controlador.seleccionar_teclado("qwerty")
        self.assertIsNone(self.controlador.vista().semilla)

    def test_aleatorio_sin_semilla_muestra_la_generada(self):
        self.controlador.seleccionar_teclado(CLAVE_ALEATORIA)
        vista = self.controlador.vista()

        self.assertIsNotNone(vista.semilla)
        self.assertEqual(
            vista.teclado.posiciones,
            generar_aleatoria(self.teclados["qwerty"], vista.semilla).posiciones,
        )

    def test_limite_de_niveles_predeterminado_es_automatico(self):
        self.assertEqual(MAX_NIVELES, 3)
        self.assertTrue(self.controlador.vista().automatico)

    def test_limite_automatico_depende_del_largo(self):
        from autocorrector.controlador import limite_por_largo

        self.assertEqual(
            [limite_por_largo(n) for n in range(1, 7)], [1, 1, 2, 2, 3, 3]
        )

        for palabra, esperado in (("gstp", 2), ("nmovte", 3), ("gtp", 2)):
            with self.subTest(palabra=palabra):
                vista = self.escribir(palabra + " ")

                self.assertEqual(vista.max_niveles, esperado)
                self.assertTrue(vista.automatico)
                self.controlador.rechazar()

    def test_limite_fijo_ignora_el_largo_y_se_puede_volver_a_automatico(self):
        self.controlador.cambiar_max_niveles(3)
        vista = self.escribir("gstp ")

        self.assertFalse(vista.automatico)
        self.assertEqual(vista.max_niveles, 3)
        self.controlador.rechazar()

        self.controlador.usar_limite_automatico()
        vista = self.escribir("gstp ")

        self.assertTrue(vista.automatico)
        self.assertEqual(vista.max_niveles, 2)

    def test_cambiar_el_limite_descarta_la_sugerencia_pendiente(self):
        self.assertEqual(self.escribir("nmovte ").fase, "sugerida")

        self.controlador.cambiar_max_niveles(2)
        vista = self.controlador.vista()

        self.assertEqual(vista.fase, "escribiendo")
        self.assertEqual(vista.max_niveles, 2)

        vista = self.escribir("nmovte ")
        self.assertEqual(vista.resultado.sugerencia, "norte")

        with self.assertRaises(ValueError):
            self.controlador.cambiar_max_niveles(0)

    def test_comparar_sin_limite_guarda_la_otra_busqueda(self):
        vista = self.escribir("nmovte ")
        self.assertIsNone(vista.comparacion)

        self.controlador.comparar_sin_limite()
        self.assertTrue(self.controlador.vista().comparando)
        self.ejecutor.correr_todas()
        vista = self.controlador.vista()

        self.assertFalse(vista.comparando)
        self.assertEqual(vista.comparacion.sugerencia, "nombre")
        self.assertGreater(
            vista.comparacion.frontera_maxima, vista.resultado.frontera_maxima
        )

    def test_comparacion_se_descarta_si_cambia_la_entrada(self):
        self.escribir("nmovte ")
        self.controlador.comparar_sin_limite()
        self.controlador.actualizar_entrada("nmov")
        self.ejecutor.correr_todas()
        vista = self.controlador.vista()

        self.assertIsNone(vista.comparacion)
        self.assertFalse(vista.comparando)

    def test_no_compara_cuando_ya_no_hay_limite(self):
        self.controlador.cambiar_max_niveles(None)
        self.escribir("nmovte ")
        self.controlador.comparar_sin_limite()

        self.assertEqual(self.ejecutor.pendientes, [])

    def test_sin_correccion_cercana_conserva_la_entrada(self):
        vista = self.escribir("xyzxyz ")

        self.assertEqual(vista.fase, "sin_correccion")
        self.assertEqual(vista.resultado.estado, "sin_correccion")
        self.assertIsNone(vista.resultado.sugerencia)
        self.assertIn("3 cambios o menos", vista.aviso)

        self.controlador.aceptar()
        self.assertEqual(self.controlador.vista().texto, ())

        self.controlador.rechazar()
        vista = self.controlador.vista()
        self.assertEqual(vista.texto, ("xyzxyz",))
        self.assertEqual(vista.fase, "escribiendo")

    def test_aviso_en_singular_con_un_nivel(self):
        controlador = Controlador(
            self.teclados, self.diccionario, self.ejecutor, max_niveles=1
        )
        controlador.actualizar_entrada("xyzxyz ")
        self.ejecutor.correr_todas()

        self.assertIn("1 cambio o menos", controlador.vista().aviso)

    def test_corrige_dentro_del_limite(self):
        vista = self.escribir("nmovte ")

        self.assertEqual(vista.fase, "sugerida")
        self.assertEqual(vista.resultado.sugerencia, "nombre")
        self.assertLessEqual(len(vista.resultado.ruta), MAX_NIVELES)

    def test_resultado_incompleto_no_tiene_costo(self):
        controlador = Controlador(
            self.teclados, self.diccionario, self.ejecutor, max_estados=5
        )
        controlador.actualizar_entrada("xyzxyz ")
        self.ejecutor.correr_todas()
        vista = controlador.vista()

        self.assertEqual(vista.fase, "incompleta")
        self.assertIsNone(vista.resultado.costo)
        self.assertIsNone(vista.resultado.sugerencia)
        self.assertNotIn("Costo", vista.aviso)

        controlador.aceptar()
        self.assertEqual(controlador.vista().texto, ())

        controlador.rechazar()
        self.assertEqual(controlador.vista().texto, ("xyzxyz",))

    def test_resultado_tardio_tras_cambiar_palabra(self):
        self.controlador.actualizar_entrada("gstp ")
        self.controlador.actualizar_entrada("gst")
        self.ejecutor.correr_todas()
        vista = self.controlador.vista()

        self.assertEqual(vista.fase, "escribiendo")
        self.assertIsNone(vista.resultado)
        self.assertEqual(vista.palabra, "gst")
        self.assertEqual(self.controlador.descartadas, 1)

    def test_resultado_tardio_tras_cambiar_teclado(self):
        self.controlador.actualizar_entrada("gstp ")
        self.controlador.seleccionar_teclado("azerty")
        self.ejecutor.correr_todas()
        vista = self.controlador.vista()

        self.assertIsNone(vista.resultado)
        self.assertEqual(vista.teclado.nombre, "AZERTY")
        self.assertEqual(self.controlador.descartadas, 1)

    def test_busqueda_vieja_no_pisa_a_la_nueva(self):
        self.controlador.actualizar_entrada("gstp ")
        self.controlador.actualizar_entrada("hoal ")
        vieja, nueva = self.ejecutor.pendientes
        nueva()
        vieja()
        vista = self.controlador.vista()

        self.assertEqual(vista.resultado.original, "hoal")
        self.assertEqual(vista.resultado.sugerencia, "hola")
        self.assertEqual(self.controlador.descartadas, 1)

    def test_error_del_nucleo_no_rompe_el_flujo(self):
        def falla(*args, **kwargs):
            raise RuntimeError("fallo simulado")

        controlador = Controlador(
            self.teclados, self.diccionario, self.ejecutor, buscar=falla
        )
        controlador.actualizar_entrada("gstp ")
        self.ejecutor.correr_todas()
        vista = controlador.vista()

        self.assertEqual(vista.fase, "escribiendo")
        self.assertEqual(vista.tipo_aviso, "error")
        self.assertIn("fallo simulado", vista.aviso)

    def test_notifica_cambios(self):
        self.escribir("gstp ")

        self.assertGreaterEqual(self.cambios, 2)


class TestAuxiliares(unittest.TestCase):
    def test_validar_palabra(self):
        self.assertIsNone(validar_palabra("gato"))
        self.assertIsNotNone(validar_palabra(""))
        self.assertIsNotNone(validar_palabra("abcdefg"))

    def test_letras_sustituidas(self):
        teclados = cargar_distribuciones()
        resultado = buscar_correccion(
            "gstp", teclados["qwerty"], cargar_diccionario()
        )

        self.assertEqual(letras_sustituidas(resultado), set("saop"))
        self.assertEqual(letras_sustituidas(None), frozenset())

    def test_posiciones_cambiadas(self):
        casos = {
            Paso("gstp", "gatp", "sustitucion", 1): ({1}, {1}),
            Paso("hoal", "hola", "intercambio", 1): ({2, 3}, {2, 3}),
            Paso("gto", "gato", "insercion", 2): (set(), {1}),
            Paso("gatos", "gato", "eliminacion", 2): ({4}, set()),
        }

        for paso, (origen, destino) in casos.items():
            with self.subTest(paso=paso):
                self.assertEqual(posiciones_cambiadas(paso), (origen, destino))


class PaginaFalsa:
    """Lo mínimo de ft.Page que usa la aplicación, sin abrir ventana."""

    def __init__(self):
        self.controls = []
        self.actualizaciones = 0
        self.tareas = []

    def add(self, *controles):
        self.controls.extend(controles)

    def update(self, *controles):
        self.actualizaciones += 1

    def run_thread(self, tarea, *args):
        tarea(*args)

    def run_task(self, tarea, *args):
        self.tareas.append(tarea)


@unittest.skipUnless(HAY_FLET, "Flet no está instalado")
class TestVistaFlet(unittest.TestCase):

    def test_hover_conserva_la_tecla_para_el_click(self):
        tecla = next(t for t in self.app.teclado.controls if t.data == "g")

        self.app._al_senalar("g", True)

        misma = next(t for t in self.app.teclado.controls if t.data == "g")
        self.assertIs(misma, tecla)

        tecla.on_click(None)
        self.assertEqual(self.app.controlador.vista().palabra, "g")

    def setUp(self):
        from autocorrector.interfaz import Aplicacion

        self.pagina = PaginaFalsa()
        self.app = Aplicacion(self.pagina)

    def test_teclado_usa_las_posiciones_de_la_distribucion(self):
        teclas = {tecla.data: tecla for tecla in self.app.teclado.controls}
        posiciones = self.app.controlador.vista().teclado.posiciones

        self.assertEqual(set(teclas), set(posiciones))

        for letra, (x, y) in posiciones.items():
            self.assertEqual(teclas[letra].left, x * 52)
            self.assertEqual(teclas[letra].top, y * 52)

    def test_flujo_completo_con_teclas_en_pantalla(self):
        teclas = {tecla.data: tecla for tecla in self.app.teclado.controls}

        for letra in "gstp":
            teclas[letra].on_click(None)

        self.app.boton_espacio.on_click(None)

        self.assertTrue(self.app.panel_resultado.visible)
        self.assertTrue(self.app.boton_aceptar.visible)
        self.assertIn("gato", self.app.titulo_resultado.value)

        self.app.boton_aceptar.on_click(None)

        self.assertFalse(self.app.panel_resultado.visible)
        self.assertEqual(
            [ficha.data for ficha in self.app.texto_escrito.controls], ["gato"]
        )
        self.assertEqual(self.app.campo.value, "")
        self.assertTrue(self.pagina.tareas)  # Se regresó el foco al campo.

    def test_cambio_de_teclado_redibuja(self):
        self.app.controlador.seleccionar_teclado("dvorak")
        teclas = {tecla.data: tecla for tecla in self.app.teclado.controls}
        dvorak = self.app.controlador.teclados["dvorak"].posiciones

        self.assertEqual(self.app.selector.value, "dvorak")
        self.assertEqual(teclas["a"].left, dvorak["a"][0] * 52)

    def test_ruta_se_dibuja_como_cadena_de_nodos(self):
        self.app.controlador.actualizar_entrada("gstp ")
        ruta = self.app.controlador.vista().resultado.ruta

        # inicio + (arista + nodo) por cada paso
        self.assertEqual(len(self.app.ruta.controls), 1 + 2 * len(ruta))
        self.assertEqual(len(self.app.metricas.controls), 4)

    def test_incompleta_oculta_ruta_y_aceptar(self):
        from autocorrector.controlador import Busqueda
        from autocorrector.astar import Resultado

        controlador = self.app.controlador
        controlador._contador += 1
        controlador._palabra = "xyzxyz"
        busqueda = Busqueda(controlador._contador, "xyzxyz", controlador.vista().teclado)
        controlador._busqueda_actual = busqueda
        controlador._fase = "buscando"
        controlador.recibir_resultado(
            busqueda, Resultado("incompleta", "xyzxyz", None, None, (), 10, 99), 0.1
        )

        self.assertTrue(self.app.panel_resultado.visible)
        self.assertFalse(self.app.boton_aceptar.visible)
        self.assertFalse(self.app.titulo_ruta.visible)
        self.assertEqual(self.app.ruta.controls, [])

    def test_sin_correccion_oculta_ruta_y_aceptar(self):
        self.app.controlador.actualizar_entrada("xyzxyz ")

        self.assertEqual(self.app.controlador.vista().fase, "sin_correccion")
        self.assertTrue(self.app.panel_resultado.visible)
        self.assertEqual(self.app.etiqueta_estado.value, "Sin corrección cercana")
        self.assertFalse(self.app.boton_aceptar.visible)
        self.assertFalse(self.app.titulo_ruta.visible)
        self.assertEqual(self.app.ruta.controls, [])
        self.assertIn("3 cambios o menos", self.app.nota_resultado.value)

    def test_selector_de_limite_cambia_la_busqueda(self):
        self.assertEqual(self.app.selector_niveles.value, "auto")

        self.app.selector_niveles.value = "2"
        self.app._al_elegir_niveles(
            type("E", (), {"control": self.app.selector_niveles})()
        )
        self.app.controlador.actualizar_entrada("nmovte ")

        self.assertEqual(self.app.selector_niveles.value, "2")
        self.assertIn("norte", self.app.titulo_resultado.value)
        self.assertIn("2 cambios", self.app.nota_resultado.value)

        self.app.controlador.cambiar_max_niveles(None)
        self.assertEqual(self.app.selector_niveles.value, "sin")

        self.app.selector_niveles.value = "auto"
        self.app._al_elegir_niveles(
            type("E", (), {"control": self.app.selector_niveles})()
        )
        self.assertEqual(self.app.selector_niveles.value, "auto")

    def textos(self, control):
        """Todos los textos de un control y sus hijos."""
        import flet as ft

        encontrados = []
        pila = [control]

        while pila:
            actual = pila.pop()

            if isinstance(actual, ft.Text):
                encontrados.append(str(actual.value or ""))

                for tramo in actual.spans or []:
                    encontrados.append(str(tramo.text))

            for hijo in getattr(actual, "controls", None) or []:
                pila.append(hijo)

            contenido = getattr(actual, "content", None)

            if contenido is not None and not isinstance(contenido, str):
                pila.append(contenido)

        return encontrados

    def test_lateral_muestra_los_niveles_hasta_el_limite(self):
        self.app.controlador.actualizar_entrada("nmovte ")
        textos = self.textos(self.app.grafo.lateral)

        self.assertIn("Límite: 3 cambios", textos)
        self.assertIn("Nivel 3 de 3", textos)
        self.assertIn("nombre", textos)
        self.assertTrue(any(t.startswith("Último nivel") for t in textos))

        self.app.controlador.cambiar_max_niveles(2)
        self.app.controlador.actualizar_entrada("nmovte ")
        textos = self.textos(self.app.grafo.lateral)

        self.assertIn("Límite: 2 cambios", textos)
        self.assertIn("Nivel 2 de 2", textos)
        self.assertNotIn("Nivel 3 de 3", textos)

    def test_lateral_cuenta_combinaciones_generadas_y_cortadas(self):
        self.app.controlador.actualizar_entrada("nmovte ")
        textos = " ".join(self.textos(self.app.grafo.lateral))

        self.assertIn("combinaciones", textos)
        self.assertIn("el límite descartó", textos)

    def test_sin_correccion_muestra_los_niveles_vacios(self):
        self.app.controlador.actualizar_entrada("xyzxyz ")
        textos = self.textos(self.app.grafo.lateral)

        self.assertIn("Límite: 3 cambios", textos)
        self.assertIn("—", textos)

    def test_muestra_los_empates_con_su_frecuencia(self):
        self.app.controlador.cambiar_max_niveles(2)
        self.app.controlador.actualizar_entrada("nmovte ")
        textos = self.textos(self.app.bloque_empates)

        self.assertIn("norte", textos)
        self.assertIn("monte", textos)
        self.assertTrue(any("elegida" in t for t in textos))
        self.assertTrue(any(t.startswith("78%") for t in textos))
        self.assertTrue(any("se optó por la de mayor probabilidad" in t for t in textos))
        palabras = [t for t in textos if t in ("norte", "monte", "note", "mote")]
        self.assertEqual(set(palabras), {"norte", "monte", "note", "mote"})
        self.assertLessEqual(len(palabras), 5)

    def test_sin_empate_lo_dice(self):
        self.app.controlador.actualizar_entrada("gstp ")
        textos = self.textos(self.app.bloque_empates)

        self.assertTrue(any("única palabra" in t for t in textos))

    def test_comparar_sin_limite_muestra_ambas_busquedas(self):
        self.app.controlador.actualizar_entrada("nmovte ")
        self.app.boton_comparar.on_click(None)
        textos = self.textos(self.app.bloque_limite)

        self.assertTrue(any(t.startswith("Con límite de 3 cambios") for t in textos))
        self.assertTrue(any(t.startswith("Sin límite") for t in textos))

    def test_senalar_tecla_resalta_vecinas(self):
        self.app._al_senalar("g", True)
        teclas = {tecla.data: tecla for tecla in self.app.teclado.controls}

        self.assertNotEqual(teclas["g"].bgcolor, teclas["q"].bgcolor)
        self.assertEqual(teclas["f"].bgcolor, teclas["h"].bgcolor)
        self.assertNotEqual(teclas["f"].bgcolor, teclas["q"].bgcolor)

        self.app._al_senalar("g", False)
        teclas = {tecla.data: tecla for tecla in self.app.teclado.controls}
        self.assertEqual(teclas["g"].bgcolor, teclas["q"].bgcolor)

    def test_generar_aleatorio_muestra_la_semilla(self):
        self.app._al_generar(None)
        vista = self.app.controlador.vista()

        self.assertEqual(vista.clave_teclado, "aleatoria")
        self.assertIn(str(vista.semilla), self.app.texto_teclado.value)
        self.assertEqual(self.app.selector.value, "aleatoria")


if __name__ == "__main__":
    unittest.main()
