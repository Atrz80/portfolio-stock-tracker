import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from fastapi.testclient import TestClient

from app import main as main_module
from app.agent_memory import recall, remember
from app.freellmpool_client import FreellmpoolClient
from app.market_data import MarketDataError, Quote, YahooMarketDataClient


class ApplicationUnitTests(unittest.TestCase):
    def test_memory_round_trip(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            memory_file = Path(temp_dir) / "memory.jsonl"
            with patch("app.agent_memory.MEMORY_FILE", memory_file):
                stored = remember("La reunión es el lunes", source="unit-test")
                recalled = recall("reunión")

            self.assertEqual(stored["status"], "success")
            self.assertEqual(recalled[0]["text"], "La reunión es el lunes")
            self.assertTrue(memory_file.exists())

    def test_freellmpool_retries_after_quota_error(self):
        responses = [
            type("Response", (), {"ok": False, "status_code": 429, "json": lambda self: {"error": {"message": "quota"}}})(),
            type("Response", (), {"ok": True, "status_code": 200, "json": lambda self: {"choices": [{"message": {"content": "ok"}}]}})(),
        ]
        calls = []

        def fake_post(*args, **kwargs):
            calls.append((args, kwargs))
            return responses[len(calls) - 1]

        with patch("app.freellmpool_client.requests.post", side_effect=fake_post), patch("app.freellmpool_client.time.sleep"):
            client = FreellmpoolClient("http://localhost:8080/v1", "local")
            result = client.chat_completar("hola", max_reintentos=2)

        self.assertEqual(result, "ok")
        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[0][1]["json"]["model"], "auto")
        self.assertEqual(calls[1][1]["json"]["model"], "fast")

    def test_api_uses_mocked_services(self):
        with patch.object(main_module, "remember", lambda text, source: {"status": "success", "stored": text}), patch.object(
            main_module, "recall", lambda query, limit: [{"text": "recuerdo"}]
        ), patch.object(
            main_module, "chat_with_memory", lambda message: f"respuesta: {message}"
        ), patch.object(
            main_module, "run_agency_task", lambda objective: {"status": "success", "result": objective}
        ):
            client = TestClient(main_module.app)

            self.assertEqual(client.get("/").status_code, 200)
            self.assertEqual(client.get("/api/portfolio").status_code, 200)
            self.assertEqual(client.post("/memory/remember", json={"text": "dato"}).json()["status"], "success")
            self.assertEqual(client.post("/memory/recall", json={"query": "dato"}).json()["results"][0]["text"], "recuerdo")
            self.assertEqual(client.post("/chat", json={"message": "hola"}).json()["response"], "respuesta: hola")
            self.assertEqual(client.post("/agency/run", json={"objective": "analizar"}).json()["result"], "analizar")

    def test_market_client_parses_real_yahoo_response(self):
        response = Mock()
        response.status_code = 200
        response.raise_for_status.return_value = None
        response.json.return_value = {
            "chart": {
                "result": [
                    {
                        "meta": {
                            "regularMarketPrice": 123.45,
                            "currency": "EUR",
                            "regularMarketTime": 1_700_000_000,
                        },
                        "indicators": {"quote": [{"close": [120.0, 123.45]}]},
                    }
                ],
                "error": None,
            }
        }

        with patch("app.market_data.requests.get", return_value=response):
            quote = YahooMarketDataClient(max_retries=0).get_quote("TEST.AS")

        self.assertEqual(quote.price, 123.45)
        self.assertEqual(quote.previous_close, 120.0)
        self.assertEqual(quote.currency, "EUR")
        self.assertAlmostEqual(quote.change_percent, 2.88, places=2)

    def test_realtime_portfolio_uses_real_quote_and_converts_to_eur(self):
        position = {
            "name": "Test ETF",
            "ticker": "IE00BK5BQT80 • TEST",
            "shares": 2,
            "price": 100.0,
            "value": 200.0,
            "gain": 0.0,
            "gainPct": 0.0,
            "allocation": 100.0,
            "badge": "test",
            "init": "T",
        }
        quote = Quote(
            symbol="VWRA.L",
            price=110.0,
            previous_close=100.0,
            currency="USD",
            timestamp=1_700_000_000,
        )
        with patch.object(main_module, "load_portfolio_data", return_value=[position]), patch.object(
            main_module.market_data_client, "get_quote", return_value=quote
        ), patch.object(main_module.market_data_client, "get_fx_rate", return_value=0.8):
            result = main_module.get_realtime_portfolio()

        self.assertEqual(result[0]["dataStatus"], "real")
        self.assertEqual(result[0]["marketPrice"], 110.0)
        self.assertEqual(result[0]["marketCurrency"], "USD")
        self.assertEqual(result[0]["price"], 88.0)
        self.assertEqual(result[0]["value"], 176.0)
        self.assertEqual(result[0]["changePercent"], 10.0)

    def test_realtime_portfolio_returns_503_without_simulated_prices(self):
        position = {
            "name": "Test ETF",
            "ticker": "IE00BK5BQT80 • TEST",
            "shares": 2,
            "price": 100.0,
            "value": 200.0,
            "gain": 0.0,
            "gainPct": 0.0,
            "allocation": 100.0,
            "badge": "test",
            "init": "T",
        }
        with patch.object(main_module, "load_portfolio_data", return_value=[position]), patch.object(
            main_module.market_data_client,
            "get_quote",
            side_effect=MarketDataError("fuera de servicio"),
        ):
            with self.assertRaises(main_module.HTTPException) as context:
                main_module.get_realtime_portfolio()

        self.assertEqual(context.exception.status_code, 503)
        self.assertIn("fuera de servicio", context.exception.detail)

    def test_portfolio_isins_have_market_symbols(self):
        for item in main_module.load_portfolio_data():
            isin = main_module._position_isin(item)
            self.assertIn(isin, main_module.YAHOO_TICKER_MAP)
            self.assertTrue(main_module.YAHOO_TICKER_MAP[isin])


if __name__ == "__main__":
    unittest.main()
