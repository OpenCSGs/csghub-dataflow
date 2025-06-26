from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from loguru import logger
from data_server.agent.webSocketManager import WebSocketManager
from data_server.agent.deps import get_websocket_manager
import json
import asyncio
import datetime

router = APIRouter()

@router.websocket("/runs/{user_id}")
async def run_websocket(
    websocket: WebSocket,
    user_id: str,
    ws_manager: WebSocketManager = Depends(get_websocket_manager),
):
    """WebSocket endpoint for run communication"""
    # TODO Guarantee one user only run one agent task at the same time
    if user_id in ws_manager.active_connections:
        await websocket.close(code=4003, reason="One user cannot run multiple task in same time, finish previously one firstly.")
    
    # Connect websocket
    connected = await ws_manager.connect(websocket, user_id)
    if not connected:
        await websocket.close(code=4002, reason="Failed to establish connection")
        return

    try:
        logger.info(f"WebSocket connection established for run {user_id}")

        while True:
            try:
                raw_message = await websocket.receive_text()
                message = json.loads(raw_message)

                if message.get("type") == "start":
                    # Handle start message
                    logger.info(f"Received start request for run {user_id}")
                    task = message.get("task")
                    if task:
                        # await ws_manager.start_stream(run_id, task, team_config)
                        asyncio.create_task(ws_manager.start_stream(user_id, task))
                    else:
                        logger.warning(f"Invalid start message format for run {user_id}")
                        await websocket.send_json(
                            {
                                "type": "error",
                                "error": "Invalid start message format",
                                "timestamp": datetime.utcnow().isoformat(),
                            }
                        )

                elif message.get("type") == "stop":
                    logger.info(f"Received stop request for run {user_id}")
                    reason = message.get("reason") or "User requested stop/cancellation"
                    await ws_manager.stop_run(user_id, reason=reason)
                    break

                elif message.get("type") == "ping":
                    await websocket.send_json({"type": "pong", "timestamp": datetime.utcnow().isoformat()})

                elif message.get("type") == "input_response":
                    # Handle input response from client
                    response = message.get("response")
                    if response is not None:
                        await ws_manager.handle_input_response(user_id, response)
                    else:
                        logger.warning(f"Invalid input response format for run {user_id}")

            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON received: {raw_message}")
                await websocket.send_json(
                    {"type": "error", "error": "Invalid message format", "timestamp": datetime.utcnow().isoformat()}
                )

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for run {user_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}")
    finally:
        await ws_manager.disconnect(user_id)