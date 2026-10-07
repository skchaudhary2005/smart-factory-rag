"""Smart Factory Edge Gateway.

Supports simulator, Modbus TCP and OPC-UA read-only telemetry sources.
The gateway normalizes data and publishes it to the existing MQTT contract.
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


def build_reader(config: dict):
    protocol = config.get("protocol", "simulator").lower()
    if protocol == "modbus":
        from modbus_client import ModbusTelemetryReader
        cfg = config.get("modbus", {})
        return ModbusTelemetryReader(
            host=cfg["host"],
            port=int(cfg.get("port", 502)),
            unit_id=int(cfg.get("unit_id", 1)),
            registers={k: int(v) for k, v in cfg["registers"].items()},
            scale={k: float(v) for k, v in cfg.get("scale", {}).items()},
        )
    if protocol == "opcua":
        from opcua_client import OPCUATelemetryReader
        cfg = config.get("opcua", {})
        return OPCUATelemetryReader(cfg["endpoint"], cfg["nodes"])
    if protocol == "simulator":
        return None
    raise ValueError("protocol must be simulator, modbus, or opcua")


def main() -> None:
    parser = argparse.ArgumentParser(description="Smart Factory Edge Gateway")
    parser.add_argument("--mode", choices=("simulator", "mqtt"), default="simulator")
    parser.add_argument("--config", default=str(Path(__file__).with_name("config.yaml")))
    parser.add_argument("--interval", type=float, default=2.0)
    args = parser.parse_args()

    config = load_config(args.config) if Path(args.config).exists() else {}
    machine_id = config.get("machine", {}).get("machine_id", "M-001")
    protocol = config.get("protocol", "simulator").lower()

    publisher = None
    reader = build_reader(config)
    if args.mode == "mqtt":
        publisher = build_publisher(config)
        publisher.connect()

    if reader:
        reader.connect()

    try:
        if protocol == "simulator":
            source = telemetry_stream(machine_id, args.interval)
            for raw in source:
                payload = normalize(machine_id, raw)
                if publisher:
                    publisher.publish(machine_id, payload)
                    print("published:", json.dumps(payload), flush=True)
                else:
                    print("simulated:", json.dumps(payload), flush=True)
        else:
            while True:
                raw = reader.read()
                payload = normalize(machine_id, raw)
                if publisher:
                    publisher.publish(machine_id, payload)
                    print("published:", json.dumps(payload), flush=True)
                else:
                    print("read-only:", json.dumps(payload), flush=True)
                import time
                time.sleep(args.interval)
    except KeyboardInterrupt:
        pass
    finally:
        if reader:
            reader.close()
        if publisher:
            publisher.close()


if __name__ == "__main__":
    main()
