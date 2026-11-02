html_part3 = """
    <script>
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

        async function refreshData() {
            try {
                let response = await fetch('http://localhost:8000/api/portfolio/realtime').catch(() => null);
                let stocks = [];
                if (response && response.ok) {
                    stocks = await response.json();
                } else {
                    stocks = [
                        { symbol: "AAPL", name: "Apple Inc.", price: 182.50, change_percent: 1.25 },
                        { symbol: "TSLA", name: "Tesla Inc.", price: 245.30, change_percent: -0.85 },
                        { symbol: "GOOGL", name: "Alphabet Inc.", price: 141.20, change_percent: 0.45 },
                        { symbol: "BTC", name: "Bitcoin", price: 65420.00, change_percent: 3.10 }
                    ];
                }

                let tbody = document.getElementById('portfolio-table-body');
                let mobileList = document.getElementById('mobile-list');
                tbody.innerHTML = '';
                mobileList.innerHTML = '';

                let totalVal = 0;
                stocks.forEach(s => {
                    totalVal += s.price;
                    let isPositive = s.change_percent >= 0;
                    let colorClass = isPositive ? 'text-emerald-400' : 'text-rose-400';
                    let icon = isPositive ? 'fa-arrow-trend-up' : 'fa-arrow-trend-down';

                    tbody.innerHTML += `
                        <tr class="hover:bg-gray-950/40 transition">
                            <td class="p-4 font-bold text-indigo-400">${s.symbol}</td>
                            <td class="p-4 text-gray-300">${s.name}</td>
                            <td class="p-4 font-semibold">$${s.price.toFixed(2)}</td>
                            <td class="p-4 ${colorClass} font-medium"><i class="fa-solid ${icon} mr-1"></i> ${s.change_percent > 0 ? '+' : ''}${s.change_percent}%</td>
                            <td class="p-4 text-right"><span class="px-2.5 py-1 bg-gray-800 text-xs rounded-lg text-gray-300">Active</span></td>
                        </tr>
                    `;

                    mobileList.innerHTML += `
                        <div class="bg-gray-900 border border-gray-800 p-3 rounded-xl flex justify-between items-center text-xs">
                            <div>
                                <span class="font-bold text-indigo-400">${s.symbol}</span>
                                <p class="text-gray-400">${s.name}</p>
                            </div>
                            <div class="text-right">
                                <span class="font-semibold">$${s.price.toFixed(2)}</span>
                                <p class="${colorClass}">${s.change_percent > 0 ? '+' : ''}${s.change_percent}%</p>
                            </div>
                        </div>
                    `;
                });

                document.getElementById('total-val').innerText = `$${totalVal.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
                document.getElementById('mobile-total').innerText = `$${totalVal.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
                document.getElementById('total-pl').innerText = `+$${(totalVal * 0.05).toFixed(2)}`;
                document.getElementById('total-pl-pct').className = "text-xs mt-2 inline-block font-semibold text-emerald-400";
                document.getElementById('total-pl-pct').innerHTML = `<i class="fa-solid fa-arrow-trend-up"></i> +5.00%`;

            } catch (err) {
                console.error("Error updating data:", err);
            }
        }

        refreshData();
        setInterval(refreshData, 10000);
    </script>
</body>
</html>
"""
