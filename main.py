from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from storage import storage
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain.agents import create_agent
from langchain_ollama import ChatOllama

system_prompt = """Eres un asistente de domótica que controla habitaciones y dispositivos.

REGLAS CRÍTICAS PARA USO DE HERRAMIENTAS:

1. SIEMPRE proporciona TODOS los parámetros requeridos por cada herramienta
2. NUNCA inventes parámetros que no existen en la herramienta
3. Lee CUIDADOSAMENTE la descripción de cada herramienta antes de usarla

HERRAMIENTAS DE HABITACIONES:
- agregar_habitacion(room_type: str) → Tipos: "comedor", "cocina", "baño", "living", "dormitorio"
- consultar_habitaciones() → Sin parámetros
- consultar_habitacion(room_name: str)
- modificar_habitacion(old_name: str, new_name: str)
- eliminar_habitacion(room_name: str)

HERRAMIENTAS DE DISPOSITIVOS:
- agregar_dispositivo(room_name: str, device_type: str, initial_state: Optional[str])
  * device_type: "light", "thermostat", "fan", "oven"
  * initial_state: "true"/"false" para luz, "0-5" para ventilador, "16-32" para termostato
  
- consultar_dispositivos(room_name: Optional[str])
- consultar_dispositivo(device_id: str)
- modificar_dispositivo(device_id: str, room: Optional[str], state: Optional[str])
- eliminar_dispositivo(device_id: str)

CONTROL DE LUCES:
- alternar_luz(device_id: str)
- encender_luz(device_id: str)
- apagar_luz(device_id: str)

CONTROL DE TERMOSTATOS:
- ajustar_termostato(device_id: str, temperature: int) → Rango: 16-32°C
- subir_temperatura(device_id: str, grados: int = 1)
- bajar_temperatura(device_id: str, grados: int = 1)

CONTROL DE VENTILADORES:
- ajustar_ventilador(device_id: str, speed: int) → Rango: 0-5
- apagar_ventilador(device_id: str)

CONTROL DE HORNOS:
- ajustar_horno(device_id: str, temperature: Optional[int], timer: Optional[int], active: Optional[bool])
- encender_horno(device_id: str)
- apagar_horno(device_id: str)
- configurar_temporizador_horno(device_id: str, minutos: int)

EJEMPLOS DE USO CORRECTO:
✓ agregar_dispositivo(room_name="cocina", device_type="light", initial_state="false")
✓ ajustar_termostato(device_id="thermo-01", temperature=22)
✓ agregar_habitacion(room_type="dormitorio")

ERRORES COMUNES A EVITAR:
✗ agregar_dispositivo(device_id="light-01") → Faltan room_name y device_type
✗ ajustar_ventilador(speed=3) → Falta device_id
✗ agregar_habitacion(name="sala") → El parámetro es room_type, no name

Responde de forma natural pero USA LAS HERRAMIENTAS CORRECTAMENTE."""

async def lifespan(app: FastAPI):
    """Gestiona el ciclo de vida de la aplicación."""
    global tools, agent
    tools = await client.get_tools()
    agent = create_agent(model, tools, system_prompt=system_prompt)
    yield

app = FastAPI(title="Domótica MCP API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

model = ChatOllama(
    model="gpt-oss:120b-cloud", 
    base_url="http://127.0.0.1:11434"
)

client = MultiServerMCPClient(
    {
        "mcp_rooms": {
            "transport": "stdio",
            "command": "uv",
            "args": [
                "run",
                "./servers/mcp_rooms.py"
            ]
        },
        "mcp_devices": {
            "transport": "stdio",
            "command": "uv",
            "args": [
                "run",
                "./servers/mcp_devices.py"
            ]
        }
    }
)

# Modelos de datos
class ChatRequest(BaseModel):
    message: str

class ChatResponse(BaseModel):
    tools_used: list[dict]
    response: str

# ========== ENDPOINTS DE CHAT ==========
@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Endpoint para enviar mensajes al agente de domótica."""
    try:
        # Verificar que el sistema esté inicializado
        if agent is None or tools is None:
            raise HTTPException(status_code=503, detail="Sistema no inicializado")
        
        response_text = ""
        tools_used = []
        
        async for chunk in agent.astream({"messages": [("user", request.message)]}):
            # Capturar herramientas usadas
            if "model" in chunk:
                model_chunk = chunk["model"]
                if "messages" in model_chunk:
                    for msg in model_chunk["messages"]:
                        if hasattr(msg, "tool_calls") and msg.tool_calls:
                            for tool_call in msg.tool_calls:
                                tools_used.append({
                                    "name": tool_call["name"],
                                    "args": tool_call["args"]
                                })
                        elif hasattr(msg, "content") and msg.content:
                            if msg.__class__.__name__ == "AIMessage":
                                response_text = msg.content
        
        # Si no hay respuesta, proporcionar un mensaje por defecto
        if not response_text:
            response_text = "Operación completada."
        
        return ChatResponse(response=response_text, tools_used=tools_used)
    
    except ValueError as e:
        # Errores de validación del sistema domótico
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # Log del error para debugging
        print(f"Error en /chat: {type(e).__name__}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# ========== ENDPOINTS DE HABITACIONES ==========

@app.get("/rooms")
async def get_rooms():
    """Obtiene la lista de todas las habitaciones."""
    try:
        return {"rooms": storage.list_rooms()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/rooms/{room_name}")
async def get_room(room_name: str):
    """Obtiene información detallada de una habitación."""
    try:
        return storage.get_room_info(room_name)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ========== ENDPOINTS DE DISPOSITIVOS ==========

@app.get("/devices")
async def get_devices(room: Optional[str] = None):
    """Obtiene la lista de todos los dispositivos, opcionalmente filtrados por habitación."""
    try:
        return {"devices": storage.list_devices(room_filter=room)}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/devices/{device_id}")
async def get_device(device_id: str):
    """Obtiene información detallada de un dispositivo."""
    try:
        storage.reload()
        if device_id not in storage.devices:
            raise HTTPException(status_code=404, detail=f"Dispositivo '{device_id}' no encontrado")
        return storage.devices[device_id].to_dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ========== ENDPOINT DE ESTADO GENERAL ==========

@app.get("/status")
async def get_status():
    """Obtiene el estado general del sistema domótico."""
    try:
        storage.reload()
        return {
            "rooms": storage.list_rooms(),
            "devices": storage.list_devices(),
            "total_rooms": len(storage.rooms),
            "total_devices": len(storage.devices)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ========== ENDPOINT DE SALUD ==========

@app.get("/health")
async def health():
    """Verifica que el servidor esté funcionando."""
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=3000)
