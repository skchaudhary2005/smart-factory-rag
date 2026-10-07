"""Smart Factory Edge Gateway.

Default mode is a local simulator so the connector can be tested without a PLC.
Real PLC/SCADA adapters should feed the same normalized mapping before MQTT publish.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from sensor_mapping import normalize
from simulator import telemetry_stream

def load_config(path: str) -> dict:
    try:
        import yaml
    except ImportError as exc:
        raise RuntimeError("PyYAML is required. Install edge_gateway/requirements.txt.") from exc
    with open(path, "r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}

def build_publisher(config: dict):
    from mqtt_publisher import MQTTPublisher
    mqtt_cfg = config.get("mqtt", {})
    return MQTTPublisher(
        host=mqtt_cfg.get("host", os.getenv("MQTT_HOST", "localhost")),
        port=int(mqtt_cfg.get("port", os.getenv("MQTT_PORT", "1883"))),
        topic_prefix=mqtt_cfg.get("topic_prefix", "factory"),
        client_id=mqtt_cfg.get("client_id", "smart-factory-edge"),
        username=mqtt_cfg.get("username", os.getenv("MQTT_USERNAME", "")),
        password=mqtt_cfg.get("password", os.getenv("MQTT_PASSWORD", "")),
    )

def main() -> None:
    parser = argparse.ArgumentParser(description="Smart Factory Edge Gateway")
    parser.add_argument("--mode", choices=("simulator", "mqtt"), default="simulator")
    parser.add_argument("--config", default=str(Path(__file__).with_name("config.yaml")))
    parser.add_argument("--interval", type=float, default=2.0)
    args = parser.parse_args()

    config = load_config(args.config) if Path(args.config).exists() else {}
    machine_id = config.get("machine", {}).get("machine_id", "M-001")

    publisher = None
    if args.mode == "mqtt":
        publisher = build_publisher(config)
        publisher.connect()

    try:
        for raw in telemetry_stream(machine_id, args.interval):
            payload = normalize(machine_id, raw)
            if publisher:
                publisher.publish(machine_id, payload)
                print("published:", json.dumps(payload), flush=True)
            else:
                print("simulated:", json.dumps(payload), flush=True)
    except KeyboardInterrupt:
        pass
    finally:
        if publisher:
            publisher.close()

if __name__ == "__main__":
    main()
