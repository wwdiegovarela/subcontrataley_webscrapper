"""Cliente GCS: buscar liquidaciones y transferencias por RUT + periodo."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Iterable

from google.cloud import storage

from browser import MESES_ES, mes_anterior
from config import GCS_BUCKET_NAME, GCS_CREDENTIALS_PATH

logger = logging.getLogger(__name__)


@dataclass
class DocGCS:
    nombre: str
    ruta_gcs: str
    rut_cuerpo: str
    tipo: str  # Liquidacion | Transferencia


def periodo_gcs_texto(referencia: date | None = None) -> str:
    """Periodo de carpeta/archivo en GCS: 'junio 2026' (mes anterior a la ejecución)."""
    p = mes_anterior(referencia)
    return f"{MESES_ES[p.month]} {p.year}"


def rut_cuerpo(rut: str) -> str:
    """
    Cuerpo numérico del RUT (sin DV), como en nombres GCS.
    '15.666.622-K' / '15666622-K' / '15666622' → '15666622'
    """
    if rut is None:
        return ""
    s = re.sub(r"[.\s]", "", str(rut)).upper()
    if "-" in s:
        return re.sub(r"\D", "", s.split("-", 1)[0])
    m = re.match(r"^(\d{7,8})[0-9K]?$", s)
    if m:
        return m.group(1)
    digits = re.sub(r"\D", "", s)
    if len(digits) >= 8:
        return digits[:8] if len(digits) > 8 else digits[:-1] if len(digits) == 9 else digits
    return digits


def _cliente() -> storage.Client:
    """ADC en Cloud Run; JSON local si GCS_CREDENTIALS_PATH está definido."""
    if GCS_CREDENTIALS_PATH:
        return storage.Client.from_service_account_json(GCS_CREDENTIALS_PATH)
    return storage.Client()


def _rut_desde_nombre_archivo(nombre: str) -> str:
    base = nombre.split("/")[-1]
    m = re.match(r"^(\d{7,8})(?:[-_][0-9Kk])?_", base)
    if m:
        return m.group(1)
    m2 = re.match(r"^(\d{7,8})_", base)
    return m2.group(1) if m2 else ""


def periodo_gcs_yyyy_mm(referencia: date | None = None) -> tuple[str, str, str]:
    """
    Periodo mes anterior como (texto 'junio 2026', '2026', '06').
    Útil para Cotizaciones: .../Cotizaciones/2026/06/...
    """
    p = mes_anterior(referencia)
    texto = f"{MESES_ES[p.month]} {p.year}"
    return texto, str(p.year), f"{p.month:02d}"


def listar_docs_periodo(
    tipo: str,
    periodo: str,
    *,
    bucket_name: str | None = None,
    layout: str = "mes_anio",
    anio: str | None = None,
    mes: str | None = None,
) -> list[DocGCS]:
    """
    Lista PDFs de un tipo/periodo en el bucket.

    layout:
      - mes_anio: **/{tipo}/{periodo}/*.pdf  (ej. Liquidacion/junio 2026)
      - yyyy_mm:  **/{tipo}/{anio}/{mes}/*.pdf  (ej. Cotizaciones/2026/06)
    """
    bucket_name = bucket_name or GCS_BUCKET_NAME
    client = _cliente()
    bucket = client.bucket(bucket_name)

    if layout == "yyyy_mm":
        if not anio or not mes:
            _, anio, mes = periodo_gcs_yyyy_mm()
        glob_pat = f"**/{tipo}/{anio}/{mes}/*.pdf"
        needle = f"/{tipo}/{anio}/{mes}/"
        # también mes sin cero a la izquierda
        mes_alt = str(int(mes))
        glob_alt = f"**/{tipo}/{anio}/{mes_alt}/*.pdf"
    else:
        glob_pat = f"**/{tipo}/{periodo}/*.pdf"
        needle = f"/{tipo}/{periodo}/"
        glob_alt = None

    logger.info("GCS list gs://%s match_glob=%s", bucket_name, glob_pat)

    def _collect(glob_pattern: str) -> list[DocGCS]:
        out: list[DocGCS] = []
        try:
            blobs = bucket.list_blobs(match_glob=glob_pattern)
            for blob in blobs:
                if blob.name.endswith("/"):
                    continue
                nombre = blob.name.rsplit("/", 1)[-1]
                cuerpo = _rut_desde_nombre_archivo(nombre)
                if not cuerpo:
                    continue
                out.append(
                    DocGCS(
                        nombre=nombre,
                        ruta_gcs=blob.name,
                        rut_cuerpo=cuerpo,
                        tipo=tipo,
                    )
                )
        except Exception as exc:
            logger.warning("match_glob falló (%s); fallback prefix %s", exc, needle)
            for blob in bucket.list_blobs():
                if needle not in blob.name and (
                    layout != "yyyy_mm"
                    or f"/{tipo}/{anio}/{mes_alt}/" not in blob.name
                ):
                    continue
                if not blob.name.lower().endswith(".pdf"):
                    continue
                nombre = blob.name.rsplit("/", 1)[-1]
                cuerpo = _rut_desde_nombre_archivo(nombre)
                if not cuerpo:
                    continue
                out.append(
                    DocGCS(
                        nombre=nombre,
                        ruta_gcs=blob.name,
                        rut_cuerpo=cuerpo,
                        tipo=tipo,
                    )
                )
        return out

    docs = _collect(glob_pat)
    if not docs and glob_alt:
        docs = _collect(glob_alt)

    logger.info("GCS %s/%s → %s archivo(s)", tipo, periodo, len(docs))
    return docs


def indice_por_rut(docs: Iterable[DocGCS]) -> dict[str, DocGCS]:
    """Un doc por RUT (si hay varios, se queda el último visto)."""
    out: dict[str, DocGCS] = {}
    for d in docs:
        out[d.rut_cuerpo] = d
    return out


def buscar_docs_tipo(
    tipo_gcs: str,
    *,
    periodo: str | None = None,
    layout: str = "mes_anio",
    referencia: date | None = None,
) -> tuple[dict[str, DocGCS], str]:
    """Índice RUT → doc para un tipo GCS."""
    if layout == "yyyy_mm":
        texto, anio, mes = periodo_gcs_yyyy_mm(referencia)
        docs = listar_docs_periodo(
            tipo_gcs, texto, layout="yyyy_mm", anio=anio, mes=mes
        )
        return indice_por_rut(docs), texto
    periodo = periodo or periodo_gcs_texto(referencia)
    docs = listar_docs_periodo(tipo_gcs, periodo, layout="mes_anio")
    return indice_por_rut(docs), periodo


def buscar_liquidaciones_y_transferencias(
    periodo: str | None = None,
    referencia: date | None = None,
) -> tuple[dict[str, DocGCS], dict[str, DocGCS], str]:
    periodo = periodo or periodo_gcs_texto(referencia)
    liqs = indice_por_rut(listar_docs_periodo("Liquidacion", periodo))
    trs = indice_por_rut(listar_docs_periodo("Transferencia", periodo))
    return liqs, trs, periodo


def descargar_doc(doc: DocGCS, dest_dir: Path, *, bucket_name: str | None = None) -> Path:
    """Descarga el blob GCS a dest_dir conservando el nombre exacto (como en el Excel)."""
    dest_dir = Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / doc.nombre
    if dest.exists() and dest.stat().st_size > 0:
        logger.info("Ya existe local: %s", dest.name)
        return dest
    client = _cliente()
    bucket = client.bucket(bucket_name or GCS_BUCKET_NAME)
    blob = bucket.blob(doc.ruta_gcs)
    blob.download_to_filename(str(dest))
    logger.info("Descargado gs://%s/%s → %s", bucket_name or GCS_BUCKET_NAME, doc.ruta_gcs, dest)
    return dest


def descargar_docs(
    docs: Iterable[DocGCS],
    dest_dir: Path,
) -> list[Path]:
    paths: list[Path] = []
    vistos: set[str] = set()
    for doc in docs:
        if doc.nombre in vistos:
            continue
        vistos.add(doc.nombre)
        paths.append(descargar_doc(doc, dest_dir))
    return paths
