"""Flujo: Pagos Cajas de Compensación (1 archivo/RUT, PDF Cotizaciones)."""

from __future__ import annotations

from pathlib import Path

from flows.carga_documento_unico import ejecutar_carga_un_documento
from flows.pagos_config import PAGOS_CAJAS


def ejecutar(driver, wait) -> Path:
    return ejecutar_carga_un_documento(driver, wait, PAGOS_CAJAS)
