import os
import json
import asyncio
import base64
import hmac
import math
import re
import shutil
import tempfile
from bisect import bisect_right
from concurrent.futures import ThreadPoolExecutor
import threading
from contextlib import asynccontextmanager
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import List, Optional
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field
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
PORTFOLIO_BACKUP_DIR = PROJECT_ROOT / "storage" / "portfolio-backups"
PORTFOLIO_LOCK = threading.RLock()
CATALOG_FILE = PROJECT_ROOT / "storage" / "ticker_catalog.json"
CATALOG_LOCK = threading.Lock()
finnhub_data_client = FinnhubMarketDataClient()


def _portfolio_database_url() -> str | None:
    database_url = os.getenv("PORTFOLIO_DATABASE_URL")
    if not database_url and os.getenv("PORTFOLIO_DATABASE_REQUIRED", "").lower() == "true":
        raise RuntimeError("PORTFOLIO_DATABASE_URL is required for this deployment.")
    return database_url


def load_portfolio_data():
    with PORTFOLIO_LOCK:
        database_url = _portfolio_database_url()
        if database_url:
            import psycopg

            with psycopg.connect(database_url, connect_timeout=10) as connection:
                with connection.cursor() as cursor:
                    _ensure_portfolio_database_schema(cursor)
                    cursor.execute(
                        "SELECT positions FROM portfolio_state WHERE id = 1"
                    )
                    row = cursor.fetchone()
            return row[0] if row else []
        if os.path.exists(PORTFOLIO_FILE):
            with open(PORTFOLIO_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        return []


def load_active_portfolio_data():
    return [position for position in load_portfolio_data() if not position.get("archived")]


def _save_portfolio_data(positions: list[dict]) -> None:
    with PORTFOLIO_LOCK:
        database_url = _portfolio_database_url()
        if database_url:
            import psycopg
            from psycopg.types.json import Jsonb

            with psycopg.connect(database_url, connect_timeout=10) as connection:
                with connection.cursor() as cursor:
                    _ensure_portfolio_database_schema(cursor)
                    cursor.execute(
                        "SELECT positions FROM portfolio_state WHERE id = 1 FOR UPDATE"
                    )
                    previous = cursor.fetchone()
                    if previous:
                        cursor.execute(
                            "INSERT INTO portfolio_backups (positions) VALUES (%s)",
                            (Jsonb(previous[0]),),
                        )
                    cursor.execute(
                        """
                        INSERT INTO portfolio_state (id, positions, updated_at)
                        VALUES (1, %s, NOW())
                        ON CONFLICT (id) DO UPDATE
                        SET positions = EXCLUDED.positions, updated_at = NOW()
                        """,
                        (Jsonb(positions),),
                    )
            return

        portfolio_path = Path(PORTFOLIO_FILE)
        if portfolio_path.exists():
            PORTFOLIO_BACKUP_DIR.mkdir(parents=True, exist_ok=True)
            backup_timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
            shutil.copy2(
                portfolio_path,
                PORTFOLIO_BACKUP_DIR / f"portfolio-{backup_timestamp}.json",
            )
        temporary_path = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=portfolio_path.parent,
                prefix=".portfolio-",
                suffix=".tmp",
                delete=False,
            ) as temporary_file:
                temporary_path = Path(temporary_file.name)
                json.dump(positions, temporary_file, ensure_ascii=False, indent=4)
                temporary_file.write("\n")
            os.replace(temporary_path, portfolio_path)
        finally:
            if temporary_path and temporary_path.exists():
                temporary_path.unlink()


def _ensure_portfolio_database_schema(cursor) -> None:
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS portfolio_state (
            id SMALLINT PRIMARY KEY CHECK (id = 1),
            positions JSONB NOT NULL,
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS portfolio_backups (
            id BIGSERIAL PRIMARY KEY,
            positions JSONB NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    )


def _valid_basic_credentials(
    authorization: str | None, session_cookie: str | None = None
) -> bool:
    expected_password = os.getenv("PORTFOLIO_ACCESS_PASSWORD")
    if not expected_password:
        return os.getenv("PORTFOLIO_AUTH_REQUIRED", "").lower() != "true"
    expected_username = os.getenv("PORTFOLIO_ACCESS_USERNAME", "portfolio")
    if not authorization or not authorization.startswith("Basic "):
        authorization = f"Basic {session_cookie}" if session_cookie else None
    if not authorization:
        return False
    try:
        decoded = base64.b64decode(authorization[6:], validate=True).decode("utf-8")
    except (ValueError, UnicodeDecodeError):
        return False
    username, separator, password = decoded.partition(":")
    return bool(separator) and hmac.compare_digest(
        username.encode("utf-8"), expected_username.encode("utf-8")
    ) and hmac.compare_digest(
        password.encode("utf-8"), expected_password.encode("utf-8")
    )


market_stream_service = MarketStreamService(load_active_portfolio_data)


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

@app.middleware("http")
async def require_portfolio_credentials(request, call_next):
    if request.url.path not in {"/", "/healthz"} and not _valid_basic_credentials(
        request.headers.get("authorization"),
        request.cookies.get("portfolio_auth"),
    ):
        return JSONResponse(
            status_code=401,
            content={"detail": "Authentication required."},
            headers={"WWW-Authenticate": 'Basic realm="Portfolio Tracker"'},
        )
    response = await call_next(request)
    if request.url.path == "/dashboard" and os.getenv("PORTFOLIO_ACCESS_PASSWORD"):
        encoded_credentials = base64.b64encode(
            (
                f"{os.getenv('PORTFOLIO_ACCESS_USERNAME', 'portfolio')}:"
                f"{os.getenv('PORTFOLIO_ACCESS_PASSWORD')}"
            ).encode("utf-8")
        ).decode("ascii")
        response.set_cookie(
            "portfolio_auth",
            encoded_credentials,
            httponly=True,
            secure=(
                request.url.scheme == "https"
                or request.headers.get("x-forwarded-proto") == "https"
            ),
            samesite="strict",
            max_age=60 * 60 * 24 * 30,
            path="/",
        )
    return response
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


class NewPortfolioPosition(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    market_symbol: str = Field(min_length=1, max_length=32)
    shares: float = Field(gt=0)
    cost_basis_eur: float = Field(gt=0)
    purchase_date: date
    isin: Optional[str] = Field(default=None, max_length=24)
    display_ticker: Optional[str] = Field(default=None, max_length=32)
    finnhub_symbol: Optional[str] = Field(default=None, max_length=32)


class NewPositionPurchase(BaseModel):
    shares: float = Field(gt=0)
    cost_basis_eur: float = Field(ge=0.01)
    purchase_date: date


class UpdatePortfolioPosition(BaseModel):
    shares: float = Field(gt=0)
    cost_basis_eur: float = Field(gt=0)


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


@app.get("/healthz")
def health_check():
    if os.getenv("PORTFOLIO_DATABASE_REQUIRED", "").lower() == "true":
        load_portfolio_data()
    return {"status": "ok"}


@app.get("/dashboard", include_in_schema=False)
def dashboard():
    return FileResponse(PROJECT_ROOT / "index.html")

@app.get("/api/portfolio", response_model=List[StockPosition])
def get_portfolio():
    return load_active_portfolio_data()


@app.get("/api/portfolio/positions")
def get_managed_portfolio_positions():
    positions = load_portfolio_data()
    return {
        "active": [position for position in positions if not position.get("archived")],
        "archived": [position for position in positions if position.get("archived")],
    }


@app.post("/api/portfolio/positions", status_code=201)
async def add_portfolio_position(request: NewPortfolioPosition):
    name = request.name.strip()
    symbol = request.market_symbol.strip().upper()
    isin = request.isin.strip().upper() if request.isin else None
    display_ticker = (request.display_ticker or symbol).strip()
    finnhub_symbol = request.finnhub_symbol.strip().upper() if request.finnhub_symbol else None
    if not name or not re.fullmatch(r"[A-Z0-9][A-Z0-9.^=_-]{0,31}", symbol):
        raise HTTPException(status_code=400, detail="Enter a valid name and Yahoo Finance symbol.")
    if isin and not re.fullmatch(r"[A-Z0-9-]{4,24}", isin):
        raise HTTPException(status_code=400, detail="The optional ISIN or identifier is invalid.")
    if finnhub_symbol and not re.fullmatch(r"[A-Z0-9][A-Z0-9.:^=_-]{0,31}", finnhub_symbol):
        raise HTTPException(status_code=400, detail="The optional Finnhub symbol is invalid.")
    if not math.isfinite(request.shares) or not math.isfinite(request.cost_basis_eur):
        raise HTTPException(status_code=400, detail="Shares and cost basis must be finite numbers.")
    if request.purchase_date > datetime.now(timezone.utc).date():
        raise HTTPException(status_code=400, detail="Purchase date cannot be in the future.")

    identifier = isin or f"CUSTOM:{symbol}"
    position = {
        "name": name,
        "ticker": f"{identifier} • {display_ticker}",
        "marketSymbol": symbol,
        "shares": request.shares,
        "costBasis": round(request.cost_basis_eur, 2),
        "transactions": [
            {
                "date": request.purchase_date.isoformat(),
                "shares": request.shares,
                "cost": round(request.cost_basis_eur, 2),
            }
        ],
        "price": round(request.cost_basis_eur / request.shares, 4),
        "value": round(request.cost_basis_eur, 2),
        "gain": 0.0,
        "gainPct": 0.0,
        "allocation": 0.0,
        "badge": "bg-indigo-500",
        "init": name[:2],
    }
    if finnhub_symbol:
        position["finnhubSymbol"] = finnhub_symbol

    with PORTFOLIO_LOCK:
        positions = load_portfolio_data()
        if any(_position_isin(item).upper() == identifier for item in positions):
            raise HTTPException(
                status_code=409,
                detail="This position already exists, including in the archive. Restore it instead.",
            )
        positions.append(position)
        _save_portfolio_data(positions)
    await market_stream_service.reload_positions()
    return position


@app.post("/api/portfolio/positions/{position_id}/purchases", status_code=201)
async def add_position_purchase(position_id: str, request: NewPositionPurchase):
    normalized_id = position_id.strip().upper()
    if not math.isfinite(request.shares) or not math.isfinite(request.cost_basis_eur):
        raise HTTPException(status_code=400, detail="Shares and purchase amount must be finite numbers.")
    if request.purchase_date > datetime.now(timezone.utc).date():
        raise HTTPException(status_code=400, detail="Purchase date cannot be in the future.")

    with PORTFOLIO_LOCK:
        positions = load_portfolio_data()
        position = next(
            (item for item in positions if _position_isin(item).upper() == normalized_id),
            None,
        )
        if position is None:
            raise HTTPException(status_code=404, detail="Position not found.")
        if position.get("archived"):
            raise HTTPException(status_code=409, detail="Restore the position before adding a purchase.")
        purchase = {
            "date": request.purchase_date.isoformat(),
            "shares": request.shares,
            "cost": round(request.cost_basis_eur, 2),
        }
        position.setdefault("transactions", []).append(purchase)
        position["shares"] = float(position["shares"]) + request.shares
        position["costBasis"] = round(
            position_cost_basis(position) + request.cost_basis_eur, 2
        )
        position["price"] = round(position["costBasis"] / position["shares"], 4)
        _save_portfolio_data(positions)
    await market_stream_service.reload_positions()
    return {"status": "purchase_added", "position": position, "purchase": purchase}


@app.put("/api/portfolio/positions/{position_id}")
async def update_portfolio_position(
    position_id: str, request: UpdatePortfolioPosition
):
    normalized_id = position_id.strip().upper()
    if not math.isfinite(request.shares) or not math.isfinite(request.cost_basis_eur):
        raise HTTPException(
            status_code=400,
            detail="Shares and total invested amount must be finite numbers.",
        )
    cost_basis = round(request.cost_basis_eur, 2)
    if cost_basis < 0.01:
        raise HTTPException(
            status_code=400, detail="Total invested amount must be at least EUR 0.01."
        )

    with PORTFOLIO_LOCK:
        positions = load_portfolio_data()
        position = next(
            (item for item in positions if _position_isin(item).upper() == normalized_id),
            None,
        )
        if position is None:
            raise HTTPException(status_code=404, detail="Position not found.")
        if position.get("archived"):
            raise HTTPException(status_code=409, detail="Restore the position before editing it.")

        transactions = position.get("transactions") or []
        recorded_shares = sum(float(transaction["shares"]) for transaction in transactions)
        if transactions and recorded_shares > 0:
            average_cost = cost_basis / request.shares
            updated_transactions = []
            allocated_cost = 0.0
            allocated_shares = 0.0
            for index, transaction in enumerate(transactions):
                updated_transaction = dict(transaction)
                updated_transaction["shares"] = (
                    request.shares - allocated_shares
                    if index == len(transactions) - 1
                    else request.shares * float(transaction["shares"]) / recorded_shares
                )
                allocated_shares += updated_transaction["shares"]
                if index == len(transactions) - 1:
                    updated_transaction["cost"] = round(cost_basis - allocated_cost, 2)
                else:
                    updated_transaction["cost"] = round(
                        updated_transaction["shares"] * average_cost, 2
                    )
                    allocated_cost += updated_transaction["cost"]
                updated_transactions.append(updated_transaction)
            position["transactions"] = updated_transactions

        position["shares"] = request.shares
        position["costBasis"] = cost_basis
        position["price"] = round(cost_basis / request.shares, 4)
        _save_portfolio_data(positions)
    await market_stream_service.reload_positions()
    return {"status": "position_updated", "position": position}


@app.post("/api/portfolio/positions/{position_id}/archive")
async def archive_portfolio_position(position_id: str):
    normalized_id = position_id.strip().upper()
    with PORTFOLIO_LOCK:
        positions = load_portfolio_data()
        position = next(
            (item for item in positions if _position_isin(item).upper() == normalized_id),
            None,
        )
        if position is None:
            raise HTTPException(status_code=404, detail="Position not found.")
        if position.get("archived"):
            raise HTTPException(status_code=409, detail="Position is already archived.")
        position["archived"] = True
        position["archivedAt"] = datetime.now(timezone.utc).isoformat()
        _save_portfolio_data(positions)
    await market_stream_service.reload_positions()
    return {"status": "archived", "position": position}


@app.post("/api/portfolio/positions/{position_id}/restore")
async def restore_portfolio_position(position_id: str):
    normalized_id = position_id.strip().upper()
    with PORTFOLIO_LOCK:
        positions = load_portfolio_data()
        position = next(
            (item for item in positions if _position_isin(item).upper() == normalized_id),
            None,
        )
        if position is None:
            raise HTTPException(status_code=404, detail="Position not found.")
        if not position.get("archived"):
            raise HTTPException(status_code=409, detail="Position is already active.")
        position.pop("archived", None)
        position.pop("archivedAt", None)
        _save_portfolio_data(positions)
    await market_stream_service.reload_positions()
    return {"status": "restored", "position": position}

@app.post("/api/portfolio")
def save_portfolio(positions: List[StockPosition]):
    raise HTTPException(
        status_code=405,
        detail="Bulk portfolio replacement is disabled to prevent accidental data loss. Manage positions individually.",
    )



def _position_isin(item: dict) -> str:
    return str(item.get("ticker", "")).split("•")[0].strip()


def _position_symbol(item: dict, provider: str = "yahoo") -> str:
    isin = _position_isin(item)
    if provider.lower() == "finnhub":
        symbol = item.get("finnhubSymbol") or FINNHUB_TICKER_MAP.get(isin)
    else:
        symbol = item.get("marketSymbol") or YAHOO_TICKER_MAP.get(isin)
    if not symbol:
        provider_name = "Finnhub" if provider.lower() == "finnhub" else "Yahoo Finance"
        raise MarketDataError(f"No {provider_name} symbol is configured for {isin}")
    return str(symbol).strip().upper()


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
    data = load_active_portfolio_data()
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


def _estimated_purchase_contributions(
    portfolio: list[dict], start_timestamp: int, end_timestamp: int
) -> float:
    start_date = datetime.fromtimestamp(start_timestamp, timezone.utc).date()
    end_date = datetime.fromtimestamp(end_timestamp, timezone.utc).date()
    contributions = 0.0
    for position in portfolio:
        transactions = position.get("transactions") or []
        total_shares = sum(float(transaction["shares"]) for transaction in transactions)
        if total_shares <= 0:
            continue
        average_cost = position_cost_basis(position) / total_shares
        contributions += sum(
            float(transaction.get("cost", float(transaction["shares"]) * average_cost))
            for transaction in transactions
            if start_date < date.fromisoformat(transaction["date"]) <= end_date
        )
    return round(contributions, 2)


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

    portfolio = load_active_portfolio_data()
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
    start_date = (
        requested_start
        if asset and period != "max"
        else max(requested_start, first_transaction)
    )
    if asset and period == "max":
        start_timestamp = 0
    else:
        start_timestamp = int(
            datetime.combine(start_date, datetime.min.time(), timezone.utc).timestamp()
        )
    end_timestamp = int(now.timestamp())
    fetch_start = max(0, start_timestamp - 7 * 86400)

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

    if asset:
        symbol = asset["market_symbol"]
        currency, price_history = market_histories[symbol]
        price_timestamps = [int(point["timestamp"]) for point in price_history]
        indexed_fx = {
            fx_symbol: (
                [int(point["timestamp"]) for point in history],
                [float(point["price"]) for point in history],
            )
            for fx_symbol, history in fx_histories.items()
        }

        def historical_price_in_eur(timestamp: int) -> float | None:
            price_index = bisect_right(price_timestamps, timestamp) - 1
            if price_index < 0:
                return None
            market_price = float(price_history[price_index]["price"])
            if currency == "EUR":
                return market_price
            if currency == "JPY":
                jpy_usd = bisect_right(
                    indexed_fx[YAHOO_FX_SYMBOLS["JPY"]][0], timestamp
                ) - 1
                eur_usd = bisect_right(
                    indexed_fx[YAHOO_FX_SYMBOLS["USD"]][0], timestamp
                ) - 1
                if jpy_usd < 0 or eur_usd < 0:
                    return None
                jpy_usd_rate = indexed_fx[YAHOO_FX_SYMBOLS["JPY"]][1][jpy_usd]
                eur_usd_rate = indexed_fx[YAHOO_FX_SYMBOLS["USD"]][1][eur_usd]
                return market_price * jpy_usd_rate / eur_usd_rate if eur_usd_rate > 0 else None
            fx_symbol = YAHOO_FX_SYMBOLS.get(currency)
            if not fx_symbol or fx_symbol not in indexed_fx:
                return None
            fx_timestamps, fx_prices = indexed_fx[fx_symbol]
            fx_index = bisect_right(fx_timestamps, timestamp) - 1
            if fx_index < 0:
                return None
            fx_price = fx_prices[fx_index]
            fx_rate = 1.0 / fx_price if currency == "USD" else fx_price
            return market_price * fx_rate

        points = [
            {"timestamp": timestamp, "value": round(price, 4)}
            for timestamp in timestamps
            if (price := historical_price_in_eur(timestamp)) is not None
        ]
    else:
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
        transaction_history = sorted(
            (
                int(
                    datetime.combine(
                        date.fromisoformat(transaction["date"]),
                        datetime.min.time(),
                        timezone.utc,
                    ).timestamp()
                ),
                float(transaction["shares"]),
            )
            for transaction in asset_transactions
        )
        total_transaction_shares = sum(shares for _, shares in transaction_history)
        average_cost_per_share = (
            asset["cost_basis"] / total_transaction_shares
            if total_transaction_shares > 0
            else 0.0
        )
        transaction_timestamps = [timestamp for timestamp, _ in transaction_history]
        cumulative_shares = [0.0]
        for _, shares in transaction_history:
            cumulative_shares.append(cumulative_shares[-1] + shares)
        known_transaction_costs = sum(
            float(transaction["cost"])
            for transaction in asset_transactions
            if transaction.get("cost") is not None
        )
        legacy_transaction_shares = sum(
            float(transaction["shares"])
            for transaction in asset_transactions
            if transaction.get("cost") is None
        )
        legacy_average_cost = (
            max(asset["cost_basis"] - known_transaction_costs, 0.0)
            / legacy_transaction_shares
            if legacy_transaction_shares > 0
            else 0.0
        )
        cumulative_costs = [0.0]
        for transaction in sorted(
            asset_transactions,
            key=lambda item: date.fromisoformat(item["date"]),
        ):
            transaction_cost = transaction.get("cost")
            if transaction_cost is None:
                transaction_cost = float(transaction["shares"]) * legacy_average_cost
            cumulative_costs.append(cumulative_costs[-1] + float(transaction_cost))
        investment_points = []
        for point in points:
            timestamp = int(point["timestamp"])
            transaction_index = bisect_right(transaction_timestamps, timestamp)
            held_shares = cumulative_shares[transaction_index]
            if held_shares <= 0:
                continue
            position_value = float(point["value"]) * held_shares
            estimated_cost_basis = cumulative_costs[transaction_index]
            investment_points.append(
                {
                    "timestamp": timestamp,
                    "value": round(position_value - estimated_cost_basis, 2),
                    "position_value": round(position_value, 2),
                    "estimated_cost_basis": round(estimated_cost_basis, 2),
                    "shares": held_shares,
                }
            )
        if not investment_points:
            raise HTTPException(
                status_code=503,
                detail="No investment history is available for this position and period.",
            )
        asset["shares"] = sum(
            float(transaction["shares"])
            for transaction in asset_transactions
            if date.fromisoformat(transaction["date"]) <= current_date
        )
        asset["last_price"] = last_value
        asset["last_value"] = round(last_value * asset["shares"], 2)
        asset["unrealized_gain"] = round(
            asset["last_value"] - asset["cost_basis"], 2
        )
        asset["unrealized_gain_pct"] = (
            round((asset["last_value"] / asset["cost_basis"] - 1) * 100, 2)
            if asset["cost_basis"]
            else 0.0
        )
        asset["period_start_value"] = round(
            float(points[0]["value"])
            * sum(
                float(transaction["shares"])
                for transaction in asset_transactions
                if date.fromisoformat(transaction["date"])
                <= datetime.fromtimestamp(int(points[0]["timestamp"]), timezone.utc).date()
            ),
            2,
        )
        asset["period_end_value"] = round(
            float(points[-1]["value"]) * asset["shares"], 2
        )
        investment_start_value = asset["period_start_value"]
        investment_end_value = asset["period_end_value"]
    else:
        investment_start_value = first_value
        investment_end_value = last_value

    contributions = _estimated_purchase_contributions(
        selected_positions, int(points[0]["timestamp"]), int(points[-1]["timestamp"])
    )
    starting_capital = investment_start_value + contributions
    investment_gain = round(
        investment_end_value - investment_start_value - contributions, 2
    )
    investment_summary = {
        "start_value": investment_start_value,
        "end_value": investment_end_value,
        "estimated_contributions": contributions,
        "gain": investment_gain,
        "gain_pct": round(investment_gain / starting_capital * 100, 2)
        if starting_capital
        else 0.0,
    }
    if asset:
        asset["period_gain"] = investment_gain
        asset["period_gain_pct"] = investment_summary["gain_pct"]

    return {
        "period": period,
        "currency": "EUR",
        "available_from": first_transaction.isoformat(),
        "asset": asset,
        "summary": summary,
        "investment_summary": investment_summary,
        "points": points,
        "note": (
            "Historical per-share prices are converted to EUR using historical "
            "exchange rates. Your purchases and cost basis do not change this price chart."
            if asset
            else
            "Historical market value is reconstructed from recorded purchases and "
            "Yahoo Finance prices. Cash balance is excluded."
        ),
        **({"investment_points": investment_points} if asset else {}),
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
    if not _valid_basic_credentials(
        websocket.headers.get("authorization"),
        websocket.cookies.get("portfolio_auth"),
    ):
        await websocket.close(code=1008, reason="Authentication required.")
        return
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
