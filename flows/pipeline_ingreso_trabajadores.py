"""
Pipeline end-to-end: ingreso de trabajadores a Subcontrataley.

1) Descargar listado finiquitables (SCL)
2) Comparar vs ControlRoll (BQ + asistencia + contratos + faena ≤1 mes)
3) Descargar plantilla vacía fresca (Crear trabajadores)
4) Rellenar Excel
5) Subir → Validar → Realizar Carga Masiva → esperar fin

Uso local:
  python run_flujo.py ingreso_trabajadores_e2e
  HEADLESS=true python ingreso_trabajadores_cloudrun.py
"""

from __future__ import annotations

import logging
import shutil
import time
from datetime import date
from pathlib import Path

from browser import click_xpath, click_y_esperar_descarga, screenshot
from comparar_trabajadores import comparar, guardar_resultado
from config import DOWNLOAD_DIR
from bq_asistencia import (
    consultar_dias_trabajados,
    consultar_primera_asistencia,
    corte_ingreso_faena,
)
from bq_empleados import consultar_empleados_activos
from cr_contratos import consultar_contratos_firmados
from flows import carga_ingreso_trabajadores
from flows import descargar_listado_trabajadores as dl_listado
from leer_listado_trabajadores import leer_listado_trabajadores
from rellenar_plantilla_trabajadores import construir_filas, escribir_plantilla
from xpaths import xp

logger = logging.getLogger(__name__)

NOMBRE = "Ingreso trabajadores E2E"


def _staging_dir() -> Path:
    dest = DOWNLOAD_DIR / "staging_trabajadores" / date.today().strftime("%Y_%m_%d")
    dest.mkdir(parents=True, exist_ok=True)
    return dest


def _comparar_y_elegibles(listado: Path) -> tuple[list[str], Path]:
    """Devuelve cuerpos RUT elegibles + path elegibles_ingreso.xlsx."""
    out_dir = listado.parent
    scl = leer_listado_trabajadores(listado)
    cr = consultar_empleados_activos()
    map_cr = {e.rut_cuerpo: e for e in cr}
    map_scl = {t.rut_cuerpo: t for t in scl}
    faltan_ruts = sorted(set(map_cr) - set(map_scl))

    dias = consultar_dias_trabajados(ventana_dias=30, ruts=faltan_ruts)
    primera = consultar_primera_asistencia(ruts=faltan_ruts)
    corte = corte_ingreso_faena()
    logger.info("Corte ingreso faena: >= %s", corte.isoformat())

    contratos = consultar_contratos_firmados()
    firmados = set(contratos.keys())

    res = comparar(
        cr,
        scl,
        dias_por_rut=dias,
        firmados=firmados,
        primera_asistencia=primera,
        corte_faena=corte,
        ventana_dias=30,
        min_dias=1,
    )
    paths = guardar_resultado(res, out_dir=out_dir, listado_path=listado)
    logger.info(
        "Comparación: faltan=%s elegibles=%s faena_antigua=%s → %s",
        res.n_faltan_en_scl,
        res.n_elegibles,
        len(res.excluidos_faena_antigua),
        paths.get("elegibles"),
    )
    ruts = [e.rut_cuerpo for e in res.elegibles]
    return ruts, paths["elegibles"]


def _descargar_plantilla_vacia(driver, wait) -> Path:
    """Crear trabajadores → Descargar Nueva Plantilla → Descargar Plantilla."""
    logger.info("Descargando plantilla vacía de ingreso…")
    click_xpath(driver, wait, xp("nav.paso_1"))
    time.sleep(1)
    click_xpath(driver, wait, xp("ingreso.crear_trabajadores"))
    time.sleep(1.2)
    click_xpath(driver, wait, xp("ingreso.descargar_plantilla"))
    time.sleep(1.2)
    screenshot(driver, "ingreso_descarga_plantilla.png")
    descargado = click_y_esperar_descarga(
        driver,
        wait,
        xp("ingreso.btn_descargar_plantilla"),
        glob_pat="*.xlsx",
        timeout=120,
    )
    staging = _staging_dir()
    dest = staging / "plantilla_ingreso_vacia.xlsx"
    shutil.copy2(descargado, dest)
    logger.info("Plantilla vacía: %s (origen %s)", dest, descargado)
    return dest


def _rellenar(plantilla_vacia: Path, ruts: list[str]) -> Path:
    staging = _staging_dir()
    out = staging / "plantilla_ingreso_trabajadores.xlsx"
    filas, excluidos = construir_filas(plantilla=plantilla_vacia, ruts=ruts)
    for e in excluidos:
        logger.warning("Excluido al rellenar: %s", e)
    if not filas:
        raise RuntimeError("Sin filas para escribir en la plantilla de ingreso")
    path = escribir_plantilla(plantilla_vacia, filas, out)
    logger.info("Plantilla rellena: %s (%s filas)", path, len(filas))
    return path


def ejecutar(driver, wait) -> Path | None:
    """
    Pipeline completo con una sola sesión de navegador.

    Returns:
        Path del Excel cargado, o None si no hay elegibles / fallo.
    """
    logger.info("=== %s: inicio ===", NOMBRE)

    # 1) Listado SCL
    listado = dl_listado.ejecutar(driver, wait, pausa_exploracion=0)
    if listado is None:
        raise RuntimeError("No se pudo descargar listado_finiquitables")

    # 2) Comparar (offline; browser queda abierto)
    ruts, _elig_path = _comparar_y_elegibles(listado)
    if not ruts:
        logger.warning("Sin elegibles para ingreso; fin OK sin carga.")
        return None

    # 3) Plantilla vacía fresca del portal
    vacia = _descargar_plantilla_vacia(driver, wait)

    # 4) Rellenar
    plantilla = _rellenar(vacia, ruts)

    # 5) Subir + validar + carga masiva
    cargado = carga_ingreso_trabajadores.ejecutar(
        driver,
        wait,
        plantilla=plantilla,
        pausa_exploracion=0,
        ya_logueado=True,
    )
    if cargado is None:
        raise RuntimeError("Fallo en validación/carga masiva de ingreso")
    logger.info("=== %s: OK excel=%s ===", NOMBRE, cargado)
    return cargado
