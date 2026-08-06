"""Configs de flujos de pago (1 archivo por línea, mismo PDF Cotizaciones)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FlujoPagoConfig:
    clave: str
    nombre_ui: str  # texto exacto del <select> Documento
    # Los 4 usan el mismo PDF de cotizaciones Previred en GCS
    tipo_gcs: str = "Cotizaciones"
    layout_gcs: str = "yyyy_mm"  # .../Cotizaciones/2026/06/


PAGOS_AFP_AFC = FlujoPagoConfig(
    clave="pagos_afp_afc",
    nombre_ui="Pagos AFP y AFC",
)

PAGOS_ISAPRE_FONASA = FlujoPagoConfig(
    clave="pagos_isapre_fonasa",
    nombre_ui="Pagos Isapre / FONASA",
)

PAGOS_MUTUALIDADES = FlujoPagoConfig(
    clave="pagos_mutualidades",
    nombre_ui="Pagos Mutualidades",
)

PAGOS_CAJAS = FlujoPagoConfig(
    clave="pagos_cajas_compensacion",
    nombre_ui="Pagos Cajas de Compensación",
)

TODOS_PAGOS: tuple[FlujoPagoConfig, ...] = (
    PAGOS_AFP_AFC,
    PAGOS_ISAPRE_FONASA,
    PAGOS_MUTUALIDADES,
    PAGOS_CAJAS,
)
