"""Read-only Modbus TCP adapter for the edge gateway."""
from __future__ import annotations
from typing import Any

class ModbusTelemetryReader:
    def __init__(self, host: str, port: int, unit_id: int, registers: dict[str, int], scale: dict[str, float] | None = None):
        try:
            from pymodbus.client import ModbusTcpClient
        except ImportError as exc:
            raise RuntimeError("pymodbus is required for Modbus mode.") from exc
        self._client = ModbusTcpClient(host=host, port=port)
        self.unit_id = unit_id
        self.registers = registers
        self.scale = scale or {}

    def connect(self) -> None:
        if not self._client.connect():
            raise ConnectionError("Unable to connect to the Modbus TCP server.")

    def read(self) -> dict[str, Any]:
        values = {}
        for field, address in self.registers.items():
            result = self._client.read_holding_registers(address=address, count=1, slave=self.unit_id)
            if result.isError():
                raise RuntimeError(f"Modbus read failed for {field} at register {address}")
            values[field] = result.registers[0] * float(self.scale.get(field, 1.0))
        return values

    def close(self) -> None:
        self._client.close()
