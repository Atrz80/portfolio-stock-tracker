"""Políticas deterministas para los roles de la agencia de mercado.

El camino realtime no llama a un LLM para cada tick: eso añadiría latencia y
puede ser incorrecto. Cada agente installed sí define una función concreta:

- analyst valida un tick;
- architect diagnostica la conexión;
- optimizer recalcula valor y P&L.

Las recomendaciones narrativas siguen disponibles mediante la agencia LLM.
"""

from __future__ import annotations

from typing import Any

from .market_data import Quote


def analyst_validate_tick(quote: Quote) -> dict[str, Any]:
    """Valida precio y disponibilidad temporal de un tick.

    Yahoo no incluye timestamp en todos los pricing push. Un precio positivo
    sigue siendo una actualización push válida; el servidor registra entonces
    ``received_at`` para medir la latencia de entrega.
    """
    valid = quote.price > 0
    return {
        "agent": "analyst",
        "valid": valid,
        "symbol": quote.symbol,
        "price": quote.price,
        "currency": quote.currency,
        "market_state": quote.market_state,
        "timestamp": quote.timestamp,
        "reason": None if valid else "precio inválido",
    }


def architect_diagnose_connection(health: dict[str, Any]) -> dict[str, Any]:
    """Clasifica el estado de la conexión push y la siguiente acción."""
    state = health.get("state")
    if state == "connected":
        action = "mantener suscripción y heartbeat"
        severity = "ok"
    elif state == "connecting":
        action = "esperar handshake push"
        severity = "info"
    else:
        action = "reconectar con backoff exponencial"
        severity = "warning"
    return {
        "agent": "architect",
        "severity": severity,
        "state": state,
        "action": action,
        "last_error": health.get("last_error"),
        "reconnect_attempts": health.get("reconnect_attempts", 0),
    }


def optimizer_calculate_position(
    position: dict[str, Any],
    quote: Quote,
    fx_to_eur: float,
) -> dict[str, Any]:
    """Recalcula una posición usando el tick y la tasa FX reales."""
    shares = float(position["shares"])
    stored_price_eur = float(position["price"])
    stored_gain = float(position.get("gain", 0.0))
    initial_cost = stored_price_eur * shares - stored_gain
    price_eur = quote.price * fx_to_eur
    value = price_eur * shares
    gain = value - initial_cost
    gain_pct = (gain / initial_cost * 100) if initial_cost else 0.0
    return {
        "agent": "optimizer",
        "price": round(price_eur, 4),
        "value": round(value, 2),
        "gain": round(gain, 2),
        "gainPct": round(gain_pct, 2),
    }
