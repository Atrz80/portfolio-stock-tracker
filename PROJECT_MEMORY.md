# PROJECT_MEMORY.md - Portfolio Stock Tracker + FastAPI + Freellmpool/CrewAI

## 🎯 1. Estado funcional verificado
- **Aplicación web**: `index.html` carga datos desde FastAPI y muestra el portfolio.
- **Backend**: `app/main.py` expone portfolio en tiempo real, memoria, chat y agencia; `main.py` mantiene compatibilidad con `uvicorn main:app`.
- **Datos locales**: `portfolio.json` es la fuente actual del portfolio.
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
3. **Arranque**: usar `start-all.bat`/`start-all.ps1`; nunca scripts que maten todos los procesos Python.
4. **Errores**: capturar excepciones, registrar logs útiles y devolver errores descriptivos.
5. **Rate limits**: reintentos exponenciales y rotación/fallback para HTTP 402/429 y fallos de red.

## 🛡️ 3. Validación y limitaciones
- [x] Arranque conjunto y health checks de FastAPI/Freellmpool.
- [x] Persistencia de memoria mediante API.
- [x] Chat real mediante Freellmpool.
- [x] Agencia en modo directo.
- [ ] Tool-calling/Crew completo: bloqueado por proveedores actuales sin candidatos compatibles.
- [ ] Google Sheets: pendiente.
- [ ] Telegram Bot: pendiente.
- [ ] Docker: pendiente; Docker no está instalado en la máquina validada.

## 🗺️ 4. Próximas tareas
1. Actualizar `index.html` a módulos ES6 si se mantiene la regla de 300 líneas.
2. Implementar y probar Google Sheets y Telegram de forma independiente.
3. Migrar `google.generativeai` a `google-genai` y revisar Python 3.12+.
4. Verificar Docker cuando esté instalado; el compose actual conserva datos de portfolio en un volumen.
5. Ampliar tests de arranque y persistencia con proveedores simulados.
