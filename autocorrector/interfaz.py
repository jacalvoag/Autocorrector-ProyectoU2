"""Aplicación de escritorio en Flet para el autocorrector con A*.

Ejecutar desde la raíz del repositorio:

    python -m autocorrector.interfaz

La ruta se dibuja como una cadena de nodos (inicio, estados intermedios y
meta) unidos por aristas con su operación y costo, al estilo de los
visualizadores de búsqueda en grafos. Solo se muestran datos que devuelve
el núcleo; no se reconstruye ni se inventa el recorrido.
"""

import flet as ft

from autocorrector.astar import Paso
from autocorrector.controlador import (
    CLAVE_ALEATORIA,
    Controlador,
    Vista,
    posiciones_cambiadas,
)
from autocorrector.diccionario import cargar_diccionario
from autocorrector.teclados import ALFABETO, Distribucion, cargar_distribuciones

TAM_TECLA = 46
SEPARACION = 6
PASO = TAM_TECLA + SEPARACION

# Paleta: la misma de la primera versión (azul, ámbar para resaltar,
# verde y rojo para avisos), organizada por uso.
PRIMARIO = ft.Colors.BLUE_800
PRIMARIO_SUAVE = ft.Colors.BLUE_50
BORDE = ft.Colors.BLUE_100
BORDE_TECLA = ft.Colors.BLUE_200
FONDO = ft.Colors.GREY_50
SUPERFICIE = ft.Colors.WHITE
TEXTO_SECUNDARIO = ft.Colors.BLUE_GREY_700
RESALTE = ft.Colors.AMBER_200
RESALTE_BORDE = ft.Colors.AMBER_700
EXITO = ft.Colors.GREEN_800
ERROR = ft.Colors.RED_700

ESTILO_AVISO = {
    "info": (ft.Icons.INFO_OUTLINE, PRIMARIO, PRIMARIO_SUAVE),
    "ok": (ft.Icons.CHECK_CIRCLE_OUTLINE, EXITO, ft.Colors.GREEN_50),
    "error": (ft.Icons.ERROR_OUTLINE, ERROR, ft.Colors.RED_50),
}
OPERACIONES = {
    "sustitucion": ("sustitución", ft.Colors.BLUE_700),
    "intercambio": ("intercambio", ft.Colors.INDIGO_400),
    "insercion": ("inserción", ft.Colors.GREEN_700),
    "eliminacion": ("eliminación", ft.Colors.RED_400),
}
FUENTE_PALABRA = "Consolas"
FUENTES_RESPALDO = ["Courier New", "monospace"]


def vecinas(teclado: Distribucion, letra: str) -> list[str]:
    return [otra for otra in ALFABETO if teclado.son_vecinas(letra, otra)]


# Piezas visuales reutilizables


def tarjeta(*controles: ft.Control, **opciones) -> ft.Container:
    return ft.Container(
        padding=20,
        border_radius=12,
        bgcolor=SUPERFICIE,
        border=ft.Border.all(1, BORDE),
        shadow=ft.BoxShadow(
            blur_radius=10,
            spread_radius=0,
            color=ft.Colors.with_opacity(0.06, ft.Colors.BLUE_GREY_900),
            offset=ft.Offset(0, 2),
        ),
        content=ft.Column(list(controles), spacing=14),
        **opciones,
    )


def titulo_seccion(icono: ft.IconData, texto: str) -> ft.Row:
    return ft.Row(
        [
            ft.Icon(icono, color=PRIMARIO, size=20),
            ft.Text(texto, size=16, weight=ft.FontWeight.BOLD, color=PRIMARIO),
        ],
        spacing=8,
        tight=True,
    )


def muestra(color: str, borde: str, texto: str) -> ft.Row:
    return ft.Row(
        [
            ft.Container(
                width=16,
                height=16,
                border_radius=4,
                bgcolor=color,
                border=ft.Border.all(1, borde),
            ),
            ft.Text(texto, size=12, color=TEXTO_SECUNDARIO),
        ],
        spacing=6,
        tight=True,
    )


def metrica(etiqueta: str, valor: str, ayuda: str) -> ft.Container:
    return ft.Container(
        expand=True,
        padding=ft.Padding.symmetric(vertical=12, horizontal=14),
        border_radius=10,
        bgcolor=PRIMARIO_SUAVE,
        tooltip=ayuda,
        content=ft.Column(
            [
                ft.Text(etiqueta, size=12, color=TEXTO_SECUNDARIO),
                ft.Text(valor, size=22, weight=ft.FontWeight.BOLD, color=PRIMARIO),
            ],
            spacing=2,
        ),
    )


def palabra_marcada(palabra: str, marcadas: frozenset[int], tamano: int = 18) -> ft.Text:
    """Palabra en monoespaciado con las letras cambiadas resaltadas."""
    return ft.Text(
        spans=[
            ft.TextSpan(
                letra,
                ft.TextStyle(
                    bgcolor=RESALTE if i in marcadas else None,
                    weight=ft.FontWeight.BOLD if i in marcadas else ft.FontWeight.W_500,
                ),
            )
            for i, letra in enumerate(palabra)
        ],
        size=tamano,
        font_family=FUENTE_PALABRA,
        font_family_fallback=FUENTES_RESPALDO,
        color=ft.Colors.BLUE_GREY_900,
    )


def nodo(palabra: str, marcadas: frozenset[int], tipo: str) -> ft.Column:
    """Estado de la ruta. tipo: inicio, intermedio o meta."""
    if tipo == "inicio":
        borde, fondo, etiqueta = PRIMARIO, PRIMARIO_SUAVE, "inicio"
    elif tipo == "meta":
        borde, fondo, etiqueta = EXITO, ft.Colors.GREEN_50, "meta"
    else:
        borde, fondo, etiqueta = BORDE_TECLA, SUPERFICIE, ""

    return ft.Column(
        [
            ft.Text(etiqueta, size=11, color=borde, weight=ft.FontWeight.BOLD),
            ft.Container(
                padding=ft.Padding.symmetric(vertical=8, horizontal=12),
                border_radius=10,
                bgcolor=fondo,
                border=ft.Border.all(2, borde),
                content=palabra_marcada(palabra, marcadas),
            ),
        ],
        spacing=2,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
    )


def arista(paso: Paso) -> ft.Column:
    nombre, color = OPERACIONES.get(paso.operacion, (paso.operacion, PRIMARIO))
    return ft.Column(
        [
            ft.Container(
                padding=ft.Padding.symmetric(vertical=2, horizontal=8),
                border_radius=20,
                bgcolor=ft.Colors.with_opacity(0.12, color),
                content=ft.Text(nombre, size=11, color=color, weight=ft.FontWeight.W_600),
            ),
            ft.Icon(ft.Icons.ARROW_FORWARD, color=color, size=20),
            ft.Text(f"+{paso.costo}", size=12, color=color, weight=ft.FontWeight.BOLD),
        ],
        spacing=0,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
    )


def cadena_de_ruta(ruta: tuple[Paso, ...]) -> list[ft.Control]:
    if not ruta:
        return []

    origen_marcado, _ = posiciones_cambiadas(ruta[0])
    controles: list[ft.Control] = [nodo(ruta[0].origen, origen_marcado, "inicio")]

    for numero, paso in enumerate(ruta, start=1):
        _, destino_marcado = posiciones_cambiadas(paso)
        tipo = "meta" if numero == len(ruta) else "intermedio"
        controles.append(arista(paso))
        controles.append(nodo(paso.destino, destino_marcado, tipo))

    return controles


def ficha_palabra(palabra: str) -> ft.Container:
    return ft.Container(
        padding=ft.Padding.symmetric(vertical=6, horizontal=12),
        border_radius=20,
        bgcolor=PRIMARIO_SUAVE,
        border=ft.Border.all(1, BORDE),
        content=ft.Text(palabra, size=15, color=PRIMARIO, weight=ft.FontWeight.W_500),
        data=palabra,
    )


class Aplicacion:
    def __init__(self, page: ft.Page) -> None:
        self.page = page
        self.tecla_senalada: str | None = None
        self.controlador = Controlador(
            cargar_distribuciones(),
            cargar_diccionario(),
            ejecutar=page.run_thread,
            al_cambiar=self.dibujar,
        )
        self._construir()
        self.dibujar()

    # Construcción

    def _construir(self) -> None:
        page = self.page
        page.title = "Autocorrector con A*"
        page.padding = 0
        page.spacing = 0
        page.scroll = ft.ScrollMode.AUTO
        page.theme_mode = ft.ThemeMode.LIGHT
        page.bgcolor = FONDO
        page.theme = ft.Theme(color_scheme_seed=ft.Colors.BLUE)

        ventana = getattr(page, "window", None)
        if ventana is not None:
            ventana.width = 1180
            ventana.height = 900
            ventana.min_width = 760

        page.add(
            self._encabezado(),
            ft.Container(
                padding=ft.Padding.symmetric(vertical=20, horizontal=24),
                content=ft.Column(
                    [
                        ft.ResponsiveRow(
                            [self._tarjeta_teclado(), self._tarjeta_palabra()],
                            spacing=20,
                            run_spacing=20,
                        ),
                        self._tarjeta_resultado(),
                        self._tarjeta_texto(),
                    ],
                    spacing=20,
                ),
            ),
        )

    def _encabezado(self) -> ft.Container:
        self.etiqueta_teclado = ft.Text(size=13, color=SUPERFICIE, weight=ft.FontWeight.W_600)
        return ft.Container(
            padding=ft.Padding.symmetric(vertical=18, horizontal=24),
            gradient=ft.LinearGradient(
                begin=ft.Alignment.CENTER_LEFT,
                end=ft.Alignment.CENTER_RIGHT,
                colors=[ft.Colors.BLUE_900, ft.Colors.BLUE_700],
            ),
            content=ft.Row(
                [
                    ft.Container(
                        width=44,
                        height=44,
                        border_radius=10,
                        bgcolor=ft.Colors.with_opacity(0.15, SUPERFICIE),
                        alignment=ft.Alignment.CENTER,
                        content=ft.Icon(ft.Icons.SPELLCHECK, color=SUPERFICIE, size=26),
                    ),
                    ft.Column(
                        [
                            ft.Text(
                                "Autocorrector con A*",
                                size=22,
                                weight=ft.FontWeight.BOLD,
                                color=SUPERFICIE,
                            ),
                            ft.Text(
                                "f(n) = g(n) + h(n)   ·   el costo de cada cambio "
                                "depende de la cercanía de las teclas",
                                size=13,
                                color=ft.Colors.BLUE_100,
                            ),
                        ],
                        spacing=2,
                        expand=True,
                    ),
                    ft.Container(
                        padding=ft.Padding.symmetric(vertical=6, horizontal=12),
                        border_radius=20,
                        border=ft.Border.all(1, ft.Colors.with_opacity(0.5, SUPERFICIE)),
                        content=ft.Row(
                            [
                                ft.Icon(ft.Icons.KEYBOARD, color=SUPERFICIE, size=16),
                                self.etiqueta_teclado,
                            ],
                            spacing=6,
                        ),
                    ),
                ],
                spacing=14,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        )

    def _tarjeta_teclado(self) -> ft.Container:
        teclados = self.controlador.teclados
        self.selector = ft.Dropdown(
            label="Distribución",
            width=200,
            dense=True,
            options=[
                ft.DropdownOption(key=clave, text=teclado.nombre)
                for clave, teclado in teclados.items()
            ]
            + [ft.DropdownOption(key=CLAVE_ALEATORIA, text="Aleatoria")],
            on_select=self._al_elegir_teclado,
        )
        self.campo_semilla = ft.TextField(
            label="Semilla",
            width=120,
            dense=True,
            hint_text="Opcional",
            keyboard_type=ft.KeyboardType.NUMBER,
        )
        self.boton_generar = ft.OutlinedButton(
            content="Generar aleatorio",
            icon=ft.Icons.CASINO_OUTLINED,
            on_click=self._al_generar,
        )
        self.texto_teclado = ft.Text(size=12, color=TEXTO_SECUNDARIO)

        self.teclado = ft.Stack()
        self.boton_borrar = ft.OutlinedButton(
            content="Borrar",
            icon=ft.Icons.BACKSPACE_OUTLINED,
            on_click=lambda e: self._tecla(self.controlador.borrar),
        )
        self.boton_espacio = ft.FilledButton(
            content="Espacio",
            icon=ft.Icons.SPACE_BAR,
            expand=True,
            on_click=lambda e: self._tecla(self.controlador.pulsar_espacio),
        )

        return tarjeta(
            titulo_seccion(ft.Icons.KEYBOARD, "Teclado"),
            ft.Row(
                [self.selector, self.campo_semilla, self.boton_generar],
                wrap=True,
                spacing=10,
                run_spacing=10,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            self.texto_teclado,
            ft.Container(
                padding=ft.Padding.symmetric(vertical=6),
                alignment=ft.Alignment.CENTER,
                content=self.teclado,
            ),
            ft.Row(
                [
                    muestra(PRIMARIO, PRIMARIO, "Tecla señalada"),
                    muestra(PRIMARIO_SUAVE, BORDE_TECLA, "Sus vecinas (costo 1)"),
                    muestra(RESALTE, RESALTE_BORDE, "Usada en la corrección"),
                ],
                wrap=True,
                spacing=16,
            ),
            ft.Row([self.boton_borrar, self.boton_espacio], spacing=10),
            col={"sm": 12, "md": 7},
        )

    def _tarjeta_palabra(self) -> ft.Container:
        self.campo = ft.TextField(
            label="Palabra",
            hint_text="De 1 a 6 letras a-z",
            helper="Presiona espacio para revisarla",
            autofocus=True,
            autocorrect=False,
            enable_suggestions=False,
            text_size=20,
            prefix_icon=ft.Icons.EDIT_OUTLINED,
            border_radius=10,
            on_change=lambda e: self.controlador.actualizar_entrada(e.control.value),
        )
        self.progreso = ft.ProgressBar(color=PRIMARIO, bgcolor=PRIMARIO_SUAVE)
        self.icono_aviso = ft.Icon(ft.Icons.INFO_OUTLINE, size=20)
        self.aviso = ft.Text(size=14, selectable=True, expand=True)
        self.caja_aviso = ft.Container(
            padding=12,
            border_radius=8,
            content=ft.Row(
                [self.icono_aviso, self.aviso],
                spacing=10,
                vertical_alignment=ft.CrossAxisAlignment.START,
            ),
        )

        reglas = ft.Column(
            [
                ft.Text("Costos de cada operación", size=12, weight=ft.FontWeight.BOLD, color=TEXTO_SECUNDARIO),
                ft.Text("Sustituir por tecla vecina: 1   ·   no vecina: 2", size=12, color=TEXTO_SECUNDARIO),
                ft.Text("Insertar o eliminar: 2   ·   intercambiar contiguas: 1", size=12, color=TEXTO_SECUNDARIO),
            ],
            spacing=2,
        )

        return tarjeta(
            titulo_seccion(ft.Icons.EDIT_NOTE, "Palabra"),
            self.campo,
            self.progreso,
            self.caja_aviso,
            ft.Divider(height=1, color=BORDE),
            reglas,
            col={"sm": 12, "md": 5},
        )

    def _tarjeta_resultado(self) -> ft.Container:
        self.titulo_resultado = ft.Text(size=20, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_GREY_900)
        self.etiqueta_estado = ft.Text(size=12, weight=ft.FontWeight.BOLD)
        self.caja_estado = ft.Container(
            padding=ft.Padding.symmetric(vertical=4, horizontal=10),
            border_radius=20,
            content=self.etiqueta_estado,
        )
        self.metricas = ft.Row(spacing=12)
        self.ruta = ft.Row(
            wrap=True,
            spacing=10,
            run_spacing=12,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )
        self.titulo_ruta = ft.Text(
            "Ruta encontrada por A*",
            size=13,
            weight=ft.FontWeight.BOLD,
            color=TEXTO_SECUNDARIO,
        )
        self.nota_resultado = ft.Text(size=13, color=TEXTO_SECUNDARIO)
        self.boton_aceptar = ft.FilledButton(
            content="Aceptar",
            icon=ft.Icons.CHECK,
            on_click=lambda e: self._tecla(self.controlador.aceptar),
        )
        self.boton_rechazar = ft.OutlinedButton(
            content="Rechazar",
            icon=ft.Icons.CLOSE,
            on_click=lambda e: self._tecla(self.controlador.rechazar),
        )

        self.panel_resultado = tarjeta(
            ft.Row(
                [
                    ft.Icon(ft.Icons.ROUTE, color=PRIMARIO, size=22),
                    self.titulo_resultado,
                    self.caja_estado,
                ],
                spacing=10,
                wrap=True,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            self.metricas,
            self.titulo_ruta,
            self.ruta,
            self.nota_resultado,
            ft.Row([self.boton_aceptar, self.boton_rechazar], spacing=10),
        )
        return self.panel_resultado

    def _tarjeta_texto(self) -> ft.Container:
        self.texto_escrito = ft.Row(wrap=True, spacing=8, run_spacing=8)
        return tarjeta(
            ft.Row(
                [
                    titulo_seccion(ft.Icons.NOTES, "Texto escrito"),
                    ft.TextButton(
                        content="Limpiar",
                        icon=ft.Icons.DELETE_OUTLINE,
                        on_click=lambda e: self._tecla(self.controlador.limpiar_texto),
                    ),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
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

    def _al_generar(self, e: ft.Event | None) -> None:
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

    def _al_senalar(self, letra: str, dentro) -> None:
        if dentro in (True, "true"):
            self.tecla_senalada = letra
        elif self.tecla_senalada == letra:
            self.tecla_senalada = None

        self._dibujar_teclado(self.controlador.vista())
        self.page.update()

    # Dibujo

    def dibujar(self) -> None:
        vista = self.controlador.vista()

        self.selector.value = vista.clave_teclado
        self.etiqueta_teclado.value = vista.teclado.nombre
        if vista.semilla is not None:
            self.campo_semilla.value = str(vista.semilla)
            self.texto_teclado.value = (
                "Escribe la misma semilla para repetir esta distribución. "
                "Pasa el cursor sobre una tecla para ver sus vecinas."
            )
        else:
            self.texto_teclado.value = "Pasa el cursor sobre una tecla para ver sus vecinas."

        self._dibujar_teclado(vista)

        self.campo.value = vista.palabra
        self.progreso.visible = vista.fase == "buscando"

        icono, color, fondo = ESTILO_AVISO[vista.tipo_aviso]
        self.icono_aviso.icon = icono
        self.icono_aviso.color = color
        self.aviso.value = vista.aviso
        self.aviso.color = color
        self.caja_aviso.bgcolor = fondo
        self.caja_aviso.border = ft.Border.only(left=ft.BorderSide(4, color))

        self.texto_escrito.controls = [ficha_palabra(p) for p in vista.texto] or [
            ft.Text("Aún no hay palabras.", color=TEXTO_SECUNDARIO, italic=True)
        ]

        self._dibujar_resultado(vista)
        self.page.update()

    def _dibujar_teclado(self, vista: Vista) -> None:
        teclado = vista.teclado
        posiciones = teclado.posiciones
        ancho = max(x for x, _ in posiciones.values()) + 1
        alto = max(y for _, y in posiciones.values()) + 1
        senalada = self.tecla_senalada
        cercanas = set(vecinas(teclado, senalada)) if senalada else set()

        teclas = []
        for letra in sorted(posiciones):
            x, y = posiciones[letra]

            if letra == senalada:
                fondo, borde, color = PRIMARIO, PRIMARIO, SUPERFICIE
            elif letra in vista.teclas_resaltadas:
                fondo, borde, color = RESALTE, RESALTE_BORDE, ft.Colors.BLUE_GREY_900
            elif letra in cercanas:
                fondo, borde, color = PRIMARIO_SUAVE, BORDE_TECLA, PRIMARIO
            else:
                fondo, borde, color = SUPERFICIE, BORDE_TECLA, ft.Colors.BLUE_GREY_900

            teclas.append(
                ft.Container(
                    left=x * PASO,
                    top=y * PASO,
                    width=TAM_TECLA,
                    height=TAM_TECLA,
                    border_radius=8,
                    alignment=ft.Alignment.CENTER,
                    bgcolor=fondo,
                    border=ft.Border.all(1, borde),
                    shadow=ft.BoxShadow(
                        blur_radius=0,
                        color=ft.Colors.with_opacity(0.18, BORDE_TECLA),
                        offset=ft.Offset(0, 2),
                    ),
                    tooltip="Vecinas: " + ", ".join(vecinas(teclado, letra)),
                    content=ft.Text(letra.upper(), size=16, weight=ft.FontWeight.W_600, color=color),
                    on_click=lambda e, l=letra: self._pulsar_letra(l),
                    on_hover=lambda e, l=letra: self._al_senalar(l, e.data),
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

        tiempo = f"{vista.segundos:.3f} s" if vista.segundos is not None else "-"
        expandidos = metrica(
            "Estados expandidos",
            f"{resultado.expandidos:,}",
            "Nodos que A* sacó de la frontera para generar sus sucesores.",
        )
        frontera = metrica(
            "Frontera máxima",
            f"{resultado.frontera_maxima:,}",
            "Tamaño más grande que alcanzó la cola de prioridad.",
        )
        duracion = metrica("Tiempo", tiempo, "Tiempo de la búsqueda en este equipo.")

        if vista.fase == "sugerida":
            self.titulo_resultado.value = f"{resultado.original}  ->  {resultado.sugerencia}"
            self.etiqueta_estado.value = "Corrección de costo mínimo"
            self.etiqueta_estado.color = EXITO
            self.caja_estado.bgcolor = ft.Colors.GREEN_50
            costo = metrica(
                "Costo mínimo g(meta)",
                str(resultado.costo),
                "Suma de los costos de las operaciones de la ruta.",
            )
            self.titulo_ruta.visible = True
            self.ruta.controls = cadena_de_ruta(resultado.ruta)
            self.nota_resultado.value = f"Teclado usado: {vista.teclado.nombre}."
            self.boton_aceptar.visible = True
            self.boton_rechazar.content = "Rechazar"
        else:
            self.titulo_resultado.value = resultado.original
            self.etiqueta_estado.value = "Búsqueda incompleta"
            self.etiqueta_estado.color = ERROR
            self.caja_estado.bgcolor = ft.Colors.RED_50
            costo = metrica(
                "Costo mínimo",
                "sin garantía",
                "El presupuesto se agotó antes de confirmar la meta óptima.",
            )
            self.titulo_ruta.visible = False
            self.ruta.controls = []
            self.nota_resultado.value = (
                "No se muestra una corrección porque no hay optimalidad "
                f"garantizada con el presupuesto actual. Teclado usado: {vista.teclado.nombre}."
            )
            self.boton_aceptar.visible = False
            self.boton_rechazar.content = "Conservar original"

        self.metricas.controls = [costo, expandidos, frontera, duracion]


def main(page: ft.Page) -> None:
    Aplicacion(page)


def ejecutar() -> None:
    ft.run(main)


if __name__ == "__main__":
    ejecutar()
