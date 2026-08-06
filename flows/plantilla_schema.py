"""
Esquemas de plantilla Excel Subcontrataley.

Hay al menos 2 layouts:

1) Liquidaciones (con asociados):
   nombre_de_archivo | documento_asociado_1..5 | RUT | Nombre | ...

2) Pagos (AFP/Isapre/Mutual/Caja) — 1 archivo:
   nombre_de_archivo | RUT | Nombre | fecha_programada | ...
"""

from __future__ import annotations

HOJA_DOCUMENTOS = "Documentos"
HOJA_HASH = "SCL_HASH_KEY"

COLUMNAS_DOCUMENTOS = (
    "nombre_de_archivo",
    "documento_asociado_1",
    "documento_asociado_2",
    "documento_asociado_3",
    "documento_asociado_4",
    "documento_asociado_5",
    "RUT",
    "Nombre",
    "fecha_programada",
    "fecha_inicio_contrato",
    "fecha_fin_contrato",
    "ingreso_faena",
    "salida_faena",
    "ap_id",
    "estado",
    "razon_rechazo",
    "contrato_id",
    "faenacontratista_id",
    "faena",
    "local",
)

COLUMNAS_DOCUMENTOS_PAGO = (
    "nombre_de_archivo",
    "RUT",
    "Nombre",
    "fecha_programada",
    "fecha_inicio_contrato",
    "fecha_fin_contrato",
    "ingreso_faena",
    "salida_faena",
    "ap_id",
    "estado",
    "razon_rechazo",
    "contrato_id",
    "faenacontratista_id",
    "faena",
    "local",
)

COLUMNAS_A_COMPLETAR = (
    "nombre_de_archivo",
    "documento_asociado_1",
)

GLOB_PLANTILLA = "cmsd_plantilla_*.xlsx"
