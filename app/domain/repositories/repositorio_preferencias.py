"""Contrato del repositorio de preferencias de la UI (capa de dominio).

Abstrae la persistencia de preferencias del usuario (tema, voz, formatos,
carpetas) para que la presentación no dependa de un formato concreto.
La implementación (JSON en disco) vive en ``data/``.
"""

from typing import Dict, Protocol


class RepositorioPreferencias(Protocol):
    """Lectura y escritura de preferencias de la interfaz."""

    def cargar(self) -> Dict[str, object]:
        """Devuelve las preferencias guardadas (vacío si no hay ninguna)."""
        ...

    def guardar(self, preferencias: Dict[str, object]) -> None:
        """Persiste las preferencias dadas.

        Args:
            preferencias: Diccionario plano de valores serializables.
        """
        ...
