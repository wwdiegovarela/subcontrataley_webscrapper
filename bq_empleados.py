"""Empleados activos ControlRoll desde BigQuery."""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass
from datetime import date, datetime
from typing import Any

from google.cloud import bigquery
from google.oauth2 import service_account

from config import GCS_CREDENTIALS_PATH
from gcs_docs import rut_cuerpo

logger = logging.getLogger(__name__)

PROJECT_ID = "worldwide-470917"
TABLE_EMPLEADOS = f"{PROJECT_ID}.cr_reportes.cr_reclutamiento_empleados"

# Universo Walmart / cadenas para subcontrataley ingreso
NOMBRES_FANTASIA_DEFAULT = ("ACUENTA", "EKONO", "LIDER", "LIDER EXPRESS")

SQL_ACTIVOS = f"""
SELECT
  CAST(rut AS STRING) AS rut,
  CAST(rut_dv AS STRING) AS rut_dv,
  nombre_completo,
  empresa,
  instalacion,
  nombre_fantasia,
  TRIM(CAST(cecos AS STRING)) AS cecos,
  cargo,
  tipo_empleado,
  estado,
  fecha_de_ingreso
FROM `{TABLE_EMPLEADOS}`
WHERE estado = @estado
  AND nombre_fantasia IN UNNEST(@nombres_fantasia)
"""


@dataclass
class EmpleadoCR:
    rut_cuerpo: str
    rut_dv: str
    nombre_completo: str
    empresa: str
    instalacion: str
    nombre_fantasia: str
    cecos: str
    cargo: str
    tipo_empleado: str
    estado: str
    fecha_de_ingreso: str | None
    dias_trabajados_30d: int | None = None
    # Placeholder hasta cablear contratos firmados (API CR / GCS).
    contrato_firmado: bool | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _cliente() -> bigquery.Client:
    if GCS_CREDENTIALS_PATH:
        creds = service_account.Credentials.from_service_account_file(
            GCS_CREDENTIALS_PATH
        )
        return bigquery.Client(project=PROJECT_ID, credentials=creds)
    return bigquery.Client(project=PROJECT_ID)


def _fecha_str(v: Any) -> str | None:
    if v is None:
        return None
    if isinstance(v, datetime):
        return v.date().isoformat()
    if isinstance(v, date):
        return v.isoformat()
    return str(v)


def consultar_empleados_activos(
    *,
    nombres_fantasia: tuple[str, ...] | list[str] = NOMBRES_FANTASIA_DEFAULT,
    estado: str = "Activo",
) -> list[EmpleadoCR]:
    """Activos ControlRoll filtrados por nombre_fantasia (query de negocio)."""
    client = _cliente()
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("estado", "STRING", estado),
            bigquery.ArrayQueryParameter(
                "nombres_fantasia", "STRING", list(nombres_fantasia)
            ),
        ]
    )
    logger.info(
        "BQ empleados: estado=%s fantasia=%s",
        estado,
        list(nombres_fantasia),
    )
    rows = client.query(SQL_ACTIVOS, job_config=job_config).result()
    out: list[EmpleadoCR] = []
    vistos: set[str] = set()
    for r in rows:
        cuerpo = rut_cuerpo(r["rut"] or r["rut_dv"] or "")
        if not cuerpo or cuerpo in vistos:
            continue
        vistos.add(cuerpo)
        out.append(
            EmpleadoCR(
                rut_cuerpo=cuerpo,
                rut_dv=str(r["rut_dv"] or ""),
                nombre_completo=str(r["nombre_completo"] or ""),
                empresa=str(r["empresa"] or ""),
                instalacion=str(r["instalacion"] or ""),
                nombre_fantasia=str(r["nombre_fantasia"] or ""),
                cecos=str(r["cecos"] or ""),
                cargo=str(r["cargo"] or ""),
                tipo_empleado=str(r["tipo_empleado"] or ""),
                estado=str(r["estado"] or ""),
                fecha_de_ingreso=_fecha_str(r["fecha_de_ingreso"]),
            )
        )
    logger.info("BQ empleados: %s filas únicas por RUT", len(out))
    return out
