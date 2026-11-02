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
