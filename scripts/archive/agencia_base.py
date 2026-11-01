import os
from crewai import Agent, Crew, Task, LLM
from crewai.project import Agentic, agent, task
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.memory import ConversationBufferMemory
from langchain_community.chat_message_histories import ChatMessageHistory
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Dict, List, Optional


class Config(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")
    google_api_key: str = ""


config = Config()


@Agentic
class AgenciaIA:
    """Clase principal que configura la agencia de IA con agentes especializados y memoria persistente."""

    def __init__(self):
        """Inicializa la agencia con configuración de modelos, herramientas y memoria."""
        # Configurar LLMs
        self.gemini_15_pro = ChatGoogleGenerativeAI(
            model="gemini-1.5-pro",
            temperature=0.7,
            google_api_key=config.google_api_key,
        )

        self.gemini_2_0_flash = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash",
            temperature=0.7,
            google_api_key=config.google_api_key,
        )

        # Memoria de conversación (CrewAI memory)
        self.memory = ConversationBufferMemory(
            chat_memory=ChatMessageHistory(),
            memory_key="chat_history",
            input_key="input",
            output_key="output",
        )

        # Crear agentes con herramientas básicas
        self.arquitecto = Agent(
            role="Arquitecto de Soluciones",
            goal="Diseñar arquitecturas de software robustas y escalables",
            backstory=(
                "Eres un arquitecto senior con 15 años de experiencia en diseño de sistemas. "
                "Siempre buscas la mejor solución técnica considerando escalabilidad, mantenibilidad y costos. "
                "Recuerdas siempre el contexto de conversaciones anteriores."
            ),
            llm=self.gemini_15_pro,
            verbose=True,
            memory=True,
            allow_delegation=False,
            system_template=(
                "Eres el Arquitecto de Soluciones. Usas tu memoria para recordar conversaciones pasadas "
                "y mantener coherencia en los diseños. Responde siempre en español."
            ),
        )

        self.desarrollador = Agent(
            role="Desarrollador Senior",
            goal="Implementar soluciones de software de alta calidad",
            backstory=(
                "Eres un desarrollador full-stack con experiencia en múltiples tecnologías y paradigmas. "
                "Convierte los diseños arquitectónicos en código limpio y eficiente. "
                "Recuerdas siempre el contexto de conversaciones anteriores."
            ),
            llm=self.gemini_2_0_flash,
            verbose=True,
            memory=True,
            allow_delegation=False,
            system_template=(
                "Eres el Desarrollador Senior. Usas tu memoria para recordar conversaciones pasadas "
                "y mantener coherencia en las implementaciones. Responde siempre en español."
            ),
        )

    def ejecutar_tarea(self, description: str, agent_role: str = "Arquitecto", context: Optional[str] = None):
        """Ejecuta una tarea con el agente especificado, guardando memoria del resultado."""
        agente = self.arquitecto if agent_role == "Arquitecto" else self.desarrollador

        task = Task(
            description=description,
            agent=agente,
            expected_output="Una solución detallada y bien estructurada",
            context=context if context else "",
        )

        crew = Crew(
            agents=[agente],
            tasks=[task],
            verbose=2,
            memory=True,
        )

        resultado = crew.kickoff()

        # Guardar en memoria de conversación
        self.memory.save_context(
            {"input": description},
            {"output": str(resultado)},
        )

        return resultado

    def conversar(self, mensaje: str, agente: str = "Arquitecto") -> str:
        """Conversación continua con memoria del contexto."""
        # Recuperar memoria
        memories = self.memory.load_memory_variables({})
        contexto = memories.get("chat_history", "")

        # Construir prompt con contexto
        prompt_completo = f"Contexto anterior:\n{contexto}\n\nNuevo mensaje:\n{mensaje}"

        # Ejecutar tarea
        resultado = self.ejecutar_tarea(
            description=prompt_completo,
            agent_role=agente,
            context=contexto,
        )

        return str(resultado)


# Instancia global de la agencia
agencia = AgenciaIA()

if __name__ == "__main__":
    print("🚀 Agencia IA inicializada correctamente")
    print("Agentes disponibles: Arquitecto, Desarrollador")
    print("Memoria CrewAI activa - conversaciones se guardan automáticamente")

    # Ejemplo de uso
    print("\n=== Ejemplo de conversación ===")
    resultado1 = agencia.conversar(
        "Diseña una arquitectura para un sistema de recomendaciones en tiempo real",
        agente="Arquitecto",
    )
    print(f"\n✅ Resultado 1:\n{resultado1[:200]}...")

    resultado2 = agencia.conversar(
        "Ahora implementa ese diseño en Python usando FastAPI y Celery",
        agente="Desarrollador",
    )
    print(f"\n✅ Resultado 2:\n{resultado2[:200]}...")