# MEMORY.md - Memoria Persistente del Proyecto (Portfolio Stock Tracker + CrewAI + OpenRouter)

> ℹ️ *Nota arquitectónica*: Para la documentación específica del proyecto de seguimiento de portfolio (HTML, JS, Google Sheets, Telegram Bot) y sus normas estrictas de modularidad y manejo de errores, consulta el archivo [PROJECT_MEMORY.md](./PROJECT_MEMORY.md).

## 🎯 1. Objetivos del Proyecto
Desarrollar una aplicación web ligera (HTML/JS) para el control y seguimiento de un portfolio de acciones e inversiones, integrada con Google Sheets y un bot de Telegram, potenciada por **CrewAI** integrado con OpenRouter.

## 🏗️ 2. Arquitectura del Sistema
- **Frontend**: HTML5 / CSS3 / Vanilla JavaScript modular.
- **Base de Datos / Persistencia**: Google Sheets.
- **Orquestación de IA**: **CrewAI** (Equipo especializado: Expert Software Developer, Senior QA & Testing Engineer, y GitHub Incident & Issue Resolver) conectados a OpenRouter (`openrouter/deepseek/deepseek-chat`).

## 📊 3. Estado Actual de Avance
- [x] Eliminación total de LiteLLM y proxies obsoletos.
- [x] Configuración de **CrewAI** y almacenamiento seguro de las API Keys en `.env`.
- [x] Creación del equipo especializado de agentes en `portfolio_crew.py` con integración dinámica de incidencias de GitHub y manejo de reintentos exponenciales.
- [x] Sincronización y preparación de ficheros pendientes para subida al repositorio remoto (`portfolio-stock-tracker`).
- [ ] Desarrollo completo de módulos, tests unitarios y resolución automatizada de incidencias guiados por el equipo CrewAI.








