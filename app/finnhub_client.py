"""Quote provider using the Finnhub.io API.

Finnhub does not offer quote WebSockets on its free plan. This client uses REST,
so the Finnhub view is refreshed explicitly.
"""

from __future__ import annotations

import os
import math
import threading
import time
from typing import Any

import requests

from .market_data import MarketDataError, Quote

FINNHUB_QUOTE_URL = "https://finnhub.io/api/v1/quote"
FINNHUB_SYMBOLS_URL = "https://finnhub.io/api/v1/stock/symbol"
FINNHUB_TICKER_MAP = {
    "IE00BK5BQT80": "VWRA.L",
    "IE000I8KRLL9": "SEMI.AS",
    "LU1829221024": "UST.PA",
    "IE00BKM4GZ66": "EIMI.L",
    "JP3733000008": "6701.T",
    "JP3419400001": "4204.T",
    "IE00BF4RFH31": "IUSN.DE",
    "JP3379550001": "5016.T",
}
FINNHUB_CURRENCY_BY_SYMBOL = {
    "VWRA.L": "GBP",
    "EIMI.L": "GBP",
    "SEMI.AS": "EUR",
    "UST.PA": "EUR",
    "IUSN.DE": "EUR",
    "6701.T": "JPY",
    "4204.T": "JPY",
    "5016.T": "JPY",
}
FINNHUB_FX_SYMBOLS = {
    "USD": "OANDA:EUR_USD",
    "JPY": "OANDA:EUR_JPY",
    "GBP": "OANDA:EUR_GBP",
    "CHF": "OANDA:EUR_CHF",
}


class FinnhubMarketDataClient:
    def __init__(
        self,
        api_key: str | None = None,
        timeout: float = 10.0,
        cache_seconds: float = 15.0,
        max_retries: int = 2,
    ) -> None:
        self.api_key = api_key or os.getenv("FINNHUB_API_KEY", "")
        self.timeout = timeout
        self.cache_seconds = cache_seconds
        self.max_retries = max_retries
        self._cache: dict[str, tuple[float, Quote]] = {}
        self._lock = threading.Lock()

    @property
    def configured(self) -> bool:
        return bool(self.api_key)

    def get_quote(self, symbol: str) -> Quote:
        symbol = symbol.strip().upper()
        if not self.configured:
            raise MarketDataError(
                "Finnhub is not configured. Add FINNHUB_API_KEY to the global environment."
            )
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
        """Return the number of euros represented by one unit of the currency."""
        currency = currency.upper()
        if currency == "EUR":
            return 1.0
        symbol = FINNHUB_FX_SYMBOLS.get(currency)
        if not symbol:
            raise MarketDataError(f"No conversion is available for {currency}")
        quote = self.get_quote(symbol)
        if not math.isfinite(quote.price) or quote.price <= 0:
            raise MarketDataError(f"Finnhub returned an invalid EUR/{currency} rate")
        return 1.0 / quote.price

    def _fetch_quote(self, symbol: str) -> Quote:
        payload = self._request_json(
            FINNHUB_QUOTE_URL,
            {"symbol": symbol},
            f"quote for {symbol}",
        )
        if not isinstance(payload, dict):
            raise MarketDataError(f"Finnhub returned an invalid response for {symbol}")

        try:
            price = float(payload.get("c"))
            previous_close = (
                float(payload["pc"]) if payload.get("pc") is not None else None
            )
        except (TypeError, ValueError) as exc:
            raise MarketDataError(f"Finnhub returned no valid price for {symbol}") from exc
        timestamp = payload.get("t")
        if not math.isfinite(price) or price <= 0:
            raise MarketDataError(f"Finnhub returned no valid price for {symbol}")
        if previous_close is not None and not math.isfinite(previous_close):
            previous_close = None
        try:
            quote_timestamp = int(timestamp) if timestamp else int(time.time())
        except (TypeError, ValueError) as exc:
            raise MarketDataError(f"Finnhub returned an invalid timestamp for {symbol}") from exc

        currency = FINNHUB_CURRENCY_BY_SYMBOL.get(symbol)
        if currency is None:
            currency = "EUR" if symbol.startswith("OANDA:EUR_") else "USD"
        return Quote(
            symbol=symbol,
            price=round(price, 6),
            previous_close=round(previous_close, 6) if previous_close is not None else None,
            currency=currency,
            timestamp=quote_timestamp,
            source="Finnhub.io",
            market_state="REGULAR",
            exchange="",
            delivery="snapshot",
        )

    def get_ticker_catalog(self, exchange: str = "US") -> list[dict[str, str]]:
        """Fetch the Finnhub ticker catalog for one exchange on explicit request."""
        payload = self._request_json(
            FINNHUB_SYMBOLS_URL,
            {"exchange": exchange},
            f"ticker catalog ({exchange})",
        )
        if not isinstance(payload, list):
            raise MarketDataError("Finnhub returned an invalid ticker catalog")

        catalog = []
        for item in payload:
            if not isinstance(item, dict):
                continue
            symbol = item.get("symbol")
            if not isinstance(symbol, str) or not symbol.strip():
                continue
            catalog.append(
                {
                    "symbol": symbol.strip(),
                    "displaySymbol": str(item.get("displaySymbol") or symbol).strip(),
                    "description": str(item.get("description") or "").strip(),
                    "type": str(item.get("type") or "").strip(),
                    "exchange": exchange,
                }
            )
        if not catalog:
            raise MarketDataError(f"Finnhub returned an empty ticker catalog for {exchange}")
        return catalog

    def _request_json(self, url: str, params: dict[str, str], resource: str) -> Any:
        if not self.configured:
            raise MarketDataError(
                "Finnhub is not configured. Add FINNHUB_API_KEY to the global environment."
            )

        last_error: MarketDataError | None = None
        for attempt in range(self.max_retries + 1):
            try:
                response = requests.get(
                    url,
                    params={**params, "token": self.api_key},
                    timeout=self.timeout,
                )
            except requests.RequestException as exc:
                last_error = MarketDataError(
                    f"Connection error while requesting {resource} from Finnhub"
                )
                if attempt < self.max_retries:
                    time.sleep(2 ** attempt)
                    continue
                raise last_error from None

            if response.status_code in (401, 403):
                raise MarketDataError(
                    "Finnhub rejected the API key or the plan does not allow this request"
                )
            if response.status_code == 404:
                raise MarketDataError(f"Finnhub could not find {resource}")
            if response.status_code in (402, 429) or response.status_code >= 500:
                last_error = MarketDataError(
                    f"Finnhub returned HTTP {response.status_code} while requesting {resource}"
                )
                if attempt < self.max_retries:
                    time.sleep(2 ** attempt)
                    continue
                raise last_error
            if response.status_code >= 400:
                raise MarketDataError(
                    f"Finnhub returned HTTP {response.status_code} while requesting {resource}"
                )
            try:
                return response.json()
            except ValueError as exc:
                raise MarketDataError(
                    f"Finnhub returned invalid JSON while requesting {resource}"
                ) from exc

        raise MarketDataError(f"Could not retrieve {resource}: {last_error}")
