"""Caso de uso puro: limpieza de Markdown a texto plano."""

import re


def limpiar_markdown(texto: str) -> str:
    """Elimina toda la sintaxis Markdown y devuelve texto plano legible.

    Soporta: títulos, negrita/cursiva, inline code, links, imágenes,
    blockquotes, listas, líneas horizontales, y bloques de código.

    Args:
        texto: Texto con formato Markdown.

    Returns:
        Texto plano, sin formato, con saltos de línea normalizados.
    """
    # Bloques de código ANTES que títulos/negrita/inline: el patrón `{1,3}`
    # de inline consume los backticks de apertura de un bloque ``` y lo rompe,
    # y las reglas de negrita/título corromperían contenido dentro del bloque.
    texto = re.sub(r"~~~.*?~~~", "", texto, flags=re.DOTALL)
    texto = re.sub(r"```.*?```", "", texto, flags=re.DOTALL)
    texto = re.sub(r"^#{1,6}\s*", "", texto, flags=re.MULTILINE)
    # Énfasis con asteriscos en pasadas separadas por conteo exacto (***, **, *):
    # el delimitador no puede estar adyacente a espacio, a otro asterisco ni ser
    # intraword, así los operadores "2 * 3 * 4", "a*b*c" o el "***" de prosa no
    # se confunden con énfasis.
    texto = re.sub(r"(?<![\w*])\*{3}(?![\s*])(.*?)(?<![\s*])\*{3}(?![\w*])", r"\1", texto)
    texto = re.sub(r"(?<![\w*])\*{2}(?![\s*])(.*?)(?<![\s*])\*{2}(?![\w*])", r"\1", texto)
    texto = re.sub(r"(?<![\w*])\*{1}(?![\s*])(.*?)(?<![\s*])\*{1}(?![\w*])", r"\1", texto)
    # Subrayado de énfasis con las mismas reglas: no puede estar adyacente a
    # espacio, a otro "_" ni ser intraword ("clave_privada" no es énfasis).
    texto = re.sub(r"(?<!\w)_{3}(?![\s_])(.*?)(?<![\s_])_{3}(?!\w)", r"\1", texto)
    texto = re.sub(r"(?<!\w)_{2}(?![\s_])(.*?)(?<![\s_])_{2}(?!\w)", r"\1", texto)
    texto = re.sub(r"(?<!\w)_{1}(?![\s_])(.*?)(?<![\s_])_{1}(?!\w)", r"\1", texto)
    texto = re.sub(r"`{1,3}(.*?)`{1,3}", r"\1", texto)
    # Imágenes ANTES que links: el patrón genérico de link deja el "!" residual.
    texto = re.sub(r"!\[([^\]]*)\]\([^)]+\)", r"\1", texto)
    texto = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", texto)
    # Blockquotes anclados al inicio de línea: sin ancla, "5 > 3" perdería el
    # operador de comparación en medio de la prosa.
    texto = re.sub(r"^\s*>\s?", "", texto, flags=re.MULTILINE)
    # Líneas horizontales ancladas a la línea completa: "a---b" o "x***y"
    # en medio de la prosa no son reglas horizontales. Acepta 3+ marcadores
    # con o sin espacio ("---", "----", "- - -", "- - - -"). Va ANTES de las
    # listas para que "* * *" o "- - -" no queden mutilados por la regla de
    # viñetas.
    texto = re.sub(r"^\s*(?:-{3,}|\*{3,}|(?:\*[ \t]*){3,}|(?:-[ \t]*){3,})\s*$", "", texto, flags=re.MULTILINE)
    # Listas ancladas al inicio de línea: sin el ancla, "- x + y" o "a * b"
    # perderían sus operadores en medio de la prosa.
    texto = re.sub(r"^\s*[-*+]\s+", "", texto, flags=re.MULTILINE)
    # Listas ordenadas (hasta 3 dígitos): "2024. Cifra..." es prosa con año,
    # no un item; "8.5" no matchea porque exige \s+ después del marcador.
    texto = re.sub(r"^\s*\d{1,3}[.)]\s+", "", texto, flags=re.MULTILINE)
    texto = re.sub(r"\n{3,}", "\n\n", texto)
    return texto.strip()
