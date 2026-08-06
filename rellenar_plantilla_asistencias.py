"""Rellena plantilla Libro de Asistencia: 1 fila por faena → 1 PDF compilado."""

from __future__ import annotations

import logging
import shutil
from dataclasses import dataclass, field
from pathlib import Path

from openpyxl import load_workbook
from openpyxl.worksheet.worksheet import Worksheet

from compilar_asistencias import _slug_faena
from flows.plantilla_schema import HOJA_DOCUMENTOS

logger = logging.getLogger(__name__)


@dataclass
class ResultadoRellenoAsistencia:
    plantilla: Path
    periodo: str
    filas: int = 0
    sin_pdf: list[str] = field(default_factory=list)
    pdfs: list[Path] = field(default_factory=list)


def _mapa_columnas(ws: Worksheet) -> dict[str, int]:
    out: dict[str, int] = {}
    for c in range(1, ws.max_column + 1):
        raw = ws.cell(1, c).value
        if raw is None:
            continue
        out[str(raw).strip().lower()] = c
    return out


def _col(mapa: dict[str, int], *nombres: str) -> int:
    for n in nombres:
        if n.lower() in mapa:
            return mapa[n.lower()]
    raise KeyError(f"No encontré columna {nombres} en {list(mapa)}")


def indice_pdfs_por_faena(pdf_dir: Path, periodo: str) -> dict[str, Path]:
    """
    Indexa PDFs por slug de faena.
    Espera nombres: {slug}_Asistencia_{periodo}.pdf
    """
    pdf_dir = Path(pdf_dir)
    suffix = f"_Asistencia_{periodo}.pdf"
    out: dict[str, Path] = {}
    for p in sorted(pdf_dir.glob("*.pdf")):
        name = p.name
        if not name.endswith(suffix):
            # tolerancia: slug_Asistencia_julio 2026.pdf
            if "_Asistencia_" not in name:
                continue
            slug = name.rsplit("_Asistencia_", 1)[0]
        else:
            slug = name[: -len(suffix)]
        out[slug] = p
    return out


def rellenar_plantilla_asistencias(
    plantilla: Path,
    pdf_dir: Path,
    *,
    periodo: str,
    guardar_como: Path | None = None,
) -> ResultadoRellenoAsistencia:
    """
    Escribe en cada fila el nombre del PDF compilado de esa faena.
    No borra filas; falla en log si una faena no tiene PDF.
    """
    plantilla = Path(plantilla)
    pdf_dir = Path(pdf_dir)
    idx = indice_pdfs_por_faena(pdf_dir, periodo)
    if not idx:
        raise FileNotFoundError(
            f"No hay PDFs de asistencia en {pdf_dir} para periodo '{periodo}'"
        )

    wb = load_workbook(plantilla)
    if HOJA_DOCUMENTOS not in wb.sheetnames:
        raise ValueError(f"No existe hoja '{HOJA_DOCUMENTOS}' en {plantilla}")
    ws = wb[HOJA_DOCUMENTOS]
    cols = _mapa_columnas(ws)
    col_archivo = _col(cols, "nombre_de_archivo")
    col_faena = _col(cols, "faena")

    res = ResultadoRellenoAsistencia(plantilla=plantilla, periodo=periodo)
    pdfs_vistos: dict[str, Path] = {}

    for row in range(2, ws.max_row + 1):
        faena_raw = ws.cell(row, col_faena).value
        if faena_raw is None or str(faena_raw).strip() == "":
            continue
        faena = str(faena_raw).strip()
        slug = _slug_faena(faena)
        pdf = idx.get(slug)
        if not pdf:
            # match flexible: slug con/sin tildes ya normalizado
            res.sin_pdf.append(faena)
            logger.warning("Sin PDF para faena='%s' slug='%s'", faena, slug)
            continue
        ws.cell(row, col_archivo, pdf.name)
        pdfs_vistos[pdf.name] = pdf
        res.filas += 1

    dest = Path(guardar_como) if guardar_como else plantilla
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.resolve() != plantilla.resolve():
        shutil.copy2(plantilla, dest)
        wb.save(dest)
    else:
        wb.save(dest)
    res.plantilla = dest
    res.pdfs = list(pdfs_vistos.values())

    logger.info(
        "Plantilla asistencia periodo=%s | filas=%s | pdfs unicos=%s | sin_pdf=%s → %s",
        periodo,
        res.filas,
        len(res.pdfs),
        len(res.sin_pdf),
        dest,
    )
    if res.filas == 0:
        raise ValueError("Ninguna fila de faena se pudo mapear a un PDF.")
    return res
