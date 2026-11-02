# Market Data Sources

## Quotes

- **Yahoo Finance** is the default source. The backend serves snapshots, and
  the web app receives push updates through `/ws/market` when market ticks
  arrive. There is no fixed polling interval.
- **Finnhub.io** fetches quotes via REST when this source is selected and when
  a price refresh is requested. It is not mixed with Yahoo push events.
- Snapshots load at app startup, after changing providers or portfolio
  positions, and when the user selects **Refresh prices** in the **Settings**
  menu. The menu shows the time and reason for the last successful snapshot.
- Finnhub requires `FINNHUB_API_KEY` in the global `.env` at
  `E:\Proyectos\ai-workstation`. Do not store the key in the repository or
  `.env.example`; the example contains only a placeholder value.
- Restart FastAPI after adding or changing the variable so the Finnhub client
  reloads it.

## Ticker Catalog

The searchable catalog corresponds to Finnhub's US market (`exchange=US`).
The web app stores it in `localStorage`, and Android in `SharedPreferences`.
Search filters the local copy and does not call the API. The catalog is not
downloaded or refreshed in the background: the user must select **Refresh
catalog**.

The backend persists the latest copy in `storage/ticker_catalog.json`.
`GET /api/catalog?exchange=US` only reads that copy; `POST
/api/catalog/refresh?exchange=US` requests a new version from Finnhub. This
allows each device to load the backend copy or refresh it and retain it locally.

## Android

The Compose app connects to the development backend at
`http://10.0.2.2:8000/` (Android emulator). On a physical device, configure a
URL that is accessible from that device before testing.
