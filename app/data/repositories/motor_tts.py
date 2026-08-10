"""Implementación concreta del motor TTS sobre el SDK de Supertonic.

Satisface el contrato ``MotorTTS`` de ``domain/repositories``. Todo
dependencia externa (supertonic, numpy) queda confinada en esta capa.
"""

import logging
from typing import Optional

import numpy as np
from supertonic import TTS

from data.config import configurar_entorno
from domain.repositories.motor_tts import DEFAULT_LANG, DEFAULT_VOICE

log = logging.getLogger("lector")


class MotorSupertonic:
    """Wrapper alrededor de ``supertonic.TTS`` con inicialización lazy.

    En lugar de usar una variable global mutable, encapsula el engine y
    su estilo, y solo inicializa cuando se necesita realmente.
    """

    def __init__(self, voz: str = DEFAULT_VOICE) -> None:
        """Args:
            voz: Identificador de la voz a usar (ej: 'M1', 'F1').
        """
        configurar_entorno()
        self._voz = voz
        self._engine: Optional[TTS] = None
        self._style = None

    def _asegurar_inicializado(self) -> None:
        """Inicializa el engine TTS si es la primera vez que se usa."""
        if self._engine is not None:
            return
        log.info("Inicializando motor Supertonic (voz=%s)...", self._voz)
        self._engine = TTS(auto_download=True)

        # Validar que la voz pedida existe
        try:
            self._style = self._engine.get_voice_style(voice_name=self._voz)
        except Exception as exc:
            raise ValueError(
                f"La voz '{self._voz}' no está disponible. "
                f"Verificá las voces instaladas con engine.list_voices()."
            ) from exc

        log.info("Motor listo con voz '%s'.", self._voz)

    @property
    def engine(self) -> TTS:
        """Acceso al engine subyacente (inicialización lazy)."""
        self._asegurar_inicializado()
        assert self._engine is not None
        return self._engine

    @property
    def style(self):
        """Estilo de voz asociado a la voz seleccionada."""
        self._asegurar_inicializado()
        return self._style

    def sintetizar(
        self,
        texto: str,
        *,
        steps: int,
        speed: float,
        lang: str = DEFAULT_LANG,
    ) -> np.ndarray:
        """Convierte texto a audio (ver contrato ``MotorTTS``).

        Args:
            texto: Texto a sintetizar.
            steps: Pasos de inferencia (más = mejor calidad).
            speed: Velocidad de habla.
            lang: Idioma de la voz (código de ``LANGUAGES_VOZ``).
        """
        try:
            wav, _ = self.engine.synthesize(
                texto,
                voice_style=self.style,
                lang=lang,
                total_steps=steps,
                speed=speed,
            )
        except Exception as exc:
            log.error("Error al sintetizar texto (%.60s...): %s", texto, exc)
            raise RuntimeError(f"Error en motor TTS al sintetizar fragmento: {exc}") from exc

        if wav.size == 0:
            log.warning("Fragmento silencioso (0 muestras). Se omite.")
            return np.array([], dtype=np.float32)

        return np.atleast_1d(wav.squeeze()).astype(np.float32)
