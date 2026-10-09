"""Helpers compartidos para flujos de carga de plantilla."""

from __future__ import annotations

import logging
import time

from browser import click_xpath, screenshot, xpk
from flows.llegar_a_plantillas import llegar_a_cargar_plantillas
from xpaths import xpath_pendiente

logger = logging.getLogger(__name__)


def ejecutar_hasta_plantilla(
    driver,
    wait,
    *,
    nombre: str,
    plantilla_key: str,
    pausa_si_pendiente: float = 120,
) -> bool:
    """
    Tronco común + click en la plantilla de esta rama.

    Returns:
        True si el click de plantilla se ejecutó.
        False si el XPath aún está pendiente (deja el browser para capturar).
    """
    llegar_a_cargar_plantillas(driver, wait)

    if xpath_pendiente(plantilla_key):
        logger.warning(
            "Rama '%s': falta capturar XPath '%s'.\n"
            "Estás en Cargar plantillas — inspecciona el click de '%s' "
            "y pégalo en el chat.",
            nombre,
            plantilla_key,
            nombre,
        )
        screenshot(driver, f"pendiente_{plantilla_key.replace('.', '_')}.png")
        time.sleep(pausa_si_pendiente)
        return False

    logger.info("Seleccionando plantilla: %s", nombre)
    click_xpath(driver, wait, xpk(driver, plantilla_key))
    time.sleep(1)
    screenshot(driver, f"plantilla_{plantilla_key.replace('.', '_')}.png")
    return True
