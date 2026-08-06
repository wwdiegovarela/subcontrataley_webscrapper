"""
Motor compartido: carga masiva con 1 archivo por RUT.

Igual que liquidaciones (descargar plantilla → rellenar → subir excel + PDFs → confirmar),
pero solo zona de documentos principales (sin transferencias).
"""

from __future__ import annotations

import logging
import time
from pathlib import Path

from browser import (
    click_xpath,
    click_y_esperar_descarga,
    esperar_select_cargado,
    screenshot,
    seleccionar_periodo_mes_anterior,
    seleccionar_por_texto,
    subir_archivo,
    subir_archivos,
)
from config import DOWNLOAD_DIR
from flows.llegar_a_plantillas import llegar_a_cargar_plantillas
from flows.pagos_config import FlujoPagoConfig
from flows.plantilla_schema import GLOB_PLANTILLA
from gcs_docs import descargar_docs, periodo_gcs_texto
from rellenar_plantilla_unico import rellenar_plantilla_un_documento
from xpaths import xp

logger = logging.getLogger(__name__)


def ejecutar_carga_un_documento(driver, wait, cfg: FlujoPagoConfig) -> Path:
    llegar_a_cargar_plantillas(driver, wait)

    logger.info("[%s] Eligiendo tipo: %s", cfg.clave, cfg.nombre_ui)
    seleccionar_por_texto(
        driver, wait, xp("liquidaciones.select_tipo"), cfg.nombre_ui
    )

    logger.info("[%s] Esperando select de periodo…", cfg.clave)
    esperar_select_cargado(
        driver, wait, xp("liquidaciones.select_periodo"), min_opciones=1
    )

    logger.info("[%s] Periodo mes anterior", cfg.clave)
    periodo_ui = seleccionar_periodo_mes_anterior(
        driver, wait, xp("liquidaciones.select_periodo")
    )
    time.sleep(1)
    screenshot(driver, f"{cfg.clave}_tipo_periodo.png")

    logger.info("[%s] Descargando plantilla", cfg.clave)
    plantilla = click_y_esperar_descarga(
        driver,
        wait,
        xp("liquidaciones.btn_descargar_plantilla"),
        glob_pat=GLOB_PLANTILLA,
    )
    screenshot(driver, f"{cfg.clave}_plantilla_descargada.png")

    periodo_gcs = periodo_gcs_texto()
    logger.info(
        "[%s] Rellenando Excel (UI='%s', GCS='%s', tipo=%s)",
        cfg.clave,
        periodo_ui,
        periodo_gcs,
        cfg.tipo_gcs,
    )
    resultado = rellenar_plantilla_un_documento(
        plantilla,
        tipo_gcs=cfg.tipo_gcs,
        layout=cfg.layout_gcs,
        periodo_gcs=periodo_gcs,
    )
    plantilla = resultado.plantilla

    staging = (
        DOWNLOAD_DIR
        / f"staging_{cfg.clave}"
        / periodo_gcs.replace(" ", "_")
    )
    logger.info("[%s] Descargando %s PDFs → %s", cfg.clave, resultado.filas, staging)
    paths = descargar_docs(resultado.docs, staging)

    logger.info("[%s] Ir a pantalla de carga", cfg.clave)
    click_xpath(driver, wait, xp("liquidaciones.ir_a_cargar"))
    time.sleep(2)
    screenshot(driver, f"{cfg.clave}_pantalla_carga.png")

    logger.info("[%s] Subiendo Excel: %s", cfg.clave, plantilla.name)
    subir_archivo(driver, wait, xp("liquidaciones.input_excel"), plantilla)
    time.sleep(1)
    click_xpath(driver, wait, xp("liquidaciones.btn_enviar_excel"))
    time.sleep(2)
    screenshot(driver, f"{cfg.clave}_excel_enviado.png")

    logger.info("[%s] Subiendo %s documentos", cfg.clave, len(paths))
    subir_archivos(
        driver, wait, xp("liquidaciones.zona_upload_liquidaciones"), paths
    )
    time.sleep(2)
    screenshot(driver, f"{cfg.clave}_pdfs.png")

    logger.info("[%s] Confirmar carga", cfg.clave)
    click_xpath(driver, wait, xp("liquidaciones.btn_confirmar_carga"))
    time.sleep(2)
    screenshot(driver, f"{cfg.clave}_confirmar.png")

    logger.info("[%s] Post-confirmar", cfg.clave)
    click_xpath(driver, wait, xp("liquidaciones.btn_post_confirmar"))
    time.sleep(2)
    screenshot(driver, f"{cfg.clave}_post_confirmar.png")

    logger.info(
        "[%s] OK | excel=%s | keep=%s | pdfs=%s | elim=%s",
        cfg.clave,
        plantilla.name,
        resultado.filas,
        len(paths),
        resultado.eliminadas,
    )
    return plantilla
