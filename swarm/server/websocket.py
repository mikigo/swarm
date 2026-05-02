import asyncio
import json
from typing import Any, Dict, Optional

from fastapi import WebSocket, WebSocketDisconnect
from loguru import logger

from swarm.server import client as client_manager
from swarm.server import task as task_manager
from swarm.server.config import settings
from swarm.server.models import Client, ClientStatus, TaskStatus


class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, client_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[client_id] = websocket
        logger.info(f"Client {client_id} connected")

    def disconnect(self, client_id: str):
        if client_id in self.active_connections:
            del self.active_connections[client_id]
            logger.info(f"Client {client_id} disconnected")

    async def send_message(self, client_id: str, message: dict) -> bool:
        if client_id not in self.active_connections:
            return False
        try:
            await self.active_connections[client_id].send_json(message)
            return True
        except Exception as e:
            logger.error(f"Failed to send message to {client_id}: {e}")
            self.disconnect(client_id)
            return False

    async def broadcast(self, message: dict):
        for client_id in list(self.active_connections.keys()):
            await self.send_message(client_id, message)


connection_manager = ConnectionManager()


async def handle_register(websocket: WebSocket, data: dict):
    import uuid
    hostname = data.get("hostname", "unknown")
    ip = data.get("ip", "unknown")
    os_info = data.get("os", "")
    python_version = data.get("python_version", "")
    
    client_id = str(uuid.uuid4())
    client = Client(
        id=client_id,
        name=f"client-{client_id[:8]}",
        hostname=hostname,
        ip=ip,
        os=os_info,
        python_version=python_version,
        status=ClientStatus.ONLINE,
    )
    
    client_manager.register_client(client)
    await connection_manager.connect(client_id, websocket)
    
    await connection_manager.send_message(client_id, {
        "action": "registered",
        "client_id": client_id,
        "message": "Registration successful",
    })
    
    logger.info(f"Client {client_id} ({hostname}) registered")


async def handle_heartbeat(client_id: str):
    client_manager.update_client_heartbeat(client_id)
    await connection_manager.send_message(client_id, {
        "action": "heartbeat_ack",
    })


async def handle_task_request(client_id: str, data: dict):
    task_result = data.get("result")
    current_task_id = data.get("task_id")
    
    if current_task_id and task_result:
        task_manager.update_task_result(current_task_id, current_task_id, task_result)
        client_manager.update_client_task(client_id, None)
    
    idle_clients = client_manager.list_idle_clients()
    if not idle_clients:
        await connection_manager.send_message(client_id, {
            "action": "no_task",
            "message": "No pending tasks",
        })
        return
    
    pending_tasks = task_manager.get_pending_tasks()
    if not pending_tasks:
        await connection_manager.send_message(client_id, {
            "action": "no_task",
            "message": "No pending tasks",
        })
        return
    
    task = pending_tasks[0]
    task_manager.update_task_status(task.id, TaskStatus.RUNNING)
    client_manager.update_client_task(client_id, task.id)
    
    if task.test_files:
        test_file = task.test_files[0]
    else:
        test_file = ""
    
    await connection_manager.send_message(client_id, {
        "action": "task",
        "task_id": task.id,
        "test_file": test_file,
        "repo_url": task.repo_url,
        "branch": task.branch,
        "client_args": task.client_args.model_dump() if task.client_args else {},
    })
    
    logger.info(f"Assigned task {task.id} to client {client_id}")


async def handle_log(client_id: str, data: dict):
    message = data.get("message", "")
    task_id = data.get("task_id")
    logger.info(f"[Task {task_id}] {message}")


async def handle_client_message(websocket: WebSocket, client_id: str, data: dict):
    action = data.get("action")
    
    if action == "register":
        await handle_register(websocket, data)
    elif action == "heartbeat":
        await handle_heartbeat(client_id)
    elif action == "next":
        await handle_task_request(client_id, data)
    elif action == "log":
        await handle_log(client_id, data)
    else:
        logger.warning(f"Unknown action: {action}")


async def websocket_endpoint(websocket: WebSocket, client_id: str = ""):
    if client_id:
        client_data = client_manager.load_client(client_id)
        if not client_data:
            await websocket.close(code=4004, reason="Client not registered")
            return
        
        await connection_manager.connect(client_id, websocket)
    else:
        client_id = None
    
    try:
        while True:
            data = await websocket.receive_json()
            if client_id is None and data.get("action") == "register":
                reg_data = await websocket.receive_json()
                client_id = data.get("client_id")
            else:
                await handle_client_message(websocket, client_id, data)
    except WebSocketDisconnect:
        if client_id:
            connection_manager.disconnect(client_id)
            client_manager.update_client_status(client_id, ClientStatus.OFFLINE)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        if client_id:
            connection_manager.disconnect(client_id)
            client_manager.update_client_status(client_id, ClientStatus.OFFLINE)