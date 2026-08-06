"""Contratos firmados vía reporte ControlRoll (token TOKEN_CR_CONTRATOS)."""

from __future__ import annotations

import json
import logging
import os
import time
import unicodedata
from dataclasses import asdict, dataclass
from typing import Any

import requests

from config import GCS_CREDENTIALS_PATH  # noqa: F401 — keep dotenv loaded via config
from gcs_docs import rut_cuerpo

logger = logging.getLogger(__name__)

API_URL = os.getenv(
    "CONTROLROLL_API_URL",
    "https://cl.controlroll.com/ww01/ServiceUrl.aspx",
).strip()

# Mismo token default que selenium_base_contratos_cloudrun.TOKEN_DOCUMENTOS_CONTRATOS
TOKEN_CR_CONTRATOS = (
    os.getenv("TOKEN_CR_CONTRATOS")
    or os.getenv("TOKEN_DOCUMENTOS_CONTRATOS")
    or "xMAOXmuzF8MeHi+qZLbgkd1Dg8WuzzHXJvPXxf207bY="
).strip()


def _sin_acentos(s: str) -> str:
    t = unicodedata.normalize("NFKD", str(s or ""))
    return "".join(c for c in t if not unicodedata.combining(c))


def _norm_key(s: str) -> str:
    return " ".join(_sin_acentos(s).strip().upper().split())


def _columna(row_or_keys: Any, nombre: str) -> str | None:
    target = _norm_key(nombre)
    keys = row_or_keys.keys() if hasattr(row_or_keys, "keys") else row_or_keys
    for k in keys:
        if _norm_key(str(k)) == target:
            return str(k)
    return None


@dataclass
class ContratoCR:
    rut_cuerpo: str
    rut_raw: str
    tipo_documento: str
    firma_colaborador: str
    firma_rep_legal: str
    estado_documento: str
    fecha_firma_colaborador: str
    nombre_documento: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _consulta_cr_json(token: str, *, max_retries: int = 5, retry_delay: float = 3) -> list[dict]:
    headers = {"method": "report", "token": token}
    last_err: Exception | None = None
    for attempt in range(1, max_retries + 1):
        try:
            logger.info(
                "CR contratos: intento %s/%s…",
                attempt,
                max_retries,
            )
            resp = requests.get(API_URL, headers=headers, timeout=180)
            text = (resp.text or "").strip()
            if resp.status_code != 200:
                raise RuntimeError(f"HTTP {resp.status_code}: {text[:200]}")
            if text.lower().startswith("<!doctype") or "Login ControlRoll" in text:
                raise RuntimeError(
                    "ControlRoll devolvió login HTML (token rechazado o API inestable)"
                )
            data = json.loads(text)
            if not isinstance(data, list):
                raise RuntimeError(f"Respuesta inesperada: {type(data)}")
            logger.info("CR contratos: %s filas", len(data))
            return data
        except Exception as e:
            last_err = e
            logger.warning("CR contratos intento %s falló: %s", attempt, e)
            if attempt < max_retries:
                time.sleep(retry_delay * attempt)
    raise RuntimeError(f"No se pudo consultar contratos CR: {last_err}") from last_err


def consultar_contratos_firmados(
    *,
    token: str | None = None,
    exigir_firma_colaborador: bool = True,
) -> dict[str, ContratoCR]:
    """
    RUT cuerpo → último/mejor registro de contrato firmado.

    Criterio (igual a selenium_base_contratos):
      - Tipo del Documento contiene CONTRATO
      - Firma del Colaborador contiene FIRMADO (si exigir_firma_colaborador)
    """
    tok = (token or TOKEN_CR_CONTRATOS).strip()
    if not tok:
        raise ValueError("Falta TOKEN_CR_CONTRATOS / TOKEN_DOCUMENTOS_CONTRATOS")

    rows = _consulta_cr_json(tok)
    if not rows:
        return {}

    sample_keys = rows[0].keys()
    col_rut = _columna(sample_keys, "RUT")
    col_firma = _columna(sample_keys, "Firma del Colaborador")
    col_firma_rl = _columna(sample_keys, "Firma de Representante Legal")
    col_tipo = _columna(sample_keys, "Tipo del Documento")
    col_estado = _columna(sample_keys, "Estado del Documento")
    col_fecha = _columna(sample_keys, "Fecha Firma del Colaborador")
    col_nombre = _columna(sample_keys, "Nombre del Documento")
    if not col_rut:
        raise RuntimeError(f"API contratos sin columna RUT. Keys: {list(sample_keys)}")

    out: dict[str, ContratoCR] = {}
    n_contrato = 0
    n_firmado = 0
    for row in rows:
        tipo = str(row.get(col_tipo) or "") if col_tipo else ""
        if col_tipo and "CONTRATO" not in _norm_key(tipo):
            continue
        n_contrato += 1
        firma = str(row.get(col_firma) or "") if col_firma else ""
        if exigir_firma_colaborador and col_firma:
            if "FIRMADO" not in _norm_key(firma):
                continue
        n_firmado += 1
        cuerpo = rut_cuerpo(row.get(col_rut) or "")
        if not cuerpo:
            continue
        out[cuerpo] = ContratoCR(
            rut_cuerpo=cuerpo,
            rut_raw=str(row.get(col_rut) or ""),
            tipo_documento=tipo,
            firma_colaborador=firma,
            firma_rep_legal=str(row.get(col_firma_rl) or "") if col_firma_rl else "",
            estado_documento=str(row.get(col_estado) or "") if col_estado else "",
            fecha_firma_colaborador=str(row.get(col_fecha) or "") if col_fecha else "",
            nombre_documento=str(row.get(col_nombre) or "") if col_nombre else "",
        )

    logger.info(
        "CR contratos: filas tipo CONTRATO=%s | firmados colaborador=%s | RUTs únicos=%s",
        n_contrato,
        n_firmado,
        len(out),
    )
    return out
