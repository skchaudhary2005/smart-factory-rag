# Smart Factory Edge Gateway

This folder provides an optional edge connector layer for the Smart Factory RAG system.

Architecture:

PLC / Sensors -> Edge Gateway -> MQTT (factory/#) -> Smart Factory API / TimescaleDB -> ML + RAG + Dashboard

The gateway does not replace the existing cloud backend and does not change the simulator path. It normalizes machine telemetry into the existing MQTT contract.

## Current implementation

- main.py — gateway entry point
- sensor_mapping.py — maps PLC/sensor tag names to normalized telemetry
- mqtt_publisher.py — publishes normalized JSON to MQTT
- simulator.py — laptop/bench simulator for testing without a real machine
- config.example.yaml — configuration template
- requirements.txt — edge-only dependencies

## Real machine

Use an industrial PC / gateway on the same OT network as the PLC. Configure the PLC protocol (OPC-UA or Modbus TCP), map read-only tags in config.yaml, normalize them, and publish to MQTT.

The gateway intentionally has no machine write/control operation. It is telemetry/read-only oriented.

## Test without hardware

Run simulator mode to publish the same telemetry shape that a real connector would publish:

    python edge_gateway/main.py --mode simulator

This lets the existing cloud pipeline be tested before a PLC is available.

## MQTT payload

    {
      "machine_id": "M-001",
      "air_temperature": 298.1,
      "process_temperature": 308.6,
      "rotational_speed": 1500,
      "torque": 42.5,
      "tool_wear": 120,
      "timestamp": "2026-01-01T00:00:00+00:00"
    }

## Important

A real PLC connection cannot be completed until the actual PLC/controller model, protocol, tag addresses/names, and network access are known. This connector layer is ready for that mapping; it does not pretend that a physical machine is already connected.
