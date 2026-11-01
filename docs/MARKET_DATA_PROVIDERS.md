# Fuentes de datos de mercado

## Cotizaciones

- **Yahoo Finance** es la fuente predeterminada. El backend sirve snapshots y
  la web recibe actualizaciones push por `/ws/market`.
- **Finnhub.io** consulta cotizaciones REST al seleccionar esa fuente y al
  solicitar una actualización de precios. No se mezcla con los eventos push
  de Yahoo.
- Finnhub requiere `FINNHUB_API_KEY` en el `.env` global de
  `E:\Proyectos\ai-workstation`. No guardes la clave en el repositorio ni en
  `.env.example`; el ejemplo solo contiene un valor de ejemplo.
- Reinicia FastAPI después de añadir o cambiar la variable para que el cliente
  Finnhub la vuelva a cargar.

## Catálogo de tickers

El catálogo consultable corresponde al mercado USA de Finnhub (`exchange=US`).
La app web lo guarda en `localStorage` y Android en `SharedPreferences`.
Buscar filtra la copia local y no llama a la API. El catálogo no se descarga
ni se renueva en segundo plano: el usuario debe pulsar **Actualizar catálogo**.

El backend persiste la última copia en `storage/ticker_catalog.json`.
`GET /api/catalog?exchange=US` solo lee esa copia; `POST
/api/catalog/refresh?exchange=US` solicita una versión nueva a Finnhub. Así,
cada dispositivo puede cargar la copia del backend o actualizarla y conservarla
localmente.

## Android

La app Compose se conecta al backend de desarrollo en `http://10.0.2.2:8000/`
(emulador Android). En un dispositivo físico, configura una URL accesible desde
ese dispositivo antes de probarlo.
