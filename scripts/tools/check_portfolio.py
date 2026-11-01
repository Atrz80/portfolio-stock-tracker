#!/usr/bin/env python3
import json

print("📊 Portfolio Status:")
print("===================")

with open('portfolio.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

print(f"Total Assets: {len(data)}")
print(f"Current Total Value: €{sum(item['value'] for item in data):.2f}")
print()

print("Top 5 Investments:")
for i, asset in enumerate(data[:5], 1):
    gain_color = "📈" if asset['gain'] >= 0 else "📉"
    print(f"{i}. {asset['name']} {gain_color}")
    print(f"   📍 {asset['ticker']}")
    print(f"   💰 €{asset['value']:.2f} ({asset['allocation']}% of portfolio)")
    print(f"   📊 Gain: {asset['gainPct']:.2f}%")
    print()

print("✅ Portfolio loaded successfully into the dashboard!")