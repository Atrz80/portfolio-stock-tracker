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
ticker, and Finnhub symbol are optional. Unlock position management to edit an
active position's shares, total invested amount, or average purchase price;
changing any one recalculates the related value. Existing purchase dates are
preserved when editing. The same lock enables recording additional purchases
by shares, EUR cost, and trade date. Archiving is reversible; position data is
retained and every change creates a timestamped backup under
`storage/portfolio-backups/`. The bulk replacement endpoint is disabled to
prevent accidental portfolio loss.

The Android Compose app also includes 1D, 1W, 1M, 1Y, YTD, and ALL history
filters, interactive portfolio and asset charts, and a settings menu for the
quote provider, ticker catalog, and backend address. See
[`../android_app/README.md`](../android_app/README.md) for installing and
connecting it to the PC server.

## Use the portfolio without keeping the PC on

The optional cloud setup uses a Render web service and a Supabase PostgreSQL
database. The free Render service sleeps after 15 minutes without traffic and
has temporary local storage, so the database is required for portfolio data.
Supabase's free projects include 500 MB and pause after one week of inactivity.
The first request after the web service sleeps may take a little longer.
See [Render free services](https://render.com/docs/free) and
[Supabase pricing](https://supabase.com/pricing) for current limits.

1. Create a Supabase project and copy its PostgreSQL connection string. Keep
   the connection string and your portfolio private.
2. In Render, create a Blueprint from this repository using `render.yaml`.
   Enter the Supabase connection string as `PORTFOLIO_DATABASE_URL` and set a
   long, unique `PORTFOLIO_ACCESS_PASSWORD` when prompted. The username is
   `portfolio`. Generate a password locally (for example,
   `py -c "import secrets; print(secrets.token_urlsafe(32))"`); do not send it
   in chat or commit it to the repository.
3. Before opening the hosted site, import the local portfolio once from
   PowerShell in the project folder:

   ```powershell
   py -3.11 -m pip install "psycopg[binary]>=3.2,<4"
   $env:PORTFOLIO_DATABASE_URL = Read-Host "Supabase PostgreSQL connection string"
   py -3.11 .\scripts\import_portfolio_to_database.py
   Remove-Item Env:PORTFOLIO_DATABASE_URL
   ```

   The import script refuses to overwrite a database that already contains
   positions. It reads `portfolio.json` locally; that file is excluded from
   the Docker image. Never commit database credentials or portfolio data.
4. Open `https://<your-render-service>.onrender.com/dashboard`. Sign in with
   username `portfolio` and the password configured in Render. For the Android
   app, set this HTTPS server URL and the same credentials under **Settings**.

Portfolio API endpoints require HTTP Basic authentication when deployed on
Render. Position changes are versioned in the PostgreSQL database. The free
tiers are suitable for trying the app, not guaranteed production availability;
keep a separate private backup of your data.

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
