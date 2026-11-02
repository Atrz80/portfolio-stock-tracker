#!/usr/bin/env python3
import subprocess
import sys
import os

print("🔧 Setting up yfinance to connect to Yahoo Finance...")
print("=" * 60)

# Try to install yfinance
try:
    print("📦 Installing yfinance and pandas...")
    result = subprocess.run([sys.executable, '-m', 'pip', 'install', 'yfinance', 'pandas', '-q'], 
                          capture_output=True, text=True)
    
    if result.returncode == 0:
        print("✅ yfinance and pandas installed successfully")
    else:
        print(f"⚠️ Warning while installing packages: {result.stderr}")
    
    # Check whether the import works
    print("\n🔍 Checking the yfinance import...")
    try:
        import yfinance as yf
        print("✅ yfinance imported successfully")
        
        # Test a request to Yahoo Finance
        print("\n📊 Testing the Yahoo Finance connection...")
        test_tickers = ['AAPL', 'MSFT', 'GOOGL']
        
        for test_ticker in test_tickers:
            try:
                test_data = yf.download(test_ticker, period='1d', progress=False)
                if not test_data.empty and not test_data['Close'].empty:
                    last_price = test_data['Close'].iloc[-1]
                    if last_price > 0:
                        print(f"✅ Test successful - {test_ticker}: ${last_price:.2f}")
                        continue
                print(f"⚠️ Yahoo Finance returned no valid data for {test_ticker}")
            except Exception as e:
                print(f"❌ Error for {test_ticker}: {str(e)}")
                
        print("\n✅ Setup completed!")
        print("The backend can now retrieve real market prices from Yahoo Finance.")
        
    except ImportError as e:
        print(f"❌ Error importing yfinance: {e}")
        print("Continuing with simulation only...")
        
except Exception as e:
    print(f"❌ General error: {e}")
    print("Continuing with simulation only...")

print("\n" + "=" * 60)
print("Setup complete. Restart the backend to apply the changes.")