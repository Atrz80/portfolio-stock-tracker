import asyncio
import json
import websockets


async def main() -> int:
    async with websockets.connect("ws://127.0.0.1:8000/ws/market", open_timeout=10) as socket:
        snapshot = json.loads(await asyncio.wait_for(socket.recv(), timeout=10))
        assert snapshot["type"] == "snapshot"
        assert len(snapshot["positions"]) == 8
        symbols = [item["marketSymbol"] for item in snapshot["positions"]]
        assert len(symbols) == len(set(symbols))
        print(f"SNAPSHOT_TYPE={snapshot['type']}")
        print(f"SNAPSHOT_POSITIONS={len(snapshot['positions'])}")
        print(f"SNAPSHOT_SYMBOLS={','.join(symbols)}")
        print(f"STREAM_HEALTH={snapshot['health']['state']}/{snapshot['health']['delivery']}")
        print(f"TOTAL_EUR={snapshot['totals']['value']}")
    return 0


raise SystemExit(asyncio.run(main()))