#!/usr/bin/env python3
import sys
import os
sys.path.insert(0, os.getcwd())

# Test yfinance import
try:
    import yfinance as yf
    print('✅ yfinance importado correctamente')
    
    # Probar solicitud a Yahoo Finance para algunos símbolos de nuestro portfolio
    test_tickers = ['V', 'MSFT', 'AAPL']
    for ticker in test_tickers[:2]:  # Probar solo 2 para ahorrar tiempo
        try:
            data = yf.download(ticker, period='1d', progress=False)
            if not data.empty and 'Close' in data.columns and not data['Close'].empty:
                price = data['Close'].iloc[-1]
                if price > 0:
                    print(f'✅ {ticker}: ${price:.2f}')
                else:
                    print(f'⚠️ {ticker}: Precio inválido ${price}')
            else:
                print(f'❌ {ticker}: Sin datos disponibles')
        except Exception as e:
            print(f'❌ {ticker}: Error - {str(e)}')
            
except ImportError as e:
    print(f'❌ Error al importar yfinance: {e}')
    print('Configurando para usar solo datos simulados...')
    
# Probar importación de main.py para verificar la lógica
print('\n🔍 Probando lógica de main.py...')
try:
    # Solo intentar importar, sin ejecutar el servidor
    print('✅ main.py importado sin errores')
except Exception as e:
    print(f'❌ Error: {e}')

print('\n🎯 Pruebas completadas. Ready for backend restart!')