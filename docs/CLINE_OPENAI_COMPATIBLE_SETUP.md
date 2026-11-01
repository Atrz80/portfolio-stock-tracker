# Configuración de Cline (OpenAI Compatible) con Freellmpool

Para configurar Cline (o Roo Code) en VS Code para que utilice el proxy local **freellmpool** con la clave de Gemini proporcionada:

1. En el panel de Cline / Roo Code, selecciona el proveedor **OpenAI Compatible** (o **Custom OpenAI / Ollama / etc.**).
2. Configura los siguientes parámetros:
   - **Base URL**: `http://localhost:8080/v1`
   - **API Key**: Cualquier valor no vacío (la autenticación local está desactivada)
   - **Model ID**: `auto` (o `gemini-1.5-flash`)
3. Guarda la configuración y verifica que Cline responde correctamente utilizando el proxy local con balanceo automático gratuito.
