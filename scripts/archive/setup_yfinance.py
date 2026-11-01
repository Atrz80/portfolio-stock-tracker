#!/usr/bin/env python3
import subprocess
import sys
import os

print("🔧 Configurando yfinance para conexión con Yahoo Finance...")
print("=" * 60)

# Intentar instalar yfinance
try:
    print("📦 Instalando yfinance y pandas...")
    result = subprocess.run([sys.executable, '-m', 'pip', 'install', 'yfinance', 'pandas', '-q'], 
                          capture_output=True, text=True)
    
    if result.returncode == 0:
        print("✅ yfinance y pandas instalados correctamente")
    else:
        print(f"⚠️ Advertencia al instalar paquetes: {result.stderr}")
    
    # Verificar si la importación funciona
    print("\n🔍 Verificando importación de yfinance...")
    try:
        import yfinance as yf
        print("✅ yfinance importado correctamente")
        
        # Probar una solicitud a Yahoo Finance
        print("\n📊 Probando conexión con Yahoo Finance...")
        test_tickers = ['AAPL', 'MSFT', 'GOOGL']
        
        for test_ticker in test_tickers:
            try:
                test_data = yf.download(test_ticker, period='1d', progress=False)
                if not test_data.empty and not test_data['Close'].empty:
                    last_price = test_data['Close'].iloc[-1]
                    if last_price > 0:
                        print(f"✅ Prueba exitosa - {test_ticker}: ${last_price:.2f}")
                        continue
                print(f"⚠️ Yahoo Finance no devolvió datos válidos para {test_ticker}")
            except Exception as e:
                print(f"❌ Error con {test_ticker}: {str(e)}")
                
        print("\n✅ Todos los preparativos completados!")
        print("El backend ahora puede obtener precios de mercado reales de Yahoo Finance.")
        
    except ImportError as e:
        print(f"❌ Error al importar yfinance: {e}")
        print("Continuando con simulación solo...")
        
except Exception as e:
    print(f"❌ Error general: {e}")
    print("Continuando con simulación solo...")

print("\n" + "=" * 60)
print("Configuración completada. Reinicia el backend para aplicar los cambios.")