import traceback
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

if __name__ == "__main__":
    print("Starting E2E tests with detailed exception handling...")
    try:
        res = client.get("/")
        print(f"GET / -> Status: {res.status_code}, Data: {res.json()}")
    except Exception as e:
        print(f"Error on GET /: {e}")
        traceback.print_exc()

    try:
        res = client.post("/memory/remember", json={"text": "Test memory entry", "source": "test"})
        print(f"POST /memory/remember -> Status: {res.status_code}, Data: {res.json()}")
    except Exception as e:
        print(f"Error on /memory/remember: {e}")
        traceback.print_exc()

    try:
        res = client.post("/memory/recall", json={"query": "Test", "limit": 2})
        print(f"POST /memory/recall -> Status: {res.status_code}, Data: {res.json()}")
    except Exception as e:
        print(f"Error on /memory/recall: {e}")
        traceback.print_exc()

    try:
        res = client.post("/chat", json={"message": "Hola"})
        print(f"POST /chat -> Status: {res.status_code}, Data: {res.json()}")
    except Exception as e:
        print(f"Error on /chat: {e}")
        traceback.print_exc()

    try:
        res = client.post("/agency/run", json={"objective": "Test objective"})
        print(f"POST /agency/run -> Status: {res.status_code}, Data: {res.json()}")
    except Exception as e:
        print(f"Error on /agency/run: {e}")
        traceback.print_exc()
