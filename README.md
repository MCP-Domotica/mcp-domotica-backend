# 🏠 Sistema Domótico MCP

Sistema de gestión domótica basado en el **Model Context Protocol (MCP)** que permite controlar dispositivos inteligentes en diferentes habitaciones mediante servidores especializados. Implementado como una arquitectura de microservicios MCP para gestión eficiente de espacios residenciales y sus dispositivos asociados.

## 📋 Descripción General

Este proyecto implementa un sistema domótico completo utilizando el Model Context Protocol (MCP) con dos servidores independientes que operan de forma coordinada:

- **`mcp_rooms`**: Servidor dedicado a la gestión completa de habitaciones (creación, modificación, eliminación y consulta)
- **`mcp_devices`**: Servidor especializado en el control de dispositivos domóticos (luces, termostatos, ventiladores y hornos)

### Capacidades del Sistema

El sistema está diseñado para gestionar hasta **6 habitaciones** con un máximo de **10 dispositivos por habitación**, aplicando reglas de negocio específicas según el tipo de espacio y dispositivo. La persistencia de datos se maneja mediante archivos JSON con sincronización automática entre procesos.

## ✨ Características Principales

### Dispositivos Soportados

El sistema implementa cuatro tipos de dispositivos inteligentes, cada uno con sus propias capacidades de control:

- 💡 **Luces**: Control binario de encendido/apagado
- 🌡️ **Termostatos**: Regulación de temperatura en rango de 16°C a 32°C
- 🌀 **Ventiladores**: Control de velocidad en 6 niveles (0 = apagado, 1-5 = velocidades)
- 🔥 **Hornos**: Gestión de temperatura (160°C - 240°C), temporizador (0-240 minutos) y estado activo/inactivo

### Tipos de Habitaciones

El sistema reconoce cinco categorías de espacios residenciales:

- 🍽️ **Comedor**: Admite todos los tipos de dispositivos
- 🍳 **Cocina**: Admite todos los tipos de dispositivos (único espacio donde se permite horno)
- 🚿 **Baño**: Restricción de seguridad - únicamente luces
- 🛋️ **Living**: Admite todos los dispositivos excepto horno
- 🛏️ **Dormitorio**: Admite todos los dispositivos excepto horno

### Reglas de Negocio

El sistema implementa las siguientes restricciones para garantizar coherencia y seguridad:

- Límite máximo de 6 habitaciones en el sistema
- Límite máximo de 10 dispositivos por habitación
- Restricción de ubicación: hornos únicamente en cocina
- Restricción de dispositivos: baños limitados a iluminación
- Asignación automática de nombres: numeración incremental para habitaciones duplicadas (ej: "dormitorio", "dormitorio 2")

## 🚀 Instalación y Configuración

### Requisitos del Sistema

- **Python**: Versión 3.13 o superior
- **uv**: Gestor de paquetes y entornos virtuales para Python ([Astral uv](https://github.com/astral-sh/uv))

### Instalación de uv

El proyecto utiliza `uv` como gestor de dependencias por su velocidad y eficiencia. Si aún no lo tiene instalado:

**Windows (PowerShell):**

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

**macOS/Linux:**

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Configuración del Proyecto

**1. Clonar el repositorio:**

```powershell
git clone https://github.com/CrisDeCrisis/mcp-domotica-backend.git
cd mcp-domotica-backend
```

**2. Sincronizar dependencias:**

```powershell
uv sync
```

> **Nota:** Este comando lee automáticamente el archivo `pyproject.toml`, crea el entorno virtual `.venv` e instala todas las dependencias necesarias. No es necesario activar manualmente el entorno virtual al utilizar `uv run`.

## 🎮 Ejecución de Servidores

### Iniciar Servidores MCP

Cada servidor puede ejecutarse de forma independiente utilizando `uv run`:

**Servidor de Gestión de Habitaciones:**

```powershell
uv run servers/mcp_rooms.py
```

**Servidor de Gestión de Dispositivos:**

```powershell
uv run servers/mcp_devices.py
```

> **Nota:** El comando `uv run` ejecuta automáticamente los scripts en el entorno virtual del proyecto, eliminando la necesidad de activación manual del entorno.

## 📚 Arquitectura del Proyecto

### Estructura de Directorios

```
backend/
├── servers/
│   ├── mcp_rooms.py       # Servidor MCP para gestión de habitaciones
│   └── mcp_devices.py     # Servidor MCP para gestión de dispositivos
├── models.py              # Definición de modelos de datos (Device, Room)
├── storage.py             # Capa de persistencia y almacenamiento
├── domotica_data.json     # Base de datos JSON para persistencia
├── pyproject.toml         # Configuración de proyecto y dependencias
└── README.md              # Documentación del proyecto
```

### Componentes del Sistema

- **Servidores MCP**: Implementan los endpoints del Model Context Protocol para cada dominio (habitaciones y dispositivos)
- **Modelos**: Clases Python que definen la estructura de datos de habitaciones y dispositivos
- **Capa de Almacenamiento**: Gestiona la persistencia en JSON con sincronización automática
- **Archivo de Datos**: Almacenamiento persistente en formato JSON con estado del sistema completo

## 🔌 API de Herramientas MCP

### Servidor de Habitaciones (`mcp_rooms`)

Proporciona operaciones CRUD completas para la gestión de espacios:

| Herramienta                                | Descripción                                     |
| ------------------------------------------ | ----------------------------------------------- |
| `consultar_habitaciones()`                 | Retorna lista completa de habitaciones          |
| `consultar_habitacion(room_name)`          | Obtiene información detallada de una habitación |
| `agregar_habitacion(room_type)`            | Crea una nueva habitación del tipo especificado |
| `modificar_habitacion(old_name, new_name)` | Actualiza el nombre de una habitación existente |
| `eliminar_habitacion(room_name)`           | Elimina una habitación (debe estar vacía)       |

### Servidor de Dispositivos (`mcp_devices`)

Proporciona control granular sobre dispositivos inteligentes:

#### Operaciones Generales

- `consultar_dispositivos(room_name?)` - Obtiene lista de dispositivos (opcional: filtrar por habitación)
- `consultar_dispositivo(device_id)` - Obtiene información detallada de un dispositivo específico
- `agregar_dispositivo(room_name, device_type, initial_state?)` - Crea un nuevo dispositivo
- `modificar_dispositivo(device_id, room?, state?)` - Actualiza ubicación o estado de un dispositivo
- `eliminar_dispositivo(device_id)` - Elimina un dispositivo del sistema

#### Control de Iluminación

- `alternar_luz(device_id)` - Cambia el estado actual (encendido ↔ apagado)
- `encender_luz(device_id)` - Activa la iluminación
- `apagar_luz(device_id)` - Desactiva la iluminación

#### Control de Climatización (Termostatos)

- `ajustar_termostato(device_id, temperature)` - Establece temperatura específica (16°C - 32°C)
- `subir_temperatura(device_id, grados?)` - Incrementa temperatura (predeterminado: 1°C)
- `bajar_temperatura(device_id, grados?)` - Reduce temperatura (predeterminado: 1°C)

#### Control de Ventilación

- `ajustar_ventilador(device_id, speed)` - Establece velocidad (0: apagado, 1-5: velocidades)
- `apagar_ventilador(device_id)` - Detiene el ventilador (velocidad 0)

#### Control de Hornos

- `ajustar_horno(device_id, temperature?, timer?, active?)` - Configuración completa del horno
- `encender_horno(device_id)` - Activa el horno con temperatura configurada
- `apagar_horno(device_id)` - Desactiva el horno completamente
- `configurar_temporizador_horno(device_id, minutos)` - Establece temporizador (0-240 minutos)

## 📦 Dependencias del Proyecto

El proyecto utiliza las siguientes tecnologías y bibliotecas, definidas en `pyproject.toml`:

### Dependencias Principales

- **`fastapi`** - Framework web moderno y de alto rendimiento para construcción de APIs
- **`uvicorn`** - Servidor ASGI de alto rendimiento para aplicaciones Python asíncronas
- **`mcp[cli]`** - Implementación del Model Context Protocol con herramientas CLI
- **`langchain`** - Framework para desarrollo de aplicaciones con modelos de lenguaje
- **`langchain-mcp-adapters`** - Adaptadores de integración entre LangChain y MCP
- **`langchain-ollama`** - Integración de LangChain con modelos Ollama locales
- **`httpx`** - Cliente HTTP asíncrono de próxima generación
- **`python-dotenv`** - Gestión de variables de entorno desde archivos .env

## 💾 Sistema de Persistencia

### Mecanismo de Almacenamiento

El sistema implementa persistencia automática mediante archivo JSON (`domotica_data.json`) con las siguientes características:

- **Guardado Automático**: Cada modificación del estado se persiste inmediatamente
- **Carga al Inicio**: El sistema recupera el estado previo al iniciar los servidores
- **Estado Inicial**: Si no existe archivo de datos, se crea una configuración predeterminada (1 living con 1 luz y 1 termostato)
- **Sincronización Multi-proceso**: La función `reload()` permite sincronizar el estado entre múltiples instancias

### Formato de Datos

El archivo JSON mantiene un registro estructurado de:

- Colección completa de habitaciones con sus metadatos
- Inventario de dispositivos con sus configuraciones y estados actuales
- Relaciones entre habitaciones y dispositivos asignados

---

## 👨‍💻 Autoría

**Desarrollador:** González, Cristian David - [GitHub](https://github.com/CrisDeCrisis)

---

## 🎓 Contexto Académico

**Proyecto:** Trabajo Práctico Integrador - Sistema Domótico con MCP

**Asignatura:** Modelos de Aplicación de la Inteligencia Artificial

**Docentes:**

- Acosta Gabriel
- Flavian Dante

**Institución:** Instituto Politécnico Formosa

**Programa Académico:** Tecnicatura Superior en Desarrollo de Software Multiplataforma
