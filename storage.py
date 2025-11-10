from typing import Optional
from models import Device, Room
import json
from pathlib import Path

class DomoticaStorage:
    """Almacenamiento centralizado de habitaciones y dispositivos."""
    
    # Límites del sistema
    MAX_ROOMS = 6
    ALLOWED_ROOM_TYPES = ["comedor", "cocina", "baño", "living", "dormitorio"]
    MAX_DEVICES_PER_ROOM = 10
    
    # Configuración de dispositivos
    # Termostatos
    MIN_TEMP = 16
    MAX_TEMP = 32
    DEFAULT_TEMP = 21
    
    # Ventiladores (0 = apagado, 1-5 = velocidades)
    MIN_FAN_SPEED = 0
    MAX_FAN_SPEED = 5
    DEFAULT_FAN_SPEED = 0
    
    # Hornos
    MIN_OVEN_TEMP = 160
    MAX_OVEN_TEMP = 240
    DEFAULT_OVEN_TEMP = 180
    MAX_OVEN_TIMER = 240  # minutos
    
    # Archivo de persistencia
    STORAGE_FILE = Path(__file__).parent / "domotica_data.json"
    
    def __init__(self):
        """Inicializa con datos por defecto o carga desde archivo."""
        self.rooms: dict[str, Room] = {}
        self.devices: dict[str, Device] = {}
        self._counters = {
            "light": 1, 
            "thermo": 1, 
            "fan": 1, 
            "oven": 1
        }
        
        # Intentar cargar datos existentes
        if self.STORAGE_FILE.exists():
            self._load_from_file()
        else:
            # Crear datos por defecto solo si no existe el archivo
            self.add_room("living")
            self.add_device("living", "light", False)
            self.add_device("living", "thermostat", 21)
    
    # ========== GENERACIÓN DE IDs ==========
    
    def _generate_device_id(self, device_type: str) -> str:
        """Genera ID auto-incremental para dispositivo."""
        key_map = {
            "light": "light",
            "thermostat": "thermo",
            "fan": "fan",
            "oven": "oven"
        }
        counter_key = key_map.get(device_type, device_type)
        device_id = f"{counter_key}-{self._counters[counter_key]:02d}"
        self._counters[counter_key] += 1
        return device_id
    
    # ========== GESTIÓN DE HABITACIONES ==========
    
    def add_room(self, room_type: str) -> dict:
        """Crea una nueva habitación."""
        self.reload()  # Sincronizar con archivo
        if len(self.rooms) >= self.MAX_ROOMS:
            raise ValueError(f"Máximo {self.MAX_ROOMS} habitaciones")
        
        # Validar que el tipo sea permitido
        if room_type not in self.ALLOWED_ROOM_TYPES:
            raise ValueError(f"Tipo de habitación '{room_type}' no válido. Tipos permitidos: {', '.join(self.ALLOWED_ROOM_TYPES)}")
        
        # Generar nombre único con numeración
        count = sum(1 for room in self.rooms.values() if room.type == room_type)
        if count == 0:
            room_name = room_type
        else:
            room_name = f"{room_type} {count + 1}"
        
        self.rooms[room_name] = Room(name=room_name, type=room_type)
        self._save_to_file()
        return {"room": room_name, "type": room_type, "status": "created"}
    
    def update_room(self, old_name: str, new_name: str) -> dict:
        """Renombra una habitación y actualiza sus dispositivos."""
        self.reload()  # Sincronizar con archivo
        if old_name not in self.rooms:
            raise ValueError(f"Habitación '{old_name}' no existe")
        if new_name in self.rooms and new_name != old_name:
            raise ValueError(f"Habitación '{new_name}' ya existe")
        
        room = self.rooms.pop(old_name)
        room.name = new_name
        self.rooms[new_name] = room
        
        # Actualizar room en dispositivos
        for device_id in room.devices:
            self.devices[device_id].room = new_name
        
        self._save_to_file()
        return {"old_name": old_name, "new_name": new_name, "status": "updated"}
    
    def delete_room(self, name: str) -> dict:
        """Elimina una habitación (debe estar vacía)."""
        self.reload()  # Sincronizar con archivo
        if name not in self.rooms:
            raise ValueError(f"Habitación '{name}' no existe")
        
        room = self.rooms[name]
        if room.devices:
            raise ValueError(
                f"No se puede eliminar habitación con dispositivos. "
                f"Eliminar primero: {room.devices}"
            )
        
        del self.rooms[name]
        self._save_to_file()
        return {"room": name, "status": "deleted"}
    
    def list_rooms(self) -> list[dict]:
        """Lista todas las habitaciones con estadísticas."""
        self.reload()  # Sincronizar con archivo
        result = []
        for room in self.rooms.values():
            lights = sum(1 for d in room.devices if self.devices[d].type == "light")
            thermos = sum(1 for d in room.devices if self.devices[d].type == "thermostat")
            fans = sum(1 for d in room.devices if self.devices[d].type == "fan")
            ovens = sum(1 for d in room.devices if self.devices[d].type == "oven")
            
            result.append({
                "name": room.name,
                "type": room.type,
                "light_count": lights,
                "thermostat_count": thermos,
                "fan_count": fans,
                "oven_count": ovens,
                "total_devices": len(room.devices)
            })
        return result
    
    def get_room_info(self, name: str) -> dict:
        """Obtiene información detallada de una habitación."""
        self.reload()  # Sincronizar con archivo
        if name not in self.rooms:
            raise ValueError(f"Habitación '{name}' no existe")
        
        room = self.rooms[name]
        devices = [self.devices[dev_id].to_dict() for dev_id in room.devices]
        
        lights = sum(1 for d in devices if d["type"] == "light")
        thermos = sum(1 for d in devices if d["type"] == "thermostat")
        
        return {
            "room": name,
            "type": room.type,
            "devices": devices,
            "light_count": lights,
            "thermostat_count": thermos
        }
    
    # ========== GESTIÓN DE DISPOSITIVOS ==========
    
    def add_device(self, room_name: str, device_type: str, initial_state=None) -> dict:
        """Añade un dispositivo a una habitación."""
        self.reload()  # Sincronizar con archivo
        if room_name not in self.rooms:
            raise ValueError(f"Habitación '{room_name}' no existe")
        
        if device_type not in ["light", "thermostat", "fan", "oven"]:
            raise ValueError(f"Tipo '{device_type}' inválido. Usar 'light', 'thermostat', 'fan' u 'oven'")
        
        room = self.rooms[room_name]
        
        # Reglas específicas por TIPO de habitación
        if device_type == "oven" and room.type != "cocina":
            raise ValueError(f"El horno solo puede añadirse en la cocina")
        
        if room.type == "baño" and device_type != "light":
            raise ValueError(f"En el baño únicamente pueden añadirse luces")
        
        # Validar límite general de dispositivos
        if len(room.devices) >= self.MAX_DEVICES_PER_ROOM:
            raise ValueError(f"Máximo {self.MAX_DEVICES_PER_ROOM} dispositivos por habitación")
        
        # Configurar estado inicial según tipo
        if device_type == "light":
            state = False if initial_state is None else bool(initial_state)
        
        elif device_type == "thermostat":
            state = self.DEFAULT_TEMP if initial_state is None else int(initial_state)
            self._validate_temperature(state)
        
        elif device_type == "fan":
            state = self.DEFAULT_FAN_SPEED if initial_state is None else int(initial_state)
            self._validate_fan_speed(state)
        
        elif device_type == "oven":
            if initial_state is None:
                state = {
                    "temperature": self.DEFAULT_OVEN_TEMP,
                    "timer": 0,  # minutos
                    "active": False
                }
            else:
                state = initial_state
                if isinstance(state, dict):
                    self._validate_oven_temp(state.get("temperature", self.DEFAULT_OVEN_TEMP))
                    self._validate_oven_timer(state.get("timer", 0))
        
        # Crear dispositivo
        device_id = self._generate_device_id(device_type)
        self.devices[device_id] = Device(
            id=device_id,
            type=device_type,
            room=room_name,
            state=state
        )
        
        room.devices.append(device_id)
        
        self._save_to_file()
        return {
            "device_id": device_id,
            "type": device_type,
            "room": room_name,
            "state": state,
            "status": "added"
        }
    
    def update_device(
        self,
        device_id: str,
        room: Optional[str] = None,
        state: Optional[bool | int | dict] = None
    ) -> dict:
        """Modifica un dispositivo (habitación y/o estado)."""
        self.reload()  # Sincronizar con archivo
        if device_id not in self.devices:
            raise ValueError(f"Dispositivo '{device_id}' no encontrado")
        
        device = self.devices[device_id]
        
        # Cambiar habitación si se especifica
        if room is not None and room != device.room:
            if room not in self.rooms:
                raise ValueError(f"Habitación '{room}' no existe")
            
            new_room = self.rooms[room]
            if len(new_room.devices) >= self.MAX_DEVICES_PER_ROOM:
                raise ValueError(f"Habitación '{room}' ya tiene {self.MAX_DEVICES_PER_ROOM} dispositivos")
            
            # Validar restricciones por TIPO de habitación
            if device.type == "oven" and new_room.type != "cocina":
                raise ValueError(f"El horno solo puede estar en la cocina")
            
            if new_room.type == "baño" and device.type != "light":
                raise ValueError(f"En el baño únicamente pueden estar luces")
            
            # Mover dispositivo
            old_room = self.rooms[device.room]
            old_room.devices.remove(device_id)
            new_room.devices.append(device_id)
            device.room = room
        
        # Cambiar estado si se especifica
        if state is not None:
            if device.type == "light":
                device.state = bool(state)
            elif device.type == "thermostat":
                self._validate_temperature(int(state))
                device.state = int(state)
            elif device.type == "fan":
                self._validate_fan_speed(int(state))
                device.state = int(state)
            elif device.type == "oven":
                if isinstance(state, dict):
                    current_state = device.state if isinstance(device.state, dict) else {}
                    current_state.update(state)
                    if "temperature" in state:
                        self._validate_oven_temp(state["temperature"])
                    if "timer" in state:
                        self._validate_oven_timer(state["timer"])
                    device.state = current_state
        
        self._save_to_file()
        return device.to_dict()
    
    def delete_device(self, device_id: str) -> dict:
        """Elimina un dispositivo del sistema."""
        self.reload()  # Sincronizar con archivo
        if device_id not in self.devices:
            raise ValueError(f"Dispositivo '{device_id}' no encontrado")
        
        device = self.devices[device_id]
        room = self.rooms[device.room]
        
        room.devices.remove(device_id)
        del self.devices[device_id]
        
        self._save_to_file()
        return {"device_id": device_id, "status": "deleted"}
    
    def list_devices(self, room_filter: Optional[str] = None) -> list[dict]:
        """Lista dispositivos, opcionalmente filtrados por habitación."""
        self.reload()  # Sincronizar con archivo
        devices = self.devices.values()
        
        if room_filter:
            if room_filter not in self.rooms:
                raise ValueError(f"Habitación '{room_filter}' no existe")
            devices = [d for d in devices if d.room == room_filter]
        
        return [d.to_dict() for d in devices]
    
    # ========== VALIDACIONES ==========
    
    def _validate_temperature(self, temp: int) -> None:
        """Valida que la temperatura esté en rango."""
        if not (self.MIN_TEMP <= temp <= self.MAX_TEMP):
            raise ValueError(
                f"Temperatura {temp}°C fuera de rango ({self.MIN_TEMP}-{self.MAX_TEMP}°C)"
            )
    
    def _validate_fan_speed(self, speed: int) -> None:
        """Valida que la velocidad del ventilador esté en rango."""
        if not (self.MIN_FAN_SPEED <= speed <= self.MAX_FAN_SPEED):
            raise ValueError(
                f"Velocidad {speed} fuera de rango ({self.MIN_FAN_SPEED}-{self.MAX_FAN_SPEED})"
            )
    
    def _validate_oven_temp(self, temp: int) -> None:
        """Valida que la temperatura del horno esté en rango."""
        if not (self.MIN_OVEN_TEMP <= temp <= self.MAX_OVEN_TEMP):
            raise ValueError(
                f"Temperatura del horno {temp}°C fuera de rango ({self.MIN_OVEN_TEMP}-{self.MAX_OVEN_TEMP}°C)"
            )
    
    def _validate_oven_timer(self, timer: int) -> None:
        """Valida que el temporizador del horno esté en rango."""
        if not (0 <= timer <= self.MAX_OVEN_TIMER):
            raise ValueError(
                f"Temporizador {timer} min fuera de rango (0-{self.MAX_OVEN_TIMER} min)"
            )
    
    # ========== PERSISTENCIA ==========
    
    def _save_to_file(self) -> None:
        """Guarda el estado actual en el archivo JSON."""
        data = {
            "rooms": {
                name: {
                    "name": room.name,
                    "type": room.type,
                    "devices": room.devices
                }
                for name, room in self.rooms.items()
            },
            "devices": {
                dev_id: {
                    "id": device.id,
                    "type": device.type,
                    "room": device.room,
                    "state": device.state
                }
                for dev_id, device in self.devices.items()
            },
            "counters": self._counters
        }
        
        with open(self.STORAGE_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def _load_from_file(self) -> None:
        """Carga el estado desde el archivo JSON."""
        try:
            with open(self.STORAGE_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Restaurar habitaciones
            self.rooms = {
                name: Room(
                    name=room_data["name"],
                    type=room_data["type"],
                    devices=room_data["devices"]
                )
                for name, room_data in data.get("rooms", {}).items()
            }
            
            # Restaurar dispositivos
            self.devices = {
                dev_id: Device(
                    id=device_data["id"],
                    type=device_data["type"],
                    room=device_data["room"],
                    state=device_data["state"]
                )
                for dev_id, device_data in data.get("devices", {}).items()
            }
            
            # Restaurar contadores
            self._counters = data.get("counters", {
                "light": 1,
                "thermo": 1,
                "fan": 1,
                "oven": 1
            })
            
        except Exception as e:
            print(f"⚠️  Error cargando datos: {e}")
            print("   Iniciando con datos limpios")
    
    def reload(self) -> None:
        """Recarga los datos desde el archivo (para sincronizar entre procesos)."""
        if self.STORAGE_FILE.exists():
            self._load_from_file()


# Instancia global
storage = DomoticaStorage()
