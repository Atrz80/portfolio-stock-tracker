import os
import json
import asyncio
import re
import threading
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from google import generativeai as genai
from .config import load_configuration
from .market_data import MarketDataError, market_data_client, YAHOO_TICKER_MAP
from .finnhub_client import FinnhubMarketDataClient, FINNHUB_TICKER_MAP

from .market_stream import MarketStreamService

load_configuration()
api_key = os.getenv("GOOGLE_API_KEY")
if api_key:
    genai.configure(api_key=api_key)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PORTFOLIO_FILE = str(PROJECT_ROOT / "portfolio.json")
CATALOG_FILE = PROJECT_ROOT / "storage" / "ticker_catalog.json"
CATALOG_LOCK = threading.Lock()
finnhub_data_client = FinnhubMarketDataClient()

def load_portfolio_data():
    if os.path.exists(PORTFOLIO_FILE):
        with open(PORTFOLIO_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


market_stream_service = MarketStreamService(load_portfolio_data)


@asynccontextmanager
async def lifespan(_: FastAPI):
    await market_stream_service.start()
    try:
        yield
    finally:
        await market_stream_service.stop()


app = FastAPI(
    title="Portfolio Stock Tracker & Live Web API",
    version="3.0.0",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
class StockPosition(BaseModel):
    name: str
    ticker: str
    shares: float
    price: float
    value: float
    gain: float
    gainPct: float
    allocation: float
    badge: str
    init: str

@app.get("/")
def read_root():
    return {
        "status": "online",
        "market_data_source": "Yahoo Finance",
        "market_data_mode": "websocket_push",
        "portfolio_currency": "EUR",
        "dashboard": "/dashboard",
        "stream": "/ws/market",
    }


@app.get("/dashboard", include_in_schema=False)
def dashboard():
    return FileResponse(PROJECT_ROOT / "index.html")

@app.get("/api/portfolio", response_model=List[StockPosition])
def get_portfolio():
    return load_portfolio_data()

@app.post("/api/portfolio")
def save_portfolio(positions: List[StockPosition]):
    with open(PORTFOLIO_FILE, "w", encoding="utf-8") as f:
        json.dump([p.dict() for p in positions], f, ensure_ascii=False, indent=4)
    return {"status": "success"}



def _position_isin(item: dict) -> str:
    return str(item.get("ticker", "")).split("•")[0].strip()


def _position_symbol(item: dict, provider: str = "yahoo") -> str:
    isin = _position_isin(item)
    ticker_map = FINNHUB_TICKER_MAP if provider.lower() == "finnhub" else YAHOO_TICKER_MAP
    symbol = ticker_map.get(isin) or YAHOO_TICKER_MAP.get(isin)
    if not symbol:
        raise MarketDataError(f"No existe un ticker de mercado configurado para {isin}")
    return symbol


def _calculate_realtime_position(item: dict, provider: str = "yahoo") -> dict:
    symbol = _position_symbol(item, provider)
    client = finnhub_data_client if provider.lower() == "finnhub" else market_data_client
    quote = client.get_quote(symbol)
    fx_to_eur = client.get_fx_rate(quote.currency)
    price_eur = quote.price * fx_to_eur

    shares = float(item["shares"])
    new_value = price_eur * shares
    stored_price_eur = float(item["price"])
    stored_gain = float(item.get("gain", 0.0))
    initial_cost = stored_price_eur * shares - stored_gain
    new_gain = new_value - initial_cost
    new_gain_pct = (new_gain / initial_cost * 100) if initial_cost else 0.0

    result = dict(item)
    result.update(
        {
            "price": round(price_eur, 4),
            "value": round(new_value, 2),
            "gain": round(new_gain, 2),
            "gainPct": round(new_gain_pct, 2),
            "marketSymbol": symbol,
            "marketPrice": round(quote.price, 4),
            "marketCurrency": quote.currency,
            "previousClose": quote.previous_close,
            "changePercent": quote.change_percent,
            "quoteTimestamp": quote.timestamp_iso,
            "dataSource": quote.source,
            "dataStatus": "real",
        }
    )
    return result


@app.get("/api/portfolio/realtime")
def get_realtime_portfolio(provider: str = "yahoo"):
    provider = provider.strip().lower()
    if provider not in {"yahoo", "finnhub"}:
        raise HTTPException(status_code=400, detail="Proveedor no válido: usa yahoo o finnhub")
    data = load_portfolio_data()
    try:
        updated_items = [_calculate_realtime_position(item, provider) for item in data]
    except MarketDataError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    total_value = sum(float(item["value"]) for item in updated_items)
    for item in updated_items:
        item["allocation"] = round(float(item["value"]) / total_value * 100, 2) if total_value else 0.0

    return updated_items


@app.get("/api/catalog")
def get_ticker_catalog(exchange: str = "US"):
    exchange = exchange.strip().upper()
    if not re.fullmatch(r"[A-Z0-9._-]{1,10}", exchange):
        raise HTTPException(status_code=400, detail="Código de mercado no válido")
    store = _read_ticker_catalog_store()
    entry = store.get("exchanges", {}).get(exchange, {})
    return {
        "exchange": exchange,
        "symbols": entry.get("symbols", []),
        "updated_at": entry.get("updated_at"),
    }


@app.post("/api/catalog/refresh")
def refresh_ticker_catalog(exchange: str = "US"):
    exchange = exchange.strip().upper()
    if not re.fullmatch(r"[A-Z0-9._-]{1,10}", exchange):
        raise HTTPException(status_code=400, detail="Código de mercado no válido")
    try:
        symbols = finnhub_data_client.get_ticker_catalog(exchange)
    except MarketDataError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    with CATALOG_LOCK:
        store = _read_ticker_catalog_store()
        store.setdefault("exchanges", {})[exchange] = {
            "symbols": symbols,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        CATALOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        temporary_file = CATALOG_FILE.with_suffix(".tmp")
        temporary_file.write_text(
            json.dumps(store, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temporary_file.replace(CATALOG_FILE)

    return {"status": "success", "exchange": exchange, **store["exchanges"][exchange]}


def _read_ticker_catalog_store() -> dict:
    if not CATALOG_FILE.exists():
        return {"exchanges": {}}
    try:
        store = json.loads(CATALOG_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise HTTPException(
            status_code=500,
            detail="No se pudo leer el catálogo local de tickers",
        ) from exc

    if not isinstance(store, dict):
        raise HTTPException(status_code=500, detail="El catálogo local de tickers no es válido")
    if isinstance(store.get("exchanges"), dict):
        return store

    legacy_symbols = store.get("finnhub")
    if isinstance(legacy_symbols, dict):
        migrated_symbols = [
            {
                "symbol": symbol,
                "displaySymbol": symbol,
                "description": isin,
                "type": "",
                "exchange": "US",
            }
            for isin, symbol in legacy_symbols.items()
        ]
        return {
            "exchanges": {
                "US": {
                    "symbols": migrated_symbols,
                    "updated_at": store.get("updated_at"),
                }
            }
        }
    return {"exchanges": {}}



@app.get("/api/market/status")
def get_market_status():
    return market_stream_service.status()


@app.websocket("/ws/market")
async def market_websocket(websocket: WebSocket):
    await websocket.accept()
    queue = market_stream_service.subscribe()
    try:
        await websocket.send_json(market_stream_service.snapshot())
        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=10)
            except asyncio.TimeoutError:
                event = {
                    "type": "stream_status",
                    "health": market_stream_service.status(),
                }
            await websocket.send_json(event)
    except WebSocketDisconnect:
        pass
    finally:
        market_stream_service.unsubscribe(queue)

from .agent_memory import remember, recall
from .agency import run_agency_task
from .chat import chat_with_memory

class MemoryRequest(BaseModel):
    text: str
    source: Optional[str] = "api_user"

class RecallRequest(BaseModel):
    query: str
    limit: Optional[int] = 5

class AgencyRequest(BaseModel):
    objective: str
    agente_tipo: Optional[str] = "analyst"
    modo: Optional[str] = None

class ChatRequest(BaseModel):
    message: str

@app.post("/memory/remember")
def api_remember(req: MemoryRequest):
    return remember(req.text, req.source)

@app.post("/memory/recall")
def api_recall(req: RecallRequest):
    return {"results": recall(req.query, req.limit)}

@app.post("/agency/run")
def api_agency_run(req: AgencyRequest):
    return run_agency_task(req.objective, req.agente_tipo, req.modo)

@app.post("/chat")
def api_chat(req: ChatRequest):
    reply = chat_with_memory(req.message)
    return {"response": reply}

@app.get("/api/google/profile")
def google_user_profile():
    return {
        "status": "configured" if api_key else "not_configured",
        "provider": "google_generativeai",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
