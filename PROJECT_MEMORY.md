# PROJECT_MEMORY.md - Portfolio Stock Tracker + FastAPI + Freellmpool/CrewAI

## 🎯 1. Estado funcional verificado
- **Aplicación web**: `index.html` carga datos desde FastAPI y muestra el portfolio.
- **Backend**: `app/main.py` expone portfolio en tiempo real, memoria, chat y agencia; `main.py` mantiene compatibilidad con `uvicorn main:app`.
- **Datos locales**: `portfolio.json` es la fuente actual del portfolio.
- **Datos de mercado**: Yahoo Finance WebSocket push público (`wss://streamer.finance.yahoo.com`), decodificación protobuf por símbolo, heartbeat de suscripción y reconexión exponencial. El snapshot inicial usa Chart API; cada tick posterior actualiza solo su posición.
- **Gateway IA**: Freellmpool local en `http://127.0.0.1:8080/v1`.
- **Memoria**: persistencia JSONL local y recuperable.
- **Agencia**: tres perfiles (`analyst`, `architect`, `optimizer`) con `crewai.LLM` conectado a Freellmpool.

## 🧱 2. Reglas de arquitectura
1. **Separación de responsabilidades**:
   - Datos/API: `app/freellmpool_client.py`, `app/agent_memory.py`, `app/session_manager.py`.
   - Lógica de negocio: `app/agency.py` y cálculos del portfolio.
   - Presentación: `index.html` y módulos JS cuando se reorganice el frontend.
   - Backend: `app/main.py`; no incluir llamadas de red inline en los endpoints.
2. **Configuración**: secretos en el entorno global `E:\Proyectos\ai-workstation\.env`; un `.env` local puede sobrescribir prioridades y no se versiona.
3. **Runtime**: Python y Freellmpool se ejecutan exclusivamente desde `E:\Proyectos\ai-workstation\runtime\venv`.
4. **Arranque**: usar `start-all.bat`/`start-all.ps1`; nunca scripts que maten todos los procesos Python.
5. **Errores**: capturar excepciones, registrar logs útiles y devolver errores descriptivos.
6. **Datos reales**: nunca simular precios de mercado; un fallo del proveedor debe producir un error explícito.
7. **Rate limits**: reintentos exponenciales y rotación/fallback para HTTP 402/429 y fallos de red.

## 🛡️ 3. Validación y limitaciones
- [x] Arranque conjunto y health checks de FastAPI/Freellmpool.
- [x] Persistencia de memoria mediante API.
- [x] Chat real mediante Freellmpool.
- [x] Agencia en modo directo con selección de `analyst`, `architect` y `optimizer`.
- [x] WebSocket push validado con eventos reales consecutivos; snapshot FastAPI con 8 posiciones y actualización individual por símbolo.
- [x] Selector web/Android de Yahoo o Finnhub, persistencia de preferencia y refresco manual de cotizaciones Finnhub.
- [x] Catálogo Finnhub USA guardado localmente en navegador/Android; búsqueda local y actualización solo mediante acción del usuario. La web y la caché tras recarga se probaron en navegador.
- [x] 17 pruebas unitarias y compilación Python superadas; la vista web móvil se comprobó a 390 px con las 8 posiciones y sin scroll horizontal.
- [x] APK Android debug compilado con `gradlew.bat assembleDebug`; wrapper Gradle 8.7 generado y probado. No se ha ejecutado en emulador/dispositivo.
- [x] Endpoint Kilo `kilo-auto/free` comprobado sin clave; Cline y Roo Code están instalados y la guía de configuración está en `docs/CLINE_FREE_LLM_APIS.md`. El proveedor aún debe seleccionarse en la interfaz de Cline.
- [x] `Abrir Portfolio Stock Tracker.bat` espera hasta 180 s al arranque en frío, abre el dashboard en una ventana aislada y detiene los servicios al cerrarla o pulsar Ctrl+C; arranque y apagado verificados de extremo a extremo.
- [ ] Tool-calling/Crew completo: bloqueado por proveedores actuales sin candidatos compatibles.
- [ ] Google Sheets: pendiente.
- [ ] Telegram Bot: pendiente.
- [ ] Docker: pendiente; Docker no está instalado en la máquina validada.
- [ ] Finnhub real: pendiente de añadir `FINNHUB_API_KEY` al `.env` global; sin clave, la API responde HTTP 503.
- [ ] Probar la app Android en un emulador o dispositivo.
- [ ] Seleccionar y guardar OpenAI Compatible con Kilo en los ajustes de Cline.

## 🗺️ 4. Próximas tareas
1. Actualizar `index.html` a módulos ES6 si se mantiene la regla de 300 líneas.
2. Implementar y probar Google Sheets y Telegram de forma independiente.
3. Migrar `google.generativeai` a `google-genai` y revisar Python 3.12+.
4. Verificar Docker cuando esté instalado; el compose actual conserva datos de portfolio en un volumen.
5. Ampliar tests de arranque y persistencia con proveedores simulados.
