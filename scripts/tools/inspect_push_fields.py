import asyncio, json
import sys
from pathlib import Path
import websockets
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from app.market_protocol import decode_yahoo_pricing

async def main():
    symbols=['VWRA.L','SEMI.AS','UST.PA','EIMI.L','6701.T','4204.T','IUSN.DE','5016.T','EURUSD=X','JPYUSD=X']
    async with websockets.connect('wss://streamer.finance.yahoo.com/?version=2', open_timeout=15) as ws:
        await ws.send(json.dumps({'subscribe':symbols}))
        for _ in range(20):
            try:
                raw=await asyncio.wait_for(ws.recv(), timeout=5)
            except asyncio.TimeoutError:
                continue
            outer=json.loads(raw)
            if not outer.get('message'):
                continue
            try:
                print(decode_yahoo_pricing(outer['message']))
            except Exception as exc:
                print('ERROR',repr(exc))
asyncio.run(main())