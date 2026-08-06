"""
Compara activos ControlRoll (BQ) vs listado Subcontrataley (Excel finiquitables).

Filtros sobre faltantes en SCL:
  - días trabajados ≥ 1 en últimos N días (cr_asistencia_hist_tb)
  - contrato firmado por colaborador (reporte CR TOKEN_CR_CONTRATOS)
  - 1ª asistencia (ingreso faena) con antigüedad ≤ 1 mes respecto a hoy

Uso:
  python comparar_trabajadores.py
  python comparar_trabajadores.py --listado downloads/staging_trabajadores/2026_08_04/listado_finiquitables.xlsx
"""

from __future__ import annotations

import argparse
import json
import logging
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from openpyxl import Workbook

from bq_asistencia import (
    consultar_dias_trabajados,
    consultar_primera_asistencia,
    corte_ingreso_faena,
)
from bq_empleados import EmpleadoCR, consultar_empleados_activos
from config import DOWNLOAD_DIR
from cr_contratos import consultar_contratos_firmados
from leer_listado_trabajadores import TrabajadorSCL, leer_listado_trabajadores

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@dataclass
class ResultadoComparacion:
    n_cr: int
    n_scl: int
    n_en_ambos: int
    n_faltan_en_scl: int
    n_solo_en_scl: int
    n_faltan_con_asistencia: int
    n_elegibles: int
    ventana_dias: int
    min_dias: int
    corte_faena: str
    faltan_en_scl: list[EmpleadoCR]
    faltan_con_asistencia: list[EmpleadoCR]
    elegibles: list[EmpleadoCR]
    solo_en_scl: list[TrabajadorSCL]
    en_ambos_cr: list[EmpleadoCR]
    excluidos_faena_antigua: list[EmpleadoCR]


def resolver_listado(path: Path | None) -> Path:
    if path is not None:
        p = Path(path)
        if not p.is_file():
            raise FileNotFoundError(p)
        return p
    root = DOWNLOAD_DIR / "staging_trabajadores"
    if not root.is_dir():
        raise FileNotFoundError(f"No hay staging en {root}")
    candidatos = sorted(
        root.glob("*/listado_finiquitables.xlsx"),
        key=lambda x: x.stat().st_mtime,
        reverse=True,
    )
    if not candidatos:
        raise FileNotFoundError(
            f"No hay listado_finiquitables.xlsx en {root}. "
            "Corré primero: python run_flujo.py listado_trabajadores"
        )
    return candidatos[0]


def comparar(
    empleados_cr: list[EmpleadoCR],
    trabajadores_scl: list[TrabajadorSCL],
    *,
    dias_por_rut: dict[str, int],
    firmados: set[str],
    primera_asistencia: dict[str, date],
    corte_faena: date,
    ventana_dias: int = 30,
    min_dias: int = 1,
) -> ResultadoComparacion:
    map_cr = {e.rut_cuerpo: e for e in empleados_cr}
    map_scl = {t.rut_cuerpo: t for t in trabajadores_scl}
    ruts_cr = set(map_cr)
    ruts_scl = set(map_scl)

    faltan = sorted(ruts_cr - ruts_scl)
    solo_scl = sorted(ruts_scl - ruts_cr)
    ambos = sorted(ruts_cr & ruts_scl)

    faltan_emp: list[EmpleadoCR] = []
    con_asis: list[EmpleadoCR] = []
    elegibles: list[EmpleadoCR] = []
    excluidos_faena: list[EmpleadoCR] = []
    for r in faltan:
        e = map_cr[r]
        dias = int(dias_por_rut.get(r, 0))
        firmado = r in firmados
        e.dias_trabajados_30d = dias
        e.contrato_firmado = firmado
        faltan_emp.append(e)
        if dias >= min_dias:
            con_asis.append(e)
        if dias >= min_dias and firmado:
            primera = primera_asistencia.get(r)
            if primera is None or primera < corte_faena:
                excluidos_faena.append(e)
                continue
            elegibles.append(e)

    return ResultadoComparacion(
        n_cr=len(ruts_cr),
        n_scl=len(ruts_scl),
        n_en_ambos=len(ambos),
        n_faltan_en_scl=len(faltan),
        n_solo_en_scl=len(solo_scl),
        n_faltan_con_asistencia=len(con_asis),
        n_elegibles=len(elegibles),
        ventana_dias=ventana_dias,
        min_dias=min_dias,
        corte_faena=corte_faena.isoformat(),
        faltan_en_scl=faltan_emp,
        faltan_con_asistencia=con_asis,
        elegibles=elegibles,
        solo_en_scl=[map_scl[r] for r in solo_scl],
        en_ambos_cr=[map_cr[r] for r in ambos],
        excluidos_faena_antigua=excluidos_faena,
    )


def _escribir_xlsx_empleados(path: Path, filas: list[EmpleadoCR], titulo: str) -> None:
    wb = Workbook()
    ws = wb.active
    ws.title = titulo[:31]
    if not filas:
        ws.append(["rut_cuerpo", "(sin filas)"])
        wb.save(path)
        return
    headers = list(filas[0].to_dict().keys())
    ws.append(headers)
    for e in filas:
        d = e.to_dict()
        ws.append([d[h] for h in headers])
    wb.save(path)


def guardar_resultado(
    res: ResultadoComparacion,
    *,
    out_dir: Path,
    listado_path: Path,
) -> dict[str, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    resumen = {
        "listado_scl": str(listado_path),
        "ventana_dias": res.ventana_dias,
        "min_dias": res.min_dias,
        "corte_ingreso_faena": res.corte_faena,
        "n_cr": res.n_cr,
        "n_scl": res.n_scl,
        "n_en_ambos": res.n_en_ambos,
        "n_faltan_en_scl": res.n_faltan_en_scl,
        "n_faltan_con_asistencia": res.n_faltan_con_asistencia,
        "n_elegibles": res.n_elegibles,
        "n_excluidos_faena_antigua": len(res.excluidos_faena_antigua),
        "n_solo_en_scl": res.n_solo_en_scl,
        "criterio_elegible": (
            "faltante SCL + dias>=min + contrato firmado colaborador "
            "+ 1ª asistencia (ingreso faena) >= hoy-1mes"
        ),
        "faltan_en_scl": [e.to_dict() for e in res.faltan_en_scl],
        "faltan_con_asistencia": [e.to_dict() for e in res.faltan_con_asistencia],
        "elegibles": [e.to_dict() for e in res.elegibles],
        "excluidos_faena_antigua": [
            e.to_dict() for e in res.excluidos_faena_antigua
        ],
        "solo_en_scl": [t.to_dict() for t in res.solo_en_scl],
    }
    paths: dict[str, Path] = {}
    p_json = out_dir / "comparacion_cr_vs_scl.json"
    p_json.write_text(
        json.dumps(resumen, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    paths["json"] = p_json

    p_xlsx = out_dir / "faltan_en_scl.xlsx"
    _escribir_xlsx_empleados(p_xlsx, res.faltan_en_scl, "faltan_en_scl")
    paths["xlsx"] = p_xlsx

    p_asis = out_dir / "elegibles_asistencia.xlsx"
    _escribir_xlsx_empleados(p_asis, res.faltan_con_asistencia, "con_asistencia")
    paths["asistencia"] = p_asis

    p_elig = out_dir / "elegibles_ingreso.xlsx"
    _escribir_xlsx_empleados(p_elig, res.elegibles, "elegibles")
    paths["elegibles"] = p_elig

    p_faena = out_dir / "excluidos_faena_antigua.xlsx"
    _escribir_xlsx_empleados(
        p_faena, res.excluidos_faena_antigua, "faena_antigua"
    )
    paths["faena_antigua"] = p_faena

    p_solo = out_dir / "solo_en_scl.json"
    p_solo.write_text(
        json.dumps([t.to_dict() for t in res.solo_en_scl], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    paths["solo_scl"] = p_solo
    return paths


def main() -> None:
    parser = argparse.ArgumentParser(description="Comparar CR (BQ) vs SCL listado")
    parser.add_argument("--listado", type=Path, default=None)
    parser.add_argument("--out-dir", type=Path, default=None)
    parser.add_argument("--ventana-dias", type=int, default=30)
    parser.add_argument("--min-dias", type=int, default=1)
    parser.add_argument(
        "--max-meses-faena",
        type=int,
        default=1,
        help="Excluir si 1ª asistencia (ingreso faena) es anterior a hoy-N meses",
    )
    parser.add_argument(
        "--sin-contratos",
        action="store_true",
        help="No consultar API CR de contratos (solo asistencia)",
    )
    args = parser.parse_args()

    listado = resolver_listado(args.listado)
    out_dir = args.out_dir or listado.parent
    logger.info("Listado SCL: %s", listado)

    scl = leer_listado_trabajadores(listado)
    cr = consultar_empleados_activos()

    map_cr = {e.rut_cuerpo: e for e in cr}
    map_scl = {t.rut_cuerpo: t for t in scl}
    faltan_ruts = sorted(set(map_cr) - set(map_scl))

    dias = consultar_dias_trabajados(
        ventana_dias=args.ventana_dias,
        ruts=faltan_ruts,
    )
    primera = consultar_primera_asistencia(ruts=faltan_ruts)
    corte = corte_ingreso_faena(meses=args.max_meses_faena)
    logger.info(
        "Corte ingreso faena: >= %s (hoy - %s mes/es)",
        corte.isoformat(),
        args.max_meses_faena,
    )

    if args.sin_contratos:
        firmados: set[str] = set(faltan_ruts)
        logger.warning("--sin-contratos: se asume contrato_firmado=True para el filtro")
    else:
        contratos = consultar_contratos_firmados()
        firmados = set(contratos.keys())

    res = comparar(
        cr,
        scl,
        dias_por_rut=dias,
        firmados=firmados,
        primera_asistencia=primera,
        corte_faena=corte,
        ventana_dias=args.ventana_dias,
        min_dias=args.min_dias,
    )

    logger.info(
        "CR=%s | SCL=%s | faltan=%s | con asistencia=%s | "
        "elegibles (asis+contrato+faena≤1m)=%s | faena antigua=%s | solo SCL=%s",
        res.n_cr,
        res.n_scl,
        res.n_faltan_en_scl,
        res.n_faltan_con_asistencia,
        res.n_elegibles,
        len(res.excluidos_faena_antigua),
        res.n_solo_en_scl,
    )
    paths = guardar_resultado(res, out_dir=out_dir, listado_path=listado)
    for k, p in paths.items():
        logger.info("Escrito %s: %s", k, p)

    if res.elegibles:
        logger.info("Elegibles ingreso — muestra:")
        for e in res.elegibles[:20]:
            p = primera.get(e.rut_cuerpo)
            logger.info(
                "  %s | %sd | contrato=%s | faena=%s | %s | %s",
                e.rut_dv or e.rut_cuerpo,
                e.dias_trabajados_30d,
                e.contrato_firmado,
                p.isoformat() if p else None,
                e.nombre_completo,
                e.instalacion,
            )

    if res.excluidos_faena_antigua:
        logger.info(
            "Excluidos por ingreso faena > %s mes/es (%s):",
            args.max_meses_faena,
            len(res.excluidos_faena_antigua),
        )
        for e in res.excluidos_faena_antigua:
            p = primera.get(e.rut_cuerpo)
            logger.info(
                "  %s | 1ª asis=%s | %s",
                e.rut_dv or e.rut_cuerpo,
                p.isoformat() if p else "(sin marca)",
                e.nombre_completo,
            )

    rechazados = [
        e
        for e in res.faltan_en_scl
        if e not in res.elegibles and e not in res.excluidos_faena_antigua
    ]
    if rechazados:
        logger.info("Faltantes NO elegibles por otros motivos (%s):", len(rechazados))
        for e in rechazados:
            logger.info(
                "  %s | dias=%s | contrato=%s | %s",
                e.rut_dv or e.rut_cuerpo,
                e.dias_trabajados_30d,
                e.contrato_firmado,
                e.nombre_completo,
            )


if __name__ == "__main__":
    main()
