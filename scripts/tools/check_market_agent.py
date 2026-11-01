"""Valida un agente CrewAI concreto contra el gateway local."""

from __future__ import annotations

import json
import sys
import time
import urllib.request

OBJECTIVES = {
    "analyst": "Valida el diseño de validación de precios push y timestamp.",
    "architect": "Diagnostica la resiliencia del WebSocket push, heartbeat y reconexión.",
    "optimizer": "Revisa el cálculo individual de valor, P&L y asignación por cada tick.",
}


def main() -> int:
    if len(sys.argv) != 2 or sys.argv[1] not in OBJECTIVES:
        print(f"Uso: {sys.argv[0]} <analyst|architect|optimizer>")
        return 2
    agent = sys.argv[1]
    payload = json.dumps(
        {
            "objective": OBJECTIVES[agent],
            "agente_tipo": agent,
            "modo": "direct",
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        "http://127.0.0.1:8000/agency/run",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    for attempt in range(1, 3):
        try:
            with urllib.request.urlopen(request, timeout=150) as response:
                result = json.load(response)
            print(f"AGENT={agent}|ATTEMPT={attempt}|STATUS={result.get('status')}|USED={result.get('agente_usado')}|LENGTH={len(str(result.get('result', '')))}")
            if result.get("status") == "success" and result.get("agente_usado") == agent:
                return 0
            print(f"AGENT_ERROR={agent}|{result.get('message')}")
        except Exception as exc:
            print(f"AGENT_REQUEST_ERROR={agent}|{exc}")
        time.sleep(2)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
