"""Regla de negocio: formatos de salida soportados por el producto."""

from typing import List, Tuple

FORMATOS_NATIVOS: Tuple[str, ...] = ("wav", "flac", "ogg", "mp3")
"""Formatos de salida soportados de forma nativa (sin ffmpeg)."""


def normalizar_formatos(cadena: str) -> List[str]:
    """Normaliza una lista de formatos separada por comas.

    Convierte a minúsculas, elimina espacios, ignora duplicados y
    conserva el orden de aparición. Lanza ``ValueError`` si algún
    formato no está soportado.

    Args:
        cadena: Texto del argumento ``--formato`` (ej: "wav,MP3").

    Returns:
        Lista de formatos válidos y únicos.

    Raises:
        ValueError: Si hay un formato desconocido.
    """
    formatos: List[str] = []
    for token in cadena.split(","):
        formato = token.strip().lower()
        if not formato:
            continue
        if formato not in FORMATOS_NATIVOS:
            raise ValueError(
                f"Formato no soportado: '{formato}'. "
                f"Válidos: {', '.join(FORMATOS_NATIVOS)}."
            )
        if formato not in formatos:
            formatos.append(formato)
    return formatos
