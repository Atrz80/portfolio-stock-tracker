#!/usr/bin/env python3
print('🧪 Ejecutando test de integración básico...')
print('=' * 50)

# Test 1: Check portfolio.json
print('1. Probando carga de datos del portfolio...')
import json
try:
    with open('portfolio.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    print(f'   ✅ {len(data)} activos cargados')
    total_value = sum(item['value'] for item in data)
    print(f'   ✅ Valor total: €{total_value:.2f}')
except Exception as e:
    print(f'   ❌ Error: {e}')

# Test 2: Check frontend animations
print('2. Probando animaciones del frontend...')
try:
    with open('index.html', 'r', encoding='utf-8') as f:
        html = f.read()
    
    animations = ['individual-row-update', 'table-row-update', 'metric-card-update', 'total-value-update']
    found = [a for a in animations if a in html]
    print(f'   ✅ Animaciones encontradas: {found}')
    
    # Check for 5-second refresh
    if 'setInterval(refreshData, 5000)' in html:
        print('   ✅ Intervalo de actualización de 5 segundos implementado')
    else:
        print('   ❌ Intervalo de actualización no encontrado')
        
except Exception as e:
    print(f'   ❌ Error: {e}')

# Test 3: Check yfinance availability
print('3. Probando integración con Yahoo Finance...')
try:
    import yfinance as yf
    print('   ✅ yfinance disponible')
    
    # Test simple download
    test_data = yf.download('AAPL', period='1d', progress=False)
    if not test_data.empty and ('Close', 'AAPL') in test_data.columns:
        price = test_data[('Close', 'AAPL')].iloc[-1]
        if price > 0:
            print(f'   ✅ AAPL: ${price:.2f}')
        else:
            print('   ⚠️  Precio inválido')
    else:
        print('   ❌ No hay datos para AAPL')
        
except ImportError:
    print('   ❌ yfinance no disponible')
except Exception as e:
    print(f'   ❌ Error: {e}')

print('=' * 50)
print('✅ Test de integración básico completado')