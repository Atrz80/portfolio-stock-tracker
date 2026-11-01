# MEMORY.md - Estado verificado de Portfolio Stock Tracker

## 🎯 Objetivo
Aplicación de seguimiento de portfolio con frontend web, backend FastAPI, memoria persistente y acceso a IA mediante Freellmpool/CrewAI.

## 🏗️ Arquitectura activa
- **Frontend**: `index.html` (HTML/CSS/Vanilla JS) en la raíz.
- **Backend**: paquete `app/`; `app/main.py` contiene FastAPI y la raíz `main.py` es un lanzador compatible para `uvicorn main:app`.
- **Gateway IA**: `freellmpool proxy` en `127.0.0.1:8080` (`/v1`).
- **Persistencia de portfolio**: `portfolio.json` en la raíz.
- **Memoria de agentes**: JSONL en `storage/crewai_memory/memory.jsonl`.
- **Sesiones**: `storage/sessions/`.
- **Orquestación**: `app/agency.py` con `crewai.LLM`; modo directo por defecto y modo `crew` opt-in.
- **Tests**: `tests/`; scripts históricos en `scripts/archive/` y utilidades en `scripts/tools/`.
- **Documentación técnica**: `docs/`.
- **Ubicación canónica**: `E:\Proyectos\portfolio-stock-tracker` (remoto `https://github.com/Atrz80/portfolio-stock-tracker.git`).
- **Entorno global de IA**: `E:\Proyectos\ai-workstation` (reglas, secretos compartidos y framework; no contiene código de este proyecto).

## ✅ Validación realizada (01/11/2026)
- [x] `start-all.bat` inicia realmente Freellmpool + FastAPI y espera health checks HTTP.
- [x] `stop-all.ps1` detiene únicamente los árboles de procesos registrados en `.services.json`.
- [x] `/`, `/api/portfolio`, `/memory/remember`, `/memory/recall`, `/chat` y `/agency/run` respondieron correctamente.
- [x] Memoria persistida y recuperada entre requests.
- [x] Chat real validado contra Freellmpool (HTTP 200).
- [x] Agencia validada en modo directo (HTTP 200).
- [x] Compilación de módulos principales con Python 3.11.9.
- [x] Reorganización del repositorio en `app/`, `tests/`, `scripts/` y `docs/` sin romper `uvicorn main:app`.
- [x] Rutas de portfolio, memoria y sesiones ancladas a la raíz del proyecto, independientes del directorio de trabajo.
- [x] 7 pruebas `unittest` aisladas superadas con Python de `E:`: memoria, fallback HTTP 429, endpoints, cliente de mercado, conversión a EUR, fallo 503 sin simulación y cobertura ISIN/ticker.
- [x] Proyecto trasladado a su ubicación canónica bajo `E:\Proyectos`, con remoto GitHub preservado.
- [x] Configuración global de IA separada en `E:\Proyectos\ai-workstation`; el proyecto carga el `.env` global sin duplicar secretos.
- [x] Variables globales instaladas en el entorno de usuario de Windows.
- [x] Runtime global instalado en `E:\Proyectos\ai-workstation\runtime`: Python 3.11, uv, FastAPI, CrewAI y Freellmpool; los procesos del proyecto se ejecutan desde binarios de `E:`.
- [x] Datos del dashboard obtenidos mediante Yahoo Finance WebSocket push (`wss://streamer.finance.yahoo.com`), decodificando pricing protobuf y distribuyendo cada cambio solo por símbolo.
- [x] Eliminados el polling de 5 segundos y el fallback aleatorio: el frontend consume `/ws/market`, actualiza una única fila por `quote_update` y reconecta con backoff.
- [x] Streaming real validado con dos eventos push consecutivos de `BTC-USD`; los activos del portfolio se muestran como `snapshot` cuando sus mercados están cerrados hasta recibir un tick.
- [x] Agentes instalados divididos por función: `analyst` valida ticks, `architect` diagnostica push/reconexión y `optimizer` revisa valor/P&L/asignación.
- [x] Tickers ISIN verificados: `VWRA.L`, `SEMI.AS`, `UST.PA`, `EIMI.L`, `6701.T`, `4204.T`, `IUSN.DE` y `5016.T`.
- [x] E2E validado: FastAPI `:8000`, Freellmpool `:8080`, dashboard, 8 posiciones de mercado y chat real (`OK`).
- [x] Selector web Yahoo/Finnhub, persistencia de preferencia y refresco manual de precios integrados; el navegador validó ocho posiciones y la vista móvil a 390 px sin desbordamiento horizontal.
- [x] Catálogo Finnhub USA con refresco explícito y búsqueda local; probado con catálogo simulado en el navegador y persistencia tras recargar.
- [x] 17 pruebas unitarias, compilación Python y contrato HTTP del catálogo superados.
- [x] App Android actualizada con proveedor persistido y caché/búsqueda local; APK debug compilado con `gradlew.bat assembleDebug`.
- [x] Wrapper Gradle 8.7 generado y probado en Windows; se alineó Kotlin 1.9.22 con Compose Compiler 1.5.8 para compilar correctamente.
- [x] Cline 4.1.26 instalado junto a Roo Code; endpoint Kilo `kilo-auto/free` probado sin clave y valores documentados. La selección del proveedor en la interfaz de Cline aún requiere acción manual.
- [x] `Abrir Portfolio Stock Tracker.bat` espera hasta 180 s al arranque en frío, inicia backend y gateway, abre el dashboard en una ventana aislada de Chrome/Edge y los detiene al cerrar esa ventana o pulsar Ctrl+C; el ciclo completo quedó probado.
- [x] `stop-all.ps1` valida manifiesto, comando, puerto y PID antes de parar procesos; `-WhatIf` confirmó el árbol previsto sin interrumpir los servicios.
- [x] `.clinerules` eliminado del proyecto: las reglas globales viven solo en `E:\Proyectos\ai-workstation\.clinerules`.

## ⚠️ Limitaciones y pendientes
- Docker no está instalado en este equipo; `docker-compose.yml` no se pudo ejecutar. Su volumen se corrigió para no ocultar el paquete `app/` y los datos de portfolio usan un volumen persistente.
- Los proveedores disponibles no admiten tool-calling de forma fiable; `CREWAI_AGENCY_MODE=crew` puede devolver HTTP 503 del gateway. El modo directo es el predeterminado.
- El contenido de la copia temporal del workspace C: fue eliminado tras validar el destino; no queda una segunda copia del código.
- `scripts/archive/` contiene generadores históricos no usados; uno (`generate_dashboard.py`) conserva un error de indentación preexistente y queda fuera de la compilación productiva.
- Google Sheets, Telegram y Docker siguen siendo trabajo pendiente/por verificar; no deben considerarse implementados solo por la documentación antigua.
- Finnhub no se pudo validar contra la API real: falta `FINNHUB_API_KEY` en el `.env` global. Las solicitudes sin clave responden HTTP 503 explícitamente.
- El catálogo consultable implementado es el de Finnhub para USA (`exchange=US`); la app Android compila, pero no se ha ejecutado en un emulador o dispositivo.
- La configuración de Kilo está documentada en `docs/CLINE_FREE_LLM_APIS.md`; seleccionar OpenAI Compatible en los ajustes de Cline es un paso manual.
- `google.generativeai` está en desuso y emite avisos; migrar a `google-genai` es una mejora futura.

## 🔐 Configuración
- Credenciales únicamente en `E:\Proyectos\ai-workstation\.env`, instaladas también en el entorno de usuario de Windows.
- `app/config.py` prioriza un `.env` local opcional y carga el entorno global si no existe.
- No incrustar claves reales en código, tests ni documentación.
- Reutilizar el cliente `app/freellmpool_client.py` con reintentos y backoff para 402/429/red.

## 🗺️ Próximas tareas
1. Dividir `index.html` en módulos ES6 manteniendo el comportamiento actual.
2. Implementar y probar Google Sheets y Telegram de forma independiente.
3. Migrar `google.generativeai` a `google-genai` y revisar compatibilidad con Python 3.12+.
4. Verificar Docker cuando esté disponible en el equipo.
5. Ampliar pruebas de arranque y persistencia con proveedores simulados.

## 📚 Documentos relacionados
- `PROJECT_MEMORY.md`: reglas y estado funcional del portfolio.
- `docs/IMPLEMENTATION_REPORT.md`: informe de los tres pilares.
- `docs/COMPATIBILITY_FIXES.md`: compatibilidad y límites conocidos.
- `docs/CLINE_OPENAI_COMPATIBLE.md`: configuración de Cline y Freellmpool.
