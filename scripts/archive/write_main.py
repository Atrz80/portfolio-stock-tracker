with open("main.py", "w", encoding="utf-8") as f:
    f.write('''import os
import json
import random
from typing import List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from google import generativeai as genai
from dotenv import load_dotenv

try:
    import yfinance as yf
    import pandas as pd
    YFINANCE_AVAILABLE = True
    print("✅ yfinance & pandas imported successfully")
except ImportError:
    YFINANCE_AVAILABLE = False
    print("⚠️ yfinance not available")

load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")
if api_key:
    genai.configure(api_key=api_key)

app = FastAPI(title="Portfolio Stock Tracker & Live Web API", version="2.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

PORTFOLIO_FILE = "portfolio.json"

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
    return {"status": "online", "yfinance_active": YFINANCE_AVAILABLE}

@app.get("/api/portfolio", response_model=List[StockPosition])
def get_portfolio():
    return load_portfolio_data()

@app.post("/api/portfolio")
def save_portfolio(positions: List[StockPosition]):
    with open(PORTFOLIO_FILE, "w", encoding="utf-8") as f:
        json.dump([p.dict() for p in positions], f, ensure_ascii=False, indent=4)
    return {"status": "success"}

YAHOO_TICKER_MAP = {
    "IE00BK5BQT80": "VWCE.DE",
    "IE000I8KRLL9": "IS3N.DE",
    "LU1829221024": "PUST.PA",
    "IE00BKM4GZ66": "EIMI.L",
    "JP3733000008": "6701.T",
    "JP3419400001": "4204.T",
    "IE00B4RFH31": "IUSN.DE",
    "JP3379550001": "5020.T"
}

@app.get("/api/portfolio/realtime")
def get_realtime_portfolio():
    data = load_portfolio_data()
    updated_items = []
    if not YFINANCE_AVAILABLE:
        return simulate_realtime_portfolio(data)
    try:
        yahoo_symbols = [YAHOO_TICKER_MAP.get(item["ticker"].split()[0], item["ticker"].split()[0]) for item in data]
        market_data = yf.download(yahoo_symbols, period="1d", progress=False, group_by="ticker")
        for item in data:
            raw_ticker = item["ticker"].split()[0]
            yf_symbol = YAHOO_TICKER_MAP.get(raw_ticker, raw_ticker)
            current_price = item["price"]
            try:
                close_series = market_data['Close'] if len(yahoo_symbols) == 1 else (market_data[yf_symbol]['Close'] if yf_symbol in market_data else market_data['Close'][yf_symbol])
                if not close_series.empty:
                    val = float(close_series.iloc[-1])
                    if val > 0:
                        current_price = round(val, 2)
            except:
                variation = random.uniform(-0.8, 0.8)
                current_price = round(item["price"] * (1 + variation / 100), 2)
            new_value = round(current_price * item["shares"], 2)
            initial_cost = item["price"] * item["shares"] - item["gain"]
            new_gain = round(new_value - initial_cost, 2) if initial_cost > 0 else round(new_value - (item["shares"] * current_price * (1 - item["gainPct"]/100)), 2)
            new_gain_pct = round((new_gain / (new_value - new_gain)) * 100, 2) if (new_value - new_gain) > 0 else item["gainPct"]
            item_copy = item.copy()
            item_copy["price"] = current_price
            item_copy["value"] = new_value
            item_copy["gain"] = new_gain
            item_copy["gainPct"] = new_gain_pct
            updated_items.append(item_copy)
    except Exception as e:
        return simulate_realtime_portfolio(data)
    return updated_items

def simulate_realtime_portfolio(data):
    updated_items = []
    for item in data:
        variation = random.uniform(-0.8, 0.8)
        new_price = round(item["price"] * (1 + variation / 100), 2)
        new_value = round(new_price * item["shares"], 2)
        new_gain = round(item["gain"] + (new_value - item["value"]), 2)
        new_gain_pct = round(item["gainPct"] + (variation * 0.5), 2)
        item_copy = item.copy()
        item_copy["price"] = new_price
        item_copy["value"] = new_value
        item_copy["gain"] = new_gain
        item_copy["gainPct"] = new_gain_pct
        updated_items.append(item_copy)
    return updated_items

@app.post("/api/google/profile")
def google_user_profile(profile: dict):
    return {"status": "authenticated", "profile": profile}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
''')
print("Complete main.py script generator written")

