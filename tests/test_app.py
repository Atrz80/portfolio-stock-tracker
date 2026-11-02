from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

if __name__ == "__main__":
    print("🚀 Running FastAPI TestClient E2E tests...")
    
    # Test the root endpoint.
    res_root = client.get("/")
    print(f"✅ GET / -> Status: {res_root.status_code}, Response: {res_root.json()}")
    assert res_root.status_code == 200
    
    # Test the portfolio endpoint.
    res_portfolio = client.get("/api/portfolio")
    print(f"✅ GET /api/portfolio -> Status: {res_portfolio.status_code}, Stocks: {len(res_portfolio.json())}")
    assert res_portfolio.status_code == 200
    
    # Test the real-time portfolio endpoint.
    res_realtime = client.get("/api/portfolio/realtime")
    print(f"✅ GET /api/portfolio/realtime -> Status: {res_realtime.status_code}, Stocks: {len(res_realtime.json())}")
    assert res_realtime.status_code == 200
    for stock in res_realtime.json():
        print(f"   - {stock['ticker']} ({stock['name']}): ${stock['price']} (Gain: {stock['gainPct']}%)")
        
    print("\n🎉 All FastAPI TestClient E2E tests passed!")

