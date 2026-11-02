import os
import json
import asyncio
from bisect import bisect_right
from concurrent.futures import ThreadPoolExecutor
import re
import threading
from contextlib import asynccontextmanager
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import List, Optional
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from google import generativeai as genai
from .config import load_configuration
from .market_data import (
    MarketDataError,
    YAHOO_FX_SYMBOLS,
    market_data_client,
    YAHOO_TICKER_MAP,
)
from .finnhub_client import FinnhubMarketDataClient, FINNHUB_TICKER_MAP
from .market_agents import position_cost_basis
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
    costBasis: Optional[float] = None
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
        raise MarketDataError(f"No market ticker is configured for {isin}")
    return symbol


def _calculate_realtime_position(item: dict, provider: str = "yahoo") -> dict:
    symbol = _position_symbol(item, provider)
    client = finnhub_data_client if provider.lower() == "finnhub" else market_data_client
    quote = client.get_quote(symbol)
    fx_to_eur = client.get_fx_rate(quote.currency)
    price_eur = quote.price * fx_to_eur

    shares = float(item["shares"])
    new_value = price_eur * shares
    initial_cost = position_cost_basis(item)
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
        raise HTTPException(status_code=400, detail="Invalid provider: use yahoo or finnhub")
    data = load_portfolio_data()
    try:
        updated_items = [_calculate_realtime_position(item, provider) for item in data]
    except MarketDataError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    total_value = sum(float(item["value"]) for item in updated_items)
    for item in updated_items:
        item["allocation"] = round(float(item["value"]) / total_value * 100, 2) if total_value else 0.0

    return updated_items


def _historical_portfolio_value(
    portfolio: list[dict],
    market_histories: dict[str, tuple[str, list[dict[str, float | int]]]],
    fx_histories: dict[str, list[dict[str, float | int]]],
    timestamps: list[int],
) -> list[dict[str, float | int]]:
    indexed_histories = {}
    for symbol, (currency, points) in market_histories.items():
        indexed_histories[symbol] = (
            currency,
            [int(point["timestamp"]) for point in points],
            [float(point["price"]) for point in points],
        )
    indexed_fx = {
        symbol: (
            [int(point["timestamp"]) for point in points],
            [float(point["price"]) for point in points],
        )
        for symbol, points in fx_histories.items()
    }

    def latest_value(
        values: tuple[list[int], list[float]], timestamp: int
    ) -> float | None:
        index = bisect_right(values[0], timestamp) - 1
        return values[1][index] if index >= 0 else None

    result = []
    for timestamp in timestamps:
        day = datetime.fromtimestamp(timestamp, timezone.utc).date()
        total = 0.0
        for position in portfolio:
            symbol = _position_symbol(position)
            transactions = position.get("transactions") or []
            shares = sum(
                float(transaction["shares"])
                for transaction in transactions
                if date.fromisoformat(transaction["date"]) <= day
            )
            if shares <= 0 or symbol not in indexed_histories:
                continue

            currency, quote_timestamps, prices = indexed_histories[symbol]
            price_index = bisect_right(quote_timestamps, timestamp) - 1
            if price_index < 0:
                continue
            market_price = prices[price_index]

            if currency == "EUR":
                fx_rate = 1.0
            elif currency == "JPY":
                jpy_usd_symbol = YAHOO_FX_SYMBOLS["JPY"]
                eur_usd_symbol = YAHOO_FX_SYMBOLS["USD"]
                jpy_usd = latest_value(indexed_fx[jpy_usd_symbol], timestamp)
                eur_usd = latest_value(indexed_fx[eur_usd_symbol], timestamp)
                if jpy_usd is None or eur_usd is None or eur_usd <= 0:
                    continue
                fx_rate = jpy_usd / eur_usd
            else:
                fx_symbol = YAHOO_FX_SYMBOLS.get(currency)
                if not fx_symbol or fx_symbol not in indexed_fx:
                    continue
                fx_quote = latest_value(indexed_fx[fx_symbol], timestamp)
                if fx_quote is None:
                    continue
                fx_rate = 1.0 / fx_quote if currency == "USD" else fx_quote
            total += market_price * fx_rate * shares
        result.append({"timestamp": timestamp, "value": round(total, 2)})
    return result


@app.get("/api/portfolio/history")
def get_portfolio_history(period: str = "1m", isin: str | None = None):
    periods = {
        "1d": (timedelta(days=1), "5m"),
        "1w": (timedelta(days=7), "30m"),
        "1m": (timedelta(days=31), "1d"),
        "1y": (timedelta(days=365), "1d"),
        "ytd": (None, "1d"),
        "max": (None, "1d"),
    }
    if period not in periods:
        raise HTTPException(
            status_code=400,
            detail="Unsupported period. Use 1d, 1w, 1m, 1y, ytd, or max.",
        )

    portfolio = load_portfolio_data()
    if not portfolio:
        raise HTTPException(status_code=404, detail="The portfolio has no positions.")

    selected_positions = portfolio
    asset = None
    if isin:
        normalized_isin = isin.strip().upper()
        selected_positions = [
            position
            for position in portfolio
            if _position_isin(position).upper() == normalized_isin
        ]
        if not selected_positions:
            raise HTTPException(status_code=404, detail="The requested position was not found.")
        selected_position = selected_positions[0]
        asset = {
            "name": selected_position.get("name", normalized_isin),
            "isin": normalized_isin,
            "cost_basis": position_cost_basis(selected_position),
        }

    transactions_by_symbol = {}
    try:
        for position in selected_positions:
            transactions = position.get("transactions") or []
            if not transactions:
                raise MarketDataError(
                    f"Purchase history is missing for {_position_isin(position)}"
                )
            for transaction in transactions:
                date.fromisoformat(transaction["date"])
                float(transaction["shares"])
            transactions_by_symbol[_position_symbol(position)] = transactions
    except (KeyError, TypeError, ValueError, MarketDataError) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    if asset:
        asset["market_symbol"] = next(iter(transactions_by_symbol))

    first_transaction = min(
        date.fromisoformat(transaction["date"])
        for transactions in transactions_by_symbol.values()
        for transaction in transactions
    )
    now = datetime.now(timezone.utc)
    window, interval = periods[period]
    if period == "ytd":
        requested_start = date(now.year, 1, 1)
    elif period == "max":
        requested_start = first_transaction
    else:
        requested_start = (now - window).date()
    start_date = max(requested_start, first_transaction)
    start_timestamp = int(
        datetime.combine(start_date, datetime.min.time(), timezone.utc).timestamp()
    )
    end_timestamp = int(now.timestamp())
    fetch_start = max(
        int(datetime.combine(first_transaction, datetime.min.time(), timezone.utc).timestamp()),
        start_timestamp - 7 * 86400,
    )

    symbols = list(transactions_by_symbol)
    try:
        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = {
                symbol: executor.submit(
                    market_data_client.get_history,
                    symbol,
                    fetch_start,
                    end_timestamp,
                    interval,
                )
                for symbol in symbols
            }
            market_histories = {symbol: future.result() for symbol, future in futures.items()}

        currencies = {currency for currency, _ in market_histories.values()}
        fx_symbols = set()
        for currency in currencies:
            if currency == "JPY":
                fx_symbols.update((YAHOO_FX_SYMBOLS["JPY"], YAHOO_FX_SYMBOLS["USD"]))
            elif currency != "EUR":
                fx_symbol = YAHOO_FX_SYMBOLS.get(currency)
                if fx_symbol:
                    fx_symbols.add(fx_symbol)
                else:
                    raise MarketDataError(f"No historical currency conversion is available for {currency}")

        with ThreadPoolExecutor(max_workers=8) as executor:
            fx_futures = {
                symbol: executor.submit(
                    market_data_client.get_history,
                    symbol,
                    fetch_start,
                    end_timestamp,
                    interval,
                )
                for symbol in fx_symbols
            }
            fx_histories = {
                symbol: future.result()[1] for symbol, future in fx_futures.items()
            }
    except MarketDataError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    timestamps = sorted(
        {
            int(point["timestamp"])
            for _, points in market_histories.values()
            for point in points
            if start_timestamp <= int(point["timestamp"]) <= end_timestamp
        }
    )
    if not timestamps:
        raise HTTPException(
            status_code=503,
            detail="Yahoo Finance returned no historical prices for the selected period.",
        )

    points = _historical_portfolio_value(
        selected_positions, market_histories, fx_histories, timestamps
    )
    points = [point for point in points if float(point["value"]) > 0]
    if not points:
        raise HTTPException(
            status_code=503,
            detail="No portfolio value could be calculated for the selected period.",
        )
    first_value = float(points[0]["value"])
    last_value = float(points[-1]["value"])
    highest_point = max(points, key=lambda point: float(point["value"]))
    lowest_point = min(points, key=lambda point: float(point["value"]))
    summary = {
        "start_value": first_value,
        "end_value": last_value,
        "change": round(last_value - first_value, 2),
        "change_pct": round((last_value / first_value - 1) * 100, 2) if first_value else 0.0,
        "high": float(highest_point["value"]),
        "high_timestamp": int(highest_point["timestamp"]),
        "low": float(lowest_point["value"]),
        "low_timestamp": int(lowest_point["timestamp"]),
    }
    if asset:
        current_date = now.date()
        asset_transactions = transactions_by_symbol[asset["market_symbol"]]
        asset["shares"] = sum(
            float(transaction["shares"])
            for transaction in asset_transactions
            if date.fromisoformat(transaction["date"]) <= current_date
        )
        asset["last_value"] = last_value
        asset["unrealized_gain"] = round(last_value - asset["cost_basis"], 2)
        asset["unrealized_gain_pct"] = (
            round((last_value / asset["cost_basis"] - 1) * 100, 2)
            if asset["cost_basis"]
            else 0.0
        )

    return {
        "period": period,
        "currency": "EUR",
        "available_from": first_transaction.isoformat(),
        "asset": asset,
        "summary": summary,
        "points": points,
        "note": (
            "Historical market value is reconstructed from recorded purchases and "
            "Yahoo Finance prices. Cash balance is excluded."
        ),
    }


@app.get("/api/catalog")
def get_ticker_catalog(exchange: str = "US"):
    exchange = exchange.strip().upper()
    if not re.fullmatch(r"[A-Z0-9._-]{1,10}", exchange):
        raise HTTPException(status_code=400, detail="Invalid market symbol")
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
        raise HTTPException(status_code=400, detail="Invalid market symbol")
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
            detail="Could not read the local ticker catalog",
        ) from exc

    if not isinstance(store, dict):
        raise HTTPException(status_code=500, detail="The local ticker catalog is invalid")
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
