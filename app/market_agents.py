"""Deterministic policies for the market agency roles.

The realtime path does not call an LLM for every tick: that would add latency
and could produce incorrect results. Each installed agent has a specific role:

- analyst validates a tick;
- architect diagnoses the connection;
- optimizer recalculates value and P&L.

Narrative recommendations remain available through the LLM agency.
"""

from __future__ import annotations

from typing import Any

from .market_data import Quote


def analyst_validate_tick(quote: Quote) -> dict[str, Any]:
    """Validate a tick's price and timestamp availability.

    Yahoo does not include a timestamp in every pricing push. A positive price
    is still a valid push update; the server then records ``received_at`` to
    measure delivery latency.
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
        "reason": None if valid else "Invalid price",
    }


def architect_diagnose_connection(health: dict[str, Any]) -> dict[str, Any]:
    """Classify the push connection state and the next action."""
    state = health.get("state")
    if state == "connected":
        action = "maintain subscription and heartbeat"
        severity = "ok"
    elif state == "connecting":
        action = "wait for the push handshake"
        severity = "info"
    else:
        action = "reconnect with exponential backoff"
        severity = "warning"
    return {
        "agent": "architect",
        "severity": severity,
        "state": state,
        "action": action,
        "last_error": health.get("last_error"),
        "reconnect_attempts": health.get("reconnect_attempts", 0),
    }


def position_cost_basis(position: dict[str, Any]) -> float:
    """Return the recorded investment cost, supporting legacy portfolio entries."""
    cost_basis = position.get("costBasis")
    if cost_basis is not None:
        return float(cost_basis)
    return float(position["price"]) * float(position["shares"]) - float(
        position.get("gain", 0.0)
    )


def optimizer_calculate_position(
    position: dict[str, Any],
    quote: Quote,
    fx_to_eur: float,
) -> dict[str, Any]:
    """Recalculate a position using the real tick and FX rate."""
    shares = float(position["shares"])
    initial_cost = position_cost_basis(position)
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
