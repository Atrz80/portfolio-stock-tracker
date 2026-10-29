import os
import random
from typing import List
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from google import generativeai as genai
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

api_key = os.getenv("GOOGLE_API_KEY")
if api_key:
    genai.configure(api_key=api_key)

app = FastAPI(
    title="Portfolio Financiero & Gemini API Backend",
    version="1.0.0",
    description="Backend en FastAPI para app Android con análisis de Gemini y datos de mercado en tiempo real."
)

class Stock(BaseModel):
    symbol: str
    name: str
    price: float
    change_percent: float

class PortfolioAnalysisRequest(BaseModel):
    stocks: List[Stock]

@app.get("/")
def read_root():
    return {"status": "online", "message": "Backend de Portfolio Financiero y Gemini funcionando correctamente."}

@app.get("/api/portfolio/realtime", response_model=List[Stock])
def get_realtime_portfolio():
    """Simula la obtención de datos de acciones en tiempo real para el portfolio."""
    # En una app real, aquí consumirías una API financiera (Yahoo Finance, Alpha Vantage, etc.)
    mock_stocks = [
        Stock(symbol="AAPL", name="Apple Inc.", price=float(round(180.0 + random.uniform(-2.0, 2.0), 2)), change_percent=float(round(random.uniform(-1.5, 1.5), 2))),
        Stock(symbol="TSLA", name="Tesla Inc.", price=float(round(240.0 + random.uniform(-5.0, 5.0), 2)), change_percent=float(round(random.uniform(-3.0, 3.0), 2))),
        Stock(symbol="GOOGL", name="Alphabet Inc.", price=float(round(140.0 + random.uniform(-1.5, 1.5), 2)), change_percent=float(round(random.uniform(-1.0, 1.0), 2))),
        Stock(symbol="BTC", name="Bitcoin", price=float(round(65000.0 + random.uniform(-500.0, 500.0), 2)), change_percent=float(round(random.uniform(-4.0, 4.0), 2)))
    ]
    return mock_stocks

@app.post("/api/gemini/analyze")
def analyze_portfolio_with_gemini(data: PortfolioAnalysisRequest):
    """Envía el portfolio a Gemini (Free Tier: gemini-1.5-flash) para análisis y recomendación financiera."""
    if not api_key:
        raise HTTPException(status_code=500, detail="API Key de Google Gemini no configurada en el servidor.")
    
    try:
        # Preparar prompt con los datos del portfolio
        portfolio_summary = "\n".join([f"- {s.symbol} ({s.name}): ${s.price} ({s.change_percent}%)" for s in data.stocks])
        prompt = f"""
        Actúa como un asesor financiero experto. Analiza el siguiente portfolio de inversiones y dame un resumen ejecutivo, evaluación de riesgo y sugerencias de diversificación en español, de forma clara y directa:
        
        {portfolio_summary}
        """
        
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(prompt)
        
        return {
            "analysis": response.text,
            "model_used": "gemini-1.5-flash"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al consultar Gemini API: {str(e)}")
