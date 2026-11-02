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

    def test_vecindad_segun_la_propuesta(self) -> None:
        # Diferencia de fila y de columna como máximo 1, con diagonales,
        # sobre el desplazamiento real de las filas del teclado.
        def vecinas(clave: str, letra: str) -> set[str]:
            teclado = self.distribuciones[clave]
            return {
                otra for otra in ALFABETO if teclado.son_vecinas(letra, otra)
            }

        self.assertEqual(vecinas("qwerty", "g"), set("tyfhvb"))
        self.assertEqual(vecinas("qwerty", "s"), set("weadzx"))
        self.assertEqual(vecinas("azerty", "s"), set("zeqdwx"))
        self.assertEqual(vecinas("dvorak", "g"), set("fcdh"))
        self.assertFalse(
            self.distribuciones["qwerty"].son_vecinas("g", "c")
        )

    def test_tabla_de_cercanias(self) -> None:
        for distribucion in self.distribuciones.values():
            tabla = distribucion.cercanias

            with self.subTest(distribucion=distribucion.nombre):
                self.assertEqual(set(tabla), set(ALFABETO))

                for letra, vecinas in tabla.items():
                    self.assertNotIn(letra, vecinas)

                    for otra in vecinas:
                        self.assertIn(letra, tabla[otra])

        aleatoria = generar_aleatoria(self.distribuciones["qwerty"], 7)
        self.assertNotEqual(
            aleatoria.cercanias, self.distribuciones["qwerty"].cercanias
        )

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