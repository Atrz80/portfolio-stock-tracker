import asyncio
import base64
import json
import os
import tempfile
import time
import unittest
from datetime import date, datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

from fastapi.testclient import TestClient

from app import main as main_module
from app.agent_memory import recall, remember
from app.freellmpool_client import FreellmpoolClient
from app.finnhub_client import FinnhubMarketDataClient
from app.market_agents import (
    analyst_validate_tick,
    architect_diagnose_connection,
    optimizer_calculate_position,
)
from app.market_data import MarketDataError, Quote, YahooMarketDataClient
from app.market_protocol import PricingData, decode_yahoo_pricing
from app.market_stream import MarketStreamService


class ApplicationUnitTests(unittest.TestCase):
    def test_dashboard_and_api_require_configured_cloud_credentials(self):
        authorization = "Basic " + base64.b64encode(
            b"portfolio:test-password"
        ).decode("ascii")
        with patch.dict(
            os.environ,
            {
                "PORTFOLIO_ACCESS_USERNAME": "portfolio",
                "PORTFOLIO_ACCESS_PASSWORD": "test-password",
            },
        ):
            client = TestClient(main_module.app)
            self.assertEqual(client.get("/healthz").status_code, 200)
            self.assertEqual(client.get("/dashboard").status_code, 401)
            self.assertEqual(client.get("/api/portfolio").status_code, 401)
            response = client.get(
                "/dashboard", headers={"Authorization": authorization}
            )
            self.assertEqual(response.status_code, 200)
            self.assertIn("portfolio_auth", response.cookies)
            self.assertEqual(
                client.get(
                    "/api/portfolio",
                    headers={"Authorization": authorization},
                ).status_code,
                200,
            )
            self.assertEqual(client.get("/api/portfolio").status_code, 200)

    def test_cloud_auth_fails_closed_when_password_is_missing(self):
        with patch.dict(
            os.environ,
            {
                "PORTFOLIO_AUTH_REQUIRED": "true",
                "PORTFOLIO_ACCESS_PASSWORD": "",
            },
        ):
            response = TestClient(main_module.app).get("/dashboard")
        self.assertEqual(response.status_code, 401)

    def test_cloud_storage_fails_closed_when_database_url_is_missing(self):
        with patch.dict(
            os.environ,
            {"PORTFOLIO_DATABASE_REQUIRED": "true", "PORTFOLIO_DATABASE_URL": ""},
        ):
            with self.assertRaisesRegex(RuntimeError, "PORTFOLIO_DATABASE_URL is required"):
                main_module.load_portfolio_data()

    def test_cloud_portfolio_loads_from_database_without_local_fallback(self):
        expected_positions = [{"name": "Cloud ETF"}]
        connection = Mock()
        cursor = Mock()
        connection.__enter__ = Mock(return_value=connection)
        connection.__exit__ = Mock(return_value=False)
        connection.cursor.return_value.__enter__ = Mock(return_value=cursor)
        connection.cursor.return_value.__exit__ = Mock(return_value=False)
        cursor.fetchone.return_value = (expected_positions,)

        with patch.dict(
            os.environ, {"PORTFOLIO_DATABASE_URL": "postgresql://test/db"}
        ), patch("psycopg.connect", return_value=connection) as connect:
            positions = main_module.load_portfolio_data()

        self.assertEqual(positions, expected_positions)
        connect.assert_called_once_with(
            "postgresql://test/db", connect_timeout=10
        )
        self.assertIn("SELECT positions FROM portfolio_state", cursor.execute.call_args.args[0])

    def test_cloud_portfolio_save_versions_previous_database_state(self):
        connection = Mock()
        cursor = Mock()
        connection.__enter__ = Mock(return_value=connection)
        connection.__exit__ = Mock(return_value=False)
        connection.cursor.return_value.__enter__ = Mock(return_value=cursor)
        connection.cursor.return_value.__exit__ = Mock(return_value=False)
        cursor.fetchone.return_value = ([{"name": "Previous"}],)
        new_positions = [{"name": "Updated"}]

        with patch.dict(
            os.environ, {"PORTFOLIO_DATABASE_URL": "postgresql://test/db"}
        ), patch("psycopg.connect", return_value=connection):
            main_module._save_portfolio_data(new_positions)

        statements = [call.args[0] for call in cursor.execute.call_args_list]
        self.assertTrue(any("INSERT INTO portfolio_backups" in sql for sql in statements))
        self.assertTrue(any("INSERT INTO portfolio_state" in sql for sql in statements))

    def test_positions_can_be_added_archived_and_restored_without_deletion(self):
        original_position = {
            "name": "Existing ETF",
            "ticker": "IE00BK5BQT80 • A2PKXG",
            "shares": 2.0,
            "costBasis": 18.0,
            "transactions": [{"date": "2025-01-01", "shares": 2.0}],
            "price": 9.0,
            "value": 18.0,
            "gain": 0.0,
            "gainPct": 0.0,
            "allocation": 100.0,
            "badge": "bg-indigo-500",
            "init": "E",
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            portfolio_file = Path(temp_dir) / "portfolio.json"
            backup_dir = Path(temp_dir) / "backups"
            portfolio_file.write_text(json.dumps([original_position]), encoding="utf-8")
            with patch.object(main_module, "PORTFOLIO_FILE", str(portfolio_file)), patch.object(
                main_module, "PORTFOLIO_BACKUP_DIR", backup_dir
            ), patch.object(
                main_module.market_stream_service,
                "reload_positions",
                new_callable=AsyncMock,
            ):
                client = TestClient(main_module.app)
                response = client.post(
                    "/api/portfolio/positions",
                    json={
                        "name": "New ETF",
                        "market_symbol": "NEW.L",
                        "shares": 4,
                        "cost_basis_eur": 40,
                        "purchase_date": "2026-01-15",
                    },
                )
                self.assertEqual(response.status_code, 201)
                added_position = response.json()
                self.assertEqual(added_position["marketSymbol"], "NEW.L")
                self.assertEqual(added_position["ticker"], "CUSTOM:NEW.L • NEW.L")
                self.assertEqual(added_position["transactions"][0]["cost"], 40)

                purchase_response = client.post(
                    "/api/portfolio/positions/CUSTOM:NEW.L/purchases",
                    json={
                        "shares": 1,
                        "cost_basis_eur": 10,
                        "purchase_date": date.today().isoformat(),
                    },
                )
                self.assertEqual(purchase_response.status_code, 201)
                purchased_position = purchase_response.json()["position"]
                self.assertEqual(purchased_position["shares"], 5)
                self.assertEqual(purchased_position["costBasis"], 50)
                self.assertEqual(purchased_position["transactions"][-1]["cost"], 10)

                archive_response = client.post(
                    "/api/portfolio/positions/IE00BK5BQT80/archive"
                )
                self.assertEqual(archive_response.status_code, 200)
                archived_positions = client.get("/api/portfolio/positions").json()
                self.assertEqual(len(archived_positions["active"]), 1)
                self.assertEqual(len(archived_positions["archived"]), 1)
                self.assertEqual(
                    archived_positions["archived"][0]["transactions"],
                    original_position["transactions"],
                )

                restore_response = client.post(
                    "/api/portfolio/positions/IE00BK5BQT80/restore"
                )
                self.assertEqual(restore_response.status_code, 200)
                self.assertEqual(len(client.get("/api/portfolio/positions").json()["active"]), 2)
                self.assertEqual(len(list(backup_dir.glob("portfolio-*.json"))), 4)

                bulk_replacement = client.post("/api/portfolio", json=[])
                self.assertEqual(bulk_replacement.status_code, 405)
                self.assertEqual(len(json.loads(portfolio_file.read_text(encoding="utf-8"))), 2)

    def test_position_can_be_edited_and_purchase_dates_are_preserved(self):
        original_position = {
            "name": "Editable ETF",
            "ticker": "IE00TEST12345 • TEST",
            "marketSymbol": "TEST.L",
            "shares": 5.0,
            "costBasis": 65.0,
            "transactions": [
                {"date": "2025-01-01", "shares": 2.0, "cost": 20.0},
                {"date": "2025-06-01", "shares": 3.0, "cost": 45.0},
            ],
            "price": 13.0,
            "value": 65.0,
            "gain": 0.0,
            "gainPct": 0.0,
            "allocation": 100.0,
            "badge": "bg-indigo-500",
            "init": "E",
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            portfolio_file = Path(temp_dir) / "portfolio.json"
            portfolio_file.write_text(json.dumps([original_position]), encoding="utf-8")
            with patch.object(main_module, "PORTFOLIO_FILE", str(portfolio_file)), patch.object(
                main_module, "PORTFOLIO_BACKUP_DIR", Path(temp_dir) / "backups"
            ), patch.object(
                main_module.market_stream_service,
                "reload_positions",
                new_callable=AsyncMock,
            ):
                client = TestClient(main_module.app)
                response = client.put(
                    "/api/portfolio/positions/IE00TEST12345",
                    json={"shares": 10, "cost_basis_eur": 100},
                )

                self.assertEqual(response.status_code, 200)
                position = response.json()["position"]
                self.assertEqual(position["shares"], 10)
                self.assertEqual(position["costBasis"], 100)
                self.assertEqual(position["price"], 10)
                self.assertEqual(
                    [transaction["date"] for transaction in position["transactions"]],
                    ["2025-01-01", "2025-06-01"],
                )
                self.assertEqual(
                    sum(transaction["shares"] for transaction in position["transactions"]),
                    10,
                )
                self.assertEqual(
                    sum(transaction["cost"] for transaction in position["transactions"]),
                    100,
                )

                archive_response = client.post(
                    "/api/portfolio/positions/IE00TEST12345/archive"
                )
                self.assertEqual(archive_response.status_code, 200)
                archived_edit = client.put(
                    "/api/portfolio/positions/IE00TEST12345",
                    json={"shares": 12, "cost_basis_eur": 120},
                )
                self.assertEqual(archived_edit.status_code, 409)

    def test_custom_market_symbols_are_used_for_yahoo_but_finnhub_needs_its_symbol(self):
        position = {
            "ticker": "CUSTOM:NEW.L • NEW",
            "marketSymbol": "NEW.L",
        }
        self.assertEqual(main_module._position_symbol(position), "NEW.L")
        with self.assertRaises(MarketDataError):
            main_module._position_symbol(position, "finnhub")

    def test_market_stream_reloads_custom_positions_without_restarting_app(self):
        positions = [{"ticker": "CUSTOM:NEW.L • NEW", "marketSymbol": "NEW.L"}]
        service = MarketStreamService(lambda: positions)
        service._started = True
        previous_client = Mock()
        previous_client.stop = AsyncMock()
        service._client = previous_client
        with patch("app.market_stream.YahooStreamClient") as stream_client, patch.object(
            service, "_load_snapshot", new_callable=AsyncMock
        ), patch.object(service, "_publish", new_callable=AsyncMock):
            asyncio.run(service.reload_positions())

        previous_client.stop.assert_awaited_once()
        stream_client.assert_called_once()
        self.assertEqual(service._positions, {"NEW.L": positions[0]})
        stream_client.return_value.start.assert_called_once()

    def test_memory_round_trip(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            memory_file = Path(temp_dir) / "memory.jsonl"
            with patch("app.agent_memory.MEMORY_FILE", memory_file):
                stored = remember("The meeting is on Monday", source="unit-test")
                recalled = recall("meeting")

            self.assertEqual(stored["status"], "success")
            self.assertEqual(recalled[0]["text"], "The meeting is on Monday")
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
            result = client.chat_complete("hello", max_retries=2)

        self.assertEqual(result, "ok")
        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[0][1]["json"]["model"], "auto")
        self.assertEqual(calls[1][1]["json"]["model"], "fast")

    def test_api_uses_mocked_services(self):
        with patch.object(main_module, "remember", lambda text, source: {"status": "success", "stored": text}), patch.object(
        main_module, "recall", lambda query, limit: [{"text": "memory"}]
        ), patch.object(
            main_module, "chat_with_memory", lambda message: f"response: {message}"
        ), patch.object(
        main_module, "run_agency_task", lambda objective, agent_type="analyst", mode=None: {"status": "success", "result": objective}
        ):
            client = TestClient(main_module.app)

            self.assertEqual(client.get("/").status_code, 200)
            self.assertEqual(client.get("/api/portfolio").status_code, 200)
            self.assertEqual(client.post("/memory/remember", json={"text": "dato"}).json()["status"], "success")
            self.assertEqual(client.post("/memory/recall", json={"query": "data"}).json()["results"][0]["text"], "memory")
            self.assertEqual(client.post("/chat", json={"message": "hello"}).json()["response"], "response: hello")
            self.assertEqual(client.post("/agency/run", json={"objective": "analyze"}).json()["result"], "analyze")
            agency_result = client.post(
                "/agency/run",
                json={"objective": "revisar", "agente_tipo": "architect", "modo": "direct"},
            ).json()
            self.assertEqual(agency_result["result"], "revisar")

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

    def test_market_client_parses_historical_yahoo_response(self):
        response = Mock()
        response.status_code = 200
        response.raise_for_status.return_value = None
        response.json.return_value = {
            "chart": {
                "result": [
                    {
                        "meta": {"currency": "EUR"},
                        "timestamp": [1_700_000_000, 1_700_086_400, 1_700_172_800],
                        "indicators": {
                            "quote": [{"close": [10.0, None, 12.5]}]
                        },
                    }
                ],
                "error": None,
            }
        }

        with patch("app.market_data.requests.get", return_value=response):
            currency, history = YahooMarketDataClient(max_retries=0).get_history(
                "TEST.AS", 1_700_000_000, 1_700_172_800
            )

        self.assertEqual(currency, "EUR")
        self.assertEqual(
            history,
            [
                {"timestamp": 1_700_000_000, "price": 10.0},
                {"timestamp": 1_700_172_800, "price": 12.5},
            ],
        )
    def test_portfolio_history_endpoint_reconstructs_holdings(self):
        now = int(time.time())
        transaction_date = datetime.fromtimestamp(now - 30, timezone.utc).date().isoformat()
        position = {
            "name": "Test ETF",
            "ticker": "IE00BK5BQT80 • TEST",
            "shares": 2,
            "costBasis": 18.0,
            "transactions": [
                {"date": transaction_date, "shares": 2}
            ],
        }
        history = [
            {"timestamp": now - 30, "price": 10.0},
            {"timestamp": now - 10, "price": 12.5},
        ]

        with patch.object(main_module, "load_portfolio_data", return_value=[position]), patch.object(
            main_module.market_data_client,
            "get_history",
            return_value=("EUR", history),
        ):
            result = main_module.get_portfolio_history("1m")

        self.assertEqual(result["period"], "1m")
        self.assertEqual(result["currency"], "EUR")
        self.assertEqual(result["summary"]["high"], 25.0)
        self.assertEqual(result["summary"]["low"], 20.0)
        self.assertEqual(result["summary"]["start_value"], 20.0)
        self.assertEqual(result["summary"]["end_value"], 25.0)
        self.assertEqual(result["summary"]["change"], 5.0)
        self.assertEqual(result["investment_summary"]["gain"], 5.0)
        self.assertEqual(result["investment_summary"]["estimated_contributions"], 0.0)
        self.assertEqual(result["points"][-1], {"timestamp": now - 10, "value": 25.0})

    def test_asset_history_endpoint_returns_position_details(self):
        now = int(time.time())
        position = {
            "name": "Test ETF",
            "ticker": "IE00BK5BQT80 • TEST",
            "shares": 3,
            "costBasis": 27.0,
            "transactions": [
                {
                    "date": datetime.fromtimestamp(now - 30 * 86400, timezone.utc).date().isoformat(),
                    "shares": 2,
                },
                {
                    "date": datetime.fromtimestamp(now - 10, timezone.utc).date().isoformat(),
                    "shares": 1,
                },
            ],
        }
        history = [
            {"timestamp": now - 31 * 86400, "price": 8.0},
            {"timestamp": now - 30 * 86400, "price": 10.0},
            {"timestamp": now - 10, "price": 12.5},
        ]

        with patch.object(main_module, "load_portfolio_data", return_value=[position]), patch.object(
            main_module.market_data_client,
            "get_history",
            return_value=("EUR", history),
        ):
            response = TestClient(main_module.app).get(
                "/api/portfolio/history",
                params={"period": "1m", "isin": "IE00BK5BQT80"},
            )

        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertEqual(result["asset"]["market_symbol"], "VWRA.L")
        self.assertEqual(result["asset"]["shares"], 3.0)
        self.assertEqual(result["asset"]["cost_basis"], 27.0)
        self.assertEqual(result["asset"]["unrealized_gain"], 10.5)
        self.assertEqual(result["asset"]["last_value"], 37.5)
        self.assertEqual(result["summary"]["end_value"], 12.5)
        self.assertEqual(result["summary"]["change"], 4.5)
        self.assertEqual(result["points"][0]["value"], 8.0)
        self.assertEqual(result["asset"]["period_start_value"], 0.0)
        self.assertEqual(result["asset"]["period_end_value"], 37.5)
        self.assertEqual(result["investment_summary"]["estimated_contributions"], 27.0)
        self.assertEqual(result["investment_summary"]["gain"], 10.5)
        self.assertEqual(result["asset"]["period_gain"], 10.5)
        self.assertEqual(result["investment_points"][0]["shares"], 2.0)
        self.assertEqual(result["investment_points"][0]["value"], 2.0)
        self.assertEqual(result["investment_points"][-1]["shares"], 3.0)
        self.assertEqual(result["investment_points"][-1]["value"], 10.5)
        self.assertIn("per-share prices", result["note"])

    def test_asset_history_endpoint_rejects_unknown_isin(self):
        with patch.object(main_module, "load_portfolio_data", return_value=[{"ticker": "IE00BK5BQT80 • TEST"}]):
            with self.assertRaises(main_module.HTTPException) as context:
                main_module.get_portfolio_history("1m", "UNKNOWN")

        self.assertEqual(context.exception.status_code, 404)

    def test_portfolio_history_rejects_unsupported_period(self):
        with self.assertRaises(main_module.HTTPException) as context:
            main_module.get_portfolio_history("all")

        self.assertEqual(context.exception.status_code, 400)

    def test_finnhub_client_parses_quote_and_uses_api_key(self):
        response = Mock(status_code=200)
        response.json.return_value = {"c": 123.45, "pc": 120.0, "t": 1_700_000_000}
        client = FinnhubMarketDataClient(api_key="test-token", max_retries=0)

        with patch("app.finnhub_client.requests.get", return_value=response) as get:
            quote = client.get_quote("aapl")

        self.assertEqual(quote.symbol, "AAPL")
        self.assertEqual(quote.price, 123.45)
        self.assertEqual(quote.currency, "USD")
        self.assertAlmostEqual(quote.change_percent, 2.88, places=2)
        self.assertEqual(get.call_args.kwargs["params"]["token"], "test-token")

    def test_finnhub_catalog_returns_searchable_symbols(self):
        response = Mock(status_code=200)
        response.json.return_value = [
            {
                "symbol": "AAPL",
                "displaySymbol": "AAPL",
                "description": "Apple Inc",
                "type": "Common Stock",
            },
            {"description": "Missing symbol"},
            None,
        ]
        client = FinnhubMarketDataClient(api_key="test-token", max_retries=0)

        with patch("app.finnhub_client.requests.get", return_value=response) as get:
            catalog = client.get_ticker_catalog("US")

        self.assertEqual(catalog, [{
            "symbol": "AAPL",
            "displaySymbol": "AAPL",
            "description": "Apple Inc",
            "type": "Common Stock",
            "exchange": "US",
        }])
        self.assertEqual(get.call_args.kwargs["params"]["exchange"], "US")

    def test_finnhub_retries_rate_limit_without_exposing_api_key(self):
        responses = [Mock(status_code=429), Mock(status_code=200)]
        responses[1].json.return_value = {"c": 123.45, "pc": 120.0, "t": 1_700_000_000}
        client = FinnhubMarketDataClient(api_key="secret-test-token", max_retries=1)

        with patch("app.finnhub_client.requests.get", side_effect=responses) as get, patch(
            "app.finnhub_client.time.sleep"
        ) as sleep:
            quote = client.get_quote("AAPL")

        self.assertEqual(quote.price, 123.45)
        self.assertEqual(get.call_count, 2)
        sleep.assert_called_once_with(1)

    def test_finnhub_connection_error_does_not_expose_api_key(self):
        client = FinnhubMarketDataClient(api_key="secret-test-token", max_retries=0)
        with patch(
            "app.finnhub_client.requests.get",
            side_effect=__import__("requests").RequestException("token=secret-test-token"),
        ):
            with self.assertRaises(MarketDataError) as context:
                client.get_quote("AAPL")

        self.assertNotIn("secret-test-token", str(context.exception))

    def test_realtime_portfolio_uses_selected_finnhub_provider(self):
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
            currency="GBP",
            timestamp=1_700_000_000,
            source="Finnhub.io",
        )
        with patch.object(main_module, "load_portfolio_data", return_value=[position]), patch.object(
            main_module.finnhub_data_client, "get_quote", return_value=quote
        ), patch.object(
            main_module.finnhub_data_client, "get_fx_rate", return_value=1.2
        ), patch.object(main_module.market_data_client, "get_quote") as yahoo_get_quote:
            result = main_module.get_realtime_portfolio(provider="finnhub")

        self.assertEqual(result[0]["dataSource"], "Finnhub.io")
        self.assertEqual(result[0]["price"], 132.0)
        yahoo_get_quote.assert_not_called()

    def test_ticker_catalog_is_cached_only_after_explicit_refresh(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            catalog_file = Path(temp_dir) / "ticker_catalog.json"
            sample = [{
                "symbol": "AAPL",
                "displaySymbol": "AAPL",
                "description": "Apple Inc",
                "type": "Common Stock",
                "exchange": "US",
            }]
            with patch.object(main_module, "CATALOG_FILE", catalog_file):
                initial = main_module.get_ticker_catalog("US")
                self.assertEqual(initial["symbols"], [])
                self.assertFalse(catalog_file.exists())
                with patch.object(
                    main_module.finnhub_data_client,
                    "get_ticker_catalog",
                    return_value=sample,
                ) as refresh:
                    updated = main_module.refresh_ticker_catalog("US")
                loaded = main_module.get_ticker_catalog("US")

        refresh.assert_called_once_with("US")
        self.assertEqual(updated["status"], "success")
        self.assertEqual(updated["exchange"], "US")
        self.assertEqual(updated["symbols"], sample)
        self.assertEqual(loaded["symbols"], sample)
        self.assertIsNotNone(loaded["updated_at"])

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

    def test_realtime_portfolio_uses_explicit_transaction_cost_basis(self):
        position = {
            "name": "Test ETF",
            "ticker": "IE00BK5BQT80 • TEST",
            "shares": 2,
            "costBasis": 150.0,
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
            currency="EUR",
            timestamp=1_700_000_000,
        )
        with patch.object(main_module, "load_portfolio_data", return_value=[position]), patch.object(
            main_module.market_data_client, "get_quote", return_value=quote
        ), patch.object(main_module.market_data_client, "get_fx_rate", return_value=1.0):
            result = main_module.get_realtime_portfolio()

        self.assertEqual(result[0]["value"], 220.0)
        self.assertEqual(result[0]["gain"], 70.0)
        self.assertEqual(result[0]["gainPct"], 46.67)

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

    def test_market_protocol_decodes_pricing_push(self):
        message = PricingData()
        message.id = "VWRA.L"
        message.price = 123.45
        message.time = 1_700_000_000_000
        message.currency = "EUR"
        message.previous_close = 120.0
        message.market_hours = 1
        message.change_percent = 2.88
        encoded = __import__("base64").b64encode(message.SerializeToString()).decode("ascii")

        decoded = decode_yahoo_pricing(encoded)

        self.assertEqual(decoded["symbol"], "VWRA.L")
        self.assertAlmostEqual(decoded["price"], 123.45, places=4)
        self.assertEqual(decoded["currency"], "EUR")
        self.assertEqual(decoded["market_state"], "REGULAR_OR_24_7")
        self.assertEqual(decoded["timestamp"], 1_700_000_000)
        self.assertEqual(decoded["delivery"], "push")

    def test_agents_validate_diagnose_and_optimize(self):
        valid_quote = Quote(
            symbol="VWRA.L",
            price=110.0,
            previous_close=100.0,
            currency="EUR",
            timestamp=1_700_000_000,
            market_state="REGULAR",
            delivery="push",
        )
        invalid_quote = Quote("TEST", 1.0, None, "EUR", None)

        self.assertTrue(analyst_validate_tick(valid_quote)["valid"])
        self.assertTrue(analyst_validate_tick(invalid_quote)["valid"])
        self.assertFalse(
            analyst_validate_tick(Quote("TEST", 0.0, None, "EUR", None))["valid"]
        )
        diagnosis = architect_diagnose_connection({"state": "disconnected", "reconnect_attempts": 2})
        self.assertEqual(diagnosis["agent"], "architect")
        self.assertIn("reconnect", diagnosis["action"])
        optimized = optimizer_calculate_position(
            {"shares": 2, "price": 100.0, "gain": 0.0}, valid_quote, 1.0
        )
        self.assertEqual(optimized["value"], 220.0)
        self.assertEqual(optimized["gain"], 20.0)

    def test_stream_service_publishes_only_changed_position(self):
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
        service = MarketStreamService(lambda: [position])
        service._positions = {"VWRA.L": position}
        service._quotes["VWRA.L"] = Quote(
            "VWRA.L", 100.0, 100.0, "EUR", 1_700_000_000, delivery="snapshot"
        )
        queue = service.subscribe()

        asyncio.run(
            service._on_quote(
                {
                    "symbol": "VWRA.L",
                    "price": 110.0,
                    "previous_close": 100.0,
                    "currency": "USD",
                    "exchange": "GER",
                    "timestamp": 1_700_000_001,
                    "timestamp_iso": "2023-11-14T22:13:21+00:00",
                    "change_percent": 10.0,
                    "market_state": "REGULAR",
                    "delivery": "push",
                }
            )
        )

        event = queue.get_nowait()
        self.assertEqual(event["type"], "quote_update")
        self.assertEqual(event["symbol"], "VWRA.L")
        self.assertEqual(event["position"]["dataStatus"], "realtime_push")
        self.assertEqual(event["position"]["marketPrice"], 110.0)
        self.assertEqual(event["position"]["marketCurrency"], "EUR")
        self.assertEqual(event["position"]["price"], 110.0)
        self.assertTrue(queue.empty())

    def test_frontend_uses_push_without_polling(self):
        html = (Path(main_module.PROJECT_ROOT) / "index.html").read_text(encoding="utf-8")
        self.assertIn("new WebSocket", html)
        self.assertIn("event.type === 'quote_update'", html)
        self.assertNotIn("setInterval(refreshData", html)
        self.assertNotIn("fetch('/api/portfolio/realtime'", html)
        self.assertIn("/api/portfolio/realtime?provider=", html)
        self.assertIn("minimumPriceFlashChangeEur = 0.01", html)
        self.assertIn("priceFlashChangeRatio = 0.002", html)
        self.assertIn("price-tick-up", html)
        self.assertIn("price-tick-down", html)
        self.assertIn("function highlightPriceMovement(stock)", html)
        self.assertIn('id="settings-dialog"', html)
        self.assertIn("function openSettingsMenu()", html)
        self.assertIn("Technical details:", html)
        self.assertIn("function assetMonogram(stock)", html)
        self.assertIn("class=\"asset-monogram", html)
        self.assertIn("pointermove", html)
        self.assertIn("function openAssetHistory(isin)", html)
        self.assertIn("Gain / loss %", html)
        self.assertIn("data-field=\"gain-pct\"", html)
        self.assertIn("function desktopRow(stock)", html)
        self.assertIn("portfolio.tickerCatalog.finnhub.US.v1", html)
        self.assertIn("fetch('/api/catalog/refresh?exchange=US'", html)
        self.assertNotIn("fetch('/api/catalog')", html)


if __name__ == "__main__":
    unittest.main()
