"""Implementación concreta del repositorio de preferencias en JSON.

Satisface el contrato ``RepositorioPreferencias`` de ``domain/repositories``.
"""

import json
import logging
from pathlib import Path
from typing import Dict

log = logging.getLogger("lector")


class PreferenciasJSONLocal:
    """Guarda y restaura preferencias de la UI en un archivo JSON local."""

    def __init__(self, ruta: Path) -> None:
        """Args:
            ruta: Ruta al archivo de preferencias (ej: ``<base>/preferencias.json``).
        """
        self._ruta = ruta

    def cargar(self) -> Dict[str, object]:
        """Devuelve las preferencias guardadas (ver contrato)."""
        try:
            with self._ruta.open("r", encoding="utf-8") as fh:
                datos = json.load(fh)
            if isinstance(datos, dict):
                return datos
        except (OSError, ValueError):
            pass
        return {}

    def guardar(self, preferencias: Dict[str, object]) -> None:
        """Persiste las preferencias (ver contrato)."""
        try:
            self._ruta.parent.mkdir(parents=True, exist_ok=True)
            with self._ruta.open("w", encoding="utf-8") as fh:
                json.dump(preferencias, fh, ensure_ascii=False, indent=2)
        except OSError:
            log.warning("No se pudieron guardar las preferencias en %s", self._ruta)
