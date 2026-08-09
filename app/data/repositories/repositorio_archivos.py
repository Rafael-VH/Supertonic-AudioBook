"""Implementación concreta del repositorio de archivos con pathlib.

Satisface el contrato ``RepositorioArchivos`` de ``domain/repositories``.
"""

import logging
import re
from pathlib import Path
from typing import List, Tuple

log = logging.getLogger("lector")


class RepositorioArchivosLocal:
    """Acceso a los archivos Markdown de entrada en el sistema de archivos."""

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
                "Detectados %d archivo(s): %s",
                len(archivos),
                ", ".join(p.name for p in archivos),
            )

        return archivos

    def leer_archivo(self, ruta: Path) -> str:
        """Lee el contenido UTF-8 de un archivo (ver contrato)."""
        return ruta.read_text(encoding="utf-8")

    @staticmethod
    def _natural_sort_key(path: Path) -> Tuple[object, ...]:
        """Genera clave de ordenamiento numérico-natural para un Path.

        Separa el nombre en tokens alternados de texto y número (los números
        se comparan como enteros), para que ``capitulo10.md`` siga a
        ``capitulo2.md`` y a ``capitulo.md``. El discriminador inicial separa
        los nombres que empiezan con número de los que empiezan con texto para
        que nunca se comparen ``int`` contra ``str``, y el ``path.stem`` final
        desempata de forma determinista nombres numéricamente iguales.

        Ejemplos:
            capitulo.md   → (1, ('capitulo',), 'capitulo')
            capitulo2.md  → (1, ('capitulo', 2), 'capitulo2')
            capitulo10.md → (1, ('capitulo', 10), 'capitulo10')
            3.md          → (0, (3,), '3')
        """
        tokens = tuple(
            int(parte) if parte.isdigit() else parte
            for parte in re.split(r"(\d+)", path.stem)
            if parte != ""
        )
        if not tokens:
            tokens = (path.stem,)
        empieza_con_numero = isinstance(tokens[0], int)
        return (0 if empieza_con_numero else 1, tokens, path.stem)
