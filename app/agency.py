# agency.py - Agency with three specialized profiles powered by Freellmpool.

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
        'role': 'Financial and Software Analyst',
        'goal': 'Validate push quotes by symbol and explain changes, price movement, timestamps, and market state.',
        'backstory': 'Expert in quantitative analysis, tick validation, and risk management.',
    },
    'architect': {
        'role': 'Solutions Architect',
        'goal': 'Diagnose the market data push connection, reconnections, heartbeats, and WebSocket delivery.',
        'backstory': 'Senior architect specializing in WebSocket streaming and resilient systems.',
    },
    'optimizer': {
        'role': 'Portfolio Optimizer',
        'goal': 'Review value, P&L, allocation, and the impact of each individual price update.',
        'backstory': 'Specialist in mathematical optimization and real-time portfolio management.',
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
                f"Act as {profile['role']}. {profile['backstory']} "
                f"Objective: {profile['goal']} Respond clearly in English."
            ),
        },
        {'role': 'user', 'content': objective},
    ]
    # Use the resilient gateway client for model rotation and bounded backoff.
    result = freellmpool_client.chat_complete(
        objective,
        system_prompt=messages[0]['content'],
    )
    if result.startswith('Error:'):
        raise RuntimeError(result)
    return str(result) if result else 'No output generated.'


def _run_crew(agent: Agent, objective: str) -> str:
    task = Task(
        description='Analyze the following objective: ' + objective,
        expected_output='Detailed report with actionable recommendations.',
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
    agent_type: str = 'analyst',
    mode: str | None = None,
) -> dict[str, Any]:
    selected_mode = (mode or AGENCY_MODE).lower()
    try:
        session_id = session_manager.start_session(agent_type)
        agent_name = agent_type if agent_type in PROFILES else 'analyst'
        profile = PROFILES[agent_name]

        if selected_mode == 'crew':
            output_text = _run_crew(agents[agent_name], objective)
        else:
            output_text = _run_direct(profile, objective)

        session_manager.update_session(session_id, MODEL)
        return {
            'status': 'success',
            'objective': objective,
            'agente_usado': agent_name,
            'modelo_usado': MODEL,
            'modo': selected_mode,
            'result': output_text,
        }
    except Exception as exc:
        session = session_manager.get_current_session()
        if session:
            session_manager.update_session(session['id'], error=True)
        return {
            'status': 'error',
            'message': str(exc),
            'objective': objective,
            'modo': selected_mode,
        }


def get_agency_statistics() -> dict[str, Any]:
    return session_manager.get_statistics()
