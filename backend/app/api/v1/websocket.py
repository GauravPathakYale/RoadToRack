"""WebSocket endpoint for real-time simulation updates."""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from datetime import datetime

from app.core.connection_manager import ConnectionManager, get_connection_manager
from app.core.simulation_manager import SimulationManager, get_simulation_manager

router = APIRouter(tags=["WebSocket"])


@router.websocket("/ws/simulation")
async def websocket_simulation(
    websocket: WebSocket,
):
    """
    WebSocket endpoint for real-time simulation updates.

    The server will broadcast:
    - state_update: Full simulation state
    - metrics_update: Current metrics
    - status_change: Simulation status changes

    The client can send:
    - {"type": "command", "command": "start|pause|resume|stop|reset"}
    - {"type": "set_speed", "speed": float}
    """
    conn_manager = get_connection_manager()
    sim_manager = get_simulation_manager()

    await conn_manager.connect(websocket)

    # Register as observer for simulation updates
    async def on_update(update: dict):
        try:
            await websocket.send_json(update)
        except Exception as e:
            print(f"[WS] Observer send error: {e}")

    sim_manager.add_observer(on_update)
    print(f"[WS] Observer registered, total observers: {len(sim_manager._observers)}")

    try:
        # Send initial state
        snapshot = sim_manager.get_snapshot()
        print(f"[WS] Client connected, snapshot exists: {snapshot is not None}, observers: {len(sim_manager._observers)}")
        if snapshot:
            initial_msg = {
                "type": "initial_state",
                "timestamp": datetime.utcnow().isoformat(),
                **snapshot,
            }
            print(f"[WS] Sending initial_state with status: {snapshot.get('status')}, tick: {snapshot.get('tick')}")
            await websocket.send_json(initial_msg)
            print("[WS] initial_state sent successfully")
        else:
            # Even if no snapshot, send current status
            await websocket.send_json({
                "type": "initial_state",
                "timestamp": datetime.utcnow().isoformat(),
                "status": sim_manager.status.name,
                "simulation_time": 0,
                "tick": 0,
                "scooters": [],
                "stations": [],
                "metrics": {},
            })
            print("[WS] Sent empty initial_state")

        while True:
            # Receive messages from client
            data = await websocket.receive_json()
            msg_type = data.get("type")

            try:
                if msg_type == "command":
                    command = data.get("command")
                    if command == "start":
                        await sim_manager.start()
                    elif command == "pause":
                        await sim_manager.pause()
                    elif command == "resume":
                        await sim_manager.resume()
                    elif command == "stop":
                        await sim_manager.stop()
                    elif command == "reset":
                        await sim_manager.reset()

                    await conn_manager.send_to(websocket, {
                        "type": "command_ack",
                        "command": command,
                        "status": sim_manager.status.name,
                    })

                elif msg_type == "set_speed":
                    speed = data.get("speed", 1.0)
                    sim_manager.set_speed(speed)
                    await conn_manager.send_to(websocket, {
                        "type": "speed_ack",
                        "speed": speed,
                    })

                elif msg_type == "ping":
                    await conn_manager.send_to(websocket, {
                        "type": "pong",
                        "timestamp": datetime.utcnow().isoformat(),
                    })

            except Exception as e:
                await conn_manager.send_to(websocket, {
                    "type": "error",
                    "message": str(e),
                })

    except WebSocketDisconnect:
        pass
    finally:
        sim_manager.remove_observer(on_update)
        await conn_manager.disconnect(websocket)
