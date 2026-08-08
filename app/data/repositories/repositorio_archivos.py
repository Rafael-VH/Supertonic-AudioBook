"""Implementación concreta del repositorio de archivos con pathlib.

Satisface el contrato ``RepositorioArchivos`` de ``domain/repositories``.
"""

import logging
import re
from pathlib import Path
from typing import List, Tuple

log = logging.getLogger("lector")


class RepositorioArchivosLocal:
    """Acceso a los capítulos Markdown de entrada en el sistema de archivos."""

    def crear_carpetas_si_no_existen(self, *carpetas: str) -> None:
        """Crea las carpetas indicadas si no existen (ver contrato)."""
        for nombre in carpetas:
            Path(nombre).mkdir(exist_ok=True)
            log.info("Carpeta asegurada: %s/", nombre)

    def listar_archivos_md(self, carpeta: str = "archivos") -> List[Path]:
        """Busca archivos .md en la carpeta y los ordena numéricamente (ver contrato)."""
        ruta = Path(carpeta)
        if not ruta.exists():
            log.warning("La carpeta '%s/' no existe.", carpeta)
            return []

        archivos = sorted(
            [f for f in ruta.iterdir() if f.suffix.lower() == ".md"],
            key=self._natural_sort_key,
        )

        if not archivos:
            log.warning("No se encontraron archivos .md en '%s/'.", carpeta)
        else:
            log.info(
                "Detectados %d capítulo(s): %s",
                len(archivos),
                ", ".join(p.name for p in archivos),
            )

        return archivos

    def leer_archivo(self, ruta: Path) -> str:
        """Lee el contenido UTF-8 de un archivo (ver contrato)."""
        return ruta.read_text(encoding="utf-8")

    @staticmethod
    def _natural_sort_key(path: Path) -> Tuple[int, ...]:
        """Genera clave de ordenamiento numérico-natural para un Path.

        Extrae todos los números del nombre del archivo y los usa como clave.
        Si no encuentra números, usa el nombre completo como string.

        Ejemplos:
            capitulo2.md  → (2,)
            capitulo10.md → (10,)
            epilogo.md    → ('epilogo.md',)  ← orden alfabético
        """
        numeros = re.findall(r"\d+", path.stem)
        if numeros:
            return tuple(int(n) for n in numeros)
        return (path.stem,)  # type: ignore[return-value]
