# MEMORY.md - Verified Status of Portfolio Stock Tracker

## 🎯 Goal
Portfolio tracking application with a web frontend, FastAPI backend,
persistent memory, and AI access through Freellmpool/CrewAI.

## User preferences
- Always write code comments, docstrings, UI text, and application messages in
  English. The user prefers to communicate in Spanish.

## 🏗️ Active Architecture
- **Frontend**: `index.html` (HTML/CSS/Vanilla JS) at the repository root.
- **Backend**: `app/` package; `app/main.py` contains FastAPI, and the root
  `main.py` is a launcher compatible with `uvicorn main:app`.
- **AI gateway**: `freellmpool proxy` at `127.0.0.1:8080` (`/v1`).
- **Portfolio persistence**: `portfolio.json` at the repository root.
- **Agent memory**: JSONL in `storage/crewai_memory/memory.jsonl`.
- **Sessions**: `storage/sessions/`.
- **Orchestration**: `app/agency.py` with `crewai.LLM`; direct mode by default
  and `crew` mode opt-in.
- **Tests**: `tests/`; historical scripts in `scripts/archive/` and utilities
  in `scripts/tools/`.
- **Technical documentation**: `docs/`.
- **Canonical location**: `E:\Proyectos\portfolio-stock-tracker` (remote
  `https://github.com/Atrz80/portfolio-stock-tracker.git`).
- **Global AI environment**: `E:\Proyectos\ai-workstation` (rules, shared
  secrets, and framework; contains no code from this project).

## ✅ Validation completed (01/11/2026)
- [x] `start-all.bat` starts Freellmpool and FastAPI and waits for HTTP health checks.
- [x] `stop-all.ps1` stops only the process trees registered in `.services.json`.
- [x] `/`, `/api/portfolio`, `/memory/remember`, `/memory/recall`, `/chat`, and `/agency/run` responded successfully.
- [x] Memory persisted and was retrieved across requests.
- [x] Live chat validated against Freellmpool (HTTP 200).
- [x] Agency validated in direct mode (HTTP 200).
- [x] Main modules compiled with Python 3.11.9.
- [x] Repository reorganized into `app/`, `tests/`, `scripts/`, and `docs/` without breaking `uvicorn main:app`.
- [x] Portfolio, memory, and session paths anchored to the project root and independent of the working directory.
- [x] 7 isolated `unittest` tests passed with Python from `E:`: memory, HTTP 429 fallback, endpoints, market client, EUR conversion, 503 failure without simulation, and ISIN/ticker coverage.
- [x] Project moved to its canonical location under `E:\Proyectos`, preserving the GitHub remote.
- [x] Global AI configuration separated into `E:\Proyectos\ai-workstation`; the project loads the global `.env` without duplicating secrets.
- [x] Global variables installed in the Windows user environment.
- [x] Global runtime installed in `E:\Proyectos\ai-workstation\runtime`: Python 3.11, uv, FastAPI, CrewAI, and Freellmpool; project processes run from binaries on `E:`.
- [x] Dashboard data retrieved through Yahoo Finance WebSocket push (`wss://streamer.finance.yahoo.com`), decoding pricing protobuf and distributing each change only to its symbol.
- [x] 5-second polling and random fallback removed: the frontend consumes `/ws/market`, updates a single row per `quote_update`, and reconnects with backoff.
- [x] Live streaming validated with two consecutive `BTC-USD` push events; portfolio assets are shown as `snapshot` while their markets are closed until a tick arrives.
- [x] Installed agents divided by function: `analyst` validates ticks, `architect` diagnoses push/reconnection, and `optimizer` reviews value/P&L/allocation.
- [x] ISIN tickers verified: `VWRA.L`, `SEMI.AS`, `UST.PA`, `EIMI.L`, `6701.T`, `4204.T`, `IUSN.DE`, and `5016.T`.
- [x] E2E validated: FastAPI `:8000`, Freellmpool `:8080`, dashboard, 8 market positions, and live chat (`OK`).
- [x] Web Yahoo/Finnhub selector, preference persistence, and manual price refresh integrated; the browser validated eight positions and the 390 px mobile view without horizontal overflow.
- [x] Finnhub US catalog with explicit refresh and local search; tested with a mock catalog in the browser and persistence after reload.
- [x] 17 unit tests, Python compilation, and catalog HTTP contract passed.
- [x] Android app updated with a persisted provider and local cache/search; debug APK built with `gradlew.bat assembleDebug`.
- [x] Gradle 8.7 wrapper generated and tested on Windows; Kotlin 1.9.22 was aligned with Compose Compiler 1.5.8 for a successful build.
- [x] Cline 4.1.26 installed alongside Roo Code; Kilo `kilo-auto/free` endpoint tested without a key and values documented. Selecting the provider in the Cline UI still requires manual action.
- [x] `Abrir Portfolio Stock Tracker.bat` waits up to 180 seconds on a cold start, starts the backend and gateway, opens the dashboard in an isolated Chrome/Edge window, and stops them when that window is closed or Ctrl+C is pressed; the full cycle was tested.
- [x] `stop-all.ps1` validates the manifest, command, port, and PID before stopping processes; `-WhatIf` confirmed the expected process tree without interrupting services.
- [x] `.clinerules` removed from the project: global rules now live only in `E:\Proyectos\ai-workstation\.clinerules`.

## ⚠️ Limitations and pending work
- Docker is not installed on this machine; `docker-compose.yml` could not be
  run. Its volume was corrected so it does not hide the `app/` package, and
  portfolio data uses a persistent volume.
- Available providers do not reliably support tool calling;
  `CREWAI_AGENCY_MODE=crew` may return HTTP 503 from the gateway. Direct mode
  is the default.
- The contents of the temporary C: workspace copy were deleted after
  validating the destination; no second copy of the code remains.
- `scripts/archive/` contains unused historical generators; one
  (`generate_dashboard.py`) retains a pre-existing indentation error and is
  excluded from the production build.
- Google Sheets, Telegram, and Docker remain pending/to be verified; they
  should not be considered implemented based solely on old documentation.
- Finnhub could not be validated against the live API: `FINNHUB_API_KEY` is
  missing from the global `.env`. Requests without a key explicitly return
  HTTP 503.
- The implemented searchable catalog is Finnhub's US catalog (`exchange=US`);
  the Android app compiles but has not been run on an emulator or device.
- Kilo configuration is documented in `docs/CLINE_FREE_LLM_APIS.md`; selecting
  OpenAI Compatible in Cline settings is a manual step.
- `google.generativeai` is deprecated and emits warnings; migrating to
  `google-genai` is a future improvement.

## 🔐 Configuration
- Credentials only in `E:\Proyectos\ai-workstation\.env`, also installed in the Windows user environment.
- `app/config.py` prioritizes an optional local `.env` and loads the global environment if it does not exist.
- Do not embed real keys in code, tests, or documentation.
- Reuse `app/freellmpool_client.py` with retries and backoff for 402/429/network errors.

## 🗺️ Next tasks
1. Split `index.html` into ES6 modules while preserving current behavior.
2. Implement and test Google Sheets and Telegram independently.
3. Migrate `google.generativeai` to `google-genai` and review compatibility
   with Python 3.12+.
4. Verify Docker when it is available on the machine.
5. Expand startup and persistence tests with mock providers.

## 📚 Related documents
- `PROJECT_MEMORY.md`: portfolio rules and functional status.
- `docs/IMPLEMENTATION_REPORT.md`: report on the three pillars.
- `docs/COMPATIBILITY_FIXES.md`: compatibility and known limitations.
- `docs/CLINE_OPENAI_COMPATIBLE.md`: Cline and Freellmpool configuration.
