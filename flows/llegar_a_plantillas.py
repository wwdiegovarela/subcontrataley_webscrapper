"""
Tronco común: login → home → pantalla 'Cargar plantillas'.

Desde ahí cada flujo específico (tipo de plantilla / documento)
sigue con sus propios clicks en flows/<nombre>.py.
"""

from __future__ import annotations

import logging
import time

from selenium.webdriver.common.keys import Keys

from browser import click_si_existe, click_xpath, escribir_xpath, screenshot
from config import require_credentials
from xpaths import LOGIN_URL, xp

logger = logging.getLogger(__name__)


def cerrar_modales_post_login(driver, wait) -> None:
    """
    Intento rápido de cerrar el aviso post-login; no bloquea el flujo.
    Si no hay Cancelar en ~1s, Escape y se sigue con la navegación.
    """
    # Intento corto (no esperar 10+ s)
    if click_si_existe(driver, wait, xp("post_login.btn_cancelar"), timeout=1):
        logger.info("Modal cerrado con Cancelar")
        time.sleep(0.3)
        return

    if click_si_existe(driver, wait, xp("post_login.boton"), timeout=0.5):
        logger.info("Modal cerrado con post_login.boton")
        time.sleep(0.3)
        return

    try:
        driver.switch_to.active_element.send_keys(Keys.ESCAPE)
    except Exception:
        from selenium.webdriver.common.action_chains import ActionChains

        ActionChains(driver).send_keys(Keys.ESCAPE).perform()
    logger.info("Post-login: Escape enviado; continúo al siguiente paso")
    time.sleep(0.3)


def hacer_login(driver, wait) -> None:
    """Autenticación + cierre rápido del modal post-login."""
    user, password = require_credentials()

    logger.info("Abriendo %s", LOGIN_URL)
    driver.get(LOGIN_URL)

    escribir_xpath(driver, wait, xp("login.usuario"), user)
    escribir_xpath(driver, wait, xp("login.password"), password)
    click_xpath(driver, wait, xp("login.boton_iniciar"))

    time.sleep(2)
    logger.info("URL post-login: %s", driver.current_url)
    screenshot(driver, "post_login.png")

    cerrar_modales_post_login(driver, wait)


def navegar_a_cargar_plantillas(driver, wait) -> None:
    """Navegación desde home hasta el punto de derivación (Cargar plantillas)."""
    logger.info("Nav paso 1")
    click_xpath(driver, wait, xp("nav.paso_1"))
    time.sleep(1)
    screenshot(driver, "nav_paso_1.png")

    logger.info("Nav paso 2")
    click_xpath(driver, wait, xp("nav.paso_2"))
    time.sleep(1)
    screenshot(driver, "nav_paso_2.png")

    logger.info("Entrar a Cargar plantillas")
    click_xpath(driver, wait, xp("nav.cargar_plantillas"))
    time.sleep(1)
    screenshot(driver, "nav_cargar_plantillas.png")


def llegar_a_cargar_plantillas(driver, wait) -> None:
    """
    Camino general completo. Punto de rama para flujos específicos.

    Uso típico::

        llegar_a_cargar_plantillas(driver, wait)
        # aquí: flujo_liquidaciones(driver, wait)  o el que corresponda
    """
    hacer_login(driver, wait)
    navegar_a_cargar_plantillas(driver, wait)
    logger.info("En Cargar plantillas — listo para derivar a un flujo específico")
