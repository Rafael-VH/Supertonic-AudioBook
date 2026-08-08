"""Caso de uso puro: segmentación de texto apto para TTS.

Incluye las reglas de negocio de segmentación: límite de caracteres por
segmento y umbral de fusión de párrafos cortos.
"""

import re
from typing import List, Tuple

MAX_CHARS_PER_SEGMENT: int = 1500
"""Máximo de caracteres por fragmento de audio."""

MERGE_THRESHOLD: int = 200
"""Párrafos con menos caracteres que este valor se fusionan con el siguiente."""

_ABREVIATURAS: Tuple[str, ...] = (
    "Dr", "Dra", "Sr", "Sra", "Sta", "Sto", "etc", "i.e", "e.g", "vs",
    "Lic", "Ing", "Mtro", "Mtra", "Prof", "Gral",
)
"""Abreviaturas cuyo punto no debe interpretarse como fin de oración."""


def _dividir_en_oraciones(texto: str) -> List[str]:
    """Divide texto en oraciones respetando abreviaturas del español.

    Python ``re`` no permite lookbehind de ancho variable, así que en vez
    de un patrón con alternancia de largos distintos (que crashea con
    ``re.error``), se protegen temporalmente los puntos de las
    abreviaturas con un carácter neutro, se parte por ``. `` y se
    restauran los puntos.

    Args:
        texto: Párrafo a dividir.

    Returns:
        Lista de oraciones (sin el punto de cierre).
    """
    protegido = texto
    for abr in _ABREVIATURAS:
        protegido = protegido.replace(abr + ".", abr + "\x00")
    subfrases = re.split(r"(?<=\.)\s+", protegido)
    return [f.replace("\x00", ".") for f in subfrases]


def segmentar_texto(texto_plano: str) -> List[str]:
    """Divide texto plano en segmentos aptos para el TTS.

    Estrategia:
    1. Divide por saltos de línea (párrafos).
    2. Fusiona párrafos cortos (< MERGE_THRESHOLD) con el siguiente,
       siempre que no excedan MAX_CHARS_PER_SEGMENT.
    3. Si un segmento excede el límite, lo parte por oraciones
       (split en ". "), manejando correctamente títulos como Dr., Sr., etc.

    Args:
        texto_plano: Texto sin formato Markdown.

    Returns:
        Lista de strings, cada uno listo para sintetizar.
    """
    parrafos = [p.strip() for p in texto_plano.split("\n") if p.strip()]

    # --- 1. Fusión de párrafos cortos ---
    fusionados: List[str] = []
    buffer = ""
    for p in parrafos:
        if not buffer:
            buffer = p
        elif len(buffer) + len(p) < MAX_CHARS_PER_SEGMENT and len(p) < MERGE_THRESHOLD:
            buffer += " " + p
        else:
            fusionados.append(buffer)
            buffer = p
    if buffer:
        fusionados.append(buffer)

    # --- 2. División de párrafos largos ---
    resultado: List[str] = []
    for p in fusionados:
        if len(p) <= MAX_CHARS_PER_SEGMENT:
            resultado.append(p)
            continue

        # Split por ". " protegiendo abreviaturas españolas
        subfrases = _dividir_en_oraciones(p)
        buffer_frase = ""
        for frase in subfrases:
            if len(buffer_frase) + len(frase) + 2 <= MAX_CHARS_PER_SEGMENT:
                buffer_frase += frase + ". "
            else:
                resultado.append(buffer_frase.strip())
                buffer_frase = frase + ". "
        if buffer_frase:
            resultado.append(buffer_frase.strip())

    return resultado
