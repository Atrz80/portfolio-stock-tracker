# PROJECT_MEMORY.md - Portfolio Stock Tracker + FastAPI + Freellmpool/CrewAI

## 🎯 1. Verified Functional Status
- **Web app**: `index.html` loads data from FastAPI and displays the portfolio.
- **Backend**: `app/main.py` exposes real-time portfolio data, memory, chat, and agency; `main.py` maintains compatibility with `uvicorn main:app`.
- **Local data**: `portfolio.json` is the current source for the portfolio.
- **Market data**: public Yahoo Finance WebSocket push (`wss://streamer.finance.yahoo.com`), per-symbol protobuf decoding, subscription heartbeat, and exponential reconnection. The initial snapshot uses the Chart API; each subsequent tick updates only its position.
- **AI gateway**: local Freellmpool at `http://127.0.0.1:8080/v1`.
- **Memory**: locally persisted and retrievable JSONL.
- **Agency**: three profiles (`analyst`, `architect`, `optimizer`) with `crewai.LLM` connected to Freellmpool.

## 🧱 2. Architecture Rules
1. **Separation of concerns**:
   - Data/API: `app/freellmpool_client.py`, `app/agent_memory.py`, `app/session_manager.py`.
   - Business logic: `app/agency.py` and portfolio calculations.
   - Presentation: `index.html` and JS modules when the frontend is reorganized.
   - Backend: `app/main.py`; do not include inline network calls in endpoints.
2. **Configuration**: secrets belong in the global environment
   `E:\Proyectos\ai-workstation\.env`; a local `.env` may override priorities
   and is not versioned.
3. **Runtime**: Python and Freellmpool run exclusively from
   `E:\Proyectos\ai-workstation\runtime\venv`.
4. **Startup**: use `start-all.bat`/`start-all.ps1`; never use scripts that
   kill all Python processes.
5. **Errors**: catch exceptions, log useful information, and return
   descriptive errors.
6. **Real data**: never simulate market prices; a provider failure must produce
   an explicit error.
7. **Rate limits**: exponential retries and rotation/fallback for HTTP 402/429
   and network failures.

## 🛡️ 3. Validation and Limitations
- [x] Joint startup and health checks for FastAPI/Freellmpool.
- [x] Memory persistence through the API.
- [x] Live chat through Freellmpool.
- [x] Agency in direct mode with selection of `analyst`, `architect`, and `optimizer`.
- [x] WebSocket push validated with consecutive real events; FastAPI snapshot with 8 positions and individual per-symbol updates.
- [x] Web/Android selector for Yahoo or Finnhub, preference persistence, and manual Finnhub quote refresh.
- [x] Finnhub US catalog stored locally in the browser/Android; local search and updates only through user action. The web app and cache after reload were tested in a browser.
- [x] 17 unit tests and Python compilation passed; the mobile web view was checked at 390 px with all 8 positions and no horizontal scrolling.
- [x] Android debug APK built with `gradlew.bat assembleDebug`; Gradle 8.7 wrapper generated and tested. Not run on an emulator/device.
- [x] Kilo `kilo-auto/free` endpoint tested without a key; Cline and Roo Code are installed, and the setup guide is in `docs/CLINE_FREE_LLM_APIS.md`. The provider still needs to be selected in the Cline UI.
- [x] `Abrir Portfolio Stock Tracker.bat` waits up to 180 seconds on a cold start, opens the dashboard in an isolated window, and stops the services when it is closed or Ctrl+C is pressed; startup and shutdown verified end to end.
- [ ] Full tool calling/Crew: blocked because current providers have no
  compatible candidates.
- [ ] Google Sheets: pending.
- [ ] Telegram Bot: pending.
- [ ] Docker: pending; Docker is not installed on the validated machine.
- [ ] Live Finnhub: pending addition of `FINNHUB_API_KEY` to the global `.env`;
  without a key, the API returns HTTP 503.
- [ ] Test the Android app on an emulator or device.
- [ ] Select and save OpenAI Compatible with Kilo in Cline settings.

## 🗺️ 4. Next Tasks
1. Convert `index.html` to ES6 modules if the 300-line rule is retained.
2. Implement and test Google Sheets and Telegram independently.
3. Migrate `google.generativeai` to `google-genai` and review Python 3.12+.
4. Verify Docker once installed; the current compose file preserves portfolio
   data in a volume.
5. Expand startup and persistence tests with mock providers.
