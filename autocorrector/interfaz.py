"""Aplicación de escritorio en Flet para el autocorrector con A*.

Ejecutar desde la raíz del repositorio:

    python -m autocorrector.interfaz
"""

import flet as ft

from autocorrector.controlador import CLAVE_ALEATORIA, Controlador, Vista
from autocorrector.diccionario import cargar_diccionario
from autocorrector.teclados import ALFABETO, Distribucion, cargar_distribuciones

TAM_TECLA = 46
SEPARACION = 6
PASO = TAM_TECLA + SEPARACION

AZUL = ft.Colors.BLUE_800
COLOR_AVISO = {
    "info": ft.Colors.BLUE_GREY_800,
    "ok": ft.Colors.GREEN_800,
    "error": ft.Colors.RED_700,
}
NOMBRE_OPERACION = {
    "sustitucion": "sustitución",
    "insercion": "inserción",
    "eliminacion": "eliminación",
    "intercambio": "intercambio",
}


def vecinas(teclado: Distribucion, letra: str) -> list[str]:
    return [otra for otra in ALFABETO if teclado.son_vecinas(letra, otra)]


class Aplicacion:
    def __init__(self, page: ft.Page) -> None:
        self.page = page
        self.controlador = Controlador(
            cargar_distribuciones(),
            cargar_diccionario(),
            ejecutar=page.run_thread,
            al_cambiar=self.dibujar,
        )
        self._construir()
        self.dibujar()

    # Construcción de controles

    def _construir(self) -> None:
        page = self.page
        page.title = "Autocorrector con A*"
        page.padding = 24
        page.scroll = ft.ScrollMode.AUTO
        page.theme_mode = ft.ThemeMode.LIGHT
        page.bgcolor = ft.Colors.GREY_50

        ventana = getattr(page, "window", None)
        if ventana is not None:
            ventana.width = 920
            ventana.height = 860

        teclados = self.controlador.teclados
        self.selector = ft.Dropdown(
            label="Distribución de teclado",
            width=260,
            options=[
                ft.DropdownOption(key=clave, text=teclado.nombre)
                for clave, teclado in teclados.items()
            ]
            + [ft.DropdownOption(key=CLAVE_ALEATORIA, text="Aleatoria")],
            on_select=self._al_elegir_teclado,
        )
        self.campo_semilla = ft.TextField(
            label="Semilla",
            width=140,
            hint_text="Opcional",
            keyboard_type=ft.KeyboardType.NUMBER,
        )
        self.boton_generar = ft.OutlinedButton(
            content="Generar aleatorio",
            on_click=self._al_generar,
        )
        self.texto_teclado = ft.Text(size=13, color=ft.Colors.BLUE_GREY_700)

        self.teclado = ft.Stack()
        self.boton_borrar = ft.OutlinedButton(
            content="Borrar", on_click=lambda e: self._tecla(self.controlador.borrar)
        )
        self.boton_espacio = ft.FilledButton(
            content="Espacio",
            width=320,
            on_click=lambda e: self._tecla(self.controlador.pulsar_espacio),
        )

        self.campo = ft.TextField(
            label="Palabra",
            hint_text="De 1 a 6 letras a-z",
            helper="Presiona espacio para revisarla",
            width=320,
            autofocus=True,
            autocorrect=False,
            enable_suggestions=False,
            on_change=lambda e: self.controlador.actualizar_entrada(e.control.value),
        )
        self.progreso = ft.ProgressRing(width=20, height=20, stroke_width=3)
        self.aviso = ft.Text(size=14, selectable=True)

        self.titulo_resultado = ft.Text(size=18, weight=ft.FontWeight.BOLD)
        self.detalle_resultado = ft.Column(spacing=4)
        self.boton_aceptar = ft.FilledButton(
            content="Aceptar", on_click=lambda e: self._tecla(self.controlador.aceptar)
        )
        self.boton_rechazar = ft.OutlinedButton(
            content="Rechazar", on_click=lambda e: self._tecla(self.controlador.rechazar)
        )
        self.panel_resultado = ft.Container(
            padding=16,
            border_radius=8,
            bgcolor=ft.Colors.WHITE,
            border=ft.Border.all(1, ft.Colors.BLUE_100),
            content=ft.Column(
                spacing=10,
                controls=[
                    self.titulo_resultado,
                    self.detalle_resultado,
                    ft.Row([self.boton_aceptar, self.boton_rechazar]),
                ],
            ),
        )

        self.texto_escrito = ft.Text(size=16, selectable=True)

        page.add(
            ft.Text("Autocorrector con A*", size=26, weight=ft.FontWeight.BOLD, color=AZUL),
            ft.Text(
                "Corrige palabras de 1 a 6 letras según la cercanía de las "
                "teclas en la distribución elegida.",
                color=ft.Colors.BLUE_GREY_700,
            ),
            ft.Row(
                [self.selector, self.campo_semilla, self.boton_generar],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            self.texto_teclado,
            self.teclado,
            ft.Row([self.boton_borrar, self.boton_espacio]),
            ft.Divider(),
            ft.Row(
                [self.campo, self.progreso],
                vertical_alignment=ft.CrossAxisAlignment.START,
            ),
            self.aviso,
            self.panel_resultado,
            ft.Divider(),
            ft.Row(
                [
                    ft.Text("Texto escrito", weight=ft.FontWeight.BOLD),
                    ft.TextButton(
                        content="Limpiar",
                        on_click=lambda e: self._tecla(self.controlador.limpiar_texto),
                    ),
                ]
            ),
            self.texto_escrito,
        )

    # Eventos

    def _al_elegir_teclado(self, e: ft.Event) -> None:
        clave = e.control.value

        if clave == CLAVE_ALEATORIA:
            self._al_generar(e)
        else:
            self._tecla(lambda: self.controlador.seleccionar_teclado(clave))

    def _al_generar(self, e: ft.Event) -> None:
        texto = (self.campo_semilla.value or "").strip()
        semilla = None

        if texto:
            if not texto.isdigit():
                self.campo_semilla.error = "Usa un entero de 0 en adelante"
                self.page.update()
                return

            semilla = int(texto)

        self.campo_semilla.error = None
        self._tecla(lambda: self.controlador.generar_aleatorio(semilla))

    def _tecla(self, accion) -> None:
        accion()
        # En Flet 1.0 focus() es asíncrono; se agenda en el ciclo de la página.
        self.page.run_task(self.campo.focus)

    def _pulsar_letra(self, letra: str) -> None:
        self._tecla(lambda: self.controlador.pulsar_tecla(letra))

    # Dibujo

    def dibujar(self) -> None:
        vista = self.controlador.vista()

        self.selector.value = vista.clave_teclado
        if vista.semilla is not None:
            self.campo_semilla.value = str(vista.semilla)
            self.texto_teclado.value = (
                f"Teclado activo: {vista.teclado.nombre}. "
                "Escribe la misma semilla para repetirlo."
            )
        else:
            self.texto_teclado.value = f"Teclado activo: {vista.teclado.nombre}."

        self._dibujar_teclado(vista)

        self.campo.value = vista.palabra
        self.progreso.visible = vista.fase == "buscando"
        self.aviso.value = vista.aviso
        self.aviso.color = COLOR_AVISO[vista.tipo_aviso]
        self.texto_escrito.value = " ".join(vista.texto) or "Aún no hay palabras."

        self._dibujar_resultado(vista)
        self.page.update()

    def _dibujar_teclado(self, vista: Vista) -> None:
        teclado = vista.teclado
        posiciones = teclado.posiciones
        ancho = max(x for x, _ in posiciones.values()) + 1
        alto = max(y for _, y in posiciones.values()) + 1

        teclas = []
        for letra in sorted(posiciones):
            x, y = posiciones[letra]
            resaltada = letra in vista.teclas_resaltadas
            teclas.append(
                ft.Container(
                    left=x * PASO,
                    top=y * PASO,
                    width=TAM_TECLA,
                    height=TAM_TECLA,
                    border_radius=6,
                    alignment=ft.Alignment.CENTER,
                    bgcolor=ft.Colors.AMBER_200 if resaltada else ft.Colors.WHITE,
                    border=ft.Border.all(1, ft.Colors.BLUE_200),
                    tooltip="Vecinas: " + ", ".join(vecinas(teclado, letra)),
                    content=ft.Text(letra.upper(), size=16, weight=ft.FontWeight.W_600),
                    on_click=lambda e, l=letra: self._pulsar_letra(l),
                    data=letra,
                )
            )

        self.teclado.controls = teclas
        self.teclado.width = ancho * PASO
        self.teclado.height = alto * PASO

    def _dibujar_resultado(self, vista: Vista) -> None:
        resultado = vista.resultado
        visible = vista.fase in ("sugerida", "incompleta") and resultado is not None
        self.panel_resultado.visible = visible

        if not visible:
            return

        lineas: list[ft.Control] = []

        if vista.fase == "sugerida":
            self.titulo_resultado.value = (
                f"{resultado.original}  ->  {resultado.sugerencia}"
            )
            lineas.append(ft.Text(f"Costo mínimo: {resultado.costo}"))
            lineas.append(ft.Text("Ruta de operaciones:"))

            for paso in resultado.ruta:
                lineas.append(
                    ft.Text(
                        f"   {paso.origen} -> {paso.destino} "
                        f"({NOMBRE_OPERACION.get(paso.operacion, paso.operacion)}, "
                        f"costo {paso.costo})",
                        font_family="monospace",
                    )
                )

            self.boton_aceptar.visible = True
            self.boton_rechazar.content = "Rechazar"
        else:
            self.titulo_resultado.value = f"{resultado.original}: búsqueda incompleta"
            lineas.append(
                ft.Text(
                    "No se muestra una corrección porque no hay optimalidad "
                    "garantizada con el presupuesto actual."
                )
            )
            self.boton_aceptar.visible = False
            self.boton_rechazar.content = "Conservar original"

        lineas.append(
            ft.Text(
                f"Estados expandidos: {resultado.expandidos:,}   "
                f"Frontera máxima: {resultado.frontera_maxima:,}   "
                f"Tiempo: {vista.segundos:.3f} s",
                color=ft.Colors.BLUE_GREY_700,
            )
        )
        lineas.append(
            ft.Text(
                f"Teclado usado: {vista.teclado.nombre}",
                color=ft.Colors.BLUE_GREY_700,
            )
        )
        self.detalle_resultado.controls = lineas


def main(page: ft.Page) -> None:
    Aplicacion(page)


def ejecutar() -> None:
    ft.run(main)


if __name__ == "__main__":
    ejecutar()
