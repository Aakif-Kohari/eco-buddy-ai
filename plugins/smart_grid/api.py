"""
Smart Grid REST API & WebSockets.
Exposes the simulation engine via a high-performance FastAPI backend.
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Any, List
import asyncio
import json
import logging
from .engine import SmartGridSimulation

logger = logging.getLogger(__name__)

app = FastAPI(title="Smart Grid Command API", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global simulation instance (would be managed differently in prod)
sim_engine: SmartGridSimulation = None

@app.on_event("startup")
async def startup_event():
    global sim_engine
    if not sim_engine:
        sim_engine = SmartGridSimulation(region="US-CA", speed_multiplier=1.0)
        # We don't start the loop here, we just initialize the object

@app.get("/api/v1/status")
async def get_status():
    """Returns the high-level status of the simulation."""
    if not sim_engine:
        return {"status": "uninitialized"}
    
    return {
        "is_running": sim_engine.is_running,
        "region": sim_engine.region,
        "sim_time": sim_engine.sim_time,
        "net_power_kw": sim_engine.net_power_kw,
        "device_count": len(sim_engine.devices)
    }

@app.get("/api/v1/devices")
async def get_devices():
    """Returns the current state of all connected IoT devices."""
    if not sim_engine:
        return []
        
    devices = []
    for d in sim_engine.devices:
        devices.append(d.get_telemetry())
    return devices

@app.post("/api/v1/devices/{device_id}/command")
async def command_device(device_id: str, payload: Dict[str, Any]):
    """Injects a manual override command into a specific device via the broker."""
    if not sim_engine:
        return {"error": "Engine not running"}
        
    topic = f"home/devices/command/{device_id}"
    await sim_engine.broker.publish(topic, payload)
    return {"status": "command_queued", "topic": topic}

@app.post("/api/v1/simulation/start")
async def start_sim():
    """Starts the simulation background loop."""
    global sim_engine
    if sim_engine and not sim_engine.is_running:
        asyncio.create_task(sim_engine.run_simulation(duration_real_seconds=86400))
        return {"status": "started"}
    return {"status": "already_running"}

@app.post("/api/v1/simulation/stop")
async def stop_sim():
    """Stops the simulation gracefully."""
    global sim_engine
    if sim_engine and sim_engine.is_running:
        sim_engine.is_running = False
        return {"status": "stopping"}
    return {"status": "already_stopped"}

# --- WebSockets ---

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info("New WebSocket client connected.")

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        logger.info("WebSocket client disconnected.")

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                logger.error(f"Failed to send WS message: {e}")

manager = ConnectionManager()

@app.websocket("/ws/telemetry")
async def websocket_telemetry(websocket: WebSocket):
    """
    Streams raw telemetry from the Message Broker directly to the web client.
    """
    await manager.connect(websocket)
    
    # Define a bridge callback that pipes broker messages to this websocket
    async def broker_to_ws(topic: str, payload: Dict[str, Any]):
        msg = json.dumps({"topic": topic, "payload": payload})
        try:
            await websocket.send_text(msg)
        except Exception:
            pass # Disconnects are handled by the exception block below

    if sim_engine:
        await sim_engine.broker.subscribe("home/devices/#", broker_to_ws)
    
    try:
        while True:
            # Keep connection open and listen for client pings
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        if sim_engine:
            await sim_engine.broker.unsubscribe("home/devices/#", broker_to_ws)
