# Cline Configuration (OpenAI Compatible) with Freellmpool

To configure Cline (or Roo Code) in VS Code to use the local **freellmpool**
proxy with the provided Gemini key:

1. In the Cline / Roo Code panel, select the **OpenAI Compatible** provider
   (or **Custom OpenAI / Ollama / etc.**).
2. Set the following parameters:
   - **Base URL**: `http://localhost:8080/v1`
   - **API Key**: Any non-empty value (local authentication is disabled)
   - **Model ID**: `auto` (o `gemini-1.5-flash`)
3. Save the configuration and verify that Cline responds correctly using the
   local proxy with free automatic load balancing.
