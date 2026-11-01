# Cliente freellmpool con rotación automática y reintentos resilientes.

import random
import time
from typing import Any

import requests


class FreellmpoolClient:
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.modelos_disponibles = [
            'auto', 'fast', 'quality', 'fair', 'agent', 'spread'
        ]
        self.indice_modelo_actual = 0
        self.historial_exitoso: list[dict[str, Any]] = []
        self.max_reintentos = 3
        self.timeout = 90

    def _obtener_modelo_siguiente(self) -> str:
        modelo = self.modelos_disponibles[self.indice_modelo_actual]
        self.indice_modelo_actual = (self.indice_modelo_actual + 1) % len(
            self.modelos_disponibles
        )
        return modelo

    @staticmethod
    def _extraer_error(response: requests.Response) -> str:
        try:
            body = response.json()
            error = body.get('error', body) if isinstance(body, dict) else body
            if isinstance(error, dict):
                return str(error.get('message') or error)
            return str(error)
        except (ValueError, TypeError):
            return response.text[:300]

    def chat_completar(
        self,
        mensaje: str,
        system_prompt: str | None = None,
        max_reintentos: int | None = None,
    ) -> str:
        if max_reintentos is None:
            max_reintentos = self.max_reintentos
        max_reintentos = max(1, int(max_reintentos))

        mensajes: list[dict[str, str]] = []
        if system_prompt:
            mensajes.append({'role': 'system', 'content': system_prompt})
        mensajes.append({'role': 'user', 'content': str(mensaje)})

        url = f'{self.base_url}/chat/completions'
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
        }
        ultimo_error = 'desconocido'

        for intento in range(max_reintentos):
            modelo_actual = self._obtener_modelo_siguiente()
            payload = {'model': modelo_actual, 'messages': mensajes}
            try:
                response = requests.post(
                    url, headers=headers, json=payload, timeout=self.timeout
                )
                if response.ok:
                    data = response.json()
                    reply = data['choices'][0]['message']['content']
                    self.historial_exitoso.append(
                        {'modelo': modelo_actual, 'intento': intento}
                    )
                    return str(reply)

                ultimo_error = self._extraer_error(response)
                status = response.status_code
                if status in (402, 429):
                    print(
                        f'Modelo {modelo_actual}: cuota/pago {status}; '
                        'probando otro modelo con backoff.'
                    )
                else:
                    print(
                        f'Modelo {modelo_actual} falló ({status}): '
                        f'{ultimo_error[:160]}'
                    )
            except requests.RequestException as exc:
                ultimo_error = str(exc)
                print(f'Modelo {modelo_actual}: error de red: {ultimo_error[:160]}')

            if intento + 1 < max_reintentos:
                espera = min(2 ** intento + random.uniform(0, 0.5), 10)
                time.sleep(espera)

        return (
            'Error: No fue posible completar la solicitud después de '
            f'{max_reintentos} intentos. Último error: {ultimo_error[:200]}'
        )

    def obtener_estado(self) -> dict[str, Any]:
        return {
            'modelo_actual': self.modelos_disponibles[self.indice_modelo_actual],
            'indice': self.indice_modelo_actual,
            'historial_exitoso': len(self.historial_exitoso),
        }
