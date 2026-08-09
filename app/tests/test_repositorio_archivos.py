"""Pruebas del repositorio concreto de archivos (data layer)."""

import tempfile
import unittest
from pathlib import Path

from data.repositories.repositorio_archivos import RepositorioArchivosLocal


class TestNaturalSortKey(unittest.TestCase):
    """La clave de ordenamiento debe ser homogénea y comparable."""

    def setUp(self) -> None:
        self.repo = RepositorioArchivosLocal()

    def test_mezcla_numerados_y_no_numerados_no_crashea(self) -> None:
        nombres = ["epilogo.md", "archivo10.md", "archivo2.md", "prefacio.md"]
        paths = [Path(n) for n in nombres]
        ordenado = sorted(paths, key=self.repo._natural_sort_key)
        self.assertEqual(
            [p.name for p in ordenado],
            ["archivo2.md", "archivo10.md", "epilogo.md", "prefacio.md"],
        )

    def test_orden_natural_corrige_lexicografico(self) -> None:
        paths = [Path("archivo10.md"), Path("archivo2.md")]
        ordenado = sorted(paths, key=self.repo._natural_sort_key)
        self.assertEqual([p.name for p in ordenado], ["archivo2.md", "archivo10.md"])

    def test_usa_multiples_numeros(self) -> None:
        self.assertLess(
            self.repo._natural_sort_key(Path("c1s2.md")),
            self.repo._natural_sort_key(Path("c1s10.md")),
        )

    def test_no_numerado_va_antes_que_su_numerado(self) -> None:
        """'capitulo.md' (intro) debe leerse antes que 'capitulo1.md'."""
        paths = [Path("capitulo1.md"), Path("capitulo.md"), Path("capitulo2.md")]
        ordenado = sorted(paths, key=self.repo._natural_sort_key)
        self.assertEqual(
            [p.name for p in ordenado],
            ["capitulo.md", "capitulo1.md", "capitulo2.md"],
        )

    def test_ceros_izquierda_desempatan_determinista(self) -> None:
        """Nombres numéricamente iguales ('archivo01' vs 'archivo1') se desempatan por nombre."""
        self.assertLess(
            self.repo._natural_sort_key(Path("archivo01.md")),
            self.repo._natural_sort_key(Path("archivo1.md")),
        )


class TestListarArchivosMd(unittest.TestCase):
    """Listado real en disco: orden natural y filtro por extensión."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.carpeta = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_lista_solo_md_ordenados(self) -> None:
        (self.carpeta / "nota.txt").write_text("x", encoding="utf-8")
        (self.carpeta / "archivo10.md").write_text("x", encoding="utf-8")
        (self.carpeta / "archivo2.md").write_text("x", encoding="utf-8")
        (self.carpeta / "epilogo.md").write_text("x", encoding="utf-8")

        repo = RepositorioArchivosLocal()
        resultado = repo.listar_archivos_md(str(self.carpeta))
        self.assertEqual(
            [p.name for p in resultado],
            ["archivo2.md", "archivo10.md", "epilogo.md"],
        )

    def test_carpeta_inexistente_devuelve_vacia(self) -> None:
        repo = RepositorioArchivosLocal()
        self.assertEqual(repo.listar_archivos_md("no_existe"), [])

    def test_leer_archivo_roundtrip(self) -> None:
        archivo = self.carpeta / "a.md"
        archivo.write_text("contenido\n", encoding="utf-8")
        repo = RepositorioArchivosLocal()
        self.assertEqual(repo.leer_archivo(archivo), "contenido\n")


if __name__ == "__main__":
    unittest.main()
