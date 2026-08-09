"""Pruebas de la función pura ``segmentar_texto``."""

import unittest

from domain.use_cases.segmentar_texto import MAX_CHARS_PER_SEGMENT, segmentar_texto


class TestSegmentarTexto(unittest.TestCase):
    """Cubre fusión de párrafos cortos y división por oraciones."""

    def test_respeta_parrafos_existentes(self) -> None:
        largo = "Palabra larga. " * 20  # > MERGE_THRESHOLD: no se fusiona
        resultado = segmentar_texto(f"{largo}\n\n{largo}\n\n{largo}")
        self.assertEqual(len(resultado), 3)

    def test_fusiona_parrafos_cortos(self) -> None:
        resultado = segmentar_texto("Corto.\n\nTambién corto.\n\nLargo." * 1)
        self.assertLess(len(resultado), 3)

    def test_dividir_parrafo_largo_por_oraciones(self) -> None:
        parrafo = ("Oración una. " * 120) + "Oración final."
        self.assertGreater(len(parrafo), MAX_CHARS_PER_SEGMENT)
        resultado = segmentar_texto(parrafo)
        self.assertGreater(len(resultado), 1)
        for segmento in resultado:
            self.assertLessEqual(len(segmento), MAX_CHARS_PER_SEGMENT)

    def test_no_parte_abreviaturas_espanolas(self) -> None:
        parrafo = ("El Dr. Pérez llegó a tiempo. " * 40).strip()
        resultado = segmentar_texto(parrafo)
        for segmento in resultado:
            self.assertIn("Dr.", segmento)

    def test_parrafo_corto_se_mantiene_entero(self) -> None:
        self.assertEqual(segmentar_texto("Hola mundo."), ["Hola mundo."])


if __name__ == "__main__":
    unittest.main()
