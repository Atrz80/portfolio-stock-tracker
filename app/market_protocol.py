"""Decoder for Yahoo Finance push pricing messages."""

from __future__ import annotations

import base64
from datetime import datetime, timezone
from typing import Any

from google.protobuf import descriptor_pb2, descriptor_pool, message_factory

from .market_data import MarketDataError

_MARKET_HOURS = {1: "REGULAR_OR_24_7"}


def _pricing_message_class():
    """Build the small subset of Yahoo's pricing protobuf we consume."""
    file_descriptor = descriptor_pb2.FileDescriptorProto()
    file_descriptor.name = "portfolio_pricing.proto"
    file_descriptor.package = "portfolio"
    message = file_descriptor.message_type.add(name="PricingData")
    fields = {
        "id": (1, descriptor_pb2.FieldDescriptorProto.TYPE_STRING),
        "price": (2, descriptor_pb2.FieldDescriptorProto.TYPE_FLOAT),
        "time": (3, descriptor_pb2.FieldDescriptorProto.TYPE_SINT64),
        "currency": (4, descriptor_pb2.FieldDescriptorProto.TYPE_STRING),
        "exchange": (5, descriptor_pb2.FieldDescriptorProto.TYPE_STRING),
        "quote_type": (6, descriptor_pb2.FieldDescriptorProto.TYPE_INT32),
        "market_hours": (7, descriptor_pb2.FieldDescriptorProto.TYPE_INT32),
        "change_percent": (8, descriptor_pb2.FieldDescriptorProto.TYPE_FLOAT),
        "previous_close": (16, descriptor_pb2.FieldDescriptorProto.TYPE_FLOAT),
    }
    for name, (number, field_type) in fields.items():
        field = message.field.add()
        field.name = name
        field.number = number
        field.type = field_type
        field.label = descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL
    pool = descriptor_pool.Default()
    try:
        pool.Add(file_descriptor)
    except Exception:
        pass
    descriptor = pool.FindMessageTypeByName("portfolio.PricingData")
    return message_factory.GetMessageClass(descriptor)


PricingData = _pricing_message_class()


def decode_yahoo_pricing(encoded_message: str) -> dict[str, Any]:
    """Decode one Base64 protobuf pricing event into normalized fields."""
    try:
        payload = base64.b64decode(encoded_message)
        message = PricingData()
        message.ParseFromString(payload)
    except Exception as exc:
        raise MarketDataError(f"No se pudo decodificar el pricing push de Yahoo: {exc}") from exc

    symbol = str(message.id or "").upper()
    if not symbol:
        raise MarketDataError("Yahoo Finance envió un pricing push sin símbolo")
    raw_timestamp = int(message.time) if message.HasField("time") else None
    timestamp = raw_timestamp // 1000 if raw_timestamp is not None else None
    return {
        "symbol": symbol,
        "price": float(message.price),
        "previous_close": (
            float(message.previous_close) if message.HasField("previous_close") else None
        ),
        "currency": str(message.currency or "USD").upper(),
        "exchange": str(message.exchange or ""),
        "timestamp": timestamp,
        "raw_timestamp": raw_timestamp,
        "timestamp_source_unit": "milliseconds",
        "timestamp_iso": (
            datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat()
            if timestamp
            else None
        ),
        "change_percent": (
            float(message.change_percent) if message.HasField("change_percent") else None
        ),
        "market_state": _MARKET_HOURS.get(int(message.market_hours), "UNKNOWN"),
        "delivery": "push",
    }
