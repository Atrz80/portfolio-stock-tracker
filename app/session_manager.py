# session_manager.py - Gestión de sesiones y memoria compartida entre agentes

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
        self.historial_sesiones = []
        self.historial_file = self.storage_dir / 'session_history.json'
        self.cargar_sesion()

    def cargar_sesion(self):
        """Carga la sesión activa y el historial persistente si existen."""
        if self.historial_file.exists():
            try:
                with open(self.historial_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                if isinstance(data, list):
                    self.historial_sesiones = data
            except (OSError, json.JSONDecodeError):
                self.historial_sesiones = []

        if self.session_file.exists():
            try:
                with open(self.session_file, 'r', encoding='utf-8') as f:
                    active = json.load(f)
                ids = {session.get('id') for session in self.historial_sesiones}
                if isinstance(active, dict) and active.get('id') not in ids:
                    self.historial_sesiones.append(active)
            except (OSError, json.JSONDecodeError):
                pass

    def _guardar_historial(self):
        with open(self.historial_file, 'w', encoding='utf-8') as f:
            json.dump(self.historial_sesiones, f, ensure_ascii=False, indent=2)

    def listar_sesiones(self):
        """Devuelve las sesiones conocidas, ordenadas de más nueva a más antigua."""
        return list(reversed(self.historial_sesiones))

    def iniciar_sesion(self, agente_tipo='default'):
        sesion = {
            'id': int(time.time()),
            'agente_tipo': agente_tipo,
            'inicio': datetime.now().isoformat(),
            'modelo_usado': None,
            'tokens_consumidos': 0,
            'errores': 0
        }
        with open(self.session_file, 'w', encoding='utf-8') as f:
            json.dump(sesion, f, ensure_ascii=False, indent=2)
        self.historial_sesiones.append(sesion)
        self._guardar_historial()
        return sesion['id']

    def actualizar_sesion(self, sesion_id, modelo=None, tokens=0, error=False):
        if not self.session_file.exists():
            return
        with open(self.session_file, 'r', encoding='utf-8') as f:
            sesion = json.load(f)
        if sesion['id'] == sesion_id:
            if modelo:
                sesion['modelo_usado'] = modelo
            sesion['tokens_consumidos'] += tokens
            if error:
                sesion['errores'] += 1
            sesion['ultimo_acceso'] = datetime.now().isoformat()
            with open(self.session_file, 'w', encoding='utf-8') as f:
                json.dump(sesion, f, ensure_ascii=False, indent=2)

    def obtener_sesion_actual(self):
        if not self.session_file.exists():
            return None
        with open(self.session_file, 'r', encoding='utf-8') as f:
            return json.load(f)

    def cerrar_sesion(self):
        if self.session_file.exists():
            os.remove(self.session_file)

    def obtener_estadisticas(self):
        total_sesiones = len(self.historial_sesiones)
        total_tokens = sum(s.get('tokens_consumidos', 0) for s in self.historial_sesiones)
        total_errores = sum(s.get('errores', 0) for s in self.historial_sesiones)
        return {
            'total_sesiones': total_sesiones,
            'total_tokens': total_tokens,
            'total_errores': total_errores,
            'modelo_mas_usado': self._modelo_mas_usado()
        }

    def _modelo_mas_usado(self):
        modelos = {}
        for sesion in self.historial_sesiones:
            modelo = sesion.get('modelo_usado')
            if modelo:
                modelos[modelo] = modelos.get(modelo, 0) + 1
        return max(modelos, key=modelos.get) if modelos else None

    def exportar_historial(self, archivo_salida=None):
        if archivo_salida is None:
            archivo_salida = 'historial_sesiones_' + str(int(time.time())) + '.json'
        with open(archivo_salida, 'w', encoding='utf-8') as f:
            json.dump(self.historial_sesiones, f, ensure_ascii=False, indent=2)
        return archivo_salida
