"""Flujo: Liquidaciones de Sueldo."""

from __future__ import annotations

import logging
import time
from pathlib import Path

from browser import (
    click_xpath,
    click_y_esperar_descarga,
    screenshot,
    esperar_select_cargado,
    seleccionar_periodo_mes_anterior,
    seleccionar_por_texto,
    subir_archivo,
    subir_archivos,
)
from config import DOWNLOAD_DIR
from flows.llegar_a_plantillas import llegar_a_cargar_plantillas
from flows.plantilla_schema import GLOB_PLANTILLA
from gcs_docs import descargar_docs, periodo_gcs_texto
from rellenar_plantilla import rellenar_plantilla_liquidaciones
from xpaths import xp

logger = logging.getLogger(__name__)

NOMBRE = "Liquidaciones de Sueldo"
TIPO_PLANTILLA = "Liquidaciones de Sueldo"


def ejecutar(driver, wait) -> Path:
    llegar_a_cargar_plantillas(driver, wait)

    logger.info("Eligiendo tipo: %s", TIPO_PLANTILLA)
    seleccionar_por_texto(
        driver, wait, xp("liquidaciones.select_tipo"), TIPO_PLANTILLA
    )

    logger.info("Esperando carga del select de periodo…")
    esperar_select_cargado(
        driver, wait, xp("liquidaciones.select_periodo"), min_opciones=1
    )

    logger.info("Eligiendo periodo (mes anterior a la ejecución)")
    periodo_ui = seleccionar_periodo_mes_anterior(
        driver, wait, xp("liquidaciones.select_periodo")
    )
    time.sleep(1)
    screenshot(driver, "liquidaciones_tipo_y_periodo.png")

    logger.info("Descargando plantilla Excel (#cmsd_btn_descargar_plantilla)")
    plantilla = click_y_esperar_descarga(
        driver,
        wait,
        xp("liquidaciones.btn_descargar_plantilla"),
        glob_pat=GLOB_PLANTILLA,
    )
    screenshot(driver, "liquidaciones_despues_descarga.png")

    periodo_gcs = periodo_gcs_texto()
    staging = DOWNLOAD_DIR / "staging_liquidaciones" / periodo_gcs.replace(" ", "_")
    logger.info(
        "Rellenando plantilla desde GCS (UI='%s', GCS='%s')",
        periodo_ui,
        periodo_gcs,
    )
    resultado = rellenar_plantilla_liquidaciones(
        plantilla,
        periodo_gcs=periodo_gcs,
        dir_transferencias_generadas=staging / "transferencias",
    )
    plantilla = resultado.plantilla
    logger.info(
        "Descargando PDFs solo de RUTs completos (%s) → %s",
        resultado.filas,
        staging,
    )
    paths_liq = descargar_docs(resultado.docs_liquidacion, staging / "liquidaciones")
    paths_tr = descargar_docs(resultado.docs_transferencia, staging / "transferencias")
    paths_tr.extend(resultado.transferencias_generadas)

    logger.info("Ir a pantalla de carga")
    click_xpath(driver, wait, xp("liquidaciones.ir_a_cargar"))
    time.sleep(2)
    screenshot(driver, "liquidaciones_pantalla_carga.png")

    logger.info("Subiendo Excel plantilla: %s", plantilla.name)
    subir_archivo(driver, wait, xp("liquidaciones.input_excel"), plantilla)
    time.sleep(1)
    click_xpath(driver, wait, xp("liquidaciones.btn_enviar_excel"))
    time.sleep(2)
    screenshot(driver, "liquidaciones_excel_enviado.png")

    logger.info("Subiendo %s liquidaciones", len(paths_liq))
    subir_archivos(
        driver, wait, xp("liquidaciones.zona_upload_liquidaciones"), paths_liq
    )
    time.sleep(2)
    screenshot(driver, "liquidaciones_pdfs_liq.png")

    logger.info("Subiendo %s transferencias", len(paths_tr))
    subir_archivos(
        driver, wait, xp("liquidaciones.zona_upload_transferencias"), paths_tr
    )
    time.sleep(2)
    screenshot(driver, "liquidaciones_pdfs_tr.png")

    logger.info("Confirmando carga")
    click_xpath(driver, wait, xp("liquidaciones.btn_confirmar_carga"))
    time.sleep(2)
    screenshot(driver, "liquidaciones_despues_confirmar.png")

    logger.info("Click post-confirmar")
    click_xpath(driver, wait, xp("liquidaciones.btn_post_confirmar"))
    time.sleep(2)
    screenshot(driver, "liquidaciones_despues_post_confirmar.png")

    logger.info(
        "%s: carga enviada | excel=%s | keep=%s | liq=%s | tr=%s | "
        "liquido0=%s | eliminados=%s",
        NOMBRE,
        plantilla.name,
        resultado.filas,
        len(paths_liq),
        len(paths_tr),
        resultado.liquido_cero,
        resultado.eliminadas,
    )
    return plantilla
