"""Aplicación de escritorio en Flet para el autocorrector con A*.

Ejecutar desde la raíz del repositorio:

    python -m autocorrector.interfaz

La ruta se dibuja como una cadena de nodos (inicio, estados intermedios y
meta) unidos por aristas con su operación y costo, al estilo de los
visualizadores de búsqueda en grafos. Solo se muestran datos que devuelve
el núcleo; no se reconstruye ni se inventa el recorrido.
"""

import asyncio

import flet as ft
import flet.canvas as cv

from autocorrector.arbol import Nodo, pasos, posiciones, seleccionar_nodos
from autocorrector.astar import Expansion, Paso, Resultado
from autocorrector.controlador import (
    CLAVE_ALEATORIA,
    OPCIONES_NIVELES,
    Controlador,
    Vista,
    posiciones_cambiadas,
    texto_cambios,
)
from autocorrector.diccionario import cargar_diccionario, probabilidades
from autocorrector.teclados import Distribucion, cargar_distribuciones

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
AVISO = ft.Colors.AMBER_900

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
    return sorted(teclado.cercanias[letra])


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


ANCHO_BARRA = 240


def barra_frecuencia(
    palabra: str, frecuencia: float, probabilidad: float, elegida: bool
) -> ft.Row:
    """Fila con una barra proporcional a la probabilidad de uso de la palabra."""
    return ft.Row(
        [
            ft.Text(
                palabra,
                width=70,
                size=15,
                weight=ft.FontWeight.BOLD if elegida else ft.FontWeight.W_500,
                color=EXITO if elegida else PRIMARIO,
            ),
            ft.Container(
                width=max(4.0, ANCHO_BARRA * probabilidad),
                height=16,
                border_radius=4,
                bgcolor=EXITO if elegida else GRIS_BORDE,
            ),
            ft.Text(
                f"{probabilidad:.0%}  (frecuencia {frecuencia:.2f})"
                + ("  <- elegida" if elegida else ""),
                size=12,
                color=EXITO if elegida else TEXTO_SECUNDARIO,
                weight=ft.FontWeight.BOLD if elegida else ft.FontWeight.NORMAL,
            ),
        ],
        spacing=10,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )


# Grafo interactivo de la búsqueda

ANCHO_NODO = 160
ALTO_NODO = 66
COLUMNA = 240
FILA = 78
ENCABEZADO = 34  # Alto de la fila con «Nivel 1 de 3», «Nivel 2 de 3»...
MAX_EMPATES_EN_ARBOL = 4  # Con la elegida son las 5 más frecuentes.
MAX_EMPATES_EN_PANEL = 5
LIMITE_GRAFO = 7
GRIS_FONDO = ft.Colors.BLUE_GREY_50
GRIS_BORDE = ft.Colors.BLUE_GREY_200
ACCION_SIMPLE = {
    "sustitucion": "cambiar una letra",
    "insercion": "agregar una letra",
    "eliminacion": "quitar una letra",
    "intercambio": "voltear dos letras",
}


class GrafoBusqueda:
    """Árbol de búsqueda que se recorre paso a paso o como animación.

    Muestra los estados en el orden real en que A* los expandió (la traza
    de la búsqueda) y, al final, resalta el camino elegido hasta la meta.
    """

    def __init__(self, page: ft.Page) -> None:
        self.page = page
        self._resultado: Resultado | None = None
        self._total_expandidos = 0
        self._nodos: dict[str, Nodo] = {}
        self._lugar: dict[str, tuple[int, float]] = {}
        self._max_niveles: int | None = None
        self.automatico = False
        self._columnas = 1
        self._perdedoras: list[tuple[str, float]] = []
        self._probabilidad: dict[str, float] = {}
        self._frecuencia: dict[str, float] = {}
        self._pasos: list[Nodo] = []
        self._paso = 0
        self._seleccion: str | None = None
        self._reproduciendo = False
        self._generacion = 0

        self.lienzo = cv.Canvas(shapes=[])
        self.area = ft.Stack()
        self.boton_inicio = ft.IconButton(
            ft.Icons.FIRST_PAGE, tooltip="Volver al inicio", on_click=lambda e: self.ir(1)
        )
        self.boton_atras = ft.IconButton(
            ft.Icons.CHEVRON_LEFT, tooltip="Paso anterior",
            on_click=lambda e: self.ir(self._paso - 1),
        )
        self.boton_reproducir = ft.FilledButton(
            content="Reproducir", icon=ft.Icons.PLAY_ARROW, on_click=self._alternar
        )
        self.boton_adelante = ft.IconButton(
            ft.Icons.CHEVRON_RIGHT, tooltip="Paso siguiente",
            on_click=lambda e: self.ir(self._paso + 1),
        )
        self.boton_final = ft.IconButton(
            ft.Icons.LAST_PAGE, tooltip="Ver el resultado final",
            on_click=lambda e: self.ir(len(self._pasos)),
        )
        self.deslizador = ft.Slider(
            min=1, max=2, value=2, expand=True, active_color=PRIMARIO,
            on_change=lambda e: self.ir(int(e.control.value)),
        )
        self.contador = ft.Text(size=13, color=TEXTO_SECUNDARIO)
        self.explicacion = ft.Text(size=16, color=ft.Colors.BLUE_GREY_900, expand=True)
        self.caja_explicacion = ft.Container(
            padding=14,
            border_radius=8,
            bgcolor=PRIMARIO_SUAVE,
            border=ft.Border.only(left=ft.BorderSide(4, PRIMARIO)),
            content=ft.Row(
                [ft.Icon(ft.Icons.LIGHTBULB_OUTLINE, color=PRIMARIO), self.explicacion],
                spacing=10,
                vertical_alignment=ft.CrossAxisAlignment.START,
            ),
        )
        self.desplazable = ft.Column([self.area], scroll=ft.ScrollMode.AUTO, height=520)
        # Panel de la derecha: cómo avanzan los niveles hasta el límite.
        self.lateral = ft.Column(spacing=6)
        self.extra = ft.Column(spacing=8)

        self.contenedor = ft.Container(
            padding=16,
            border_radius=12,
            bgcolor=FONDO,
            border=ft.Border.all(1, BORDE),
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.Icon(ft.Icons.ACCOUNT_TREE_OUTLINED, color=PRIMARIO),
                            ft.Text("Así buscó A*", size=16, weight=ft.FontWeight.BOLD, color=PRIMARIO),
                        ],
                        spacing=8,
                    ),
                    ft.Row(
                        [
                            self.boton_inicio,
                            self.boton_atras,
                            self.boton_reproducir,
                            self.boton_adelante,
                            self.boton_final,
                            self.deslizador,
                        ],
                        spacing=4,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    self.contador,
                    ft.Row(
                        [
                            muestra(RESALTE, RESALTE_BORDE, "Revisando ahora"),
                            muestra(GRIS_FONDO, GRIS_BORDE, "Ya revisada"),
                            muestra(SUPERFICIE, PRIMARIO, "Camino elegido"),
                            muestra(ft.Colors.GREEN_50, EXITO, "Meta"),
                        ],
                        wrap=True,
                        spacing=16,
                    ),
                    ft.ResponsiveRow(
                        [
                            ft.Container(
                                ft.Row([self.desplazable], scroll=ft.ScrollMode.AUTO),
                                col={"xs": 12, "lg": 8},
                            ),
                            ft.Container(
                                ft.Column([self.lateral, self.extra], spacing=10),
                                col={"xs": 12, "lg": 4},
                            ),
                        ],
                        spacing=16,
                        run_spacing=12,
                    ),
                    self.caja_explicacion,
                ],
                spacing=10,
            ),
        )

    # Datos

    def mostrar(
        self,
        resultado: Resultado,
        traza: tuple[Expansion, ...],
        max_niveles: int | None = None,
    ) -> None:
        """Carga una búsqueda nueva; si es la misma, conserva el paso actual."""
        if resultado is self._resultado:
            return

        self.detener()
        self._resultado = resultado
        self.contenedor.visible = bool(traza)

        if not traza:
            return

        self._total_expandidos = len(traza)
        self._nodos = seleccionar_nodos(resultado, traza, LIMITE_GRAFO)
        self._lugar = posiciones(self._nodos)
        self._pasos = pasos(self._nodos)
        self._paso = len(self._pasos)
        self._seleccion = None
        self._max_niveles = max_niveles
        self._frecuencia = dict(resultado.empates)
        mostradas = resultado.empates[: 1 + MAX_EMPATES_EN_ARBOL]
        self._probabilidad = dict(
            zip((p for p, _ in mostradas), probabilidades([f for _, f in mostradas]))
        )
        # Palabras que cuestan lo mismo que la elegida y perdieron por frecuencia.
        self._perdedoras = list(resultado.empates[1:1 + MAX_EMPATES_EN_ARBOL])

        columnas = max(c for c, _ in self._lugar.values()) + 1
        filas = max(f for _, f in self._lugar.values()) + 1
        self._columnas = columnas
        filas += len(self._perdedoras)
        ancho = int((columnas - 1) * COLUMNA + ANCHO_NODO + 8)
        alto = int(ENCABEZADO + (filas - 1) * FILA + ALTO_NODO + 8)
        self.area.width = ancho
        self.area.height = alto
        self.lienzo.width = ancho
        self.lienzo.height = alto
        self.desplazable.height = min(alto, 520)
        self.deslizador.max = max(2, len(self._pasos))
        self.deslizador.divisions = max(1, len(self._pasos) - 1)
        self._dibujar()

    # Navegación

    def ir(self, paso: int) -> None:
        if not self._pasos:
            return

        self._paso = max(1, min(paso, len(self._pasos)))
        self._seleccion = None
        self._dibujar()
        self.page.update()

    def seleccionar(self, estado: str) -> None:
        self._seleccion = estado
        self._dibujar()
        self.page.update()

    def detener(self) -> None:
        self._reproduciendo = False
        self._generacion += 1
        self.boton_reproducir.content = "Reproducir"
        self.boton_reproducir.icon = ft.Icons.PLAY_ARROW

    def _alternar(self, e=None) -> None:
        if self._reproduciendo:
            self.detener()
            self.page.update()
            return

        if self._paso >= len(self._pasos):
            self._paso = 0

        self._reproduciendo = True
        self._generacion += 1
        self.boton_reproducir.content = "Pausar"
        self.boton_reproducir.icon = ft.Icons.PAUSE
        self.page.run_task(self._animar, self._generacion)

    async def _animar(self, generacion: int) -> None:
        while (
            self._reproduciendo
            and generacion == self._generacion
            and self._paso < len(self._pasos)
        ):
            self._paso += 1
            self._seleccion = None
            self._dibujar()
            self.page.update()
            await asyncio.sleep(0.9)

        if generacion == self._generacion:
            self.detener()
            self.page.update()

    # Dibujo

    def _dibujar(self) -> None:
        if not self._pasos:
            return

        paso = max(1, self._paso)
        visibles = self._pasos[:paso]
        visibles_ids = {n.estado for n in visibles}
        actual = visibles[-1]
        final = paso == len(self._pasos)
        destacado = self._seleccion or actual.estado

        lineas = []
        etiquetas = []
        for nodo in visibles:
            if nodo.padre not in visibles_ids:
                continue

            c1, f1 = self._lugar[nodo.padre]
            c2, f2 = self._lugar[nodo.estado]
            x1, y1 = c1 * COLUMNA + ANCHO_NODO, ENCABEZADO + f1 * FILA + ALTO_NODO / 2
            x2, y2 = c2 * COLUMNA, ENCABEZADO + f2 * FILA + ALTO_NODO / 2
            camino = final and nodo.tipo in ("ruta", "meta")
            lineas.append(
                cv.Line(
                    x1, y1, x2, y2,
                    paint=ft.Paint(
                        color=PRIMARIO if camino else GRIS_BORDE,
                        stroke_width=4 if camino else 2,
                    ),
                )
            )

            if camino:
                costo = nodo.g - self._nodos[nodo.padre].g
                etiquetas.append(
                    ft.Container(
                        left=(x1 + x2) / 2 - 18,
                        top=(y1 + y2) / 2 - 28,
                        padding=ft.Padding.symmetric(horizontal=6, vertical=1),
                        border_radius=8,
                        bgcolor=PRIMARIO,
                        content=ft.Text(f"+{costo}", size=12, color=SUPERFICIE, weight=ft.FontWeight.BOLD),
                    )
                )

        self.lienzo.shapes = lineas
        tarjetas = [self._tarjeta(n, n.estado == actual.estado, final, n.estado == destacado)
                    for n in visibles]
        extras = self._tarjetas_empate() if final else []
        self.area.controls = [
            self.lienzo,
            *self._encabezados(),
            *tarjetas,
            *extras,
            *etiquetas,
        ]

        self.lateral.controls = self._lateral(visibles, final)
        self.deslizador.value = paso
        limite = (
            "sin límite de cambios"
            if self._max_niveles is None
            else f"límite de {texto_cambios(self._max_niveles)}"
        )
        self.contador.value = (
            f"Paso {paso} de {len(self._pasos)}. A* revisó {self._total_expandidos:,} "
            f"palabras en total ({limite}); aquí se ven las primeras y el camino final."
        )
        self.explicacion.value = self._explicar(self._nodos[destacado], final)

    def _lateral(self, visibles: list[Nodo], final: bool) -> list[ft.Control]:
        """Los niveles de la búsqueda, uno bajo otro, hasta llegar al límite.

        Cada nivel es un cambio. Se van mostrando al mismo ritmo que el
        árbol; al final quedan las palabras del camino elegido.
        """
        limite = self._max_niveles
        ultimo = limite if limite is not None else self._columnas - 1
        info = {n.nivel: n for n in (self._resultado.niveles if self._resultado else ())}
        meta = next((n for n in self._nodos.values() if n.tipo == "meta"), None)
        columna_meta = self._lugar[meta.estado][0] if meta else None

        por_columna: dict[int, Nodo] = {}
        origen = (
            [n for n in self._nodos.values() if n.tipo in ("inicio", "ruta", "meta")]
            if final
            else visibles
        )
        for nodo in sorted(origen, key=lambda n: n.orden):
            por_columna[self._lugar[nodo.estado][0]] = nodo

        total = self._resultado.podados if self._resultado else 0
        encabezado = [
            ft.Row(
                [
                    ft.Icon(ft.Icons.STAIRS_OUTLINED, color=AVISO if limite else PRIMARIO, size=20),
                    ft.Text(
                        f"Límite: {texto_cambios(limite)}" if limite else "Sin límite de cambios",
                        size=16,
                        weight=ft.FontWeight.BOLD,
                        color=PRIMARIO,
                    ),
                ],
                spacing=8,
            ),
            ft.Text(
                (
                    f"Cada nivel es un cambio. A* no pasa del nivel {limite}: "
                    "las ramas más lejanas se cortan sin explorarse."
                    + (
                        f" Límite automático: una palabra de "
                        f"{len(self._resultado.original)} letras admite {limite}."
                        if self.automatico and self._resultado
                        else ""
                    )
                    + (f" Aquí cortó {total:,} combinaciones." if final and total else "")
                )
                if limite
                else "Cada nivel es un cambio. Sin límite, A* puede seguir tan lejos como haga falta.",
                size=12,
                color=TEXTO_SECUNDARIO,
            ),
        ]

        filas: list[ft.Control] = []

        for nivel in range(ultimo + 1):
            nodo = por_columna.get(nivel)
            es_limite = limite is not None and nivel == limite
            sobra = final and columna_meta is not None and nivel > columna_meta
            sin_meta = final and columna_meta is None and nivel > 0

            if nodo is not None:
                palabra = nodo.estado
                es_meta = final and nodo.tipo == "meta"
                color = EXITO if es_meta else PRIMARIO
                fondo = ft.Colors.GREEN_50 if es_meta else (PRIMARIO_SUAVE if nodo.tipo != "explorado" else GRIS_FONDO)
            else:
                palabra = "—" if (sobra or sin_meta) else "?"
                color = TEXTO_SECUNDARIO
                fondo = SUPERFICIE
                es_meta = False

            nombre = (
                "Lo que escribiste"
                if nivel == 0
                else f"Nivel {nivel}" + (f" de {limite}" if limite else "")
            )
            detalle: list[ft.Control] = []

            if nivel > 0 and nodo is not None and nodo.padre:
                padre = self._nodos.get(nodo.padre)
                costo = nodo.g - padre.g if padre else nodo.g
                accion = ACCION_SIMPLE.get(nodo.operacion or "", "un cambio")
                detalle.append(ft.Text(f"desde «{nodo.padre}»: {accion} (+{costo})", size=11, color=TEXTO_SECUNDARIO))

            if nivel > 0 and nivel in info and info[nivel].expandidos and (nodo is not None or final):
                dato = info[nivel]
                texto = (
                    f"de {dato.expandidos} palabras salieron {dato.generados:,} combinaciones"
                )
                if dato.podados:
                    texto += f"; el límite descartó {dato.podados:,}"
                detalle.append(ft.Text(texto, size=11, color=AVISO if dato.podados else TEXTO_SECUNDARIO))

            if es_limite:
                detalle.append(
                    ft.Text(
                        "Último nivel: solo se acepta una palabra del diccionario; "
                        "más allá no se explora.",
                        size=11,
                        weight=ft.FontWeight.BOLD,
                        color=AVISO,
                    )
                )
            elif sobra:
                detalle.append(ft.Text("No hizo falta llegar aquí.", size=11, color=TEXTO_SECUNDARIO))
            elif sin_meta and es_limite is False:
                detalle.append(ft.Text("Sin palabra válida en este nivel.", size=11, color=TEXTO_SECUNDARIO))

            if nivel > 0:
                filas.append(
                    ft.Row(
                        [ft.Icon(ft.Icons.ARROW_DOWNWARD, size=16, color=GRIS_BORDE)],
                        alignment=ft.MainAxisAlignment.CENTER,
                    )
                )

            filas.append(
                ft.Container(
                    padding=ft.Padding.symmetric(vertical=8, horizontal=12),
                    border_radius=10,
                    bgcolor=ft.Colors.AMBER_50 if es_limite and nodo is None else fondo,
                    border=ft.Border.all(
                        2 if es_limite else 1,
                        ft.Colors.AMBER_700 if es_limite else (EXITO if es_meta else BORDE),
                    ),
                    opacity=0.55 if (nodo is None and not es_limite) else 1,
                    content=ft.Column(
                        [
                            ft.Row(
                                [
                                    ft.Text(nombre, size=11, weight=ft.FontWeight.BOLD, color=AVISO if es_limite else TEXTO_SECUNDARIO),
                                    ft.Text(
                                        palabra,
                                        size=20,
                                        weight=ft.FontWeight.BOLD,
                                        color=color,
                                        font_family=FUENTE_PALABRA,
                                        font_family_fallback=FUENTES_RESPALDO,
                                    ),
                                ],
                                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                            ),
                            *detalle,
                        ],
                        spacing=2,
                    ),
                )
            )

        return [*encabezado, *filas]

    def _frase_empate(self, meta: str) -> str:
        if not self._perdedoras or meta not in self._frecuencia:
            return ""

        otras = ", ".join(
            f"«{p}» ({self._probabilidad.get(p, 0):.0%})"
            for p, _ in self._perdedoras
        )
        return (
            f" Empató en costo con {otras}, pero «{meta}» "
            f"({self._probabilidad.get(meta, 0):.0%} de probabilidad de uso entre "
            "las más frecuentes) es la más usada y por eso se eligió."
        )

    def _encabezados(self) -> list[ft.Control]:
        """Rótulo de cada columna: el nivel (cantidad de cambios) y el límite."""
        limite = self._max_niveles
        rotulos: list[ft.Control] = []

        for nivel in range(self._columnas):
            if nivel == 0:
                texto, ultimo = "Lo que escribiste", False
            else:
                ultimo = limite is not None and nivel == limite
                texto = f"Nivel {nivel}" + (f" de {limite}" if limite else "")
                texto += " · último permitido" if ultimo else ""

            rotulos.append(
                ft.Container(
                    left=nivel * COLUMNA,
                    top=0,
                    width=ANCHO_NODO,
                    height=ENCABEZADO - 8,
                    alignment=ft.Alignment.CENTER,
                    border_radius=6,
                    bgcolor=ft.Colors.AMBER_50 if ultimo else PRIMARIO_SUAVE,
                    border=ft.Border.all(1, ft.Colors.AMBER_700 if ultimo else BORDE),
                    content=ft.Text(
                        texto,
                        size=11,
                        weight=ft.FontWeight.BOLD,
                        color=AVISO if ultimo else PRIMARIO,
                    ),
                )
            )

        return rotulos

    def _tarjetas_empate(self) -> list[ft.Control]:
        """Palabras que empataron en costo con la meta y perdieron por frecuencia."""
        meta = next((n for n in self._nodos.values() if n.tipo == "meta"), None)

        if meta is None or not self._perdedoras:
            return []

        columna, fila_meta = self._lugar[meta.estado]
        base = max(f for _, f in self._lugar.values()) + 1
        tarjetas: list[ft.Control] = []

        for i, (palabra, frecuencia) in enumerate(self._perdedoras):
            tarjetas.append(
                ft.Container(
                    left=columna * COLUMNA,
                    top=ENCABEZADO + (base + i) * FILA,
                    width=ANCHO_NODO,
                    height=ALTO_NODO,
                    border_radius=12,
                    bgcolor=GRIS_FONDO,
                    border=ft.Border.all(2, GRIS_BORDE),
                    alignment=ft.Alignment.CENTER,
                    tooltip=f"Costo igual que «{meta.estado}», pero se usa menos",
                    data=f"empate:{palabra}",
                    content=ft.Column(
                        [
                            ft.Text(palabra, size=17, weight=ft.FontWeight.BOLD, color=TEXTO_SECUNDARIO),
                            ft.Text(
                                f"costo {meta.g} · prob. {self._probabilidad.get(palabra, 0):.0%} · frec. {frecuencia:.2f}",
                                size=11,
                                color=TEXTO_SECUNDARIO,
                            ),
                            ft.Text("perdió por frecuencia", size=11, color=AVISO, weight=ft.FontWeight.BOLD),
                        ],
                        spacing=0,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        alignment=ft.MainAxisAlignment.CENTER,
                    ),
                )
            )

        return tarjetas

    def _tarjeta(self, nodo: Nodo, es_actual: bool, final: bool, destacado: bool) -> ft.Container:
        if final and nodo.tipo == "meta":
            fondo, borde = ft.Colors.GREEN_50, EXITO
        elif final and nodo.tipo in ("ruta", "inicio"):
            fondo, borde = SUPERFICIE, PRIMARIO
        elif es_actual:
            fondo, borde = RESALTE, RESALTE_BORDE
        elif nodo.tipo == "inicio":
            fondo, borde = PRIMARIO_SUAVE, PRIMARIO
        else:
            fondo, borde = GRIS_FONDO, GRIS_BORDE

        columna, fila = self._lugar[nodo.estado]
        return ft.Container(
            left=columna * COLUMNA,
            top=ENCABEZADO + fila * FILA,
            width=ANCHO_NODO,
            height=ALTO_NODO,
            border_radius=12,
            bgcolor=fondo,
            border=ft.Border.all(3 if destacado else 2, ft.Colors.BLUE_GREY_900 if destacado else borde),
            alignment=ft.Alignment.CENTER,
            tooltip="Clic para ver qué pasó aquí",
            on_click=lambda e, estado=nodo.estado: self.seleccionar(estado),
            data=nodo.estado,
            content=ft.Column(
                [
                    ft.Text(nodo.estado, size=17, weight=ft.FontWeight.BOLD,
                            font_family=FUENTE_PALABRA, font_family_fallback=FUENTES_RESPALDO),
                    ft.Text(f"g {nodo.g} + h {nodo.h} = f {nodo.f}", size=11, color=TEXTO_SECUNDARIO),
                    *(
                        [
                            ft.Text(
                                f"prob. {self._probabilidad.get(nodo.estado, 1):.0%} · frec. {self._frecuencia[nodo.estado]:.2f}",
                                size=11,
                                color=EXITO,
                                weight=ft.FontWeight.BOLD,
                            )
                        ]
                        if final and nodo.tipo == "meta" and nodo.estado in self._frecuencia
                        else []
                    ),
                ],
                spacing=0,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                alignment=ft.MainAxisAlignment.CENTER,
            ),
        )

    def _explicar(self, nodo: Nodo, final: bool) -> str:
        if nodo.tipo == "inicio":
            return (
                f"A* empieza en «{nodo.estado}», lo que escribiste. Todavía no hay "
                f"cambios (g = 0) y estima que faltan al menos {nodo.h} (h = {nodo.h})."
            )

        padre = self._nodos.get(nodo.padre)
        costo = nodo.g - padre.g if padre else nodo.g
        accion = ACCION_SIMPLE.get(nodo.operacion or "", "un cambio")

        if nodo.tipo == "meta":
            return (
                f"«{nodo.estado}» es una palabra válida. Se llega desde «{nodo.padre}» al "
                f"{accion} (+{costo}). Costo total: {nodo.g}. No quedaba ninguna opción "
                "con f menor, así que es la corrección más barata."
            ) + self._frase_empate(nodo.estado)

        texto = (
            f"Paso {nodo.orden}: A* revisa «{nodo.estado}». Viene de «{nodo.padre}» al "
            f"{accion} (+{costo}). Lleva g = {nodo.g}, le faltan al menos h = {nodo.h}, "
            f"así que f = {nodo.f}."
        )
        if final and nodo.tipo == "ruta":
            texto += " Forma parte del camino elegido."
        elif nodo.tipo == "explorado":
            texto += " No llevó a una corrección más barata, así que se descartó."
        return texto


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
            ft.Container(
                padding=ft.Padding.symmetric(vertical=20, horizontal=24),
                content=ft.Column(
                    [
                        self._encabezado(),
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
        self.etiqueta_teclado = ft.Text(size=13, color=PRIMARIO, weight=ft.FontWeight.W_600)
        return tarjeta(
            ft.Row(
                [
                    ft.Container(
                        width=44,
                        height=44,
                        border_radius=10,
                        bgcolor=PRIMARIO_SUAVE,
                        alignment=ft.Alignment.CENTER,
                        content=ft.Icon(ft.Icons.SPELLCHECK, color=PRIMARIO, size=26),
                    ),
                    ft.Column(
                        [
                            ft.Text(
                                "Autocorrector con A*",
                                size=22,
                                weight=ft.FontWeight.BOLD,
                                color=PRIMARIO,
                            ),
                            ft.Text(
                                "f(n) = g(n) + h(n)   ·   el costo de cada cambio "
                                "depende de la cercanía de las teclas",
                                size=13,
                                color=TEXTO_SECUNDARIO,
                            ),
                        ],
                        spacing=2,
                        expand=True,
                    ),
                    ft.Container(
                        padding=ft.Padding.symmetric(vertical=6, horizontal=12),
                        border_radius=20,
                        bgcolor=PRIMARIO_SUAVE,
                        border=ft.Border.all(1, BORDE),
                        content=ft.Row(
                            [
                                ft.Icon(ft.Icons.KEYBOARD, color=PRIMARIO, size=16),
                                self.etiqueta_teclado,
                            ],
                            spacing=6,
                            tight=True,
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
        self.selector_niveles = ft.Dropdown(
            label="Límite de cambios",
            width=200,
            dense=True,
            options=[
                ft.DropdownOption(key="auto", text="Automático (por largo)"),
                *[
                ft.DropdownOption(
                    key="sin" if valor is None else str(valor),
                    text="Sin límite" if valor is None else texto_cambios(valor),
                )
                for valor in OPCIONES_NIVELES
                ],
            ],
            on_select=self._al_elegir_niveles,
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
                [self.selector, self.selector_niveles, self.boton_generar],
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
        self.bloque_empates = ft.Column(spacing=8)
        self.boton_comparar = ft.OutlinedButton(
            content="Comparar con búsqueda sin límite",
            icon=ft.Icons.COMPARE_ARROWS,
            on_click=lambda e: self._tecla(self.controlador.comparar_sin_limite),
        )
        self.grafo = GrafoBusqueda(self.page)
        self.bloque_limite = self.grafo.extra
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
            self.bloque_empates,
            self.grafo.contenedor,
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

    def _al_elegir_niveles(self, e: ft.Event) -> None:
        clave = e.control.value

        if clave == "auto":
            self._tecla(self.controlador.usar_limite_automatico)
            return

        valor = None if clave == "sin" else int(clave)
        self._tecla(lambda: self.controlador.cambiar_max_niveles(valor))

    def _al_generar(self, e: ft.Event | None) -> None:
        self._tecla(self.controlador.generar_aleatorio)

    def _tecla(self, accion) -> None:
        accion()
        # En Flet 1.0 focus() es asíncrono; se agenda en el ciclo de la página.
        self.page.run_task(self.campo.focus)

    def _pulsar_letra(self, letra: str) -> None:
        self._tecla(lambda: self.controlador.pulsar_tecla(letra))

    def _estilo_tecla(self, letra: str, vista: Vista):
        if letra == self.tecla_senalada:
            return PRIMARIO, PRIMARIO, SUPERFICIE
        if letra in vista.teclas_resaltadas:
            return RESALTE, RESALTE_BORDE, ft.Colors.BLUE_GREY_900
        if (
            self.tecla_senalada is not None
            and letra in vista.teclado.cercanias[self.tecla_senalada]
        ):
            return PRIMARIO_SUAVE, BORDE_TECLA, PRIMARIO
        return SUPERFICIE, BORDE_TECLA, ft.Colors.BLUE_GREY_900

    def _al_senalar(self, letra: str, dentro) -> None:
        if dentro in (True, "true"):
            self.tecla_senalada = letra
        elif self.tecla_senalada == letra:
            self.tecla_senalada = None

        vista = self.controlador.vista()
        for tecla in self.teclado.controls:
            fondo, borde, color = self._estilo_tecla(tecla.data, vista)
            tecla.bgcolor = fondo
            tecla.border = ft.Border.all(1, borde)
            tecla.content.color = color

        self.page.update()

    # Dibujo

    def dibujar(self) -> None:
        vista = self.controlador.vista()

        self.selector.value = vista.clave_teclado
        if vista.automatico:
            self.selector_niveles.value = "auto"
        else:
            self.selector_niveles.value = (
                "sin" if vista.max_niveles is None else str(vista.max_niveles)
            )
        self.etiqueta_teclado.value = vista.teclado.nombre
        if vista.semilla is not None:
            # La semilla se muestra para poder repetir la distribución,
            # por ejemplo con: python -m autocorrector.cli gstp
            # --teclado aleatorio --semilla N
            self.texto_teclado.value = (
                f"Semilla de esta distribución: {vista.semilla}. "
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

        teclas = []
        for letra in sorted(posiciones):
            x, y = posiciones[letra]

            fondo, borde, color = self._estilo_tecla(letra, vista)

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

    def _dibujar_limite(self, vista: Vista, resultado: Resultado) -> None:
        """Botón y tabla para comparar con la búsqueda sin límite.

        Lo visual del límite (niveles, ramificación y poda) lo dibuja el
        panel lateral del grafo.
        """
        if vista.max_niveles is None:
            self.bloque_limite.controls = []
            return

        self.boton_comparar.disabled = vista.comparando
        self.boton_comparar.content = (
            "Comparando..." if vista.comparando else "Comparar con búsqueda sin límite"
        )
        controles: list[ft.Control] = [self.boton_comparar]

        if vista.comparacion is not None:
            controles.append(self._tabla_comparacion(vista, resultado))

        self.bloque_limite.controls = controles

    def _tabla_comparacion(self, vista: Vista, resultado: Resultado) -> ft.Control:
        sin = vista.comparacion
        assert sin is not None

        def fila(nombre: str, r: Resultado) -> ft.Control:
            if r.estado == "incompleta":
                final = "no terminó (se agotó el presupuesto)"
            elif r.estado == "sugerida":
                final = f"sugiere «{r.sugerencia}», costo {r.costo}"
            else:
                final = "sin corrección"

            return ft.Text(
                f"{nombre}: {r.expandidos:,} estados expandidos, "
                f"frontera máxima {r.frontera_maxima:,}; {final}.",
                size=13,
                color=ft.Colors.BLUE_GREY_900,
            )

        return ft.Container(
            padding=10,
            border_radius=8,
            bgcolor=PRIMARIO_SUAVE,
            content=ft.Column(
                [
                    fila(f"Con límite de {texto_cambios(vista.max_niveles)}", resultado),
                    fila("Sin límite", sin),
                ],
                spacing=4,
            ),
        )

    def _dibujar_empates(self, resultado: Resultado) -> None:
        """Palabras de igual costo con su frecuencia; gana la más usada."""
        candidatas = resultado.empates[:MAX_EMPATES_EN_PANEL]

        if not candidatas:
            return

        if len(candidatas) == 1:
            palabra, frecuencia = candidatas[0]
            cabecera = (
                f"«{palabra}» es la única palabra a costo {resultado.costo} "
                f"(frecuencia {frecuencia:.2f}); no hubo empate."
            )
        else:
            cabecera = (
                f"{len(resultado.empates)} palabras cuestan lo mismo "
                f"({resultado.costo}). Aquí están las {len(candidatas)} más "
                "usadas con su probabilidad relativa de uso; se optó por la "
                "de mayor probabilidad."
            )

        probs = probabilidades([f for _, f in candidatas])
        filas = [
            barra_frecuencia(palabra, frecuencia, prob, palabra == resultado.sugerencia)
            for (palabra, frecuencia), prob in zip(candidatas, probs)
            if len(candidatas) > 1
        ]

        self.bloque_empates.controls = [
            ft.Container(
                padding=14,
                border_radius=10,
                bgcolor=SUPERFICIE,
                border=ft.Border.all(1, BORDE),
                content=ft.Column(
                    [
                        ft.Text("Desempate por frecuencia", size=13, weight=ft.FontWeight.BOLD, color=TEXTO_SECUNDARIO),
                        ft.Text(cabecera, size=14, color=ft.Colors.BLUE_GREY_900),
                        *filas,
                    ],
                    spacing=8,
                ),
            )
        ]

    def _dibujar_resultado(self, vista: Vista) -> None:
        resultado = vista.resultado
        visible = (
            vista.fase in ("sugerida", "incompleta", "sin_correccion")
            and resultado is not None
        )
        self.panel_resultado.visible = visible

        if not visible:
            self.grafo.detener()
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

        limite = (
            "sin límite"
            if vista.max_niveles is None
            else texto_cambios(vista.max_niveles)
        )
        self.bloque_limite.controls = []
        self.bloque_empates.controls = []

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
            self.nota_resultado.value = (
                f"Teclado usado: {vista.teclado.nombre}. "
                f"Límite de cambios: {limite}."
            )
            self._dibujar_limite(vista, resultado)
            self._dibujar_empates(resultado)
            self.boton_aceptar.visible = True
            self.boton_rechazar.content = "Rechazar"
        elif vista.fase == "sin_correccion":
            self.titulo_resultado.value = resultado.original
            self.etiqueta_estado.value = "Sin corrección cercana"
            self.etiqueta_estado.color = AVISO
            self.caja_estado.bgcolor = ft.Colors.AMBER_50
            costo = metrica(
                "Límite de cambios",
                str(vista.max_niveles),
                "Operaciones máximas que puede tener una corrección.",
            )
            self.titulo_ruta.visible = False
            self.ruta.controls = []
            self.nota_resultado.value = (
                "Ninguna palabra del diccionario queda a "
                f"{texto_cambios(vista.max_niveles)} o menos de la que escribiste. "
                f"Teclado usado: {vista.teclado.nombre}."
            )
            self._dibujar_limite(vista, resultado)
            self.boton_aceptar.visible = False
            self.boton_rechazar.content = "Conservar original"
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
        self.grafo.automatico = vista.automatico
        self.grafo.mostrar(resultado, vista.traza, vista.max_niveles)


def main(page: ft.Page) -> None:
    Aplicacion(page)


def ejecutar() -> None:
    ft.run(main)


if __name__ == "__main__":
    ejecutar()
