"""Lectura de PDFs de liquidación (TOTAL LIQUIDO)."""

from __future__ import annotations

import logging
import re
from pathlib import Path

import fitz  # PyMuPDF

logger = logging.getLogger(__name__)

# TOTAL LIQUIDO suele ir en la línea siguiente: "$617.783" o "0" / "$0"
_RE_TOTAL_LIQUIDO = re.compile(
    r"TOTAL\s+L[IÍ]QUIDO\s*[\r\n]+\s*\$?\s*([\d.\s]+)",
    re.IGNORECASE,
)
_RE_TOTAL_LIQUIDO_MISMA = re.compile(
    r"TOTAL\s+L[IÍ]QUIDO\s*:?\s*\$?\s*([\d.\s]+)",
    re.IGNORECASE,
)


def _monto_a_int(raw: str) -> int | None:
    digits = re.sub(r"[^\d]", "", raw or "")
    if digits == "":
        return None
    return int(digits)


def extraer_texto_pdf(pdf_path: Path) -> str:
    doc = fitz.open(pdf_path)
    try:
        return "\n".join(page.get_text() for page in doc)
    finally:
        doc.close()


def parse_total_liquido(pdf_path: Path) -> int | None:
    """
    Lee TOTAL LIQUIDO del PDF de liquidación.
    Retorna int (ej. 617783) o None si no se pudo parsear.
    """
    path = Path(pdf_path)
    if not path.exists():
        logger.warning("PDF no existe: %s", path)
        return None
    try:
        texto = extraer_texto_pdf(path)
    except Exception as exc:
        logger.warning("No se pudo leer PDF %s: %s", path.name, exc)
        return None

    m = _RE_TOTAL_LIQUIDO.search(texto) or _RE_TOTAL_LIQUIDO_MISMA.search(texto)
    if not m:
        logger.warning("No encontré TOTAL LIQUIDO en %s", path.name)
        return None
    monto = _monto_a_int(m.group(1))
    logger.info("TOTAL LIQUIDO %s → %s", path.name, monto)
    return monto


def liquidacion_es_cero(pdf_path: Path) -> bool:
    """True solo si se parseó TOTAL LIQUIDO y es exactamente 0."""
    monto = parse_total_liquido(pdf_path)
    return monto == 0
