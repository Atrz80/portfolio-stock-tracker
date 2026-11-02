"""Yahoo push stream, portfolio state and incremental browser delivery."""

from __future__ import annotations

import asyncio
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable

import websockets

from .market_agents import analyst_validate_tick, optimizer_calculate_position
from .market_data import (
    MarketDataError,
    Quote,
    YAHOO_FX_SYMBOLS,
    YAHOO_TICKER_MAP,
    market_data_client,
)
from .market_protocol import decode_yahoo_pricing

YAHOO_STREAM_URL = "wss://streamer.finance.yahoo.com/?version=2"
HEARTBEAT_SECONDS = 15
RECONNECT_MAX_SECONDS = 30


@dataclass
class StreamHealth:
    provider: str = "Yahoo Finance"
    transport: str = "websocket"
    delivery: str = "push"
    state: str = "disconnected"
    connected_at: str | None = None
    last_event_at: str | None = None
    last_error: str | None = None
    rejected_events: int = 0
    last_rejected_event_at: str | None = None
    reconnect_attempts: int = 0
    subscribed_symbols: list[str] | None = None

    def public_dict(self) -> dict[str, Any]:
        result = asdict(self)
        if result["last_event_at"]:
            try:
                event_time = datetime.fromisoformat(result["last_event_at"])
                result["last_event_age_seconds"] = round(
                    (datetime.now(timezone.utc) - event_time).total_seconds(), 2
                )
            except ValueError:
                pass
        return result


class YahooStreamClient:
    """Yahoo WebSocket client with heartbeat and exponential reconnect."""

    def __init__(
        self,
        symbols: list[str],
        on_quote: Callable[[dict[str, Any]], Awaitable[None]],
        health: StreamHealth,
    ) -> None:
        self.symbols = sorted(set(symbols))
        self.on_quote = on_quote
        self.health = health
        self._task: asyncio.Task | None = None
        self._stop = asyncio.Event()

    def start(self) -> None:
        if self._task and not self._task.done():
            return
        self._stop.clear()
        self._task = asyncio.create_task(self._run(), name="yahoo-market-stream")

    async def stop(self) -> None:
        self._stop.set()
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        self.health.state = "stopped"
        self.health.subscribed_symbols = None

    async def _run(self) -> None:
        attempt = 0
        while not self._stop.is_set():
            try:
                attempt += 1
                self.health.reconnect_attempts = attempt
                self.health.state = "connecting"
                async with websockets.connect(
                    YAHOO_STREAM_URL,
                    open_timeout=15,
                    close_timeout=5,
                    ping_interval=20,
                    ping_timeout=20,
                    max_size=2**20,
                ) as websocket:
                    await websocket.send(json.dumps({"subscribe": self.symbols}))
                    self.health.state = "connected"
                    self.health.connected_at = datetime.now(timezone.utc).isoformat()
                    self.health.last_error = None
                    self.health.subscribed_symbols = list(self.symbols)
                    self.health.reconnect_attempts = 0
                    attempt = 0
                    heartbeat = asyncio.create_task(
                        self._heartbeat(websocket), name="yahoo-stream-heartbeat"
                    )
                    try:
                        async for raw_message in websocket:
                            if self._stop.is_set():
                                break
                            await self._handle_message(raw_message)
                    finally:
                        heartbeat.cancel()
                        try:
                            await heartbeat
                        except asyncio.CancelledError:
                            pass
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                self.health.state = "disconnected"
                self.health.last_error = str(exc)
                self.health.subscribed_symbols = None
                delay = min(2 ** min(attempt, 5), RECONNECT_MAX_SECONDS)
                try:
                    await asyncio.wait_for(self._stop.wait(), timeout=delay)
                except asyncio.TimeoutError:
                    pass

    async def _heartbeat(self, websocket) -> None:
        while not self._stop.is_set():
            await asyncio.sleep(HEARTBEAT_SECONDS)
            await websocket.send(json.dumps({"subscribe": self.symbols}))

    async def _handle_message(self, raw_message: str) -> None:
        try:
            outer = json.loads(raw_message)
            encoded = outer.get("message")
            if not encoded:
                return
            quote = decode_yahoo_pricing(encoded)
        except (MarketDataError, json.JSONDecodeError) as exc:
            self.health.last_error = str(exc)
            return
        await self.on_quote(quote)


class MarketStreamService:
    """Maintain portfolio state and distribute one event per changed symbol."""

    def __init__(self, portfolio_loader: Callable[[], list[dict[str, Any]]]) -> None:
        self.portfolio_loader = portfolio_loader
        self.health = StreamHealth()
        self._positions: dict[str, dict[str, Any]] = {}
        self._quotes: dict[str, Quote] = {}
        self._subscribers: set[asyncio.Queue[dict[str, Any]]] = set()
        self._client: YahooStreamClient | None = None
        self._started = False
        self._last_event_by_symbol: dict[str, str] = {}

    @property
    def stream_symbols(self) -> list[str]:
        symbols = {
            position.get("marketSymbol")
            or YAHOO_TICKER_MAP.get(self._position_isin(position), "")
            for position in self.portfolio_loader()
        }
        currencies = {
            quote.currency
            for symbol, quote in self._quotes.items()
            if symbol in symbols and quote.currency != "EUR"
        }
        symbols.update(
            YAHOO_FX_SYMBOLS[currency]
            for currency in currencies
            if currency in YAHOO_FX_SYMBOLS
        )
        return sorted(symbol for symbol in symbols if symbol)

    @staticmethod
    def _position_isin(position: dict[str, Any]) -> str:
        return str(position.get("ticker", "")).split("•")[0].strip()

    def _position_symbol(self, position: dict[str, Any]) -> str:
        isin = self._position_isin(position)
        symbol = position.get("marketSymbol") or YAHOO_TICKER_MAP.get(isin)
        if not symbol:
            raise MarketDataError(f"No market ticker is configured for {isin}")
        return symbol

    async def start(self) -> None:
        if self._started:
            return
        self._started = True
        self._positions = {self._position_symbol(item): item for item in self.portfolio_loader()}
        await self._load_snapshot()
        self._client = YahooStreamClient(
            symbols=self.stream_symbols,
            on_quote=self._on_quote,
            health=self.health,
        )
        self._client.start()

    async def stop(self) -> None:
        if self._client:
            await self._client.stop()
        self._started = False
        await self._publish({"type": "stream_status", "health": self.health.public_dict()})

    async def reload_positions(self) -> None:
        if not self._started:
            return
        if self._client:
            await self._client.stop()
        self._positions = {
            self._position_symbol(position): position
            for position in self.portfolio_loader()
        }
        await self._load_snapshot()
        self._client = YahooStreamClient(
            symbols=self.stream_symbols,
            on_quote=self._on_quote,
            health=self.health,
        )
        self._client.start()
        await self._publish(self.snapshot())

    async def _load_snapshot(self) -> None:
        for symbol in YAHOO_FX_SYMBOLS.values():
            try:
                self._quotes[symbol] = market_data_client.get_quote(symbol)
            except MarketDataError as exc:
                self.health.last_error = str(exc)
        for symbol, position in list(self._positions.items()):
            try:
                self._quotes[symbol] = market_data_client.get_quote(symbol)
                self._positions[symbol] = self._calculate_position(position)
            except MarketDataError as exc:
                self.health.last_error = str(exc)

    async def _on_quote(self, raw_quote: dict[str, Any]) -> None:
        symbol = raw_quote["symbol"]
        snapshot_quote = self._quotes.get(symbol)
        quote = Quote(
            symbol=symbol,
            price=raw_quote["price"],
            previous_close=raw_quote.get("previous_close"),
            currency=(
                snapshot_quote.currency
                if snapshot_quote
                else raw_quote.get("currency", "USD")
            ),
            timestamp=raw_quote.get("timestamp"),
            source="Yahoo Finance",
            market_state=raw_quote.get("market_state", "UNKNOWN"),
            incoming_change_percent=raw_quote.get("change_percent"),
            exchange=raw_quote.get("exchange", ""),
            delivery="push",
        )
        validation = analyst_validate_tick(quote)
        if not validation["valid"]:
            self.health.rejected_events += 1
            self.health.last_rejected_event_at = datetime.now(timezone.utc).isoformat()
            return
        self._quotes[symbol] = quote
        self.health.last_event_at = datetime.now(timezone.utc).isoformat()
        self._last_event_by_symbol[symbol] = self.health.last_event_at

        for position in self._affected_positions(symbol):
            try:
                updated = self._calculate_position(position)
            except MarketDataError as exc:
                self.health.last_error = str(exc)
                continue
            self._positions[self._position_symbol(position)] = updated
            await self._publish(
                {
                    "type": "quote_update",
                    "symbol": self._position_symbol(position),
                    "position": updated,
                    "totals": self._totals(),
                    "received_at": datetime.now(timezone.utc).isoformat(),
                }
            )

    def _affected_positions(self, changed_symbol: str) -> list[dict[str, Any]]:
        if changed_symbol in self._positions:
            return [self._positions[changed_symbol]]
        currency = next(
            (currency for currency, symbol in YAHOO_FX_SYMBOLS.items() if symbol == changed_symbol),
            None,
        )
        if not currency:
            return []
        affected = []
        for position in self._positions.values():
            quote = self._quotes.get(self._position_symbol(position))
            if quote and quote.currency == currency:
                affected.append(position)
        return affected

    def _calculate_position(self, position: dict[str, Any]) -> dict[str, Any]:
        symbol = self._position_symbol(position)
        quote = self._quotes.get(symbol)
        if quote is None:
            quote = market_data_client.get_quote(symbol)
            self._quotes[symbol] = quote
        fx_to_eur = self._fx_to_eur(quote.currency)
        calculated = optimizer_calculate_position(position, quote, fx_to_eur)
        result = dict(position)
        result.update(calculated)
        result.update(
            {
                "marketSymbol": symbol,
                "marketPrice": round(quote.price, 4),
                "marketCurrency": quote.currency,
                "previousClose": quote.previous_close,
                "changePercent": quote.change_percent,
                "quoteTimestamp": quote.timestamp_iso,
                "dataSource": quote.source,
                "dataStatus": "realtime_push" if quote.delivery == "push" else "snapshot",
                "marketState": quote.market_state,
                "exchange": quote.exchange,
            }
        )
        return result

    def _fx_to_eur(self, currency: str) -> float:
        currency = currency.upper()
        if currency == "EUR":
            return 1.0
        if currency == "USD":
            eur_usd = self._quotes.get(YAHOO_FX_SYMBOLS["USD"])
            if eur_usd and eur_usd.price > 0:
                return 1.0 / eur_usd.price
        if currency == "JPY":
            jpy_usd = self._quotes.get(YAHOO_FX_SYMBOLS["JPY"])
            eur_usd = self._quotes.get(YAHOO_FX_SYMBOLS["USD"])
            if jpy_usd and eur_usd and jpy_usd.price > 0 and eur_usd.price > 0:
                return jpy_usd.price / eur_usd.price
        return market_data_client.get_fx_rate(currency)

    def _totals(self) -> dict[str, float]:
        total_value = sum(float(position.get("value", 0)) for position in self._positions.values())
        total_gain = sum(float(position.get("gain", 0)) for position in self._positions.values())
        total_cost = total_value - total_gain
        for position in self._positions.values():
            position["allocation"] = (
                round(float(position["value"]) / total_value * 100, 2) if total_value else 0.0
            )
        return {
            "value": round(total_value, 2),
            "gain": round(total_gain, 2),
            "gainPct": round((total_gain / total_cost * 100) if total_cost else 0.0, 2),
            "assets": len(self._positions),
        }

    def snapshot(self) -> dict[str, Any]:
        return {
            "type": "snapshot",
            "positions": list(self._positions.values()),
            "totals": self._totals(),
            "health": self.health.public_dict(),
        }

    async def _publish(self, event: dict[str, Any]) -> None:
        for queue in list(self._subscribers):
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                try:
                    queue.get_nowait()
                    queue.put_nowait(event)
                except (asyncio.QueueEmpty, asyncio.QueueFull):
                    pass

    def subscribe(self) -> asyncio.Queue[dict[str, Any]]:
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=100)
        self._subscribers.add(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue[dict[str, Any]]) -> None:
        self._subscribers.discard(queue)

    def status(self) -> dict[str, Any]:
        status = self.health.public_dict()
        status["last_event_by_symbol"] = dict(self._last_event_by_symbol)
        status["symbols"] = self.stream_symbols
        return status
