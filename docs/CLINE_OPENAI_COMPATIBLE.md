# CLINE_OPENAI_COMPATIBLE.md - Cline's OpenAI-Compatible Configuration for Freellmpool

## Cline Configuration (VS Code Extension)

To make Cline work with freellmpool and automatic model rotation, configure
Cline as **OpenAI Compatible**:

### Step 1: Open Cline Settings
In VS Code, open the Command Palette (Ctrl+Shift+P) and search for:
`Cline: Open Settings`

### Step 2: Configure OpenAI Compatible
Set the following values in Cline:

| Field | Value |
|-------|-------|
| Provider | OpenAI Compatible |
| Base URL | `http://localhost:8080/v1` |
| API Key | Any non-empty value (local authentication is disabled) |
| Model | `auto` (uses automatic rotation) |

### Step 3: Models available in freellmpool
freellmpool automatically rotates among these models:
- `auto` - Automatic selection
- `gemini-1.5-flash` - Fast Gemini model
- `agent` - Optimized for agents
- `spread` - Balanced
- `fast` - Fast response

### Step 4: Automatic rotation
The `app/freellmpool_client.py` client handles automatic rotation. Shared
configuration is located in `E:\Proyectos\ai-workstation\.env` and loaded by
`app/config.py`:
- If a model fails (token exhaustion, rate limit, etc.), it tries the next one
- Implements exponential retry with backoff
- Logs which models succeeded

## Using the start_all.bat script

Running `start_all.bat` will:
1. Start the FastAPI backend (port 8000)
2. Check freellmpool (port 8080)
3. Show a menu with chat, agency, memory, and statistics options

Selecting **Exit (option 6)** stops all processes.

## Key files
- `app/freellmpool_client.py` - Client with automatic rotation and retry
- `app/session_manager.py` - Session and shared-memory management
- `app/agency.py` - 3 specialized agents (analyst, architect, optimizer)
- `app/chat.py` - Chat with persistent memory
- `app/agent_memory.py` - Persistent remember/recall memory
- `app/main.py` - FastAPI with REST endpoints
- `main.py` - Launcher compatible with `uvicorn main:app`
- `.env` - Environment variables