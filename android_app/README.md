# Aplicación Android

La app Compose consume el backend FastAPI en `http://10.0.2.2:8000/` (dirección del host desde el emulador Android).

- Los precios se consultan en `GET /api/portfolio/realtime?provider=yahoo|finnhub`. La selección del proveedor queda guardada localmente; los precios también pueden refrescarse manualmente.
- El catálogo estadounidense se lee con `GET /api/catalog?exchange=US` o se actualiza explícitamente con `POST /api/catalog/refresh?exchange=US`. Ambos endpoints devuelven `exchange`, `symbols` y `updated_at` (`POST` también devuelve `status`). Cada símbolo contiene `symbol`, `displaySymbol`, `description`, `type` y `exchange`. La respuesta se conserva en `SharedPreferences`; el catálogo no se descarga ni actualiza automáticamente. La búsqueda local filtra los campos del catálogo guardado.
- Las respuestas de portfolio se mapean según los campos reales del backend (`ticker`, `shares`, `gainPct`, `changePercent`, `marketSymbol`, entre otros).
- El análisis Gemini anterior no es compatible: el backend actual no define `POST /api/gemini/analyze`, por lo que la app indica que no está disponible.

Código Android activo: `app/src/main/java/com/example/portfolioapp/`.

## Compilar

Se requiere Java 17 y Android SDK Platform 34. En Windows, desde esta carpeta:

```powershell
.\gradlew.bat assembleDebug
```

El wrapper usa Gradle 8.7 y descarga esa versión la primera vez. El APK de
depuración se genera en `app/build/outputs/apk/debug/app-debug.apk`.
