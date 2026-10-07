"""Industrial telemetry simulator used to validate the edge gateway without hardware."""

from __future__ import annotations

import time
from typing import Iterator

def telemetry_stream(machine_id: str, interval_seconds: float = 2.0) -> Iterator[dict]:
    """Yield stable, realistic-looking telemetry for bench testing."""
    while True:
        yield {
            "machine_id": machine_id,
            "air_temperature": 298.1,
            "process_temperature": 308.6,
            "rotational_speed": 1500,
            "torque": 42.5,
            "tool_wear": 120,
        }
        time.sleep(interval_seconds)
