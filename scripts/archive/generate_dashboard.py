import os

html_part1 = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Portfolio Stock Tracker - Google Profile & Live JSON</title>
    <script src="https://cdn.jsdelivr.net/npm/@tailwindcss/browser@4"></script>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
    <style>
        .phone-frame { width: 380px; height: 780px; background: #111827; border: 12px solid #1f2937; border-radius: 40px; box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.7); overflow: hidden; display: flex; flex-direction: column; position: relative; margin: 0 auto; }
        .phone-screen { flex: 1; overflow-y: auto; background: #0b0f19; color: #f3f4f6; padding: 16px; }
        .phone-notch { position: absolute; top: 0; left: 50%; transform: translateX(-50%); width: 140px; height: 22px; background: #1f2937; border-bottom-left-radius: 12px; border-bottom-right-radius: 12px; z-index: 50; }
    </style>
</head>
<body class="bg-gray-950 text-gray-100 min-h-screen flex flex-col font-sans">
    <header class="bg-gray-900 border-b border-gray-800 p-4 shadow-md flex flex-wrap justify-between items-center gap-4">
        <div class="flex items-center space-x-3">
            <div class="bg-indigo-600 p-2.5 rounded-xl text-white font-bold text-xl shadow-lg"><i class="fa-solid fa-chart-pie"></i></div>
            <div>
                <h1 class="text-xl font-bold tracking-tight">Portfolio Stock Tracker</h1>
                <p class="text-xs text-gray-400">Google Profile Sync | Real-time JSON Portfolio</p>
            </div>
        </div>
        <div class="flex items-center space-x-3">
            <div id="google-auth-container">
                <button onclick="loginWithGoogle()" id="google-login-btn" class="px-4 py-2 bg-white text-gray-900 hover:bg-gray-100 text-sm font-semibold rounded-lg transition shadow flex items-center gap-2">
                    <i class="fa-brands fa-google text-red-500"></i> Sign in with Google
                </button>
            </div>
            <button onclick="setViewMode('desktop')" id="btn-desktop" class="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-sm font-semibold rounded-lg transition shadow"><i class="fa-solid fa-desktop mr-2"></i> Desktop</button>

html_part2 = """
    <main class="flex-1 p-6 flex justify-center items-center">
        <!-- Desktop View -->
        <div id="desktop-view" class="w-full max-w-7xl space-y-6">
            <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
                <div class="bg-gray-900 border border-gray-800 p-5 rounded-2xl shadow-sm">
                    <p class="text-xs text-gray-400 font-medium uppercase">Total Portfolio Value</p>
                    <h3 id="total-val" class="text-2xl font-extrabold mt-1 text-white">0,00 €</h3>
                    <span class="text-xs text-emerald-400 mt-2 inline-block"><i class="fa-solid fa-arrow-trend-up"></i> Live (JSON)</span>
                </div>
                <div class="bg-gray-900 border border-gray-800 p-5 rounded-2xl shadow-sm">
                    <p class="text-xs text-gray-400 font-medium uppercase">Total Gain / Loss</p>
                    <h3 id="total-pl" class="text-2xl font-extrabold mt-1">0,00 €</h3>
                    <span id="total-pl-pct" class="text-xs mt-2 inline-block font-semibold">0.00%</span>
                </div>
                <div class="bg-gray-900 border border-gray-800 p-5 rounded-2xl shadow-sm">
                    <p class="text-xs text-gray-400 font-medium uppercase">Total Assets</p>
                    <h3 id="total-assets" class="text-2xl font-extrabold mt-1 text-indigo-400">0</h3>
                    <span class="text-xs text-gray-400 mt-2 inline-block">ETFs and Stocks</span>
                </div>
                <div class="bg-gray-900 border border-gray-800 p-5 rounded-2xl shadow-sm">
                    <p class="text-xs text-gray-400 font-medium uppercase">Google Profile</p>
                    <h3 id="google-status" class="text-2xl font-extrabold mt-1 text-emerald-400">Local Sync</h3>
                    <span class="text-xs text-emerald-500 mt-2 inline-block"><i class="fa-solid fa-circle-check"></i> portfolio.json</span>
                </div>
            </div>

            <div class="bg-gray-900 border border-gray-800 rounded-2xl overflow-hidden shadow-xl">
                <div class="p-5 border-b border-gray-800 flex justify-between items-center">
                    <h3 class="font-bold text-lg"><i class="fa-solid fa-list mr-2 text-indigo-500"></i> Portfolio Positions (portfolio.json)</h3>
                    <button onclick="refreshData()" class="px-3 py-1.5 bg-gray-800 hover:bg-gray-700 text-xs font-semibold rounded-lg border border-gray-700 transition"><i class="fa-solid fa-rotate mr-1"></i> Refresh Prices</button>
                </div>
                <div class="overflow-x-auto">
                    <table class="w-full text-left border-collapse">
                        <thead>
                            <tr class="bg-gray-950/60 text-gray-400 text-xs uppercase border-b border-gray-800">
                                <th class="p-4">Asset / Ticker</th>
                                <th class="p-4">Price</th>
                                <th class="p-4">Total Value</th>
                                <th class="p-4">Gain %</th>
                                <th class="p-4 text-right">Allocation</th>
                            </tr>
                        </thead>
                        <tbody id="portfolio-table-body" class="divide-y divide-gray-800 text-sm"></tbody>
                    </table>
                </div>
            </div>
        </div>

        <!-- Mobile APK View -->
        <div id="mobile-view" class="hidden w-full">
            <div class="phone-frame">
                <div class="phone-notch"></div>
                <div class="phone-screen space-y-4">
                    <div class="flex justify-between items-center pt-4 pb-2 border-b border-gray-800">
                        <span class="font-bold text-indigo-400"><i class="fa-solid fa-mobile mr-1"></i> StockTracker APK</span>
                        <span class="text-xs bg-emerald-950 text-emerald-400 px-2 py-0.5 rounded-full border border-emerald-800">Google Sync</span>
                    </div>
                    <div class="bg-gray-900 border border-gray-800 p-4 rounded-xl">
                        <p class="text-xs text-gray-400">Mobile Portfolio Balance</p>
                        <h3 id="mobile-total" class="text-xl font-extrabold text-white mt-1">0,00 €</h3>
                    </div>
                    <div class="space-y-2" id="mobile-list"></div>
                </div>
            </div>
        </div>
    </main>
"""

            <button onclick="setViewMode('mobile')" id="btn-mobile" class="px-4 py-2 bg-gray-800 hover:bg-gray-700 text-sm font-semibold rounded-lg transition border border-gray-700"><i class="fa-solid fa-mobile-screen mr-2"></i> Mobile APK</button>
        </div>
    </header>
"""
