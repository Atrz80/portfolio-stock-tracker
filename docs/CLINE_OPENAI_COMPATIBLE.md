# CLINE_OPENAI_COMPATIBLE.md - Configuración de Cline para OpenAI Compatible con Freellmpool

## Configuración para Cline (VS Code Extension)

Para que Cline funcione con freellmpool y rotación automática de modelos, configura Cline como **OpenAI Compatible**:

### Paso 1: Abrir configuración de Cline
En VS Code, abre la paleta de comandos (Ctrl+Shift+P) y busca: `Cline: Open Settings`

### Paso 2: Configurar como OpenAI Compatible
Configura los siguientes valores en Cline:

| Campo | Valor |
|-------|-------|
| Provider | OpenAI Compatible |
| Base URL | `http://localhost:8080/v1` |
| API Key | Cualquier valor no vacío (la autenticación local está desactivada) |
| Model | `auto` (usa rotación automática) |

### Paso 3: Modelos disponibles en freellmpool
freellmpool rota automáticamente entre estos modelos:
- `auto` - Selección automática
- `gemini-1.5-flash` - Modelo rápido de Gemini
- `agent` - Optimizado para agentes
- `spread` - Balanceado
- `fast` - Respuesta rápida

### Paso 4: Rotación automática
El cliente `app/freellmpool_client.py` maneja la rotación automática. La configuración compartida reside en `E:\Proyectos\ai-workstation\.env` y se carga mediante `app/config.py`:
- Si un modelo falla (agotamiento de tokens, rate limit, etc.), prueba el siguiente
- Implementa retry exponencial con backoff
- Registra qué modelos tuvieron éxito

## Uso con el script start_all.bat

Ejecutar `start_all.bat` arrancará:
1. FastAPI backend (puerto 8000)
2. Verificará freellmpool (puerto 8080)
3. Mostrará un menú con opciones de chat, agencia, memoria y estadísticas

Al seleccionar **Salir (opción 6)**, se detendrán todos los procesos.

## Archivos clave
- `app/freellmpool_client.py` - Cliente con rotación automática y retry
- `app/session_manager.py` - Gestión de sesiones y memoria compartida
- `app/agency.py` - 3 agentes especializados (analyst, architect, optimizer)
- `app/chat.py` - Chat con memoria persistente
- `app/agent_memory.py` - Memoria persistente remember/recall
- `app/main.py` - FastAPI con endpoints REST
- `main.py` - Lanzador compatible con `uvicorn main:app`
- `.env` - Variables de entorno