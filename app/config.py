"""Configuración compartida del proyecto.

La configuración local del proyecto tiene prioridad. Si no existe, se carga
el entorno global compartido definido por ``AI_WORKSTATION_HOME`` o por la
ubicación canónica ``E:\\Proyectos\\ai-workstation``.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
LOCAL_ENV_FILE = PROJECT_ROOT / ".env"
DEFAULT_GLOBAL_HOME = Path(r"E:\Proyectos\ai-workstation")
GLOBAL_HOME = Path(os.getenv("AI_WORKSTATION_HOME", str(DEFAULT_GLOBAL_HOME)))
GLOBAL_ENV_FILE = GLOBAL_HOME / ".env"


def load_configuration() -> Path | None:
    """Carga el entorno local y después el global sin sobrescribir variables locales."""
    local_exists = LOCAL_ENV_FILE.exists()
    if local_exists:
        load_dotenv(LOCAL_ENV_FILE, override=False)

    global_exists = GLOBAL_ENV_FILE.exists()
    if global_exists:
        load_dotenv(GLOBAL_ENV_FILE, override=False)

    return LOCAL_ENV_FILE if local_exists else GLOBAL_ENV_FILE if global_exists else None


ENV_FILE = load_configuration()
