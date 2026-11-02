import os
import sys
import time
import requests

# Force UTF-8 encoding to avoid emoji-related errors on Windows
os.environ["PYTHONIOENCODING"] = "utf-8"
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

from dotenv import load_dotenv
from crewai import Agent, Crew, Process, Task

load_dotenv()

# Ensure OPENROUTER_API_KEY is available to CrewAI / LiteLLM
if not os.getenv("OPENROUTER_API_KEY") and os.getenv("OPENAI_API_KEY"):
    os.environ["OPENROUTER_API_KEY"] = os.getenv("OPENAI_API_KEY")

# Configure an OpenRouter-based LLM for CrewAI
llm = os.getenv("MODEL", "openrouter/deepseek/deepseek-chat")

def fetch_github_issues():
    """Fetch open GitHub repository issues using exponential backoff."""
    repo = "Atrz80/portfolio-stock-tracker"
    url = f"https://api.github.com/repos/{repo}/issues?state=open"
    headers = {"Accept": "application/vnd.github+json"}
    token = os.getenv("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    
    retries = 3
    delay = 2
    for attempt in range(retries):
        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                issues = response.json()
                if not issues:
                    return "There are currently no open issues in the repository."
                return "\n".join([f"- Issue #{i.get('number')}: {i.get('title')}\n  Body: {i.get('body')}" for i in issues])
            elif response.status_code == 429:
                print(f"⚠️ Rate limit reached (429). Retrying in {delay}s...")
                time.sleep(delay)
                delay *= 2
            else:
                return f"Error querying the GitHub API: {response.status_code} - {response.text}"
        except Exception as e:
            if attempt == retries - 1:
                return f"Exception connecting to the GitHub API: {e}"
            time.sleep(delay)
            delay *= 2
    return "Could not retrieve GitHub issues due to network or quota limits."

# --- 1. Define Specialized Agents ---

expert_developer = Agent(
    role="Expert Software Developer",
    goal="Write clean, production-ready, modular ES6 JavaScript and Python code adhering strictly to architectural guidelines and separation of concerns.",
    backstory="Master software engineer specialized in scalable applications, clean code, and robust implementation for web and data systems.",
    verbose=True,
    llm=llm,
)

expert_tester = Agent(
    role="Senior QA & Testing Engineer",
    goal="Design comprehensive unit tests, integration tests, and validation suites to ensure zero regressions and robust functionality.",
    backstory="Obsessed with test-driven development (TDD), edge cases, mocking, and rigorous software validation.",
    verbose=True,
    llm=llm,
)

github_resolver = Agent(
    role="GitHub Incident & Issue Resolver",
    goal="Analyze incoming GitHub issues, bug reports, and traceback errors from code commits, then provide precise debugging patches and fixes.",
    backstory="Expert troubleshooter and DevOps engineer specialized in debugging production failures, parsing stack traces, and resolving GitHub issues swiftly.",
    verbose=True,
    llm=llm,
)

# --- 2. Define Crew Tasks ---

dev_task = Task(
    description=(
        "Develop the core portfolio stock tracker modules (data schema, Google Sheets connection service, "
        "and modular ES6 frontend components for P&L calculations). Ensure strict adherence to separation of concerns."
    ),
    expected_output="Production-ready modular code implementation for the portfolio tracking system.",
    agent=expert_developer,
)

test_task = Task(
    description=(
        "Create comprehensive unit tests and test suites for the newly implemented portfolio tracker modules, "
        "validating calculations, edge cases, and error handling."
    ),
    expected_output="Complete unit test files and testing instructions.",
    agent=expert_tester,
)

issue_resolution_task = Task(
    description=(
        "Analyze the following open GitHub issues for the repository and provide robust code patches and resolution reports:\n\n"
        f"{fetch_github_issues()}"
    ),
    expected_output="A troubleshooting report with exact code patches for resolving open GitHub issues.",
    agent=github_resolver,
)

# --- 3. Assemble the Crew ---

portfolio_crew = Crew(
    agents=[expert_developer, expert_tester, github_resolver],
    tasks=[dev_task, test_task, issue_resolution_task],
    process=Process.sequential,
    verbose=True,
)

if __name__ == "__main__":
    print("Starting CrewAI with the specialized team (Developer, Tester, GitHub Incident Resolver)...")
    try:
        result = portfolio_crew.kickoff()
        print("\n\n########################")
        print("## Crew Result ##")
        print("########################\n")
        print(result)
    except Exception as e:
        print(f"❌ Error during CrewAI execution: {e}")
