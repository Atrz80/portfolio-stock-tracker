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
class AIAgency:
    """Main class that configures the AI agency with specialized agents and persistent memory."""

    def __init__(self):
        """Initialize the agency with model, tool, and memory configuration."""
        # Configure LLMs
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

        # Conversation memory (CrewAI memory)
        self.memory = ConversationBufferMemory(
            chat_memory=ChatMessageHistory(),
            memory_key="chat_history",
            input_key="input",
            output_key="output",
        )

        # Create agents with basic tools
        self.architect = Agent(
            role="Solutions Architect",
            goal="Design robust and scalable software architectures",
            backstory=(
                "You are a senior architect with 15 years of experience in system design. "
                "You always seek the best technical solution, considering scalability, maintainability, and cost. "
                "Always remember the context of previous conversations."
            ),
            llm=self.gemini_15_pro,
            verbose=True,
            memory=True,
            allow_delegation=False,
            system_template=(
                "You are the Solutions Architect. Use your memory to recall past conversations "
                "and maintain consistency in your designs. Always respond in English."
            ),
        )

        self.developer = Agent(
            role="Senior Developer",
            goal="Implement high-quality software solutions",
            backstory=(
                "You are a full-stack developer experienced in multiple technologies and paradigms. "
                "Turn architectural designs into clean, efficient code. "
                "Always remember the context of previous conversations."
            ),
            llm=self.gemini_2_0_flash,
            verbose=True,
            memory=True,
            allow_delegation=False,
            system_template=(
                "You are the Senior Developer. Use your memory to recall past conversations "
                "and maintain consistency in your implementations. Always respond in English."
            ),
        )

    def run_task(self, description: str, agent_role: str = "Architect", context: Optional[str] = None):
        """Run a task with the specified agent and save the result to memory."""
        selected_agent = self.architect if agent_role == "Architect" else self.developer

        task = Task(
            description=description,
            agent=selected_agent,
            expected_output="A detailed, well-structured solution",
            context=context if context else "",
        )

        crew = Crew(
            agents=[selected_agent],
            tasks=[task],
            verbose=2,
            memory=True,
        )

        result = crew.kickoff()

        # Save to conversation memory
        self.memory.save_context(
            {"input": description},
            {"output": str(result)},
        )

        return result

    def converse(self, message: str, agent_role: str = "Architect") -> str:
        """Continue a conversation while retaining contextual memory."""
        # Retrieve memory
        memories = self.memory.load_memory_variables({})
        context = memories.get("chat_history", "")

        # Build a prompt with context
        complete_prompt = f"Previous context:\n{context}\n\nNew message:\n{message}"

        # Run the task
        result = self.run_task(
            description=complete_prompt,
            agent_role=agent_role,
            context=context,
        )

        return str(result)


# Global agency instance
agency = AIAgency()

if __name__ == "__main__":
    print("🚀 AI agency initialized successfully")
    print("Available agents: Architect, Developer")
    print("CrewAI memory is active - conversations are saved automatically")

    # Usage example
    print("\n=== Conversation example ===")
    result1 = agency.converse(
        "Design an architecture for a real-time recommendation system",
        agent_role="Architect",
    )
    print(f"\n✅ Result 1:\n{result1[:200]}...")

    result2 = agency.converse(
        "Now implement that design in Python using FastAPI and Celery",
        agent_role="Developer",
    )
    print(f"\n✅ Result 2:\n{result2[:200]}...")