# Probar APIs gratuitas con Cline o Roo Code

[`awesome-free-llm-apis`](https://github.com/mnfst/awesome-free-llm-apis) es
un catálogo de servicios independientes, no una API, proxy ni extensión que se
pueda instalar para habilitar todos sus proveedores a la vez. Para probar uno
hay que configurar en Cline/Roo Code su URL compatible, modelo y credencial si
la requiere. La compatibilidad con herramientas y streaming varía por
proveedor.

## Configuración probada: Kilo Code

La extensión Cline está instalada en este entorno. Se probó el endpoint de Kilo
con una petición compatible con OpenAI y el modelo respondió sin credenciales.
En los ajustes de Cline, selecciona **OpenAI Compatible** y configura:

- **Base URL:** `https://api.kilo.ai/api/gateway`
- **Model ID:** `kilo-auto/free`
- **API key:** déjala vacía; no se necesita para este endpoint.

Guarda los ajustes y prueba primero con una petición sencilla. El modelo es un
router gratuito y puede seleccionar modelos distintos; disponibilidad, límites
y soporte de herramientas pueden cambiar. La lista vigente está en
[`awesome-free-llm-apis`](https://github.com/mnfst/awesome-free-llm-apis).

Si configuras un proveedor que sí requiere clave, guárdala en el almacén seguro
de la extensión; no la añadas al repositorio, `.vscode/settings.json` ni a la
configuración de la aplicación.

Este entorno tiene instalada la extensión **Roo Code**. Para configurar una
instalación de Cline en vez de Roo Code, ambas extensiones pueden configurarse
por separado.

La configuración existente de Freellmpool es independiente y está documentada
en [CLINE_OPENAI_COMPATIBLE.md](./CLINE_OPENAI_COMPATIBLE.md).
