"""Contrato del repositorio de archivos de entrada (capa de dominio).

Abstrae el acceso al sistema de archivos: listado de archivos Markdown,
creación de carpetas y lectura de texto. La implementación concreta
(pathlib) vive en ``data/``.
"""

from pathlib import Path
from typing import List, Protocol


class RepositorioArchivos(Protocol):
    """Acceso a los archivos Markdown de entrada."""

    def crear_carpetas_si_no_existen(self, *carpetas: str) -> None:
        """Crea las carpetas indicadas si no existen.

        Args:
            *carpetas: Nombres de carpeta a crear (ej: 'archivos', 'audio').
        """
        ...

    def listar_archivos_md(self, carpeta: str = "archivos") -> List[Path]:
        """Busca archivos .md en la carpeta y los ordena numéricamente.

        Args:
            carpeta: Directorio donde buscar.

        Returns:
            Lista de objetos Path ordenados.
        """
        ...

    def leer_archivo(self, ruta: Path) -> str:
        """Lee el contenido UTF-8 de un archivo.

        Args:
            ruta: Ruta al archivo a leer.

        Returns:
            Contenido del archivo como texto.
        """
        ...
