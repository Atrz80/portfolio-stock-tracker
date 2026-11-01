"""Verifica un pricing push real de Yahoo Finance.

``BTC-USD`` se usa como referencia líquida 24/7 para certificar que el
transporte WebSocket entrega cambios reales. Los activos del portfolio pueden
estar cerrados y no emitir ticks durante una ventana concreta.
"""

from __future__ import annotations

import asyncio
import json
import sys
import time
from pathlib import Path

import websockets

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.market_protocol import decode_yahoo_pricing  # noqa: E402


async def check(symbol: str = "BTC-USD", timeout_seconds: int = 30) -> int:
    prices: list[float] = []
    deadline = time.monotonic() + timeout_seconds
    async with websockets.connect(
        "wss://streamer.finance.yahoo.com/?version=2", open_timeout=15
    ) as websocket:
        await websocket.send(json.dumps({"subscribe": [symbol]}))
        while time.monotonic() < deadline:
            try:
                raw = await asyncio.wait_for(websocket.recv(), timeout=5)
            except asyncio.TimeoutError:
                continue
            outer = json.loads(raw)
            if not outer.get("message"):
                continue
            quote = decode_yahoo_pricing(outer["message"])
            if quote["symbol"] != symbol or quote["price"] <= 0:
                continue
            prices.append(quote["price"])
            print(
                f"PUSH symbol={quote['symbol']} price={quote['price']} "
                f"timestamp={quote['timestamp_iso']} change={quote['change_percent']}"
            )
            if len(prices) >= 2:
                break
    if len(prices) < 2:
        print(f"PUSH_INSUFFICIENT={len(prices)}")
        return 1
    print(f"PUSH_REAL_EVENTS={len(prices)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(check()))
