# session_manager.py - Session management and shared memory across agents.

import os
import json
import time
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class SessionManager:
    def __init__(self, storage_dir=None):
        if storage_dir is None:
            storage_dir = PROJECT_ROOT / 'storage' / 'sessions'
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.session_file = self.storage_dir / 'active_session.json'
        self.session_history = []
        self.history_file = self.storage_dir / 'session_history.json'
        self.load_session()

    def load_session(self):
        """Load the active session and persistent history when available."""
        if self.history_file.exists():
            try:
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                if isinstance(data, list):
                    self.session_history = data
            except (OSError, json.JSONDecodeError):
                self.session_history = []

        if self.session_file.exists():
            try:
                with open(self.session_file, 'r', encoding='utf-8') as f:
                    active = json.load(f)
                ids = {session.get('id') for session in self.session_history}
                if isinstance(active, dict) and active.get('id') not in ids:
                    self.session_history.append(active)
            except (OSError, json.JSONDecodeError):
                pass

    def _save_history(self):
        with open(self.history_file, 'w', encoding='utf-8') as f:
            json.dump(self.session_history, f, ensure_ascii=False, indent=2)

    def list_sessions(self):
        """Return known sessions, ordered from newest to oldest."""
        return list(reversed(self.session_history))

    def start_session(self, agent_type='default'):
        session = {
            'id': int(time.time()),
            'agente_tipo': agent_type,
            'inicio': datetime.now().isoformat(),
            'modelo_usado': None,
            'tokens_consumidos': 0,
            'errores': 0
        }
        with open(self.session_file, 'w', encoding='utf-8') as f:
            json.dump(session, f, ensure_ascii=False, indent=2)
        self.session_history.append(session)
        self._save_history()
        return session['id']

    def update_session(self, session_id, model=None, tokens=0, error=False):
        if not self.session_file.exists():
            return
        with open(self.session_file, 'r', encoding='utf-8') as f:
            session = json.load(f)
        if session['id'] == session_id:
            if model:
                session['modelo_usado'] = model
            session['tokens_consumidos'] += tokens
            if error:
                session['errores'] += 1
            session['ultimo_acceso'] = datetime.now().isoformat()
            with open(self.session_file, 'w', encoding='utf-8') as f:
                json.dump(session, f, ensure_ascii=False, indent=2)

    def get_current_session(self):
        if not self.session_file.exists():
            return None
        with open(self.session_file, 'r', encoding='utf-8') as f:
            return json.load(f)

    def close_session(self):
        if self.session_file.exists():
            os.remove(self.session_file)

    def get_statistics(self):
        total_sessions = len(self.session_history)
        total_tokens = sum(s.get('tokens_consumidos', 0) for s in self.session_history)
        total_errors = sum(s.get('errores', 0) for s in self.session_history)
        return {
            'total_sesiones': total_sessions,
            'total_tokens': total_tokens,
            'total_errores': total_errors,
            'modelo_mas_usado': self._most_used_model()
        }

    def _most_used_model(self):
        models = {}
        for session in self.session_history:
            model = session.get('modelo_usado')
            if model:
                models[model] = models.get(model, 0) + 1
        return max(models, key=models.get) if models else None

    def export_history(self, output_file=None):
        if output_file is None:
            output_file = 'session_history_' + str(int(time.time())) + '.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(self.session_history, f, ensure_ascii=False, indent=2)
        return output_file
