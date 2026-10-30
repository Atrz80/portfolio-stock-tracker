# PROJECT_MEMORY.md - Portfolio Stock Tracker (HTML + JS + Google Sheets + Telegram Bot + LiteLLM AI)

## 🎯 1. Resumen y Estado Actual del Desarrollo
- **Propósito**: Aplicación ligera y eficiente para el seguimiento de carteras de inversión y acciones (*Portfolio Stock Tracker*), integrada con Google Sheets como base de datos en la nube y un bot de Telegram para notificaciones y comandos interactivos.
- **Frontend**: HTML5 / CSS3 / Vanilla JavaScript modular, diseñado para renderizar gráficos de evolución en tiempo real y tablas de rendimiento.
- **Backend / Integración**: 
  - Scripts en JavaScript (Google Apps Script / Node.js) para sincronización con **Google Sheets**.
  - **Telegram Bot API** para alertas automatizadas y comandos de consulta de portfolio.
  - **LiteLLM Proxy Local** (puerto `4000`) conectado a modelos de OpenRouter (`openrouter/deepseek/deepseek-chat`) con enrutamiento resiliente y control de tokens de prompt.

---

## 🏗️ 2. Normas Estrictas de Arquitectura, Modularidad y Manejo de Errores

### 🧱 A. Reglas de Modularidad
1. **Separación de Responsabilidades (SoC)**:
   - **Capa de Datos**: Toda la lógica de conexión con Google Sheets y llamadas a APIs externas debe estar aislada en módulos independientes (`api.js` / `sheetsService.js`).
   - **Capa de Lógica de Negocio**: Cálculos financieros, rentabilidades, P&L y procesamiento de carteras deben residir en módulos puramente funcionales libres de dependencias DOM.
   - **Capa de Presentación (UI)**: Manipulación del DOM y renderizado gráfico estrictamente desacoplados en componentes de interfaz (`ui.js`).
2. **Modularidad Estricta en JavaScript**:
   - Uso de módulos ES6 (`import` / `export`) para evitar contaminación del ámbito global.
   - Prohibido el uso de scripts monolíticos superiores a 300 líneas por archivo.

### 🛡️ B. Normas Estrictas de Manejo de Errores
1. **Captura Robusta (Try/Catch & Async/Await)**:
   - Toda operación asíncrona (fetch, llamadas a Google Sheets, peticiones al Bot de Telegram o LiteLLM) debe envolverse en bloques `try/catch` con tipado de errores descriptivo.
2. **Resiliencia ante Fallos de Red / Rate Limits (HTTP 429 / 402)**:
   - Implementación obligatoria de reintentos con espera exponencial (*exponential backoff*) y fallback automático configurado en el proxy LiteLLM (`simple-shuffle`).
3. **Feedback Visual y Logs**:
   - Ningún error debe ser silencioso (`console.log` vacío). Todo error crítico debe mostrar notificaciones claras en la UI para el usuario y registrar logs estructurados con marca de tiempo.

---

## 🗺️ 3. Plan de Tareas Pendientes (Roadmap)

- [x] **Fase 1**: Configuración del entorno base, proxy LiteLLM y validación E2E de modelos en OpenRouter.
- [ ] **Fase 2**: Desarrollo del módulo cliente de Google Sheets (conexión, lectura y escritura de transacciones y precios de activos).
- [ ] **Fase 3**: Implementación de la interfaz web frontend (HTML/JS) para el dashboard de portfolio y gráficos de evolución de activos.
- [ ] **Fase 4**: Desarrollo e integración del Bot de Telegram para alertas de precios y comandos de resumen de portfolio.
- [ ] **Fase 5**: Pruebas de integración end-to-end (Frontend <-> Google Sheets <-> Telegram Bot <-> IA LiteLLM).
