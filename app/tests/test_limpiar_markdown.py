"""Pruebas de la función pura ``limpiar_markdown``."""

import unittest

from domain.use_cases.limpiar_markdown import limpiar_markdown


class TestLimpiarMarkdown(unittest.TestCase):
    """Cubre los tipos de sintaxis Markdown soportados."""

    def test_quita_titulos(self) -> None:
        self.assertEqual(limpiar_markdown("# Título"), "Título")
        self.assertEqual(limpiar_markdown("## Subtítulo"), "Subtítulo")

    def test_quita_negrita_cursiva_y_codigo_inline(self) -> None:
        texto = "**negrita** _cursiva_ `codigo`"
        self.assertEqual(limpiar_markdown(texto), "negrita cursiva codigo")

    def test_quita_links_e_imagenes(self) -> None:
        self.assertEqual(limpiar_markdown("[texto](https://x.com)"), "texto")
        self.assertEqual(limpiar_markdown("![alt](img.png)"), "alt")

    def test_quita_blockquotes_y_listas(self) -> None:
        texto = "> cita\n- item1\n- item2"
        self.assertEqual(limpiar_markdown(texto), "cita\nitem1\nitem2")

    def test_quita_bloques_de_codigo(self) -> None:
        texto = "antes\n```python\nprint(1)\n```\ndespues"
        self.assertEqual(limpiar_markdown(texto), "antes\n\ndespues")

    def test_quita_bloques_tilde(self) -> None:
        texto = "antes\n~~~\ncodigo\n~~~\ndespues"
        self.assertEqual(limpiar_markdown(texto), "antes\n\ndespues")

    def test_normaliza_saltos_y_recorta(self) -> None:
        self.assertEqual(limpiar_markdown("  hola\n\n\n\nmundo  "), "hola\n\nmundo")

    def test_prosa_con_operadores_no_se_altera(self) -> None:
        """La regla de listas no debe comer operadores en medio de la prosa."""
        texto = "2 + 3 = 5\na * b = c"
        self.assertEqual(limpiar_markdown(texto), texto)

    def test_multiplicaciones_con_espacios_no_se_altera(self) -> None:
        """Varios asteriscos espaciados (operador) no deben tratarse como énfasis."""
        texto = "2 * 3 * 4 = 24"
        self.assertEqual(limpiar_markdown(texto), texto)

    def test_underscores_no_comen_snake_case(self) -> None:
        """El énfasis con '_' no debe comerse identificadores ni operadores."""
        self.assertEqual(limpiar_markdown("clave_privada_valor"), "clave_privada_valor")
        self.assertEqual(limpiar_markdown("2 __ 3 = 5"), "2 __ 3 = 5")
        self.assertEqual(limpiar_markdown("texto _cursiva_ fin"), "texto cursiva fin")

    def test_hr_guiones_espaciados(self) -> None:
        """'- - -' es una línea horizontal válida y no debe mutilarse a '- -'."""
        self.assertEqual(limpiar_markdown("- - -"), "")
        self.assertEqual(limpiar_markdown("- item"), "item")

    def test_hr_con_mas_de_tres_marcadores(self) -> None:
        """Una línea de 3+ marcadores idénticos (con o sin espacio) es un HR."""
        self.assertEqual(limpiar_markdown("----"), "")
        self.assertEqual(limpiar_markdown("****"), "")
        self.assertEqual(limpiar_markdown("- - - -"), "")
        self.assertEqual(limpiar_markdown("* * * *"), "")

    def test_operadores_asterisco_sin_espacios_no_se_altera(self) -> None:
        """'a*b*c' o '5*4*3=60' son operadores/identificadores, no énfasis."""
        texto = "a*b*c\n5*4*3=60\napp*util*main"
        self.assertEqual(limpiar_markdown(texto), texto)

    def test_negrita_pegada_a_palabra_no_se_mutila(self) -> None:
        """Un cierre de énfasis pegado a palabra no debe quedar medio comido."""
        self.assertEqual(limpiar_markdown("**a**b"), "**a**b")
        self.assertEqual(limpiar_markdown("la **mejor**opcion"), "la **mejor**opcion")
        self.assertEqual(limpiar_markdown("a**b**c"), "a**b**c")
        self.assertEqual(limpiar_markdown("***a***b"), "***a***b")
        self.assertEqual(limpiar_markdown("**Nota:***esto* es clave"), "**Nota:***esto* es clave")

    def test_comparadores_y_flechas_no_se_altera(self) -> None:
        """El '>' de blockquote anclado no debe comerse comparadores ni flechas."""
        texto = "5 > 3\na -> b"
        self.assertEqual(limpiar_markdown(texto), texto)

    def test_quita_listas_ordenadas(self) -> None:
        texto = "1. primero\n2. segundo"
        self.assertEqual(limpiar_markdown(texto), "primero\nsegundo")

    def test_hr_solo_en_linea_completa(self) -> None:
        """'---' de prosa no es una línea horizontal; 'a---b' debe sobrevivir."""
        self.assertEqual(limpiar_markdown("a---b"), "a---b")
        self.assertEqual(limpiar_markdown("x***y"), "x***y")
        self.assertEqual(limpiar_markdown("---"), "")
        self.assertEqual(limpiar_markdown("* * *"), "")

    def test_negrita_dentro_de_bloque_de_codigo_no_se_toca(self) -> None:
        """Las reglas de negrita no deben corromper el interior de un bloque ```."""
        texto = "antes\n```\n**no_negrita**\n```\ndespues"
        self.assertEqual(limpiar_markdown(texto), "antes\n\ndespues")


if __name__ == "__main__":
    unittest.main()
