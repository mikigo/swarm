import json
from typing import Dict, List, Optional

from loguru import logger

from swarm.server.config import settings
from swarm.server.models import Client, ClientStatus


DATA_FILE = settings.data_dir / "clients.json"


def _load_clients() -> Dict[str, Client]:
    if not DATA_FILE.exists():
        return {}
    try:
        data = json.loads(DATA_FILE.read_text())
        return {cid: Client(**cdata) for cid, cdata in data.items()}
    except Exception as e:
        logger.error(f"Failed to load clients: {e}")
        return {}


def _save_clients(clients: Dict[str, Client]) -> bool:
    try:
        data = {cid: c.model_dump() for cid, c in clients.items()}
        DATA_FILE.write_text(json.dumps(data, indent=2, default=str))
        return True
    except Exception as e:
        logger.error(f"Failed to save clients: {e}")
        return False


def register_client(client: Client) -> bool:
    clients = _load_clients()
    clients[client.id] = client
    return _save_clients(clients)


def update_client(client: Client) -> bool:
    clients = _load_clients()
    if client.id not in clients:
        return False
    clients[client.id] = client
    return _save_clients(clients)


def load_client(client_id: str) -> Optional[Client]:
    clients = _load_clients()
    return clients.get(client_id)


def list_clients() -> List[Client]:
    clients = _load_clients()
    return list(clients.values())


def list_online_clients() -> List[Client]:
    clients = _load_clients()
    return [c for c in clients.values() if c.status == ClientStatus.ONLINE]


def list_idle_clients() -> List[Client]:
    clients = _load_clients()
    return [
        c for c in clients.values()
        if c.status == ClientStatus.ONLINE and c.current_task_id is None
    ]


def unregister_client(client_id: str) -> bool:
    clients = _load_clients()
    if client_id in clients:
        del clients[client_id]
        return _save_clients(clients)
    return False


def update_client_status(client_id: str, status: ClientStatus) -> bool:
    client = load_client(client_id)
    if not client:
        return False
    client.status = status
    return update_client(client)


def update_client_heartbeat(client_id: str) -> bool:
    from datetime import datetime
    client = load_client(client_id)
    if not client:
        return False
    client.last_heartbeat = datetime.now()
    return update_client(client)


def update_client_task(client_id: str, task_id: Optional[str]) -> bool:
    client = load_client(client_id)
    if not client:
        return False
    client.current_task_id = task_id
    if task_id:
        client.status = ClientStatus.BUSY
    else:
        client.status = ClientStatus.ONLINE
    return update_client(client)