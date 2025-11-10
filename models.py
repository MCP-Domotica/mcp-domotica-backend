from dataclasses import dataclass, field
from typing import Literal, Any

@dataclass
class Device:
    """Dispositivo en el sistema."""
    id: str
    type: Literal["light", "thermostat", "fan", "oven"]
    room: str
    state: bool | int | dict[str, Any]  # bool para luces, int para termostato/ventilador, dict para horno
    
    def to_dict(self) -> dict:
        """Convierte a diccionario para serialización."""
        return {
            "id": self.id,
            "type": self.type,
            "room": self.room,
            "state": self.state
        }

@dataclass
class Room:
    """Habitación que contiene dispositivos."""
    name: str
    type: str  # comedor, cocina, baño, living, dormitorio
    devices: list[str] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        """Convierte a diccionario para serialización."""
        return {
            "name": self.name,
            "type": self.type,
            "devices": self.devices.copy(),
            "device_count": len(self.devices)
        }
