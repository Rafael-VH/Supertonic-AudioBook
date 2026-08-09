"""Caso de uso: procesar un capítulo Markdown y exportarlo a audio.

Orquesta el pipeline completo (leer → limpiar → segmentar → sintetizar →
exportar) dependiendo SOLO de contratos de dominio y funciones puras.
Los valores técnicos (silencio entre segmentos, margen de memoria) se
inyectan desde la raíz de composición; este módulo nunca importa ``data/``.
"""

import logging
import os
import tempfile
from pathlib import Path
from typing import Callable, List, Optional

import numpy as np

from domain.entities.capitulo import Capitulo
from domain.repositories.exportador_audio import ExportadorAudio
from domain.repositories.motor_tts import MotorTTS
from domain.repositories.repositorio_archivos import RepositorioArchivos
from domain.use_cases.limpiar_markdown import limpiar_markdown
from domain.use_cases.segmentar_texto import segmentar_texto

log = logging.getLogger("lector")


class ProcesarCapitulo:
    """Orquesta la conversión de un capítulo Markdown a audios.

    Args:
        motor: Motor de síntesis (contrato de dominio).
        archivos: Acceso a los capítulos en disco (contrato de dominio).
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
        capitulo: Capitulo,
        ruta_base: Path,
        *,
        steps: int,
        speed: float,
        formatos: List[str],
        on_progreso: Optional[Callable[[int, int], None]] = None,
        debe_detenerse: Optional[Callable[[], bool]] = None,
    ) -> None:
        """Convierte un capítulo en audios en los formatos pedidos.

        Args:
            capitulo: Capítulo de entrada (entidad de dominio).
            ruta_base: Ruta de salida sin extensión (ej: ``audio/capitulo``).
            steps: Pasos de inferencia para el TTS.
            speed: Velocidad de habla.
            formatos: Formatos de salida (lista normalizada).
            on_progreso: Callback ``(procesados, total)`` por cada segmento.
            debe_detenerse: Callback que, si devuelve ``True``, aborta la
                síntesis entre segmentos y exporta lo generado hasta ahora.
        """
        log.info("=" * 50)
        log.info("  Procesando: %s", capitulo.nombre)
        log.info("=" * 50)

        # --- Leer y limpiar ---
        log.info("Leyendo y limpiando Markdown...")
        try:
            texto_plano = limpiar_markdown(self._archivos.leer_archivo(capitulo.ruta))
        except Exception as exc:
            log.error("No se pudo leer '%s': %s", capitulo.ruta, exc)
            return

        if not texto_plano.strip():
            log.warning("El archivo está vacío después de limpiar. Se omite.")
            return

        # --- Segmentar ---
        segmentos = segmentar_texto(texto_plano)
        total = len(segmentos)
        log.info("  → %d segmento(s) para procesar.", total)

        # WAV de trabajo: es el destino final si 'wav' está pedido; si no, un
        # temporal que sirve de fuente intermedia y se borra al terminar.
        usando_wav = "wav" in formatos
        if usando_wav:
            ruta_wav_trabajo = Path(str(ruta_base) + ".wav")
        else:
            fd, tmp = tempfile.mkstemp(suffix=".wav", dir=str(ruta_base.parent))
            os.close(fd)
            ruta_wav_trabajo = Path(tmp)

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

                wav = self._motor.sintetizar(texto, steps=steps, speed=speed)
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
            if parcial_escrito:
                self._exportador.wav_append(fragmentos, ruta_wav_trabajo)
                for formato in formatos:
                    if formato == "wav" and usando_wav:
                        continue
                    self._exportador.convertir_desde_wav(
                        ruta_wav_trabajo,
                        Path(str(ruta_base) + "." + formato),
                        formato,
                    )
            else:
                for formato in formatos:
                    self._exportador.escribir_audio(
                        fragmentos,
                        Path(str(ruta_base) + "." + formato),
                        formato,
                    )
        finally:
            if not usando_wav and ruta_wav_trabajo.exists():
                ruta_wav_trabajo.unlink()

        for formato in formatos:
            ruta = Path(str(ruta_base) + "." + formato)
            duracion = self._exportador.duracion_audio(ruta)
            log.info("  + %s (%s): %.1f s", ruta.name, formato.upper(), duracion)
