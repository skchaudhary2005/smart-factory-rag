"""Read-only OPC-UA adapter for the edge gateway."""
from __future__ import annotations
from typing import Any

class OPCUATelemetryReader:
    def __init__(self, endpoint: str, nodes: dict[str, str]):
        try:
            from opcua import Client
        except ImportError as exc:
            raise RuntimeError("opcua is required for OPC-UA mode.") from exc
        self._client = Client(endpoint)
        self.nodes = nodes

    def connect(self) -> None:
        self._client.connect()

    def read(self) -> dict[str, Any]:
        return {field: self._client.get_node(node_id).get_value() for field, node_id in self.nodes.items()}

    def close(self) -> None:
        self._client.disconnect()
