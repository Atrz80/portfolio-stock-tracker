import json
import urllib.request

agents = {
    "analyst": "Validate push price and timestamp validation design.",
    "architect": "Assess WebSocket push resilience, heartbeat, and reconnection.",
    "optimizer": "Review per-tick value, P&L, and allocation calculations.",
}
for agent, objective in agents.items():
    payload = json.dumps({"objective": objective, "agente_tipo": agent, "modo": "direct"}).encode("utf-8")
    request = urllib.request.Request(
        "http://127.0.0.1:8000/agency/run",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=120) as response:
        result = json.load(response)
    print(f"AGENT={agent}|STATUS={result.get('status')}|USED={result.get('agente_usado')}|LENGTH={len(str(result.get('result', '')))}")
    if result.get("status") != "success" or result.get("agente_usado") != agent:
        raise SystemExit(1)