"""Memoria persistente y local para los agentes.

El almacenamiento usa JSONL para que sea append-only, recuperable de forma
simple y compatible entre sesiones y sistemas Windows/Linux. La búsqueda es
 léxica y no depende de clases internas de CrewAI, cuya API cambia entre versiones.
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
STORAGE_DIR = Path(
    os.getenv("CREWAI_STORAGE_DIR", str(PROJECT_ROOT / "storage" / "crewai_memory"))
).resolve()
MEMORY_FILE = STORAGE_DIR / "memory.jsonl"
STORAGE_DIR.mkdir(parents=True, exist_ok=True)

_WORD_RE = re.compile(r"[\wÀ-ÿ]+", re.UNICODE)


def _tokens(value: str) -> set[str]:
    return {word.casefold() for word in _WORD_RE.findall(value)}


def remember(text: str, source: str = "user_interaction") -> dict[str, Any]:
    """Guarda un hecho o contexto y devuelve un resultado estructurado."""
    text = str(text).strip()
    if not text:
        return {"status": "error", "message": "El texto de memoria está vacío"}

    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source": source,
        "text": text,
    }
    try:
        with MEMORY_FILE.open("a", encoding="utf-8") as file:
            file.write(json.dumps(record, ensure_ascii=False) + "\n")
        return {"status": "success", "stored": text, "source": source}
    except OSError as exc:
        return {"status": "error", "message": str(exc)}


def recall(query: str, limit: int = 5) -> list[dict[str, Any]]:
    """Recupera hasta ``limit`` recuerdos relevantes, priorizando coincidencias."""
    limit = max(1, min(int(limit), 50))
    query_tokens = _tokens(query)
    records: list[dict[str, Any]] = []

    try:
        if MEMORY_FILE.exists():
            with MEMORY_FILE.open("r", encoding="utf-8") as file:
                for line in file:
                    try:
                        record = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if isinstance(record, dict) and record.get("text"):
                        records.append(record)
    except OSError as exc:
        print(f"Error leyendo memoria persistente: {exc}")
        return []

    if not query_tokens:
        return records[-limit:][::-1]

    def score(record: dict[str, Any]) -> tuple[int, str]:
        text_tokens = _tokens(str(record.get("text", "")))
        matches = len(query_tokens & text_tokens)
        return matches, str(record.get("timestamp", ""))

    ranked = sorted(records, key=score, reverse=True)
    relevant = [record for record in ranked if score(record)[0] > 0]
    return (relevant or records[-limit:])[:limit]

