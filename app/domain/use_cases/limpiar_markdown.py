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
    texto = re.sub(r"^#{1,6}\s*", "", texto, flags=re.MULTILINE)
    texto = re.sub(r"\*{1,3}(.*?)\*{1,3}", r"\1", texto)
    texto = re.sub(r"_{1,3}(.*?)_{1,3}", r"\1", texto)
    texto = re.sub(r"`{1,3}(.*?)`{1,3}", r"\1", texto)
    texto = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", texto)
    texto = re.sub(r"!\[([^\]]*)\]\([^)]+\)", r"\1", texto)
    texto = re.sub(r">\s?", "", texto, flags=re.MULTILINE)
    texto = re.sub(r"[-*+]\s", "", texto)
    texto = re.sub(r"---|\*\*\*", "", texto)
    texto = re.sub(r"~~~.*?~~~", "", texto, flags=re.DOTALL)
    texto = re.sub(r"```.*?```", "", texto, flags=re.DOTALL)
    texto = re.sub(r"\n{3,}", "\n\n", texto)
    return texto.strip()
