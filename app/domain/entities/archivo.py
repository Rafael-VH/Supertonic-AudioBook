"""Entidad de dominio: un archivo Markdown por convertir."""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Archivo:
    """Archivo de entrada (Markdown) listo para procesar.

    Atributos:
        ruta: Ruta al archivo .md de entrada.
    """

    ruta: Path

    @property
    def nombre(self) -> str:
        """Nombre del archivo con extensión (ej: 'archivo3.md')."""
        return self.ruta.name

    @property
    def titulo(self) -> str:
        """Nombre del archivo sin extensión (se usa para nombrar el audio)."""
        return self.ruta.stem
