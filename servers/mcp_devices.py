import sys
from pathlib import Path

# Añadir directorio backend al path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from mcp.server.fastmcp import FastMCP
from typing import Optional
from storage import storage

mcp = FastMCP("Gestión de Dispositivos")

# ========== PROMPT ==========

@mcp.prompt()
def device_manager_role() -> str:
    """
    Define el rol y responsabilidades del servidor de gestión de dispositivos.
    """
    return """
    Eres un asistente especializado en la GESTIÓN DE DISPOSITIVOS de un sistema domótico.
    
    TUS RESPONSABILIDADES:
    - Crear, listar, modificar y eliminar dispositivos
    - Controlar el comportamiento específico de cada tipo de dispositivo
    - Proporcionar información sobre el estado de los dispositivos
    
    TIPOS DE DISPOSITIVOS Y SUS COMPORTAMIENTOS:
    
    1. LUCES (light):
       - Solo pueden encenderse o apagarse (alternar estado)
       - Estado: booleano (True/False)
    
    2. TERMOSTATOS (thermostat):
       - Pueden ajustarse entre 16°C y 32°C
       - Estado: temperatura en grados Celsius (entero)
    
    3. VENTILADORES (fan):
       - 5 velocidades (1-5) o apagado (0)
       - Estado: velocidad 0-5 (entero)
    
    4. HORNOS (oven):
       - Temperatura regulable: 160°C - 240°C
       - Temporizador: 0-240 minutos
       - Puede estar activo o inactivo
       - Estado: diccionario {temperature, timer, active}
    
    REGLAS IMPORTANTES:
    - Máximo 10 dispositivos por habitación
    - Los dispositivos deben estar asociados a una habitación existente
    - Respetar los rangos de valores específicos de cada tipo
    - El horno solo puede añadirse en la cocina
    - En el baño únicamente pueden añadirse luces
    
    COMUNICACIÓN:
    - Sé claro sobre las capacidades de cada dispositivo
    - Informa cuando se excedan los límites permitidos
    - Confirma los cambios de estado realizados
    """

# ========== RESOURCES ==========

@mcp.resource("domotica://devices/state")
def get_devices_state() -> str:
    """
    Obtiene el estado actual de todos los dispositivos del sistema.
    Proporciona información detallada por tipo de dispositivo.
    """
    output = "=== ESTADO DE DISPOSITIVOS ===\n\n"
    
    devices = storage.list_devices()
    
    if not devices:
        output += "No hay dispositivos en el sistema.\n"
        return output
    
    # Agrupar por tipo
    by_type = {
        'light': [],
        'thermostat': [],
        'fan': [],
        'oven': []
    }
    
    for dev in devices:
        dev_type = dev['type']
        if dev_type in by_type:
            by_type[dev_type].append(dev)
    
    # Luces
    if by_type['light']:
        output += "💡 LUCES:\n"
        for dev in by_type['light']:
            estado = '✓ Encendida' if dev['state'] else '✗ Apagada'
            output += f"   {dev['id']} ({dev['room']}): {estado}\n"
        output += "\n"
    
    # Termostatos
    if by_type['thermostat']:
        output += "🌡️ TERMOSTATOS:\n"
        for dev in by_type['thermostat']:
            output += f"   {dev['id']} ({dev['room']}): {dev['state']}°C\n"
        output += "\n"
    
    # Ventiladores
    if by_type['fan']:
        output += "🌀 VENTILADORES:\n"
        for dev in by_type['fan']:
            estado = "Apagado" if dev['state'] == 0 else f"Velocidad {dev['state']}/5"
            output += f"   {dev['id']} ({dev['room']}): {estado}\n"
        output += "\n"
    
    # Hornos
    if by_type['oven']:
        output += "🔥 HORNOS:\n"
        for dev in by_type['oven']:
            if isinstance(dev['state'], dict):
                temp = dev['state'].get('temperature', 0)
                timer = dev['state'].get('timer', 0)
                active = dev['state'].get('active', False)
                estado = f"{'🟢 Activo' if active else '⚪ Inactivo'} - {temp}°C"
                if timer > 0:
                    estado += f" - ⏲️ {timer} min"
                output += f"   {dev['id']} ({dev['room']}): {estado}\n"
            else:
                output += f"   {dev['id']} ({dev['room']}): {dev['state']}\n"
        output += "\n"
    
    output += f"Total: {len(devices)} dispositivos en el sistema\n"
    
    return output

@mcp.resource("domotica://devices/{device_id}")
def get_device_detail(device_id: str) -> str:
    """
    Obtiene información detallada de un dispositivo específico.
    """
    try:
        if device_id not in storage.devices:
            return f"Error: Dispositivo '{device_id}' no encontrado"
        
        device = storage.devices[device_id].to_dict()
        
        tipo_str = {
            'light': '💡 Luz',
            'thermostat': '🌡️ Termostato',
            'fan': '🌀 Ventilador',
            'oven': '🔥 Horno'
        }.get(device['type'], device['type'])
        
        output = f"=== DISPOSITIVO: {device_id} ===\n\n"
        output += f"Tipo: {tipo_str}\n"
        output += f"Habitación: {device['room']}\n"
        
        # Estado según tipo
        if device['type'] == 'light':
            output += f"Estado: {'Encendida ✓' if device['state'] else 'Apagada ✗'}\n"
        elif device['type'] == 'thermostat':
            output += f"Temperatura: {device['state']}°C\n"
            output += f"Rango permitido: {storage.MIN_TEMP}°C - {storage.MAX_TEMP}°C\n"
        elif device['type'] == 'fan':
            if device['state'] == 0:
                output += f"Estado: Apagado\n"
            else:
                output += f"Velocidad: {device['state']}/5\n"
            output += f"Velocidades disponibles: 0 (apagado) - 5 (máxima)\n"
        elif device['type'] == 'oven':
            if isinstance(device['state'], dict):
                output += f"Temperatura: {device['state'].get('temperature', 0)}°C\n"
                output += f"Temporizador: {device['state'].get('timer', 0)} minutos\n"
                output += f"Estado: {'🟢 Activo' if device['state'].get('active', False) else '⚪ Inactivo'}\n"
                output += f"\nRango temperatura: {storage.MIN_OVEN_TEMP}°C - {storage.MAX_OVEN_TEMP}°C\n"
                output += f"Temporizador máximo: {storage.MAX_OVEN_TIMER} minutos\n"
        
        return output
        
    except Exception as e:
        return f"Error: {str(e)}"

# ========== TOOLS - CONSULTAS ==========

@mcp.tool()
def consultar_dispositivos(room_name: Optional[str] = None) -> list[dict]:
    """
    Obtiene la lista de dispositivos. Puede filtrar por habitación.
    
    Args:
        room_name: nombre de la habitación para filtrar (opcional)
    
    Returns:
        Lista de dispositivos con toda su información.
    """
    return storage.list_devices(room_name)

@mcp.tool()
def consultar_dispositivo(device_id: str) -> dict:
    """
    Obtiene información detallada de un dispositivo específico.
    
    Args:
        device_id: ID del dispositivo (ej: 'light-01', 'thermo-01', 'fan-01', 'oven-01')
    
    Returns:
        Información completa del dispositivo.
    """
    if device_id not in storage.devices:
        raise ValueError(f"Dispositivo '{device_id}' no encontrado")
    
    return storage.devices[device_id].to_dict()

# ========== TOOLS - GESTIÓN ==========

@mcp.tool()
def agregar_dispositivo(
    room_name: str, 
    device_type: str, 
    initial_state: Optional[str] = None
) -> dict:
    """
    Añade un dispositivo a una habitación. El ID se genera automáticamente.
    
    Args:
        room_name: nombre de la habitación donde se instalará
        device_type: tipo de dispositivo: 'light', 'thermostat', 'fan', 'oven'
        initial_state: estado inicial (opcional):
            - light: "true" o "false" (por defecto: "false")
            - thermostat: temperatura 16-32 (por defecto: "21")
            - fan: velocidad 0-5 (por defecto: "0")
            - oven: is active (por defecto: inactivo)
    
    Returns:
        Confirmación con ID generado y estado inicial.
    
    Restricciones:
        - Máximo 10 dispositivos por habitación
        - La habitación debe existir
        - El horno solo puede añadirse en la cocina
        - En el baño únicamente pueden añadirse luces
    """
    # Procesar initial_state según tipo
    state = None
    if initial_state is not None:
        if device_type == "light":
            state = initial_state.lower() == "true"
        elif device_type in ["thermostat", "fan"]:
            state = int(initial_state)
    
    return storage.add_device(room_name, device_type, state)

@mcp.tool()
def modificar_dispositivo(
    device_id: str, 
    room: Optional[str] = None, 
    state: Optional[str] = None
) -> dict:
    """
    Modifica un dispositivo existente (habitación o estado).
    
    Args:
        device_id: ID del dispositivo
        room: nueva habitación (opcional)
        state: nuevo estado (opcional):
            - light: "true" o "false"
            - thermostat: temperatura como string (ej: "24")
            - fan: velocidad como string (ej: "3")
            - oven: usar herramientas específicas (ajustar_horno)
    
    Returns:
        Estado actualizado del dispositivo.
    """
    # Procesar state según el tipo de dispositivo
    processed_state = None
    if state is not None:
        device = storage.devices.get(device_id)
        if device:
            if device.type == "light":
                processed_state = state.lower() == "true"
            elif device.type in ["thermostat", "fan"]:
                processed_state = int(state)
    
    return storage.update_device(device_id, room, processed_state)

@mcp.tool()
def eliminar_dispositivo(device_id: str) -> dict:
    """
    Elimina un dispositivo del sistema.
    
    Args:
        device_id: ID del dispositivo a eliminar
    
    Returns:
        Confirmación de eliminación.
    """
    return storage.delete_device(device_id)

# ========== TOOLS - CONTROL ESPECÍFICO DE LUCES ==========

@mcp.tool()
def alternar_luz(device_id: str) -> dict:
    """
    Alterna el estado de una luz (encendida ↔ apagada).
    
    Args:
        device_id: identificador de la luz (ej: 'light-01')
    
    Returns:
        Estado actualizado de la luz.
    """
    if device_id not in storage.devices:
        raise ValueError(f"Dispositivo '{device_id}' no encontrado")
    
    device = storage.devices[device_id]
    if device.type != "light":
        raise ValueError(f"Dispositivo '{device_id}' no es una luz, es un {device.type}")
    
    new_state = not device.state
    return storage.update_device(device_id, state=new_state)

@mcp.tool()
def encender_luz(device_id: str) -> dict:
    """
    Enciende una luz específica.
    
    Args:
        device_id: identificador de la luz
    
    Returns:
        Estado actualizado.
    """
    if device_id not in storage.devices:
        raise ValueError(f"Dispositivo '{device_id}' no encontrado")
    
    device = storage.devices[device_id]
    if device.type != "light":
        raise ValueError(f"Dispositivo '{device_id}' no es una luz")
    
    return storage.update_device(device_id, state=True)

@mcp.tool()
def apagar_luz(device_id: str) -> dict:
    """
    Apaga una luz específica.
    
    Args:
        device_id: identificador de la luz
    
    Returns:
        Estado actualizado.
    """
    if device_id not in storage.devices:
        raise ValueError(f"Dispositivo '{device_id}' no encontrado")
    
    device = storage.devices[device_id]
    if device.type != "light":
        raise ValueError(f"Dispositivo '{device_id}' no es una luz")
    
    return storage.update_device(device_id, state=False)

# ========== TOOLS - CONTROL ESPECÍFICO DE TERMOSTATOS ==========

@mcp.tool()
def ajustar_termostato(device_id: str, temperature: int) -> dict:
    """
    Ajusta la temperatura de un termostato.
    
    Args:
        device_id: identificador del termostato (ej: 'thermo-01')
        temperature: temperatura deseada en °C (16-32)
    
    Returns:
        Estado actualizado con la nueva temperatura.
    """
    if device_id not in storage.devices:
        raise ValueError(f"Dispositivo '{device_id}' no encontrado")
    
    device = storage.devices[device_id]
    if device.type != "thermostat":
        raise ValueError(f"Dispositivo '{device_id}' no es un termostato")
    
    return storage.update_device(device_id, state=temperature)

@mcp.tool()
def subir_temperatura(device_id: str, grados: int = 1) -> dict:
    """
    Incrementa la temperatura del termostato.
    
    Args:
        device_id: identificador del termostato
        grados: cuántos grados subir (por defecto: 1)
    
    Returns:
        Estado actualizado.
    """
    if device_id not in storage.devices:
        raise ValueError(f"Dispositivo '{device_id}' no encontrado")
    
    device = storage.devices[device_id]
    if device.type != "thermostat":
        raise ValueError(f"Dispositivo '{device_id}' no es un termostato")
    
    nueva_temp = min(device.state + grados, storage.MAX_TEMP)
    return storage.update_device(device_id, state=nueva_temp)

@mcp.tool()
def bajar_temperatura(device_id: str, grados: int = 1) -> dict:
    """
    Reduce la temperatura del termostato.
    
    Args:
        device_id: identificador del termostato
        grados: cuántos grados bajar (por defecto: 1)
    
    Returns:
        Estado actualizado.
    """
    if device_id not in storage.devices:
        raise ValueError(f"Dispositivo '{device_id}' no encontrado")
    
    device = storage.devices[device_id]
    if device.type != "thermostat":
        raise ValueError(f"Dispositivo '{device_id}' no es un termostato")
    
    nueva_temp = max(device.state - grados, storage.MIN_TEMP)
    return storage.update_device(device_id, state=nueva_temp)

# ========== TOOLS - CONTROL ESPECÍFICO DE VENTILADORES ==========

@mcp.tool()
def ajustar_ventilador(device_id: str, speed: int) -> dict:
    """
    Ajusta la velocidad de un ventilador.
    
    Args:
        device_id: identificador del ventilador (ej: 'fan-01')
        speed: velocidad deseada (0=apagado, 1-5=velocidades)
    
    Returns:
        Estado actualizado con la nueva velocidad.
    """
    if device_id not in storage.devices:
        raise ValueError(f"Dispositivo '{device_id}' no encontrado")
    
    device = storage.devices[device_id]
    if device.type != "fan":
        raise ValueError(f"Dispositivo '{device_id}' no es un ventilador")
    
    return storage.update_device(device_id, state=speed)

@mcp.tool()
def apagar_ventilador(device_id: str) -> dict:
    """
    Apaga el ventilador (velocidad 0).
    
    Args:
        device_id: identificador del ventilador
    
    Returns:
        Estado actualizado.
    """
    return ajustar_ventilador(device_id, 0)

# ========== TOOLS - CONTROL ESPECÍFICO DE HORNOS ==========

@mcp.tool()
def ajustar_horno(
    device_id: str, 
    temperature: Optional[int] = None,
    timer: Optional[int] = None,
    active: Optional[bool] = None
) -> dict:
    """
    Ajusta los parámetros del horno.
    
    Args:
        device_id: identificador del horno (ej: 'oven-01')
        temperature: temperatura deseada en °C (160-240), opcional
        timer: temporizador en minutos (0-240), opcional
        active: activar/desactivar el horno, opcional
    
    Returns:
        Estado actualizado del horno.
    """
    if device_id not in storage.devices:
        raise ValueError(f"Dispositivo '{device_id}' no encontrado")
    
    device = storage.devices[device_id]
    if device.type != "oven":
        raise ValueError(f"Dispositivo '{device_id}' no es un horno")
    
    # Obtener estado actual
    current_state = device.state if isinstance(device.state, dict) else {
        "temperature": storage.DEFAULT_OVEN_TEMP,
        "timer": 0,
        "active": False
    }
    
    # Preparar nuevo estado
    new_state = current_state.copy()
    
    if temperature is not None:
        new_state["temperature"] = temperature
    
    if timer is not None:
        new_state["timer"] = timer
    
    if active is not None:
        new_state["active"] = active
    
    return storage.update_device(device_id, state=new_state)

@mcp.tool()
def encender_horno(device_id: str) -> dict:
    """
    Enciende el horno (activa el horno con la temperatura configurada).
    
    Args:
        device_id: identificador del horno
    
    Returns:
        Estado actualizado.
    """
    return ajustar_horno(device_id, active=True)

@mcp.tool()
def apagar_horno(device_id: str) -> dict:
    """
    Apaga el horno (desactiva el horno).
    
    Args:
        device_id: identificador del horno
    
    Returns:
        Estado actualizado.
    """
    return ajustar_horno(device_id, active=False)

@mcp.tool()
def configurar_temporizador_horno(device_id: str, minutos: int) -> dict:
    """
    Configura el temporizador del horno.
    
    Args:
        device_id: identificador del horno
        minutos: tiempo en minutos (0-240)
    
    Returns:
        Estado actualizado.
    """
    return ajustar_horno(device_id, timer=minutos)

if __name__ == "__main__":
    mcp.run(transport="stdio")
