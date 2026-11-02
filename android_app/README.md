# Android Application

The Compose app includes portfolio performance periods (1D, 1W, 1M, 1Y, YTD,
and ALL), interactive portfolio and asset charts, an investment-performance
view, quote provider controls, and a searchable ticker catalog.

The app's **Settings** menu lets you set the backend address. The default
`http://10.0.2.2:8000/` is for the Android emulator only. To connect a physical
phone to the Windows PC, start the project with LAN access enabled:

```powershell
& "E:\Proyectos\portfolio-stock-tracker\Abrir Portfolio Stock Tracker.bat" -ListenOnLan
```

Confirm access on the PC, keep the launcher open, and enter the printed PC
address (for example, `http://192.168.1.20:8000/`) in the app's Settings.
Connect both devices to the same trusted Wi-Fi. The local API has no login, so
do not enable LAN access on public or untrusted networks.

Prices are fetched from `GET /api/portfolio/realtime?provider=yahoo|finnhub`.
The provider selection and backend URL are saved on-device. Price refreshes
are manual; Yahoo push updates are currently available in the web dashboard.
Portfolio and asset history use `GET /api/portfolio/history`.

The US ticker catalog can be loaded from `GET /api/catalog?exchange=US` or
refreshed with `POST /api/catalog/refresh?exchange=US`. The catalog is stored
on-device and searched locally.

## Build

Java 17 and Android SDK Platform 34 are required. On Windows, from this
directory:

```powershell
.\gradlew.bat assembleDebug
```

The wrapper uses Gradle 8.7. The debug APK is generated at
`app/build/outputs/apk/debug/app-debug.apk`.
