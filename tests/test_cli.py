import subprocess
import sys
import unittest


class TestCLI(unittest.TestCase):
    def ejecutar(self, *argumentos: str):
        return subprocess.run(
            [sys.executable, "-m", "autocorrector.cli", *argumentos],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )

    def test_corrige_con_diccionario_real(self):
        proceso = self.ejecutar("gstp", "--teclado", "qwerty")

        self.assertEqual(proceso.returncode, 0, proceso.stderr)
        self.assertIn("Estado: sugerida", proceso.stdout)
        self.assertIn("Sugerencia:", proceso.stdout)
        self.assertIn("Costo mínimo:", proceso.stdout)

    def test_informa_busqueda_incompleta(self):
        proceso = self.ejecutar("gatp", "--max-estados", "1")

        self.assertEqual(proceso.returncode, 0, proceso.stderr)
        self.assertIn("Estado: incompleta", proceso.stdout)
        self.assertNotIn("Costo mínimo:", proceso.stdout)

    def test_rechaza_entrada_invalida(self):
        proceso = self.ejecutar("gáto")

        self.assertEqual(proceso.returncode, 2)
        self.assertIn("Error:", proceso.stderr)


if __name__ == "__main__":
    unittest.main()