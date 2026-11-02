import tempfile
import unittest
from pathlib import Path

from autocorrector.diccionario import cargar_diccionario


class TestDiccionario(unittest.TestCase):
    def test_carga_lista_fija(self) -> None:
        palabras = cargar_diccionario()

        self.assertEqual(len(palabras), 160)
        self.assertIn("gato", palabras)
        self.assertIn("tecla", palabras)
        self.assertNotIn("gatp", palabras)

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