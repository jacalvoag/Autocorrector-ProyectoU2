import json
import tempfile
import unittest
from pathlib import Path

from autocorrector.teclados import (
    ALFABETO,
    cargar_distribuciones,
    generar_aleatoria,
)


class TestTeclados(unittest.TestCase):
    def setUp(self) -> None:
        self.distribuciones = cargar_distribuciones()

    def test_se_cargan_las_tres_distribuciones(self) -> None:
        self.assertEqual(
            set(self.distribuciones),
            {"qwerty", "azerty", "dvorak"},
        )

        for distribucion in self.distribuciones.values():
            self.assertEqual(
                set(distribucion.posiciones),
                set(ALFABETO),
            )

    def test_vecindad_depende_de_las_posiciones(self) -> None:
        qwerty = self.distribuciones["qwerty"]

        self.assertTrue(qwerty.son_vecinas("a", "s"))
        self.assertTrue(qwerty.son_vecinas("q", "a"))
        self.assertFalse(qwerty.son_vecinas("q", "p"))
        self.assertFalse(qwerty.son_vecinas("a", "a"))

    def test_aleatoria_conserva_letras_y_posiciones(self) -> None:
        base = self.distribuciones["qwerty"]
        primera = generar_aleatoria(base, semilla=2026)
        segunda = generar_aleatoria(base, semilla=2026)

        self.assertEqual(primera.posiciones, segunda.posiciones)
        self.assertEqual(set(primera.posiciones), set(ALFABETO))
        self.assertEqual(
            set(primera.posiciones.values()),
            set(base.posiciones.values()),
        )

    def test_descubre_un_archivo_nuevo(self) -> None:
        qwerty = Path(__file__).resolve().parents[1]
        qwerty /= "autocorrector/distribuciones/qwerty.json"
        datos = json.loads(qwerty.read_text(encoding="utf-8"))
        datos["nombre"] = "Distribución de prueba"

        with tempfile.TemporaryDirectory() as temporal:
            nueva = Path(temporal) / "personalizada.json"
            nueva.write_text(
                json.dumps(datos),
                encoding="utf-8",
            )

            cargadas = cargar_distribuciones(Path(temporal))

        self.assertIn("personalizada", cargadas)


if __name__ == "__main__":
    unittest.main()