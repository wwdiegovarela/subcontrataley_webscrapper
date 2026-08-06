"""Configuración Subcontrataley (variables de entorno)."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

# Cloud Run Job / Service
IS_CLOUD_RUN = bool(
    os.getenv("K_SERVICE")
    or os.getenv("CLOUD_RUN_JOB")
    or os.getenv("K_REVISION")
)

HEADLESS = os.getenv(
    "HEADLESS",
    "true" if IS_CLOUD_RUN else "false",
).lower() in ("1", "true", "yes")

IMPLICIT_WAIT = int(os.getenv("IMPLICIT_WAIT", "10"))
EXPLICIT_WAIT = int(os.getenv("EXPLICIT_WAIT", "30" if IS_CLOUD_RUN else "20"))

SUBCONTRATALEY_USERNAME = os.getenv("SUBCONTRATALEY_USERNAME", "")
SUBCONTRATALEY_PASSWORD = os.getenv("SUBCONTRATALEY_PASSWORD", "")

# En Cloud Run: /tmp (filesystem escribible)
_default_dl = (
    Path(tempfile.gettempdir()) / "subcontrataley_downloads"
    if IS_CLOUD_RUN
    else Path(__file__).parent / "downloads"
)
DOWNLOAD_DIR = Path(os.getenv("DOWNLOAD_DIR", str(_default_dl))).resolve()
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

_default_debug = (
    Path(tempfile.gettempdir()) / "subcontrataley_debug"
    if IS_CLOUD_RUN
    else Path(__file__).parent / "debug"
)
DEBUG_DIR = Path(os.getenv("DEBUG_DIR", str(_default_debug))).resolve()
DEBUG_DIR.mkdir(parents=True, exist_ok=True)

# GCS — documentos
GCS_BUCKET_NAME = os.getenv("GCS_BUCKET_NAME", "worldwide-documentos-instalaciones")
# Local: JSON. Cloud Run: SA del job (ADC) si no se define path.
GCS_CREDENTIALS_PATH = os.getenv("GCS_CREDENTIALS_PATH", "").strip() or None

# Chrome en contenedor (Dockerfile)
CHROME_BIN = os.getenv("CHROME_BIN", "").strip() or None
CHROMEDRIVER_PATH = os.getenv("CHROMEDRIVER_PATH", "").strip() or None


def require_credentials() -> tuple[str, str]:
    user = SUBCONTRATALEY_USERNAME.strip()
    password = SUBCONTRATALEY_PASSWORD.strip()
    if not user or not password:
        raise ValueError(
            "Faltan credenciales. Define SUBCONTRATALEY_USERNAME y "
            "SUBCONTRATALEY_PASSWORD en .env o en el Job de Cloud Run."
        )
    return user, password
