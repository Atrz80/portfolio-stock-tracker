import os
import json
from pathlib import Path
from typing import List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from google import generativeai as genai
from .config import load_configuration
from .market_data import MarketDataError, market_data_client

load_configuration()
api_key = os.getenv("GOOGLE_API_KEY")
if api_key:
    genai.configure(api_key=api_key)

app = FastAPI(title="Portfolio Stock Tracker & Live Web API", version="2.2.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PORTFOLIO_FILE = str(PROJECT_ROOT / "portfolio.json")

def load_portfolio_data():
    if os.path.exists(PORTFOLIO_FILE):
        with open(PORTFOLIO_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

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
        "market_data_mode": "real",
        "portfolio_currency": "EUR",
        "dashboard": "/dashboard",
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

YAHOO_TICKER_MAP = {
    "IE00BK5BQT80": "VWRA.L",
    "IE000I8KRLL9": "SEMI.AS",
    "LU1829221024": "UST.PA",
    "IE00BKM4GZ66": "EIMI.L",
    "JP3733000008": "6701.T",
    "JP3419400001": "4204.T",
    "IE00B4RFH31": "IUSN.DE",
    "JP3379550001": "5016.T",
}


def _position_isin(item: dict) -> str:
    return str(item.get("ticker", "")).split("•")[0].strip()


def _position_symbol(item: dict) -> str:
    isin = _position_isin(item)
    symbol = YAHOO_TICKER_MAP.get(isin)
    if not symbol:
        raise MarketDataError(f"No existe un ticker de mercado configurado para {isin}")
    return symbol


def _calculate_realtime_position(item: dict) -> dict:
    symbol = _position_symbol(item)
    quote = market_data_client.get_quote(symbol)
    fx_to_eur = market_data_client.get_fx_rate(quote.currency)
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
def get_realtime_portfolio():
    data = load_portfolio_data()
    try:
        updated_items = [_calculate_realtime_position(item) for item in data]
    except MarketDataError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    total_value = sum(float(item["value"]) for item in updated_items)
    total_cost = sum(
        float(item["price"]) * float(item["shares"]) - float(item.get("gain", 0.0))
        for item in data
    )
    for item in updated_items:
        item["allocation"] = round(float(item["value"]) / total_value * 100, 2) if total_value else 0.0

    return updated_items


@app.get("/api/market/status")
def get_market_status():
    return {
        "status": "online",
        "provider": "Yahoo Finance",
        "endpoint": "/v8/finance/chart",
        "mode": "real",
        "cache_seconds": market_data_client.cache_seconds,
        "portfolio_currency": "EUR",
    }

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
    return run_agency_task(req.objective)

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
