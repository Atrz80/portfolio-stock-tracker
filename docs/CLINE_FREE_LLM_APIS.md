# Trying Free APIs with Cline or Roo Code

[`awesome-free-llm-apis`](https://github.com/mnfst/awesome-free-llm-apis) is
a catalog of independent services, not an API, proxy, or extension that can be
installed to enable all its providers at once. To try one, configure its
compatible URL, model, and credentials in Cline/Roo Code if required. Tool and
streaming compatibility varies by provider.

## Tested configuration: Kilo Code

Cline is installed in this environment. Kilo's endpoint was tested with an
OpenAI-compatible request, and the model responded without credentials. In
Cline settings, select **OpenAI Compatible** and configure:

- **Base URL:** `https://api.kilo.ai/api/gateway`
- **Model ID:** `kilo-auto/free`
- **API key:** leave it blank; it is not required for this endpoint.

Save the settings and start with a simple request. The model is a free router
that may select different models; availability, limits, and tool support may
change. The current list is at
[`awesome-free-llm-apis`](https://github.com/mnfst/awesome-free-llm-apis).

If you configure a provider that does require a key, store it in the
extension's secure storage; do not add it to the repository,
`.vscode/settings.json`, or the application configuration.

The **Roo Code** extension is installed in this environment. To configure a
Cline installation instead of Roo Code, the two extensions can be configured
separately.

The existing Freellmpool configuration is separate and documented in
[CLINE_OPENAI_COMPATIBLE.md](./CLINE_OPENAI_COMPATIBLE.md).
