"""Caso de uso: sintetizar un audio de muestra para probar voz e idioma.

Genera un WAV corto con el motor y el exportador inyectados, sin pasar por
el pipeline completo de capítulos. Lo usa la GUI para que el usuario pruebe
una voz con el idioma seleccionado antes de procesar.
"""

from pathlib import Path

from domain.repositories.exportador_audio import ExportadorAudio
from domain.repositories.motor_tts import DEFAULT_LANG, DEFAULT_SPEED, DEFAULT_TTS_STEPS, MotorTTS


class SintetizarMuestra:
    """Produce un archivo WAV de muestra en la voz e idioma pedidos."""

    def __init__(self, motor: MotorTTS, exportador: ExportadorAudio) -> None:
        self._motor = motor
        self._exportador = exportador

    def generar(
        self,
        texto: str,
        *,
        lang: str = DEFAULT_LANG,
        ruta: Path,
    ) -> Path:
        """Sintetiza ``texto`` y lo escribe como WAV PCM en ``ruta``.

        Args:
            texto: Texto de ejemplo a pronunciar.
            lang: Idioma de la voz (código de ``LANGUAGES_VOZ``).
            ruta: Archivo WAV de destino (se sobrescribe).

        Returns:
            La ruta del WAV generado.
        """
        wav = self._motor.sintetizar(
            texto,
            steps=DEFAULT_TTS_STEPS,
            speed=DEFAULT_SPEED,
            lang=lang,
        )
        self._exportador.escribir_audio([wav], ruta, "wav")
        return ruta
