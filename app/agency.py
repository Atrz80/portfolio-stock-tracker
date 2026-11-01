# agency.py - Agencia con tres perfiles especializados sobre Freellmpool.

import os
from typing import Any

from crewai import Agent, Crew, LLM, Process, Task
from .config import load_configuration
from .freellmpool_client import FreellmpoolClient
from .session_manager import SessionManager

load_configuration()

BASE_URL = os.getenv('OPENAI_BASE_URL', 'http://localhost:8080/v1')
API_KEY = os.getenv('OPENAI_API_KEY', 'local')
MODEL = os.getenv('MODEL', 'auto')
if MODEL in ('gemini-1.5-flash', 'gemini-1.5-pro'):
    MODEL = 'auto'
AGENCY_MODE = os.getenv('CREWAI_AGENCY_MODE', 'direct').lower()

freellmpool_client = FreellmpoolClient(BASE_URL, API_KEY)
session_manager = SessionManager()
llm = LLM(
    model=MODEL,
    base_url=BASE_URL,
    api_key=API_KEY,
    custom_openai=True,
)

PROFILES: dict[str, dict[str, str]] = {
    'analyst': {
        'role': 'Analista Financiero y de Software',
        'goal': 'Validar cotizaciones push por símbolo y explicar cambios, variación, timestamp y estado de mercado.',
        'backstory': 'Experto en análisis cuantitativo, validación de ticks y gestión de riesgos.',
    },
    'architect': {
        'role': 'Arquitecto de Soluciones',
        'goal': 'Diagnosticar la conexión push de mercado, reconexiones, heartbeat y difusión WebSocket.',
        'backstory': 'Arquitecto senior especializado en streaming WebSocket y sistemas resilientes.',
    },
    'optimizer': {
        'role': 'Optimizador de Portafolio',
        'goal': 'Revisar valor, P&L, asignación y efectos de cada actualización individual de precio.',
        'backstory': 'Especialista en optimización matemática y Cartera de activos en tiempo real.',
    },
}

agents = {
    name: Agent(
        role=profile['role'],
        goal=profile['goal'],
        backstory=profile['backstory'],
        verbose=False,
        memory=True,
        allow_delegation=False,
        llm=llm,
    )
    for name, profile in PROFILES.items()
}


def _run_direct(profile: dict[str, str], objective: str) -> str:
    messages = [
        {
            'role': 'system',
            'content': (
                f"Actúa como {profile['role']}. {profile['backstory']} "
                f"Objetivo: {profile['goal']} Responde en español y de forma clara."
            ),
        },
        {'role': 'user', 'content': objective},
    ]
    # Use the resilient gateway client so every agent gets model rotation and
    # bounded backoff on quota/payment/network failures.
    result = freellmpool_client.chat_completar(
        objective,
        system_prompt=messages[0]['content'],
    )
    if result.startswith('Error:'):
        raise RuntimeError(result)
    return str(result) if result else 'No output generated.'


def _run_crew(agent: Agent, objective: str) -> str:
    task = Task(
        description='Analizar el siguiente objetivo: ' + objective,
        expected_output='Reporte detallado con recomendaciones accionables.',
        agent=agent,
    )
    crew = Crew(
        agents=[agent],
        tasks=[task],
        process=Process.sequential,
        memory=True,
        verbose=False,
    )
    result = crew.kickoff()
    return str(result) if result else 'No output generated.'


def run_agency_task(
    objective: str,
    agente_tipo: str = 'analyst',
    mode: str | None = None,
) -> dict[str, Any]:
    selected_mode = (mode or AGENCY_MODE).lower()
    try:
        session_id = session_manager.iniciar_sesion(agente_tipo)
        agent_name = agente_tipo if agente_tipo in PROFILES else 'analyst'
        profile = PROFILES[agent_name]

        if selected_mode == 'crew':
            output_text = _run_crew(agents[agent_name], objective)
        else:
            output_text = _run_direct(profile, objective)

        session_manager.actualizar_sesion(session_id, MODEL)
        return {
            'status': 'success',
            'objective': objective,
            'agente_usado': agent_name,
            'modelo_usado': MODEL,
            'modo': selected_mode,
            'result': output_text,
        }
    except Exception as exc:
        session = session_manager.obtener_sesion_actual()
        if session:
            session_manager.actualizar_sesion(session['id'], error=True)
        return {
            'status': 'error',
            'message': str(exc),
            'objective': objective,
            'modo': selected_mode,
        }


def obtener_estadisticas_agencia() -> dict[str, Any]:
    return session_manager.obtener_estadisticas()
