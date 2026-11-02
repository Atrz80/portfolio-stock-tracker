# Portfolio Stock Tracker Documentation

- `CLINE_OPENAI_COMPATIBLE.md`: configuring Cline with Freellmpool.
- `CLINE_FREE_LLM_APIS.md`: trying a provider from the `awesome-free-llm-apis` catalog in Cline/Roo.
- `CLINE_OPENAI_COMPATIBLE_SETUP.md`: gateway setup guide.
- `COMPATIBILITY_FIXES.md`: version compatibility and known limitations.
- `IMPLEMENTATION_REPORT.md`: status of the three functional pillars.
- `MARKET_DATA_PROVIDERS.md`: quote sources, Finnhub configuration, and catalog cache.
- `../Abrir Portfolio Stock Tracker.bat`: starts the local dashboard in Chrome/Edge and stops the services when its window is closed or Ctrl+C is pressed.

The current status and pending tasks are maintained in `MEMORY.md` and
`PROJECT_MEMORY.md` at the repository root.

The dashboard includes selectable portfolio history and per-asset history
charts with pointer/touch crosshairs. Historical holdings are reconstructed
from purchase transactions in the local `portfolio.json`; keep personal
holdings and transaction records out of public commits.

The dashboard's **Settings** menu contains quote providers, catalog controls,
and the **Manage portfolio positions** panel. The panel can add, archive, and
restore holdings. Adding a position requires its name, Yahoo Finance symbol,
share count, total invested amount in EUR, and purchase date. ISIN, display
ticker, and Finnhub symbol are optional. Archiving is reversible; position data
is retained and every change creates a timestamped backup under
`storage/portfolio-backups/`. The bulk replacement endpoint is disabled to
prevent accidental portfolio loss. Unlocking position management also enables
recording additional purchases by shares, EUR cost, and trade date.

The Android Compose app also includes 1D, 1W, 1M, 1Y, YTD, and ALL history
filters, interactive portfolio and asset charts, and a settings menu for the
quote provider, ticker catalog, and backend address. See
[`../android_app/README.md`](../android_app/README.md) for installing and
connecting it to the PC server.

## Test on a phone

The responsive web dashboard and Android app can both be used on a phone. To
use the web version without installing an APK, connect the PC and
phone to the same trusted Wi-Fi, then launch `Abrir Portfolio Stock
Tracker.bat` with `-ListenOnLan` (from PowerShell, quote the filename if
needed). Confirm the LAN access prompt, leave the launcher window open, and
open the printed `http://<PC-IP>:8000/dashboard` address in the phone browser.
If Windows Firewall prompts, allow access on Private networks only. Close the
launcher window when finished to stop the services.

LAN mode is opt-in because the local API has no login and exposes the portfolio
to devices on that private network. Do not use it on public or untrusted Wi-Fi.
The app still needs the PC to remain on and connected; it is not an offline,
standalone mobile app.
