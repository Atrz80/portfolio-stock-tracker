import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from app import main as main_module
from app.agent_memory import recall, remember
from app.freellmpool_client import FreellmpoolClient


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


if __name__ == "__main__":
    unittest.main()
