# MEMORY.md - Memoria Persistente del Proyecto (Portfolio Financiero Android + Backend Python + Gemini)

## 🎯 1. Objetivos del Proyecto
Desarrollar una aplicación móvil nativa en Android para el control y seguimiento de un portfolio financiero personal con datos y gráficos en tiempo real, impulsada por análisis y recomendaciones de la API de Google Gemini (Free Tier).

## 🏗️ 2. Arquitectura del Sistema
- **Frontend**: Android (Kotlin / Jetpack Compose) - Interfaz de usuario moderna, gráficos en tiempo real con Canvas y consumo de API REST.
- **Backend**: Python (FastAPI + Uvicorn) - API REST central, lógica de negocio y procesamiento de datos financieros.
- **Inteligencia Artificial**: Google Gemini API (`gemini-1.5-flash`) para análisis predictivo y asesoramiento financiero automatizado.
- **Persistencia / Base de Datos**: ChromaDB y almacenamiento ligero en SQLite/JSON para el portfolio local.
- **Contenedorización, CI/CD & Autocuración**: Docker & Docker Compose para el backend, GitHub Actions para APKs y bot autónomo de autocuración con Gemini (`auto-fix.yml` y `autofix.py`).

## 🛠️ 3. Decisiones Técnicas Tomadas
- Uso del SDK oficial de Google (`google-generativeai`) conectado directamente.
- Uso del modelo Free Tier `gemini-1.5-flash` por su alta velocidad y manejo de cuotas.
- FastAPI en el backend con soporte para recarga en caliente en Docker.
- API Key configurada y validada en `.env`.
- Frontend Android estructurado con Jetpack Compose, Retrofit y gráficos vectoriales nativos en Canvas (`PriceChartCard`).
- GitHub Actions configurado con Gradle 8.7 y AGP 8.4.0.
- **Sistema Autónomo de Autocuración (`auto-fix.yml` y `autofix.py`)**: Analiza fallos de compilación mediante Gemini AI, aplica correcciones (como `android.useAndroidX=true`) y hace commit/push automático a `main`.

## 📊 4. Estado Actual de Avance
- [x] Limpieza y optimización del entorno Docker (eliminación de One-API, MySQL, Redis).
- [x] Creación de la estructura base del backend (FastAPI + Gemini).
- [x] Configuración de credenciales (`GOOGLE_API_KEY`) y variables de entorno.
- [x] Implementación de endpoints de prueba para portfolio financiero y Gemini.
- [x] Creación de la estructura frontend Android en Kotlin con Jetpack Compose (DashboardScreen, Modelos y Retrofit).
- [x] Implementación de componente de gráficos de evolución de precios en tiempo real (`PriceChartComponent.kt`).
- [x] Configuración y optimización del pipeline de CI/CD en GitHub Actions (Gradle 8.7 + AGP 8.4.0).
- [x] Configuración del Sistema Autónomo de Autocuración en GitHub con Gemini AI (`auto-fix.yml` + `autofix.py`).
- [ ] Pruebas end-to-end de integración Frontend <-> Backend.





