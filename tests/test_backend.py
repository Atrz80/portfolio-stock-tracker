#!/usr/bin/env python3
import json
import pandas as pd
from fastapi.testclient import TestClient
import sys
import os
sys.path.insert(0, os.getcwd())

# Import the app module
try:
    import importlib.util
    from app import main as main_module
    
    # Try to import yfinance first to check if it's available
    try:
        import yfinance as yf
        print('✅ yfinance importado correctamente')
        yfinance_available = True
    except ImportError:
        print('❌ yfinance no disponible - usando simulación solo')
        yfinance_available = False
    
    # Create test client
    client = TestClient(main_module.app)
    
    print('🧪 Probando endpoint /api/portfolio...')
    response = client.get('/api/portfolio')
    print(f'Status: {response.status_code}')
    data = response.json()
    print(f'Activos cargados: {len(data)}')
    print(f'Valor total: €{sum(item["value"] for item in data):.2f}')
    
    print('\n🧪 Probando endpoint /api/portfolio/realtime...')
    response2 = client.get('/api/portfolio/realtime')
    print(f'Status: {response2.status_code}')
    data2 = response2.json()
    print(f'Activos actualizados: {len(data2)}')
    print(f'Valor total actualizado: €{sum(item["value"] for item in data2):.2f}')
    
    print('\n✅ Todas las pruebas completadas!')
    
except Exception as e:
    print(f'❌ Error: {e}')
    import traceback
    traceback.print_exc()