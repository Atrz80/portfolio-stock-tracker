html_part2 = """
    <main class="flex-1 p-6 flex justify-center items-center">
        <!-- Desktop View -->
        <div id="desktop-view" class="w-full max-w-7xl space-y-6">
            <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
                <div class="bg-gray-900 border border-gray-800 p-5 rounded-2xl shadow-sm">
                    <p class="text-xs text-gray-400 font-medium uppercase">Total Portfolio Value</p>
                    <h3 id="total-val" class="text-2xl font-extrabold mt-1 text-white">0,00 €</h3>
                    <span class="text-xs text-emerald-400 mt-2 inline-block"><i class="fa-solid fa-arrow-trend-up"></i> Live</span>
                </div>
                <div class="bg-gray-900 border border-gray-800 p-5 rounded-2xl shadow-sm">
                    <p class="text-xs text-gray-400 font-medium uppercase">Total Gain / Loss</p>
                    <h3 id="total-pl" class="text-2xl font-extrabold mt-1">0,00 €</h3>
                    <span id="total-pl-pct" class="text-xs mt-2 inline-block font-semibold">0.00%</span>
                </div>
                <div class="bg-gray-900 border border-gray-800 p-5 rounded-2xl shadow-sm">
                    <p class="text-xs text-gray-400 font-medium uppercase">Total Assets</p>
                    <h3 id="total-assets" class="text-2xl font-extrabold mt-1 text-indigo-400">4</h3>
                    <span class="text-xs text-gray-400 mt-2 inline-block">Stocks & Crypto</span>
                </div>
                <div class="bg-gray-900 border border-gray-800 p-5 rounded-2xl shadow-sm">
                    <p class="text-xs text-gray-400 font-medium uppercase">Backend & CrewAI</p>
                    <h3 class="text-2xl font-extrabold mt-1 text-emerald-400">Connected</h3>
                    <span class="text-xs text-emerald-500 mt-2 inline-block"><i class="fa-solid fa-circle-check"></i> FastAPI Active</span>
                </div>
            </div>

            <div class="bg-gray-900 border border-gray-800 rounded-2xl overflow-hidden shadow-xl">
                <div class="p-5 border-b border-gray-800 flex justify-between items-center">
                    <h3 class="font-bold text-lg"><i class="fa-solid fa-list mr-2 text-indigo-500"></i> Real-Time Positions</h3>
                    <button onclick="refreshData()" class="px-3 py-1.5 bg-gray-800 hover:bg-gray-700 text-xs font-semibold rounded-lg border border-gray-700 transition"><i class="fa-solid fa-rotate mr-1"></i> Refresh Prices</button>
                </div>
                <div class="overflow-x-auto">
                    <table class="w-full text-left border-collapse">
                        <thead>
                            <tr class="bg-gray-950/60 text-gray-400 text-xs uppercase border-b border-gray-800">
                                <th class="p-4">Ticker</th>
                                <th class="p-4">Name</th>
                                <th class="p-4">Current Price</th>
                                <th class="p-4">24h Change</th>
                                <th class="p-4 text-right">Action</th>
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
                        <span class="text-xs bg-emerald-950 text-emerald-400 px-2 py-0.5 rounded-full border border-emerald-800">v1.0 Online</span>
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
