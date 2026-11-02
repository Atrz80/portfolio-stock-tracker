# Android Application

The Compose app uses the FastAPI backend at `http://10.0.2.2:8000/` (the host
address from the Android emulator).

- Prices are fetched from `GET /api/portfolio/realtime?provider=yahoo|finnhub`.
  The provider selection is saved locally; prices can also be refreshed
  manually.
- The US catalog is read with `GET /api/catalog?exchange=US` or explicitly
  refreshed with `POST /api/catalog/refresh?exchange=US`. Both endpoints
  return `exchange`, `symbols`, and `updated_at` (`POST` also returns
  `status`). Each symbol contains `symbol`, `displaySymbol`, `description`,
  `type`, and `exchange`. The response is stored in `SharedPreferences`; the
  catalog is not downloaded or updated automatically. Local search filters
  the saved catalog fields.
- Portfolio responses are mapped according to the backend's actual fields
  (`ticker`, `shares`, `gainPct`, `changePercent`, `marketSymbol`, among
  others).
- The previous Gemini analysis is not supported: the current backend does not
  define `POST /api/gemini/analyze`, so the app indicates that it is
  unavailable.

Active Android code: `app/src/main/java/com/example/portfolioapp/`.

## Build

Java 17 and Android SDK Platform 34 are required. On Windows, from this
directory:

```powershell
.\gradlew.bat assembleDebug
```

The wrapper uses Gradle 8.7 and downloads that version the first time. The
debug APK is generated at `app/build/outputs/apk/debug/app-debug.apk`.
