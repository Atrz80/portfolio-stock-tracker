# Freellmpool client with automatic rotation and resilient retries.

import random
import time
from typing import Any

import requests


class FreellmpoolClient:
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.available_models = [
            'auto', 'fast', 'quality', 'fair', 'agent', 'spread'
        ]
        self.current_model_index = 0
        self.success_history: list[dict[str, Any]] = []
        self.max_retries = 3
        self.timeout = 90

    def _get_next_model(self) -> str:
        model = self.available_models[self.current_model_index]
        self.current_model_index = (self.current_model_index + 1) % len(
            self.available_models
        )
        return model

    @staticmethod
    def _extract_error(response: requests.Response) -> str:
        try:
            body = response.json()
            error = body.get('error', body) if isinstance(body, dict) else body
            if isinstance(error, dict):
                return str(error.get('message') or error)
            return str(error)
        except (ValueError, TypeError):
            return response.text[:300]

    def chat_complete(
        self,
        message: str,
        system_prompt: str | None = None,
        max_retries: int | None = None,
    ) -> str:
        if max_retries is None:
            max_retries = self.max_retries
        max_retries = max(1, int(max_retries))

        messages: list[dict[str, str]] = []
        if system_prompt:
            messages.append({'role': 'system', 'content': system_prompt})
        messages.append({'role': 'user', 'content': str(message)})

        url = f'{self.base_url}/chat/completions'
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
        }
        last_error = 'unknown'

        for attempt in range(max_retries):
            current_model = self._get_next_model()
            payload = {'model': current_model, 'messages': messages}
            try:
                response = requests.post(
                    url, headers=headers, json=payload, timeout=self.timeout
                )
                if response.ok:
                    data = response.json()
                    reply = data['choices'][0]['message']['content']
                    self.success_history.append(
                        {'model': current_model, 'attempt': attempt}
                    )
                    return str(reply)

                last_error = self._extract_error(response)
                status = response.status_code
                if status in (402, 429):
                    print(
                        f'Model {current_model}: quota/payment error {status}; '
                        'trying another model with backoff.'
                    )
                else:
                    print(
                        f'Model {current_model} failed ({status}): '
                        f'{last_error[:160]}'
                    )
            except requests.RequestException as exc:
                last_error = str(exc)
                print(f'Model {current_model}: network error: {last_error[:160]}')

            if attempt + 1 < max_retries:
                delay = min(2 ** attempt + random.uniform(0, 0.5), 10)
                time.sleep(delay)

        return (
            'Error: Could not complete the request after '
            f'{max_retries} attempts. Last error: {last_error[:200]}'
        )

    def get_status(self) -> dict[str, Any]:
        return {
            'current_model': self.available_models[self.current_model_index],
            'index': self.current_model_index,
            'successful_requests': len(self.success_history),
        }
