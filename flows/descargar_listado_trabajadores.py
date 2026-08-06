"""
Fase 1: listado de trabajadores en Subcontrataley (menú finiquitos/personal).

Patrón exploratorio (igual que el resto del scraper):
  1. Login reutilizado.
  2. Click Carga Masiva (mismo nav.paso_1 que liquidaciones/asistencias).
  3. Ejecuta en orden cada XPath de PASOS_NAV que ya esté capturado.
  4. Al llegar a uno pendiente (None), pantalla + pausa: pegás el XPath en el chat.
  5. Cuando todos los pasos (incluido export) estén listos, descarga el Excel.

Uso:
  python run_flujo.py listado_trabajadores
"""

from __future__ import annotations

import logging
import shutil
import time
from datetime import date
from pathlib import Path

from browser import click_xpath, click_y_esperar_descarga, screenshot
from config import DOWNLOAD_DIR
from flows.llegar_a_plantillas import hacer_login
from xpaths import xp, xpath_pendiente

logger = logging.getLogger(__name__)

NOMBRE = "Listado trabajadores (finiquitables)"

# Clicks DESPUÉS de Carga Masiva (nav.paso_1 ya se reutiliza).
# El ÚLTIMO dispara la descarga.
PASOS_NAV: list[str] = [
    "trabajadores.paso_1",  # Finiquitar trabajadores
    "trabajadores.paso_2",  # Descarga Plantilla Nueva
    "trabajadores.btn_exportar",
]

# Glob provisional; se ajusta al nombre real del archivo del portal.
GLOB_LISTADO = "*.xlsx"


def _staging_dir(referencia: date | None = None) -> Path:
    ref = referencia or date.today()
    slug = ref.strftime("%Y_%m_%d")
    dest = DOWNLOAD_DIR / "staging_trabajadores" / slug
    dest.mkdir(parents=True, exist_ok=True)
    return dest


def _siguientes_pendientes() -> list[str]:
    return [k for k in PASOS_NAV if xpath_pendiente(k)]


def navegar_hasta_export(driver, wait) -> str | None:
    """
    Clickea todos los pasos EXCEPTO el último (export/descarga).

    Returns:
        None si los pasos intermedios están listos.
        Key pendiente si hay que capturar un XPath.
    """
    if not PASOS_NAV:
        raise RuntimeError("PASOS_NAV vacío")

    intermedios = PASOS_NAV[:-1]
    for key in intermedios:
        if xpath_pendiente(key):
            logger.warning(
                "XPath pendiente: '%s'.\n"
                "Inspeccioná el siguiente click en Chrome DevTools y pegalo "
                "en el chat, por ejemplo:\n"
                "  flujo: listado_trabajadores\n"
                "  paso: %s\n"
                "  xpath: /html/body/...\n"
                "Si sobran pasos (menos clicks de los que planificamos), "
                "decilo y los quitamos de PASOS_NAV.",
                key,
                key,
            )
            screenshot(driver, f"pendiente_{key.replace('.', '_')}.png")
            return key

        logger.info("Click: %s", key)
        click_xpath(driver, wait, xp(key))
        time.sleep(1)
        screenshot(driver, f"{key.replace('.', '_')}.png")

    return None


def _click_carga_masiva(driver, wait) -> None:
    """Mismo primer click del menú que liquidaciones / libro asistencia / pagos."""
    logger.info("Nav Carga Masiva (nav.paso_1)")
    click_xpath(driver, wait, xp("nav.paso_1"))
    time.sleep(1)
    screenshot(driver, "trabajadores_carga_masiva.png")


def ejecutar(driver, wait, *, pausa_exploracion: float = 180, ya_logueado: bool = False) -> Path | None:
    """
    Login → Carga Masiva → nav propios → descarga si export ya tiene XPath.

    Returns:
        Path del Excel en staging, o None si aún falta capturar pasos.
    """
    if not ya_logueado:
        hacer_login(driver, wait)
        screenshot(driver, "trabajadores_post_login.png")
    _click_carga_masiva(driver, wait)
    logger.info(
        "En Carga Masiva. Pasos siguientes: %s | Pendientes: %s",
        PASOS_NAV,
        _siguientes_pendientes() or "(ninguno)",
    )

    pendiente = navegar_hasta_export(driver, wait)
    if pendiente is not None:
        logger.info(
            "Navegador abierto ~%.0fs para capturar '%s'.",
            pausa_exploracion,
            pendiente,
        )
        time.sleep(pausa_exploracion)
        return None

    key_export = PASOS_NAV[-1]
    if xpath_pendiente(key_export):
        logger.warning(
            "XPath pendiente: '%s' (botón que descarga el listado).\n"
            "  flujo: listado_trabajadores\n"
            "  paso: %s\n"
            "  xpath: /html/body/...",
            key_export,
            key_export,
        )
        screenshot(driver, f"pendiente_{key_export.replace('.', '_')}.png")
        time.sleep(pausa_exploracion)
        return None

    logger.info("Descargando listado (glob=%s)…", GLOB_LISTADO)
    plantilla = click_y_esperar_descarga(
        driver,
        wait,
        xp(key_export),
        glob_pat=GLOB_LISTADO,
        timeout=90,
    )

    staging = _staging_dir()
    dest = staging / "listado_finiquitables.xlsx"
    shutil.copy2(plantilla, dest)
    logger.info("Listado copiado a %s (origen %s)", dest, plantilla)
    return dest
