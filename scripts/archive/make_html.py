with open("index.html", "w", encoding="utf-8") as f:
    f.write("""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Portfolio Stock Tracker - Live Decision Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/@tailwindcss/browser@4"></script>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
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
                <p class="text-xs text-gray-400">Live data (JSON) • Auto-refresh every 5s • FastAPI backend</p>
            </div>
        </div>
        <div class="flex items-center space-x-3">
            <button onclick="openAddModal()" class="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-sm font-semibold rounded-lg transition shadow flex items-center gap-2"><i class="fa-solid fa-plus"></i> Add Investment</button>
            <button onclick="setViewMode('desktop')" id="btn-desktop" class="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-sm font-semibold rounded-lg transition shadow"><i class="fa-solid fa-desktop mr-2"></i> Desktop</button>
            <button onclick="setViewMode('mobile')" id="btn-mobile" class="px-4 py-2 bg-gray-800 hover:bg-gray-700 text-sm font-semibold rounded-lg transition border border-gray-700"><i class="fa-solid fa-mobile-screen mr-2"></i> Mobile APK</button>
        </div>
    </header>
""")
print("Part 1 written")
with open("index.html", "a", encoding="utf-8") as f:
    f.write("""
    <main class="flex-1 p-6 flex justify-center items-start">
        <!-- Desktop View -->
        <div id="desktop-view" class="w-full max-w-7xl space-y-6">
            <!-- Metrics Cards -->
            <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
                <div class="bg-gray-900 border border-gray-800 p-5 rounded-2xl shadow-sm">
                    <p class="text-xs text-gray-400 font-medium uppercase">Total Portfolio Value</p>
                    <h3 id="total-val" class="text-2xl font-extrabold mt-1 text-white">0,00 €</h3>
                    <span class="text-xs text-emerald-400 mt-2 inline-block"><i class="fa-solid fa-arrow-trend-up"></i> Updated live (5s)</span>
                </div>
                <div class="bg-gray-900 border border-gray-800 p-5 rounded-2xl shadow-sm">
                    <p class="text-xs text-gray-400 font-medium uppercase">Total Gain / Loss (P&L)</p>
                    <h3 id="total-pl" class="text-2xl font-extrabold mt-1">0,00 €</h3>
                    <span id="total-pl-pct" class="text-xs mt-2 inline-block font-semibold">0.00%</span>
                </div>
                <div class="bg-gray-900 border border-gray-800 p-5 rounded-2xl shadow-sm">
                    <p class="text-xs text-gray-400 font-medium uppercase">Portfolio Assets</p>
                    <h3 id="total-assets" class="text-2xl font-extrabold mt-1 text-indigo-400">0</h3>
                    <span class="text-xs text-gray-400 mt-2 inline-block">ETFs, Stocks, and Funds</span>
                </div>
                <div class="bg-gray-900 border border-gray-800 p-5 rounded-2xl shadow-sm">
                    <p class="text-xs text-gray-400 font-medium uppercase">Backend Status</p>
                    <h3 class="text-2xl font-extrabold mt-1 text-emerald-400">Connected</h3>
                    <span class="text-xs text-emerald-500 mt-2 inline-block"><i class="fa-solid fa-circle-check"></i> FastAPI / portfolio.json</span>
                </div>
            </div>

            <!-- Charts Section for Decision Making -->
            <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
                <div class="bg-gray-900 border border-gray-800 p-5 rounded-2xl shadow-xl lg:col-span-1 flex flex-col justify-between">
                    <div>
                        <h3 class="font-bold text-lg mb-2"><i class="fa-solid fa-chart-pie mr-2 text-indigo-500"></i> Asset Allocation</h3>
                        <p class="text-xs text-gray-400 mb-4">Percentage distribution of your investment by asset.</p>
                    </div>
                    <div class="relative h-64 flex justify-center items-center">
                        <canvas id="allocationChart"></canvas>
                    </div>
                </div>

                <div class="bg-gray-900 border border-gray-800 p-5 rounded-2xl shadow-xl lg:col-span-2 flex flex-col justify-between">
                    <div>
                        <h3 class="font-bold text-lg mb-2"><i class="fa-solid fa-chart-line mr-2 text-emerald-500"></i> Performance by Position (P&L €)</h3>
                        <p class="text-xs text-gray-400 mb-4">Comparison of net gains and losses for each instrument.</p>
                    </div>
                    <div class="relative h-64">
                        <canvas id="performanceChart"></canvas>
                    </div>
                </div>
            </div>
""")
print("Part 2a written")

with open("index.html", "a", encoding="utf-8") as f:
    f.write("""
            <!-- Positions Table -->
            <div class="bg-gray-900 border border-gray-800 rounded-2xl overflow-hidden shadow-xl">
                <div class="p-5 border-b border-gray-800 flex justify-between items-center">
                    <h3 class="font-bold text-lg"><i class="fa-solid fa-list mr-2 text-indigo-500"></i> Detailed Positions (Live Data)</h3>
                    <div class="flex gap-2">
                        <button onclick="refreshData()" class="px-3 py-1.5 bg-gray-800 hover:bg-gray-700 text-xs font-semibold rounded-lg border border-gray-700 transition"><i class="fa-solid fa-rotate mr-1"></i> Refresh Now</button>
                    </div>
                </div>
                <div class="overflow-x-auto">
                    <table class="w-full text-left border-collapse">
                        <thead>
                            <tr class="bg-gray-950/60 text-gray-400 text-xs uppercase border-b border-gray-800">
                                <th class="p-4">Asset / Name</th>
                                <th class="p-4">Ticker / ISIN</th>
                                <th class="p-4">Shares</th>
                                <th class="p-4">Current Price</th>
                                <th class="p-4">Total Value</th>
                                <th class="p-4">P&L</th>
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
                        <span class="text-xs bg-emerald-950 text-emerald-400 px-2 py-0.5 rounded-full border border-emerald-800">Live (5s)</span>
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
""")
print("Part 2b written")

with open("index.html", "a", encoding="utf-8") as f:
    f.write("""
    <!-- Add Investment Modal -->
    <div id="add-modal" class="hidden fixed inset-0 bg-black/80 z-50 flex justify-center items-center p-4">
        <div class="bg-gray-900 border border-gray-800 rounded-2xl w-full max-w-lg p-6 space-y-4 shadow-2xl">
            <div class="flex justify-between items-center border-b border-gray-800 pb-3">
                <h3 class="font-bold text-lg text-white"><i class="fa-solid fa-circle-plus text-emerald-500 mr-2"></i> Add New Investment</h3>
                <button onclick="closeAddModal()" class="text-gray-400 hover:text-white"><i class="fa-solid fa-xmark text-lg"></i></button>
            </div>
            <form id="add-form" onsubmit="submitNewAsset(event)" class="space-y-3">
                <div>
                    <label class="block text-xs font-medium text-gray-300 mb-1">Asset Name (e.g., Vanguard S&P 500)</label>
                    <input type="text" id="asset-name" required class="w-full bg-gray-950 border border-gray-800 rounded-lg p-2.5 text-sm text-white focus:border-indigo-500 focus:outline-none">
                </div>
                <div class="grid grid-cols-2 gap-3">
                    <div>
                        <label class="block text-xs font-medium text-gray-300 mb-1">Ticker / ISIN</label>
                        <input type="text" id="asset-ticker" required placeholder="IE00B5BMR087" class="w-full bg-gray-950 border border-gray-800 rounded-lg p-2.5 text-sm text-white focus:border-indigo-500 focus:outline-none">
                    </div>
                    <div>
                        <label class="block text-xs font-medium text-gray-300 mb-1">Number of Shares</label>
                        <input type="number" step="any" id="asset-shares" required placeholder="10" class="w-full bg-gray-950 border border-gray-800 rounded-lg p-2.5 text-sm text-white focus:border-indigo-500 focus:outline-none">
                    </div>
                </div>
                <div class="grid grid-cols-3 gap-3">
                    <div>
                        <label class="block text-xs font-medium text-gray-300 mb-1">Purchase Price (€)</label>
                        <input type="number" step="any" id="asset-price" required placeholder="150.00" class="w-full bg-gray-950 border border-gray-800 rounded-lg p-2.5 text-sm text-white focus:border-indigo-500 focus:outline-none">
                    </div>
                    <div>
                        <label class="block text-xs font-medium text-gray-300 mb-1">Purchase Date</label>
                        <input type="date" id="asset-date" class="w-full bg-gray-950 border border-gray-800 rounded-lg p-2.5 text-sm text-white focus:border-indigo-500 focus:outline-none">
                    </div>
                    <div>
                        <label class="block text-xs font-medium text-gray-300 mb-1">Fees / Commissions (€)</label>
                        <input type="number" step="any" id="asset-fees" value="0" class="w-full bg-gray-950 border border-gray-800 rounded-lg p-2.5 text-sm text-white focus:border-indigo-500 focus:outline-none">
                    </div>
                </div>
                <div class="flex justify-end gap-3 pt-3 border-t border-gray-800">
                    <button type="button" onclick="closeAddModal()" class="px-4 py-2 bg-gray-800 hover:bg-gray-700 text-sm font-semibold rounded-lg transition">Cancel</button>
                    <button type="submit" class="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-sm font-semibold rounded-lg transition shadow">Save Investment</button>
                </div>
            </form>
        </div>
    </div>
""")
print("Part 3a written")

with open("index.html", "a", encoding="utf-8") as f:
    f.write("""
    <script>
        let allocationChartInstance = null;
        let performanceChartInstance = null;

        function setViewMode(mode) {
            const desktopView = document.getElementById('desktop-view');
            const mobileView = document.getElementById('mobile-view');
            const btnDesktop = document.getElementById('btn-desktop');
            const btnMobile = document.getElementById('btn-mobile');

            if (mode === 'desktop') {
                desktopView.classList.remove('hidden');
                mobileView.classList.add('hidden');
                btnDesktop.className = "px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-sm font-semibold rounded-lg transition shadow";
                btnMobile.className = "px-4 py-2 bg-gray-800 hover:bg-gray-700 text-sm font-semibold rounded-lg transition border border-gray-700";
            } else {
                desktopView.classList.add('hidden');
                mobileView.classList.remove('hidden');
                btnMobile.className = "px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-sm font-semibold rounded-lg transition shadow";
                btnDesktop.className = "px-4 py-2 bg-gray-800 hover:bg-gray-700 text-sm font-semibold rounded-lg transition border border-gray-700";
            }
        }

        function openAddModal() {
            document.getElementById('add-modal').classList.remove('hidden');
        }

        function closeAddModal() {
            document.getElementById('add-modal').classList.add('hidden');
        }

        async function submitNewAsset(e) {
            e.preventDefault();
            const name = document.getElementById('asset-name').value;
            const ticker = document.getElementById('asset-ticker').value;
            const shares = parseFloat(document.getElementById('asset-shares').value);
            const price = parseFloat(document.getElementById('asset-price').value);
            const value = parseFloat((shares * price).toFixed(2));

            const newPos = {
                name: name,
                ticker: ticker,
                shares: shares,
                price: price,
                value: value,
                gain: 0.00,
                gainPct: 0.00,
                allocation: 0.0,
                badge: "bg-indigo-500",
                init: name.charAt(0).toUpperCase()
            };

            try {
                let res = await fetch('http://localhost:8000/api/portfolio');
                let current = res.ok ? await res.json() : [];
                current.push(newPos);

                await fetch('http://localhost:8000/api/portfolio', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(current)
                });

                closeAddModal();
                document.getElementById('add-form').reset();
                refreshData();
            } catch (err) {
                console.error("Error saving new investment:", err);
                alert("Error saving to the backend.");
            }
        }
""")
print("Part 3b1 written")

with open("index.html", "a", encoding="utf-8") as f:
    f.write("""
        async function refreshData() {
            try {
                let response = await fetch('http://localhost:8000/api/portfolio/realtime').catch(() => null);
                let stocks = [];
                if (response && response.ok) {
                    stocks = await response.json();
                } else {
                    return;
                }

                let tbody = document.getElementById('portfolio-table-body');
                let mobileList = document.getElementById('mobile-list');
                tbody.innerHTML = '';
                mobileList.innerHTML = '';

                let totalVal = 0;
                let totalGain = 0;

                stocks.forEach(s => {
                    totalVal += s.value;
                    totalGain += s.gain || 0;
                    let isPositive = (s.gainPct || 0) >= 0;
                    let colorClass = isPositive ? 'text-emerald-400' : 'text-rose-400';
                    let icon = isPositive ? 'fa-arrow-trend-up' : 'fa-arrow-trend-down';

                    tbody.innerHTML += `
                        <tr class="hover:bg-gray-950/40 transition">
                            <td class="p-4 flex items-center space-x-3">
                                <div class="w-9 h-9 rounded-xl bg-indigo-600/20 text-indigo-400 font-bold flex items-center justify-center text-xs">${s.init || 'V'}</div>
                                <span class="font-bold text-gray-100">${s.name}</span>
                            </td>
                            <td class="p-4 text-xs font-mono text-indigo-400">${s.ticker}</td>
                            <td class="p-4 text-gray-300 font-medium">${s.shares}</td>
                            <td class="p-4 font-semibold">€${s.price.toFixed(2)}</td>
                            <td class="p-4 font-bold text-white">€${s.value.toLocaleString('es-ES', {minimumFractionDigits: 2})}</td>
                            <td class="p-4 ${colorClass} font-semibold"><i class="fa-solid ${icon} mr-1"></i> €${(s.gain || 0).toFixed(2)} (${s.gainPct > 0 ? '+' : ''}${s.gainPct.toFixed(2)}%)</td>
                            <td class="p-4 text-right"><span class="px-2.5 py-1 bg-gray-800 text-xs rounded-lg text-indigo-300 font-semibold">${s.allocation || 0}%</span></td>
                        </tr>
                    `;

                    mobileList.innerHTML += `
                        <div class="bg-gray-900 border border-gray-800 p-3 rounded-xl flex justify-between items-center text-xs">
                            <div>
                                <span class="font-bold text-indigo-400">${s.name}</span>
                                <p class="text-gray-400 font-mono">${s.ticker}</p>
                            </div>
                            <div class="text-right">
                                <span class="font-semibold text-white">€${s.value.toFixed(2)}</span>
                                <p class="${colorClass}">${s.gainPct > 0 ? '+' : ''}${s.gainPct.toFixed(2)}%</p>
                            </div>
                        </div>
                    `;
                });

                document.getElementById('total-val').innerText = `€${totalVal.toLocaleString('es-ES', {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
                document.getElementById('mobile-total').innerText = `€${totalVal.toLocaleString('es-ES', {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
                
                let plColor = totalGain >= 0 ? 'text-emerald-400' : 'text-rose-400';
                document.getElementById('total-pl').className = `text-2xl font-extrabold mt-1 ${plColor}`;
                document.getElementById('total-pl').innerText = `€${totalGain.toFixed(2)}`;
                document.getElementById('total-pl-pct').className = `text-xs mt-2 inline-block font-semibold ${plColor}`;
                document.getElementById('total-assets').innerText = stocks.length;

                updateCharts(stocks);

            } catch (err) {
                console.error("Error updating data:", err);
            }
        }
""")
print("refreshData written")
