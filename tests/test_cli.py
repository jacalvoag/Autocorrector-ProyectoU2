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

    def test_informa_sin_correccion_cercana(self):
        proceso = self.ejecutar("xyzxyz")

        self.assertEqual(proceso.returncode, 0, proceso.stderr)
        self.assertIn("Estado: sin_correccion", proceso.stdout)
        self.assertIn("3 cambios o menos", proceso.stdout)
        self.assertNotIn("Costo mínimo:", proceso.stdout)

    def test_max_niveles_cambia_el_resultado(self):
        dos = self.ejecutar("nmovte", "--max-niveles", "2")
        sin_limite = self.ejecutar("nmovte", "--max-niveles", "0")

        self.assertIn("Sugerencia: norte", dos.stdout)
        self.assertIn("Sugerencia: nombre", sin_limite.stdout)

    def test_rechaza_max_niveles_negativo(self):
        proceso = self.ejecutar("gstp", "--max-niveles", "-1")

        self.assertEqual(proceso.returncode, 2)
        self.assertIn("--max-niveles", proceso.stderr)

    def test_rechaza_entrada_invalida(self):
        proceso = self.ejecutar("gáto")

        self.assertEqual(proceso.returncode, 2)
        self.assertIn("Error:", proceso.stderr)


if __name__ == "__main__":
    unittest.main()