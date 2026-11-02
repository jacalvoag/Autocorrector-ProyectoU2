"""Estado de la interfaz y coordinación de búsquedas con el núcleo.

No depende de Flet: la vista solo llama a estos métodos y vuelve a
dibujarse cuando el controlador avisa que algo cambió. Así el flujo
completo se puede probar sin abrir una ventana.
"""

import secrets
import threading
from collections.abc import Callable
from dataclasses import dataclass
from time import perf_counter
from typing import Literal

from autocorrector.astar import Paso, Resultado, buscar_correccion
from autocorrector.teclados import ALFABETO, Distribucion, generar_aleatoria

# Elegido midiendo palabras con uno y dos errores al azar en los tres
# teclados y uno aleatorio. Detalle en docs/revision_propuesta.md.
MAX_ESTADOS = 200_000
CLAVE_ALEATORIA = "aleatoria"
TECLADO_BASE_ALEATORIO = "qwerty"

Fase = Literal["escribiendo", "buscando", "sugerida", "incompleta"]
TipoAviso = Literal["info", "ok", "error"]


@dataclass(frozen=True)
class Busqueda:
    """Datos con los que se lanzó una búsqueda."""

    numero: int
    palabra: str
    teclado: Distribucion


@dataclass(frozen=True)
class Vista:
    """Copia del estado que la interfaz usa para dibujarse."""

    fase: Fase
    palabra: str
    clave_teclado: str
    teclado: Distribucion
    semilla: int | None
    aviso: str
    tipo_aviso: TipoAviso
    resultado: Resultado | None
    segundos: float | None
    texto: tuple[str, ...]
    teclas_resaltadas: frozenset[str]


def validar_palabra(palabra: str) -> str | None:
    """Devuelve el motivo por el que la palabra no se puede buscar."""
    if not palabra:
        return "Escribe una palabra antes de presionar espacio."

    for letra in palabra:
        if letra in ALFABETO:
            continue

        if letra in "ñÑ":
            return "La ñ no forma parte del alfabeto acordado (a-z)."

        if letra.lower() in "áéíóúü":
            return "Escribe la palabra sin tildes ni diéresis."

        if letra.isalpha() and letra.lower() in ALFABETO:
            return "Usa solo letras minúsculas."

        return f"El carácter «{letra}» no está permitido. Solo se aceptan letras a-z."

    if len(palabra) > 6:
        return f"La palabra tiene {len(palabra)} letras; el máximo es 6."

    return None


def letras_sustituidas(resultado: Resultado | None) -> frozenset[str]:
    """Letras que participan en las sustituciones de la ruta."""
    if resultado is None:
        return frozenset()

    letras: set[str] = set()

    for paso in resultado.ruta:
        if paso.operacion != "sustitucion":
            continue

        for antes, despues in zip(paso.origen, paso.destino):
            if antes != despues:
                letras.update((antes, despues))

    return frozenset(letras)


def posiciones_cambiadas(paso: Paso) -> tuple[frozenset[int], frozenset[int]]:
    """Índices que cambian en el origen y en el destino de un paso.

    Sirve para resaltar en la interfaz qué letra se sustituyó, insertó,
    eliminó o intercambió.
    """
    origen, destino = paso.origen, paso.destino

    if len(origen) == len(destino):
        distintos = frozenset(
            i for i, (a, b) in enumerate(zip(origen, destino)) if a != b
        )
        return distintos, distintos

    corto, largo = sorted((origen, destino), key=len)
    i = next(
        (i for i, (a, b) in enumerate(zip(corto, largo)) if a != b),
        len(corto),
    )

    if len(destino) > len(origen):
        return frozenset(), frozenset({i})

    return frozenset({i}), frozenset()


class Controlador:
    def __init__(
        self,
        teclados: dict[str, Distribucion],
        diccionario: frozenset[str],
        ejecutar: Callable[[Callable[[], None]], None],
        al_cambiar: Callable[[], None] = lambda: None,
        *,
        max_estados: int | None = MAX_ESTADOS,
        buscar: Callable[..., Resultado] = buscar_correccion,
    ) -> None:
        if not teclados:
            raise ValueError("Se necesita al menos una distribución.")

        if CLAVE_ALEATORIA in teclados:
            raise ValueError(
                f"«{CLAVE_ALEATORIA}» está reservado para el teclado generado."
            )

        self.teclados = dict(teclados)
        self.diccionario = diccionario
        self._ejecutar = ejecutar
        self._al_cambiar = al_cambiar
        self._max_estados = max_estados
        self._buscar = buscar
        self._candado = threading.RLock()

        self._clave = (
            TECLADO_BASE_ALEATORIO
            if TECLADO_BASE_ALEATORIO in self.teclados
            else next(iter(self.teclados))
        )
        self._teclado = self.teclados[self._clave]
        self._semilla: int | None = None

        self._fase: Fase = "escribiendo"
        self._palabra = ""
        self._aviso = "Escribe una palabra y presiona espacio."
        self._tipo_aviso: TipoAviso = "info"
        self._resultado: Resultado | None = None
        self._segundos: float | None = None
        self._texto: list[str] = []
        self._busqueda_actual: Busqueda | None = None
        self._contador = 0
        self.descartadas = 0

    # Lectura

    def vista(self) -> Vista:
        with self._candado:
            return Vista(
                fase=self._fase,
                palabra=self._palabra,
                clave_teclado=self._clave,
                teclado=self._teclado,
                semilla=self._semilla,
                aviso=self._aviso,
                tipo_aviso=self._tipo_aviso,
                resultado=self._resultado,
                segundos=self._segundos,
                texto=tuple(self._texto),
                teclas_resaltadas=letras_sustituidas(self._resultado),
            )

    # Teclados

    def seleccionar_teclado(self, clave: str) -> None:
        if clave == CLAVE_ALEATORIA:
            self.generar_aleatorio()
            return

        with self._candado:
            if clave not in self.teclados:
                raise ValueError(f"Distribución desconocida: {clave}")

            self._clave = clave
            self._teclado = self.teclados[clave]
            self._semilla = None
            self._despues_de_cambiar_teclado()

        self._notificar()

    def generar_aleatorio(self, semilla: int | None = None) -> None:
        if semilla is None:
            semilla = secrets.randbelow(1_000_000)

        if semilla < 0:
            raise ValueError("La semilla debe ser un entero no negativo.")

        base = self.teclados.get(
            TECLADO_BASE_ALEATORIO, next(iter(self.teclados.values()))
        )

        with self._candado:
            self._clave = CLAVE_ALEATORIA
            self._teclado = generar_aleatoria(base, semilla)
            self._semilla = semilla
            self._despues_de_cambiar_teclado()

        self._notificar()

    def _despues_de_cambiar_teclado(self) -> None:
        if self._descartar_pendiente():
            self._avisar(
                f"Cambió el teclado a {self._teclado.nombre}. "
                "Se descartó la revisión anterior; presiona espacio "
                "para buscar con el teclado nuevo.",
                "info",
            )
        else:
            self._avisar(f"Teclado activo: {self._teclado.nombre}.", "info")

    # Entrada

    def actualizar_entrada(self, valor: str) -> None:
        """Recibe el contenido completo del campo de texto."""
        with self._candado:
            if " " in valor or "\t" in valor or "\n" in valor:
                self._procesar(valor)
            elif valor != self._palabra:
                self._palabra = valor

                if self._descartar_pendiente():
                    self._avisar(
                        "La palabra cambió; se descartó la revisión anterior.",
                        "info",
                    )

        self._notificar()

    def pulsar_tecla(self, letra: str) -> None:
        self.actualizar_entrada(self.vista().palabra + letra)

    def borrar(self) -> None:
        self.actualizar_entrada(self.vista().palabra[:-1])

    def pulsar_espacio(self) -> None:
        self.actualizar_entrada(self.vista().palabra + " ")

    def _procesar(self, valor: str) -> None:
        partes = valor.split()

        if not partes:
            self._palabra = ""
            self._descartar_pendiente()
            self._avisar("Escribe una palabra antes de presionar espacio.", "error")
            return

        palabra = partes[0]
        ignorado = " ".join(partes[1:])
        self._palabra = palabra
        self._descartar_pendiente()

        error = validar_palabra(palabra)
        nota = (
            f" Se procesa una palabra por operación; se ignoró «{ignorado}»."
            if ignorado
            else ""
        )

        if error is not None:
            self._avisar(error + nota, "error")
            return

        if palabra in self.diccionario:
            self._texto.append(palabra)
            self._palabra = ""
            self._avisar(f"«{palabra}» es válida y se conservó.{nota}", "ok")
            return

        self._contador += 1
        busqueda = Busqueda(self._contador, palabra, self._teclado)
        self._busqueda_actual = busqueda
        self._fase = "buscando"
        self._avisar(
            f"Buscando corrección para «{palabra}» con "
            f"{self._teclado.nombre}...{nota}",
            "info",
        )
        self._ejecutar(lambda: self._correr_busqueda(busqueda))

    # Búsqueda en segundo plano

    def _correr_busqueda(self, busqueda: Busqueda) -> None:
        inicio = perf_counter()

        try:
            resultado = self._buscar(
                busqueda.palabra,
                busqueda.teclado,
                self.diccionario,
                max_estados=self._max_estados,
            )
            error = None
        except Exception as excepcion:  # El hilo no debe morir en silencio.
            resultado = None
            error = excepcion

        self.recibir_resultado(busqueda, resultado, perf_counter() - inicio, error)

    def recibir_resultado(
        self,
        busqueda: Busqueda,
        resultado: Resultado | None,
        segundos: float,
        error: Exception | None = None,
    ) -> bool:
        """Aplica un resultado solo si sigue correspondiendo a la entrada."""
        with self._candado:
            vigente = (
                self._busqueda_actual is not None
                and busqueda.numero == self._busqueda_actual.numero
                and busqueda.palabra == self._palabra
                and busqueda.teclado is self._teclado
            )

            if not vigente:
                self.descartadas += 1
                return False

            self._busqueda_actual = None
            self._segundos = segundos

            if error is not None or resultado is None:
                self._fase = "escribiendo"
                self._resultado = None
                self._avisar(f"No se pudo completar la búsqueda: {error}", "error")
            elif resultado.estado == "incompleta":
                self._fase = "incompleta"
                self._resultado = resultado
                self._avisar(
                    "Se agotó el presupuesto de búsqueda "
                    f"({self._max_estados:,} estados) sin encontrar una "
                    "corrección con optimalidad garantizada.",
                    "error",
                )
            elif resultado.estado == "valida":
                self._fase = "escribiendo"
                self._resultado = None
                self._texto.append(busqueda.palabra)
                self._palabra = ""
                self._avisar(f"«{busqueda.palabra}» es válida.", "ok")
            else:
                self._fase = "sugerida"
                self._resultado = resultado
                self._avisar(
                    f"Sugerencia para «{busqueda.palabra}»: "
                    f"«{resultado.sugerencia}». ¿Aceptas el cambio?",
                    "info",
                )

        self._notificar()
        return True

    # Decisión del usuario

    def aceptar(self) -> None:
        with self._candado:
            if self._fase != "sugerida" or self._resultado is None:
                return

            original = self._resultado.original
            sugerencia = self._resultado.sugerencia
            self._texto.append(sugerencia)
            self._reiniciar_palabra()
            self._avisar(f"Se reemplazó «{original}» por «{sugerencia}».", "ok")

        self._notificar()

    def rechazar(self) -> None:
        with self._candado:
            if self._fase not in ("sugerida", "incompleta") or self._resultado is None:
                return

            original = self._resultado.original
            self._texto.append(original)
            self._reiniciar_palabra()
            self._avisar(f"Se conservó «{original}».", "info")

        self._notificar()

    def limpiar_texto(self) -> None:
        with self._candado:
            self._texto.clear()
            self._avisar("Se borró el texto escrito.", "info")

        self._notificar()

    # Auxiliares

    def _reiniciar_palabra(self) -> None:
        self._palabra = ""
        self._fase = "escribiendo"
        self._resultado = None
        self._segundos = None

    def _descartar_pendiente(self) -> bool:
        """Invalida la búsqueda o sugerencia en curso. Indica si había una."""
        habia = self._fase != "escribiendo"
        self._busqueda_actual = None
        self._fase = "escribiendo"
        self._resultado = None
        self._segundos = None
        return habia

    def _avisar(self, mensaje: str, tipo: TipoAviso) -> None:
        self._aviso = mensaje
        self._tipo_aviso = tipo

    def _notificar(self) -> None:
        self._al_cambiar()
