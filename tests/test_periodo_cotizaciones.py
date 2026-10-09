"""Test offline de la regla de disponibilidad de cotizaciones (día 14).

Ejecutar:  python -m pytest tests/test_periodo_cotizaciones.py   (o)   python tests/test_periodo_cotizaciones.py
"""
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from browser import mes_anterior  # noqa: E402
from gcs_docs import periodo_cotizaciones, referencia_para_periodo  # noqa: E402


def test_borde_dia_14():
    # Cotización de septiembre disponible desde el 14 de octubre
    assert periodo_cotizaciones(date(2026, 10, 13), override="") == date(2026, 8, 1)
    assert periodo_cotizaciones(date(2026, 10, 14), override="") == date(2026, 9, 1)
    assert periodo_cotizaciones(date(2026, 10, 31), override="") == date(2026, 9, 1)
    assert periodo_cotizaciones(date(2026, 10, 1), override="") == date(2026, 8, 1)


def test_cambio_de_anio():
    assert periodo_cotizaciones(date(2027, 1, 13), override="") == date(2026, 11, 1)
    assert periodo_cotizaciones(date(2027, 1, 14), override="") == date(2026, 12, 1)
    assert periodo_cotizaciones(date(2027, 2, 5), override="") == date(2026, 12, 1)


def test_dia_configurable():
    assert periodo_cotizaciones(date(2026, 10, 10), override="", dia_disponible=10) == date(2026, 9, 1)
    assert periodo_cotizaciones(date(2026, 10, 9), override="", dia_disponible=10) == date(2026, 8, 1)


def test_override_explicito():
    assert periodo_cotizaciones(date(2026, 10, 1), override="2026-05") == date(2026, 5, 1)
    try:
        periodo_cotizaciones(date(2026, 10, 1), override="2026-13")
    except ValueError:
        pass
    else:
        raise AssertionError("override inválido debía fallar")


def test_referencia_coherente_con_mes_anterior():
    for p in (date(2026, 8, 1), date(2026, 12, 1), date(2027, 1, 1)):
        assert mes_anterior(referencia_para_periodo(p)) == p


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("OK", name)
