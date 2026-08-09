"""Pruebas de integración del caso de uso ``ProcesarArchivo``.

Usan un motor TTS simulado y el exportador real (soundfile) para cubrir el
pipeline de síntesis incremental: flushes por memoria, sobrescritura de
salidas previas y cancelación.
"""

import os
import tempfile
import unittest
from pathlib import Path
from typing import List
from unittest.mock import patch

import numpy as np

from data.config import SAMPLE_RATE
from data.repositories.exportador_audio import ExportadorAudioSoundfile
from data.repositories.repositorio_archivos import RepositorioArchivosLocal
from domain.entities.archivo import Archivo
from domain.use_cases.procesar_archivo import ProcesarArchivo

DURACION_SEGMENTO = 0.2
SEGMENTO = np.full(int(SAMPLE_RATE * DURACION_SEGMENTO), 0.5, dtype=np.float32)


class MotorTTSStub:
    """Motor de síntesis simulado: devuelve un fragmento de audio fijo."""

    def __init__(self, silencio: bool = False) -> None:
        self._vacio = silencio

    def sintetizar(self, texto: str, *, steps: int, speed: float, lang: str = "es") -> np.ndarray:
        if self._vacio:
            return np.array([], dtype=np.float32)
        return SEGMENTO.copy()


def _escribir_markdown(carpeta: Path, nombre: str, texto: str) -> Path:
    ruta = carpeta / nombre
    ruta.write_text(texto, encoding="utf-8")
    return ruta


class TestProcesarArchivo(unittest.TestCase):
    """Cubre el pipeline completo con un motor simulado."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.base = Path(self._tmp.name)
        self.entrada = self.base / "archivos"
        self.salida = self.base / "audio"
        self.entrada.mkdir()
        self.salida.mkdir()
        self.repo = RepositorioArchivosLocal()
        self.exportador = ExportadorAudioSoundfile()

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _use_case(self, margen_memoria: int) -> ProcesarArchivo:
        return ProcesarArchivo(
            MotorTTSStub(),
            self.repo,
            self.exportador,
            silencio_muestras=0,
            memoria_safe_margin_bytes=margen_memoria,
        )

    def _duracion(self, ruta: Path) -> float:
        return self.exportador.duracion_audio(ruta)

    def test_flush_por_memoria_genera_wav_valido(self) -> None:
        """Con margen chico, el flush parcial no debe perder audio."""
        ruta = _escribir_markdown(
            self.entrada, "libro.md", ("Primer párrafo largo de contenido. " * 10) + "\n\n" + ("Segundo párrafo largo de contenido. " * 10)
        )
        archivo = Archivo(ruta)
        salida_wav = self.salida / "libro.wav"

        self._use_case(margen_memoria=1).procesar(
            archivo, self.salida / "libro", steps=5, speed=1.0, formatos=["wav"]
        )

        self.assertTrue(salida_wav.exists())
        self.assertGreater(self._duracion(salida_wav), 0.0)

    def test_volver_a_procesar_no_duplica_audio(self) -> None:
        """Re-procesar el mismo archivo debe regenerar, no concatenar."""
        ruta = _escribir_markdown(
            self.entrada, "libro.md", ("Párrafo de prueba para el test. " * 8) + "\n\n" + ("Otro párrafo de prueba para el test. " * 8)
        )
        archivo = Archivo(ruta)
        use_case = self._use_case(margen_memoria=1)
        ruta_base = self.salida / "libro"

        use_case.procesar(archivo, ruta_base, steps=5, speed=1.0, formatos=["wav"])
        primera = self._duracion(self.salida / "libro.wav")

        use_case.procesar(archivo, ruta_base, steps=5, speed=1.0, formatos=["wav"])
        segunda = self._duracion(self.salida / "libro.wav")

        self.assertAlmostEqual(segunda, primera, places=1)

    def test_flush_con_formato_no_wav_convierte_desde_temporal(self) -> None:
        """El path de flush con salida FLAC usa el WAV temporal y lo borra."""
        ruta = _escribir_markdown(
            self.entrada, "libro.md", ("Contenido extenso de prueba para forzar el volcado. " * 10)
        )
        archivo = Archivo(ruta)

        self._use_case(margen_memoria=1).procesar(
            archivo, self.salida / "libro", steps=5, speed=1.0, formatos=["flac"]
        )

        self.assertTrue((self.salida / "libro.flac").exists())
        self.assertFalse((self.salida / "libro.wav").exists())
        self.assertEqual({p.name for p in self.salida.iterdir()}, {"libro.flac"})

    def test_flush_wav_y_flac_publica_ambos(self) -> None:
        """El flush parcial con varios formatos debe publicar todos sin pisar el temp WAV."""
        ruta = _escribir_markdown(
            self.entrada, "libro.md", ("Contenido extenso para forzar el volcado. " * 10)
        )
        archivo = Archivo(ruta)

        self._use_case(margen_memoria=1).procesar(
            archivo, self.salida / "libro", steps=5, speed=1.0, formatos=["wav", "flac"]
        )

        self.assertTrue((self.salida / "libro.wav").exists())
        self.assertTrue((self.salida / "libro.flac").exists())
        self.assertGreater(self._duracion(self.salida / "libro.wav"), 0.0)
        self.assertEqual(
            {p.name for p in self.salida.iterdir()},
            {"libro.wav", "libro.flac"},
        )

    def test_publica_wav_al_final(self) -> None:
        """En la fase de publicación, el WAV se publica después de los demás formatos."""
        salidas = [
            (Path("tmp.wav"), Path("libro.WAV")),
            (Path("tmp.mp3"), Path("libro.mp3")),
            (Path("tmp.flac"), Path("libro.flac")),
        ]
        orden = ProcesarArchivo._orden_publicacion(salidas)
        self.assertEqual(
            [dest.name for _, dest in orden],
            ["libro.mp3", "libro.flac", "libro.WAV"],
        )

    def test_fallo_publicacion_no_wav_no_actualiza_wav(self) -> None:
        """Si falla publicar un formato no-WAV, el WAV previo no se publica."""
        ruta = _escribir_markdown(
            self.entrada, "libro.md", ("Contenido extenso para forzar el volcado. " * 10)
        )
        archivo = Archivo(ruta)
        use_case = self._use_case(margen_memoria=1)

        use_case.procesar(archivo, self.salida / "libro", steps=5, speed=1.0, formatos=["wav"])
        previo = (self.salida / "libro.wav").read_bytes()

        destinos: List[str] = []
        reemplazo_real = os.replace

        def _reemplazo_que_falla_en_flac(origen, destino):
            destinos.append(str(destino))
            if str(destino).lower().endswith(".flac"):
                raise PermissionError(13, "archivo en uso", str(destino))
            return reemplazo_real(origen, destino)

        with patch("os.replace", side_effect=_reemplazo_que_falla_en_flac):
            with self.assertRaises(PermissionError):
                use_case.procesar(
                    archivo, self.salida / "libro", steps=5, speed=1.0, formatos=["wav", "flac"]
                )

        self.assertEqual(
            destinos,
            [str(self.salida / "libro.flac")],
            "solo el FLAC debe intentar publicarse; el WAV queda sin tocar",
        )
        self.assertEqual((self.salida / "libro.wav").read_bytes(), previo)

    def test_archivo_vacio_no_genera_salida(self) -> None:
        ruta = _escribir_markdown(self.entrada, "vacio.md", "   \n\n  ")
        archivo = Archivo(ruta)

        self._use_case(margen_memoria=1).procesar(
            archivo, self.salida / "vacio", steps=5, speed=1.0, formatos=["wav"]
        )

        self.assertFalse((self.salida / "vacio.wav").exists())

    def test_cancelado_al_inicio_no_genera_salida(self) -> None:
        ruta = _escribir_markdown(self.entrada, "libro.md", "Contenido.")
        archivo = Archivo(ruta)

        self._use_case(margen_memoria=1).procesar(
            archivo,
            self.salida / "libro",
            steps=5,
            speed=1.0,
            formatos=["wav"],
            debe_detenerse=lambda: True,
        )

        self.assertFalse((self.salida / "libro.wav").exists())

    def test_cancelar_no_destruye_salida_previa(self) -> None:
        """Cancelar al inicio no debe borrar el output bueno de una corrida anterior."""
        ruta = _escribir_markdown(self.entrada, "libro.md", "Contenido.")
        archivo = Archivo(ruta)
        use_case = self._use_case(margen_memoria=1)

        use_case.procesar(archivo, self.salida / "libro", steps=5, speed=1.0, formatos=["wav"])
        self.assertTrue((self.salida / "libro.wav").exists())
        duracion_previa = self._duracion(self.salida / "libro.wav")

        use_case.procesar(
            archivo,
            self.salida / "libro",
            steps=5,
            speed=1.0,
            formatos=["wav"],
            debe_detenerse=lambda: True,
        )

        self.assertTrue((self.salida / "libro.wav").exists())
        self.assertAlmostEqual(self._duracion(self.salida / "libro.wav"), duracion_previa, places=1)

    def test_fallo_no_destruye_salida_previa(self) -> None:
        """Un motor que falla a mitad de corrida tampoco debe borrar el output previo."""
        ruta = _escribir_markdown(self.entrada, "libro.md", "Contenido.")
        archivo = Archivo(ruta)
        use_case = self._use_case(margen_memoria=1)
        use_case.procesar(archivo, self.salida / "libro", steps=5, speed=1.0, formatos=["wav"])
        self.assertTrue((self.salida / "libro.wav").exists())
        duracion_previa = self._duracion(self.salida / "libro.wav")

        class MotorQueFalla:
            def sintetizar(self, texto, *, steps, speed, lang="es"):
                raise RuntimeError("fallo del motor")

        use_case = ProcesarArchivo(
            MotorQueFalla(),
            self.repo,
            self.exportador,
            silencio_muestras=0,
            memoria_safe_margin_bytes=1,
        )
        with self.assertRaises(RuntimeError):
            use_case.procesar(archivo, self.salida / "libro", steps=5, speed=1.0, formatos=["wav"])

        self.assertTrue((self.salida / "libro.wav").exists())
        self.assertAlmostEqual(self._duracion(self.salida / "libro.wav"), duracion_previa, places=1)


if __name__ == "__main__":
    unittest.main()
