"""
Entry point exploratorio: llega hasta 'Cargar plantillas' y espera.

Uso:
  python login.py

Desde ahí cada carga (liquidaciones, contratos, etc.) será un flujo aparte.
Para armar el siguiente: captura el XPath del click que abre ESA plantilla.
"""

from __future__ import annotations

import logging
import time

from browser import iniciar_navegador, screenshot
from flows import llegar_a_cargar_plantillas

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def main() -> None:
    driver, wait = iniciar_navegador(headless=False)
    try:
        llegar_a_cargar_plantillas(driver, wait)
        logger.info(
            "Tronco común OK (Cargar plantillas).\n"
            "Deriva: captura el XPath del flujo específico a cargar "
            "y dime el nombre del flujo (ej. liquidaciones).\n"
            "Navegador abierto 120s."
        )
        time.sleep(120)
    except Exception:
        screenshot(driver, "flujo_error.png")
        raise
    finally:
        driver.quit()
        logger.info("Navegador cerrado")


if __name__ == "__main__":
    main()
