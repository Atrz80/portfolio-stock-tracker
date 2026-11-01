"""Proveedor de cotizaciones reales de mercado.

Usa el endpoint público de Yahoo Finance ``/v8/finance/chart``. No requiere
API key y entrega precio de mercado, cierres diarios, moneda y timestamp.
Los datos se almacenan en caché durante un intervalo corto para no saturar
el servicio cuando el frontend refresca cada pocos segundos.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone

import requests

YAHOO_CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
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
YAHOO_FX_SYMBOLS = {
    "USD": "EURUSD=X",
    "JPY": "JPYUSD=X",
    "GBP": "GBPEUR=X",
    "CHF": "CHFEUR=X",
}


@dataclass(frozen=True)
class Quote:
    symbol: str
    price: float
    previous_close: float | None
    currency: str
    timestamp: int | None
    source: str = "Yahoo Finance"
    market_state: str = "UNKNOWN"
    incoming_change_percent: float | None = None
    exchange: str = ""
    delivery: str = "snapshot"

    @property
    def change_percent(self) -> float | None:
        if self.incoming_change_percent is not None:
            return round(float(self.incoming_change_percent), 2)
        if not self.previous_close:
            return None
        return round((self.price - self.previous_close) / self.previous_close * 100, 2)

    @property
    def timestamp_iso(self) -> str | None:
        if not self.timestamp:
            return None
        return datetime.fromtimestamp(self.timestamp, tz=timezone.utc).isoformat()


class MarketDataError(RuntimeError):
    """Error descriptivo al obtener datos de mercado."""


class YahooMarketDataClient:
    def __init__(
        self,
        timeout: float = 10.0,
        cache_seconds: float = 15.0,
        max_retries: int = 2,
    ) -> None:
        self.timeout = timeout
        self.cache_seconds = cache_seconds
        self.max_retries = max_retries
        self._cache: dict[str, tuple[float, Quote]] = {}
        self._lock = threading.Lock()

    def get_quote(self, symbol: str) -> Quote:
        symbol = symbol.strip().upper()
        now = time.monotonic()
        with self._lock:
            cached = self._cache.get(symbol)
            if cached and now - cached[0] < self.cache_seconds:
                return cached[1]

        quote = self._fetch_quote(symbol)
        with self._lock:
            self._cache[symbol] = (time.monotonic(), quote)
        return quote

    def get_fx_rate(self, currency: str) -> float:
        """Devuelve la tasa de conversión de la moneda a EUR.

        Para EUR la tasa es 1.0. Para USD se usa EURUSD=X y se divide,
        porque Yahoo publica USD por EUR. Para JPY se usa JPYUSD=X y se
        convierte primero a USD y después a EUR.
        """
        currency = currency.upper()
        if currency == "EUR":
            return 1.0
        symbol = YAHOO_FX_SYMBOLS.get(currency)
        if not symbol:
            raise MarketDataError(f"No hay conversión disponible para {currency}")
        quote = self.get_quote(symbol)
        if currency == "USD":
            eur_usd = quote.price
            if eur_usd <= 0:
                raise MarketDataError("Yahoo Finance devolvió una tasa EUR/USD inválida")
            return 1.0 / eur_usd
        if currency == "JPY":
            jpy_usd = quote.price
            eur_usd = self.get_quote("EURUSD=X").price
            if jpy_usd <= 0 or eur_usd <= 0:
                raise MarketDataError("Yahoo Finance devolvió una tasa JPY/EUR inválida")
            return jpy_usd / eur_usd
        return quote.price

    def _fetch_quote(self, symbol: str) -> Quote:
        url = YAHOO_CHART_URL.format(symbol=symbol)
        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                response = requests.get(
                    url,
                    params={"range": "5d", "interval": "1d", "includePrePost": "false"},
                    headers={"User-Agent": "Mozilla/5.0 PortfolioStockTracker/2.0"},
                    timeout=self.timeout,
                )
                if response.status_code == 404:
                    raise MarketDataError(f"Yahoo Finance no conoce el símbolo {symbol}")
                if response.status_code in (402, 429) or response.status_code >= 500:
                    raise MarketDataError(
                        f"Yahoo Finance respondió HTTP {response.status_code} para {symbol}"
                    )
                response.raise_for_status()
                payload = response.json()
                results = payload.get("chart", {}).get("result") or []
                if not results:
                    error = payload.get("chart", {}).get("error")
                    raise MarketDataError(f"Yahoo Finance no devolvió datos para {symbol}: {error}")

                result = results[0]
                meta = result.get("meta") or {}
                quote_data = ((result.get("indicators") or {}).get("quote") or [{}])[0]
                closes = [float(value) for value in quote_data.get("close", []) if value is not None]
                price = meta.get("regularMarketPrice")
                if price is None and closes:
                    price = closes[-1]
                if price is None:
                    raise MarketDataError(f"La respuesta de Yahoo Finance no incluye precio para {symbol}")

                previous_close = None
                if len(closes) >= 2:
                    previous_close = closes[-2]
                elif meta.get("chartPreviousClose") is not None:
                    previous_close = float(meta["chartPreviousClose"])
                elif meta.get("previousClose") is not None:
                    previous_close = float(meta["previousClose"])

                return Quote(
                    symbol=symbol,
                    price=round(float(price), 6),
                    previous_close=round(previous_close, 6) if previous_close is not None else None,
                    currency=str(meta.get("currency") or "USD").upper(),
                    timestamp=meta.get("regularMarketTime"),
                    market_state=str(meta.get("marketState") or "UNKNOWN").upper(),
                    exchange=str(meta.get("exchange") or ""),
                    delivery="snapshot",
                )
            except (requests.RequestException, ValueError, MarketDataError) as exc:
                last_error = exc
                if attempt < self.max_retries:
                    time.sleep(2 ** attempt)

        raise MarketDataError(
            f"No se pudo obtener una cotización real para {symbol}: {last_error}"
        ) from last_error


market_data_client = YahooMarketDataClient()
