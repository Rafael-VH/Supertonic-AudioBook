"""Caso de uso: procesar un archivo Markdown y exportarlo a audio.

Orquesta el pipeline completo (leer → limpiar → segmentar → sintetizar →
exportar) dependiendo SOLO de contratos de dominio y funciones puras.
Los valores técnicos (silencio entre segmentos, margen de memoria) se
inyectan desde la raíz de composición; este módulo nunca importa ``data/``.
"""

import logging
import os
import tempfile
from pathlib import Path
from typing import Callable, List, Optional, Tuple

import numpy as np

from domain.entities.archivo import Archivo
from domain.repositories.exportador_audio import ExportadorAudio
from domain.repositories.motor_tts import DEFAULT_LANG, MotorTTS
from domain.repositories.repositorio_archivos import RepositorioArchivos
from domain.use_cases.limpiar_markdown import limpiar_markdown
from domain.use_cases.segmentar_texto import segmentar_texto

log = logging.getLogger("lector")


class ProcesarArchivo:
    """Orquesta la conversión de un archivo Markdown a audios.

    Args:
        motor: Motor de síntesis (contrato de dominio).
        archivos: Acceso a los archivos en disco (contrato de dominio).
        exportador: Escritura de audio (contrato de dominio).
        silencio_muestras: Muestras de silencio entre fragmentos.
        memoria_safe_margin_bytes: Umbral de RAM para volcado parcial.
    """

    def __init__(
        self,
        motor: MotorTTS,
        archivos: RepositorioArchivos,
        exportador: ExportadorAudio,
        *,
        silencio_muestras: int,
        memoria_safe_margin_bytes: int,
    ) -> None:
        self._motor = motor
        self._archivos = archivos
        self._exportador = exportador
        self._silencio_muestras = silencio_muestras
        self._memoria_safe_margin_bytes = memoria_safe_margin_bytes

    def procesar(
        self,
        archivo: Archivo,
        ruta_base: Path,
        *,
        steps: int,
        speed: float,
        formatos: List[str],
        lang: str = DEFAULT_LANG,
        on_progreso: Optional[Callable[[int, int], None]] = None,
        debe_detenerse: Optional[Callable[[], bool]] = None,
    ) -> None:
        """Convierte un archivo en audios en los formatos pedidos.

        Args:
            archivo: Archivo de entrada (entidad de dominio).
            ruta_base: Ruta de salida sin extensión (ej: ``audio/archivo``).
            steps: Pasos de inferencia para el TTS.
            speed: Velocidad de habla.
            formatos: Formatos de salida (lista normalizada).
            lang: Idioma de la voz (código de ``LANGUAGES_VOZ``).
            on_progreso: Callback ``(procesados, total)`` por cada segmento.
            debe_detenerse: Callback que, si devuelve ``True``, aborta la
                síntesis entre segmentos y exporta lo generado hasta ahora.

        Nota: cada salida se publica por separado y de forma atómica
        (``os.replace``), y solo después de generarla por completo. Si la
        corrida se cancela o falla durante la síntesis, el output previo de
        cada formato queda intacto. En la fase de publicación el WAV va
        último: si falla un formato no-WAV (ej: archivo abierto en otra app),
        el WAV previo no se reemplaza, aunque los formatos ya publicados sí
        quedaron actualizados.
        """
        log.info("=" * 50)
        log.info("  Procesando: %s", archivo.nombre)
        log.info("=" * 50)

        # --- Leer y limpiar ---
        log.info("Leyendo y limpiando Markdown...")
        try:
            texto_plano = limpiar_markdown(self._archivos.leer_archivo(archivo.ruta))
        except Exception as exc:
            log.error("No se pudo leer '%s': %s", archivo.ruta, exc)
            return

        if not texto_plano.strip():
            log.warning("El archivo está vacío después de limpiar. Se omite.")
            return

        # --- Segmentar ---
        segmentos = segmentar_texto(texto_plano)
        total = len(segmentos)
        log.info("  → %d segmento(s) para procesar.", total)

        # Formatos normalizados sin duplicados: si llegara repetido, el segundo
        # os.replace fallaría publicando dos veces el mismo temporal.
        formatos = list(dict.fromkeys(formatos))

        # El WAV de trabajo es SIEMPRE un temporal: nada se escribe sobre la
        # ruta final hasta que la corrida terminó con éxito. Así, si se cancela
        # o falla, el output previo queda intacto; y como wav_append NO
        # sobrescribe, un WAV viejo en la ruta final nunca se mezcla con audio
        # nuevo. Cada corrida regenera únicamente los formatos pedidos: salidas
        # previas de formatos no pedidos en esta corrida permanecen en disco.
        ruta_base.parent.mkdir(exist_ok=True)
        fd, tmp = tempfile.mkstemp(suffix=".wav", dir=str(ruta_base.parent))
        os.close(fd)
        ruta_wav_trabajo = Path(tmp)
        temporales: List[Path] = [ruta_wav_trabajo]

        # --- Sintetizar incrementalmente ---
        log.info("Generando voz sintética...")
        fragmentos: List[np.ndarray] = []
        memoria_acumulada = 0
        parcial_escrito = False
        cancelado = False

        try:
            procesados = 0
            for texto in segmentos:
                procesados += 1
                if debe_detenerse is not None and debe_detenerse():
                    cancelado = True
                    break

                wav = self._motor.sintetizar(texto, steps=steps, speed=speed, lang=lang)
                if on_progreso is not None:
                    on_progreso(procesados, total)
                if wav.size == 0:
                    continue

                fragmentos.append(wav)
                memoria_acumulada += wav.nbytes
                fragmentos.append(np.zeros(self._silencio_muestras, dtype=np.float32))
                memoria_acumulada += self._silencio_muestras * np.dtype(np.float32).itemsize

                # Si estamos acumulando mucha RAM, volcamos a disco
                if memoria_acumulada > self._memoria_safe_margin_bytes:
                    log.info("Volcando a disco por límite de memoria...")
                    self._exportador.wav_append(fragmentos, ruta_wav_trabajo)
                    fragmentos.clear()
                    memoria_acumulada = 0
                    parcial_escrito = True

            if cancelado:
                log.warning("Cancelado por el usuario. Exportando lo generado hasta ahora...")

            if not fragmentos and not parcial_escrito:
                log.error("No se generó ningún fragmento de audio.")
                return

            # --- Exportar ---
            log.info("Exportando audio...")
            # Fase 1: generar todo a archivos temporales. Así, un fallo en
            # cualquier conversión no deja ninguna salida vieja reemplazada.
            salidas: List[Tuple[Path, Path]] = []
            if parcial_escrito:
                self._exportador.wav_append(fragmentos, ruta_wav_trabajo)
                for formato in formatos:
                    if formato == "wav":
                        salidas.append((ruta_wav_trabajo, Path(str(ruta_base) + ".wav")))
                    else:
                        temporal = self._nuevo_temporal(ruta_base.parent, formato, temporales)
                        self._exportador.convertir_desde_wav(ruta_wav_trabajo, temporal, formato)
                        salidas.append((temporal, Path(str(ruta_base) + "." + formato)))
            else:
                for formato in formatos:
                    temporal = self._nuevo_temporal(ruta_base.parent, formato, temporales)
                    self._exportador.escribir_audio(fragmentos, temporal, formato)
                    salidas.append((temporal, Path(str(ruta_base) + "." + formato)))

            # Fase 2: publicar. La garantía es por archivo (cada os.replace es
            # atómico); si un formato falla aquí, los demás ya se actualizaron.
            # El WAV se publica al final: así, si un formato falla (ej: archivo
            # abierto en otra app), no queda un WAV nuevo con el resto de los
            # formatos viejos — el WAV solo se actualiza si todo lo demás pudo.
            for temporal, destino in self._orden_publicacion(salidas):
                self._publicar(temporal, destino, temporales)
        finally:
            for temporal in temporales:
                try:
                    temporal.unlink()
                except (FileNotFoundError, PermissionError):
                    pass

        for formato in formatos:
            ruta = Path(str(ruta_base) + "." + formato)
            duracion = self._exportador.duracion_audio(ruta)
            log.info("  + %s (%s): %.1f s", ruta.name, formato.upper(), duracion)

    def _publicar(self, origen: Path, destino: Path, temporales: List[Path]) -> None:
        """Publica ``origen`` como ``destino`` solo en éxito.

        ``os.replace`` es atómico: si existe un output previo en ``destino``
        queda intacto hasta este momento (y se sobrescribe recién acá).
        """
        try:
            os.replace(origen, destino)
        except PermissionError:
            log.error(
                "El archivo '%s' está en uso por otra aplicación; no se actualizó.",
                destino,
            )
            raise
        temporales.remove(origen)

    @staticmethod
    def _orden_publicacion(salidas: List[Tuple[Path, Path]]) -> List[Tuple[Path, Path]]:
        """Ordena las salidas para publicar: los no-WAV primero, el WAV al final."""
        return sorted(salidas, key=lambda par: par[1].name.lower().endswith(".wav"))

    @staticmethod
    def _nuevo_temporal(carpeta: Path, sufijo: str, temporales: List[Path]) -> Path:
        """Crea un archivo temporal de salida y lo registra para limpieza."""
        fd, tmp = tempfile.mkstemp(suffix="." + sufijo, dir=str(carpeta))
        os.close(fd)
        temporal = Path(tmp)
        temporales.append(temporal)
        return temporal
