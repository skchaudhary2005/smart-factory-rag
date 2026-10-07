"""Normalize PLC/SCADA values into the Smart Factory telemetry contract."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping

NUMERIC_FIELDS = (
    "air_temperature",
    "process_temperature",
    "rotational_speed",
    "torque",
    "tool_wear",
)

def _number(value: Any) -> float | int | None:
    if value is None:
        return None
    if isinstance(value, bool):
        raise ValueError("boolean is not a valid numeric telemetry value")
    number = float(value)
    return int(number) if number.is_integer() else number

def normalize(machine_id: str, raw: Mapping[str, Any]) -> dict[str, Any]:
    """Convert raw PLC/SCADA tags to the backend's normalized telemetry shape."""
    payload: dict[str, Any] = {
        "machine_id": machine_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    for field in NUMERIC_FIELDS:
        if field in raw:
            payload[field] = _number(raw[field])
    return payload

def map_tags(tag_values: Mapping[str, Any], tag_config: Mapping[str, str]) -> dict[str, Any]:
    """Map configured PLC tag names to normalized field names."""
    result: dict[str, Any] = {}
    for field, tag_name in tag_config.items():
        if tag_name in tag_values:
            result[field] = tag_values[tag_name]
    return result
