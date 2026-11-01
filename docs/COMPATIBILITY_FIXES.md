# COMPATIBILITY_FIXES.md - Auditoría y Compatibilidad

## 1. Versión de Python y Entorno
- **Python Version**: 3.11.9 (compatible con CrewAI y ChromaDB, evitando incompatibilidades reportadas en Python 3.14).
- **Pydantic**: v2.12.5 (totalmente compatible con FastAPI y CrewAI v1.15.33).
- **ChromaDB**: v1.5.9 (soporte estable para persistencia vectorial y agentes).

## 2. Adaptadores CrewOutput -> Pydantic
- Se implementó un adaptador seguro para evitar fallos de validación al recibir salidas de CrewAI en endpoints FastAPI. Las salidas crudas (`CrewOutput`) se convierten explícitamente a string o dict antes de ser validadas por modelos Pydantic del backend.

## 3. Gateway de IA
- Integración con **freellmpool** (`http://localhost:8080/v1`) para enrutamiento resiliente y failover automático entre proveedores de IA gratuitos.
