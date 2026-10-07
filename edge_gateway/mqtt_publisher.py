"""MQTT publisher for normalized factory telemetry."""

from __future__ import annotations

import json
from typing import Any

class MQTTPublisher:
    def __init__(self, host: str, port: int, topic_prefix: str, client_id: str,
                 username: str = "", password: str = "") -> None:
        try:
            import paho.mqtt.client as mqtt
        except ImportError as exc:
            raise RuntimeError(
                "paho-mqtt is required. Install edge_gateway/requirements.txt."
            ) from exc
        self._mqtt = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION2,
            client_id=client_id,
            protocol=mqtt.MQTTv5,
        )
        if username:
            self._mqtt.username_pw_set(username, password)
        self.host = host
        self.port = port
        self.topic_prefix = topic_prefix.rstrip("/")
        self._connected = False

    def connect(self) -> None:
        self._mqtt.connect(self.host, self.port, keepalive=60)
        self._mqtt.loop_start()
        self._connected = True

    def publish(self, machine_id: str, payload: dict[str, Any]) -> None:
        if not self._connected:
            raise RuntimeError("MQTT publisher is not connected")
        topic = f"{self.topic_prefix}/{machine_id}/telemetry"
        info = self._mqtt.publish(topic, json.dumps(payload), qos=1)
        info.wait_for_publish()
        if info.rc != 0:
            raise RuntimeError(f"MQTT publish failed with rc={info.rc}")

    def close(self) -> None:
        if self._connected:
            self._mqtt.loop_stop()
            self._mqtt.disconnect()
            self._connected = False
