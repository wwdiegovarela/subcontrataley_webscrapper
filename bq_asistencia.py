"""Días trabajados y primera marca desde cr_asistencia_hist_tb."""

from __future__ import annotations

import logging
from datetime import date

from google.cloud import bigquery

from bq_empleados import PROJECT_ID, _cliente
from gcs_docs import rut_cuerpo

logger = logging.getLogger(__name__)

TABLE_ASISTENCIA = f"{PROJECT_ID}.cr_reportes.cr_asistencia_hist_tb"

# Misma regla que control_cumplimiento_documental:
# asistencia=1 y rutrol = rutasi (el trabajador marcó como sí mismo).
_FILTRO_ASISTENCIA = """
COALESCE(SAFE_CAST(asistencia AS INT64), 0) = 1
  AND rutasi IS NOT NULL
  AND REGEXP_REPLACE(TRIM(CAST(rutrol AS STRING)), r'[^0-9]', '')
    = REGEXP_REPLACE(TRIM(CAST(rutasi AS STRING)), r'[^0-9]', '')
"""

SQL_DIAS = f"""
SELECT
  REGEXP_REPLACE(TRIM(CAST(rutasi AS STRING)), r'[^0-9]', '') AS rut,
  COUNT(DISTINCT DATE(dia)) AS dias_trabajados
FROM `{TABLE_ASISTENCIA}`
WHERE {_FILTRO_ASISTENCIA}
  AND DATE(dia) >= DATE_SUB(CURRENT_DATE("America/Santiago"), INTERVAL @dias DAY)
  AND (
    @filtrar_ruts = FALSE
    OR REGEXP_REPLACE(TRIM(CAST(rutasi AS STRING)), r'[^0-9]', '') IN UNNEST(@ruts)
  )
GROUP BY 1
"""

SQL_PRIMERA = f"""
SELECT
  REGEXP_REPLACE(TRIM(CAST(rutasi AS STRING)), r'[^0-9]', '') AS rut,
  MIN(DATE(dia)) AS primera_asistencia
FROM `{TABLE_ASISTENCIA}`
WHERE {_FILTRO_ASISTENCIA}
  AND (
    @filtrar_ruts = FALSE
    OR REGEXP_REPLACE(TRIM(CAST(rutasi AS STRING)), r'[^0-9]', '') IN UNNEST(@ruts)
  )
GROUP BY 1
"""


def consultar_dias_trabajados(
    *,
    ventana_dias: int = 30,
    ruts: list[str] | None = None,
) -> dict[str, int]:
    """
    RUT cuerpo → cantidad de días distintos con asistencia en la ventana.

    Si ``ruts`` se pasa, solo se consultan esos cuerpos.
    """
    client = _cliente()
    cuerpos = sorted({rut_cuerpo(r) for r in (ruts or []) if rut_cuerpo(r)})
    filtrar = bool(cuerpos)
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("dias", "INT64", int(ventana_dias)),
            bigquery.ScalarQueryParameter("filtrar_ruts", "BOOL", filtrar),
            bigquery.ArrayQueryParameter("ruts", "STRING", cuerpos or [""]),
        ]
    )
    logger.info(
        "BQ asistencia: últimos %s días%s",
        ventana_dias,
        f" (filtrando {len(cuerpos)} RUTs)" if filtrar else "",
    )
    rows = client.query(SQL_DIAS, job_config=job_config).result()
    out: dict[str, int] = {}
    for r in rows:
        cuerpo = rut_cuerpo(r["rut"] or "")
        if not cuerpo:
            continue
        out[cuerpo] = int(r["dias_trabajados"] or 0)
    logger.info("BQ asistencia: %s RUTs con ≥1 día en ventana", len(out))
    return out


def consultar_primera_asistencia(
    *,
    ruts: list[str] | None = None,
) -> dict[str, date]:
    """
    RUT cuerpo → primera fecha (MIN dia) con asistencia válida en el histórico.

    Misma regla: asistencia=1 y rutrol = rutasi.
    """
    client = _cliente()
    cuerpos = sorted({rut_cuerpo(r) for r in (ruts or []) if rut_cuerpo(r)})
    filtrar = bool(cuerpos)
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("filtrar_ruts", "BOOL", filtrar),
            bigquery.ArrayQueryParameter("ruts", "STRING", cuerpos or [""]),
        ]
    )
    logger.info(
        "BQ asistencia: primera marca%s",
        f" (filtrando {len(cuerpos)} RUTs)" if filtrar else "",
    )
    rows = client.query(SQL_PRIMERA, job_config=job_config).result()
    out: dict[str, date] = {}
    for r in rows:
        cuerpo = rut_cuerpo(r["rut"] or "")
        if not cuerpo:
            continue
        d = r["primera_asistencia"]
        if d is None:
            continue
        out[cuerpo] = d if isinstance(d, date) else date.fromisoformat(str(d)[:10])
    logger.info("BQ asistencia: %s RUTs con primera marca", len(out))
    return out


def corte_ingreso_faena(*, hoy: date | None = None, meses: int = 1) -> date:
    """
    Fecha mínima aceptable de ingreso a faena (1ª asistencia).

    Quedan fuera los que tengan primera marca anterior a ``hoy - meses``.
    """
    from dateutil.relativedelta import relativedelta

    base = hoy or date.today()
    return base - relativedelta(months=int(meses))
