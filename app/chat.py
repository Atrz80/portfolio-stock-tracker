# chat.py - Chat with freellmpool, automatic rotation, and persistent memory.

import os
from .config import load_configuration
from .freellmpool_client import FreellmpoolClient
from .agent_memory import recall, remember

load_configuration()

BASE_URL = os.getenv('OPENAI_BASE_URL', 'http://localhost:8080/v1')
API_KEY = os.getenv('OPENAI_API_KEY', 'local')

client = FreellmpoolClient(BASE_URL, API_KEY)

def chat_with_memory(message):
    try:
        memories = recall(message, limit=3)
        context_str = '\n'.join(
            [str(memory.get('text', memory)) for memory in memories]
        ) if memories else 'None'
        system_prompt = (
            'You are an intelligent financial and software assistant integrated '
            'with Portfolio Stock Tracker.\nRetrieved context:\n' + context_str
        )
        reply = client.chat_complete(message, system_prompt=system_prompt)
        remember('User: ' + message + ' | Assistant: ' + reply, source='chat_interaction')
        return reply
    except Exception as e:
        return 'Chat error with freellmpool: ' + str(e)
