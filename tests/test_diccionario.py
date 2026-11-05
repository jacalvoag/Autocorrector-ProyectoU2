import tempfile
import unittest
from pathlib import Path

from autocorrector.diccionario import cargar_diccionario


class TestDiccionario(unittest.TestCase):
    def test_carga_diccionario_generado(self) -> None:
        palabras = cargar_diccionario()

        self.assertIn("gato", palabras)
        self.assertIn("casa", palabras)
        self.assertNotIn("gatp", palabras)

    def test_diccionario_generado_trae_frecuencias(self) -> None:
        palabras = cargar_diccionario()

        self.assertEqual(set(palabras.frecuencias), set(palabras))
        self.assertGreater(palabras.frecuencias["de"], palabras.frecuencias["gato"])
        self.assertGreater(palabras.frecuencias["gato"], 2.5)

    def test_diccionario_generado_sin_siglas_ni_palabras_raras(self) -> None:
        palabras = cargar_diccionario()

        for basura in ("tpo", "too", "abc", "sra", "nro", "km", "d", "ap"):
            with self.subTest(palabra=basura):
                self.assertNotIn(basura, palabras)

        for comun in ("top", "casa", "nombre", "monte", "a", "de", "y"):
            with self.subTest(palabra=comun):
                self.assertIn(comun, palabras)

    def test_lee_frecuencias_y_palabras_sin_frecuencia(self) -> None:
        with tempfile.TemporaryDirectory() as temporal:
            ruta = Path(temporal) / "palabras.txt"
            ruta.write_text("casa 4.5\nperro 3.25\n", encoding="utf-8")

            palabras = cargar_diccionario(ruta)

            self.assertEqual(palabras, frozenset({"casa", "perro"}))
            self.assertEqual(
                palabras.frecuencias, {"casa": 4.5, "perro": 3.25}
            )

            ruta.write_text("casa perro\n", encoding="utf-8")

            self.assertEqual(cargar_diccionario(ruta).frecuencias, {})

    def test_rechaza_frecuencia_no_positiva(self) -> None:
        with tempfile.TemporaryDirectory() as temporal:
            ruta = Path(temporal) / "palabras.txt"
            ruta.write_text("casa 0\n", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "Frecuencia"):
                cargar_diccionario(ruta)

    def test_rechaza_palabra_repetida(self) -> None:
        with tempfile.TemporaryDirectory() as temporal:
            ruta = Path(temporal) / "palabras.txt"
            ruta.write_text("casa perro casa", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "repetida"):
                cargar_diccionario(ruta)

    def test_rechaza_caracteres_invalidos(self) -> None:
        with tempfile.TemporaryDirectory() as temporal:
            ruta = Path(temporal) / "palabras.txt"
            ruta.write_text("gato árbol", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "Caracteres"):
                cargar_diccionario(ruta)

    def test_rechaza_archivo_vacio(self) -> None:
        with tempfile.TemporaryDirectory() as temporal:
            ruta = Path(temporal) / "palabras.txt"
            ruta.write_text("", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "vacío"):
                cargar_diccionario(ruta)


if __name__ == "__main__":
    unittest.main()