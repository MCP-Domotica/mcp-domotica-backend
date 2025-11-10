import sys
from pathlib import Path

# Añadir directorio backend al path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from mcp.server.fastmcp import FastMCP
from storage import storage

mcp = FastMCP("Gestión de Habitaciones")

# ========== PROMPT ==========

@mcp.prompt()
def room_manager_role() -> str:
    """
    Define el rol y responsabilidades del servidor de gestión de habitaciones.
    """
    return """
    Eres un asistente especializado en la GESTIÓN DE HABITACIONES de un sistema domótico.
    
    TUS RESPONSABILIDADES:
    - Crear, listar, modificar y eliminar habitaciones
    - Proporcionar información sobre las habitaciones y sus dispositivos
    - Validar las operaciones respetando el límite de habitaciones
    
    REGLAS IMPORTANTES:
    - Máximo 6 habitaciones en el sistema
    - Tipos de habitación permitidos: comedor, cocina, baño, living, dormitorio
    - El sistema numera automáticamente habitaciones del mismo tipo (ej: dormitorio, dormitorio 2, dormitorio 3)
    - No se puede eliminar una habitación con dispositivos (debe estar vacía)
    
    COMUNICACIÓN:
    - Sé claro y conciso en tus respuestas
    - Informa al usuario sobre límites y restricciones
    - Confirma cada operación realizada
    """

# ========== RESOURCES ==========

@mcp.resource("domotica://rooms/state")
def get_rooms_state() -> str:
    """
    Obtiene el estado actual de todas las habitaciones del sistema.
    Proporciona información detallada para que el agente conozca el contexto.
    """
    output = "=== ESTADO DE HABITACIONES ===\n\n"
    
    rooms = storage.list_rooms()
    
    if not rooms:
        output += "No hay habitaciones en el sistema.\n"
    else:
        for room_data in rooms:
            output += f"📍 {room_data['name']}\n"
            output += f"   - Luces: {room_data.get('light_count', 0)}\n"
            output += f"   - Termostatos: {room_data.get('thermostat_count', 0)}\n"
            
            # Contar otros dispositivos
            room_info = storage.get_room_info(room_data['name'])
            devices = room_info['devices']
            fans = sum(1 for d in devices if d['type'] == 'fan')
            ovens = sum(1 for d in devices if d['type'] == 'oven')
            
            if fans > 0:
                output += f"   - Ventiladores: {fans}\n"
            if ovens > 0:
                output += f"   - Hornos: {ovens}\n"
            
            output += f"   - Total dispositivos: {room_data['total_devices']}\n\n"
    
    output += f"\nOcupación: {len(rooms)}/{storage.MAX_ROOMS} habitaciones\n"
    
    return output

@mcp.resource("domotica://rooms/{room_name}")
def get_room_detail(room_name: str) -> str:
    """
    Obtiene información detallada de una habitación específica.
    Incluye todos los dispositivos y su estado actual.
    """
    try:
        room_info = storage.get_room_info(room_name)
        
        output = f"=== HABITACIÓN: {room_name.upper()} ===\n\n"
        
        devices = room_info['devices']
        if not devices:
            output += "Esta habitación no tiene dispositivos.\n"
        else:
            output += "DISPOSITIVOS:\n"
            for dev in devices:
                tipo_str = {
                    'light': '💡 Luz',
                    'thermostat': '🌡️ Termostato',
                    'fan': '🌀 Ventilador',
                    'oven': '🔥 Horno'
                }.get(dev['type'], dev['type'])
                
                # Formatear estado según tipo
                if dev['type'] == 'light':
                    estado = 'Encendida' if dev['state'] else 'Apagada'
                elif dev['type'] == 'thermostat':
                    estado = f"{dev['state']}°C"
                elif dev['type'] == 'fan':
                    estado = f"Apagado" if dev['state'] == 0 else f"Velocidad {dev['state']}"
                elif dev['type'] == 'oven':
                    if isinstance(dev['state'], dict):
                        temp = dev['state'].get('temperature', 0)
                        timer = dev['state'].get('timer', 0)
                        active = dev['state'].get('active', False)
                        estado = f"{'Activo' if active else 'Inactivo'} - {temp}°C"
                        if timer > 0:
                            estado += f" - Timer: {timer} min"
                    else:
                        estado = str(dev['state'])
                else:
                    estado = str(dev['state'])
                
                output += f"  • {dev['id']} ({tipo_str}): {estado}\n"
        
        return output
        
    except ValueError as e:
        return f"Error: {str(e)}"

# ========== TOOLS - CONSULTAS ==========

@mcp.tool()
def consultar_habitaciones() -> list[dict]:
    """
    Obtiene la lista completa de habitaciones con su información.
    
    Returns:
        Lista de habitaciones con nombre y cantidad de dispositivos por tipo.
    """
    return storage.list_rooms()

@mcp.tool()
def consultar_habitacion(room_name: str) -> dict:
    """
    Obtiene información detallada de una habitación específica.
    
    Args:
        room_name: nombre de la habitación
    
    Returns:
        Información completa de la habitación incluyendo todos sus dispositivos.
    """
    return storage.get_room_info(room_name)

# ========== TOOLS - GESTIÓN ==========

@mcp.tool()
def agregar_habitacion(room_type: str) -> dict:
    """
    Crea una nueva habitación en el sistema.
    
    Args:
        room_type: tipo de habitación (comedor, cocina, baño, living, dormitorio)
    
    Returns:
        Confirmación de creación con el nombre generado de la habitación.
    
    Restricciones:
        - Máximo 6 habitaciones en el sistema
        - Solo tipos permitidos: comedor, cocina, baño, living, dormitorio
        - El sistema numera automáticamente (ej: si ya existe "dormitorio", crea "dormitorio 2")
    """
    return storage.add_room(room_type)

@mcp.tool()
def modificar_habitacion(old_name: str, new_name: str) -> dict:
    """
    Modifica el nombre de una habitación existente.
    Actualiza automáticamente todos los dispositivos asociados.
    
    Args:
        old_name: nombre actual de la habitación
        new_name: nuevo nombre para la habitación
    
    Returns:
        Confirmación con ambos nombres (antiguo y nuevo).
    """
    return storage.update_room(old_name, new_name)

@mcp.tool()
def eliminar_habitacion(room_name: str) -> dict:
    """
    Elimina una habitación del sistema.
    
    Args:
        room_name: nombre de la habitación a eliminar
    
    Returns:
        Confirmación de eliminación.
    
    Restricciones:
        - La habitación debe estar vacía (sin dispositivos)
        - Primero deben eliminarse todos los dispositivos de la habitación
    """
    return storage.delete_room(room_name)

if __name__ == "__main__":
    mcp.run(transport="stdio")
