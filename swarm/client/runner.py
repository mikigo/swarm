import asyncio
import json
import os
import platform
import socket
import subprocess
import sys
import time
import uuid
from pathlib import Path
from typing import Optional

import httpx
import websockets
from loguru import logger

from swarm.client import git, uploader, venv


class ClientRunner:
    def __init__(self, server_url: str):
        self.server_url = server_url
        self.client_id: Optional[str] = None
        self.websocket: Optional[websockets.WebSocketClientProtocol] = None
        self.current_task_id: Optional[str] = None
        self.current_test_file: Optional[str] = None
    
    async def connect(self):
        self.websocket = await websockets.connect(f"{self.server_url.replace('http', 'ws')}/ws")
    
    async def register(self):
        hostname = socket.gethostname()
        ip = socket.gethostbyname(hostname)
        os_info = platform.platform()
        python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        client_id = str(uuid.uuid4())
        
        await self.websocket.send(json.dumps({
            "action": "register",
            "hostname": hostname,
            "ip": ip,
            "os": os_info,
            "python_version": python_version,
            "client_id": client_id,
        }))
        
        response = await self.websocket.recv()
        data = json.loads(response)
        self.client_id = data.get("client_id")
        
        logger.info(f"Registered as {self.client_id}")
    
    async def send_heartbeat(self):
        if self.websocket:
            await self.websocket.send(json.dumps({"action": "heartbeat"}))
    
    async def request_task(self, result: Optional[dict] = None):
        message = {"action": "next"}
        if self.current_task_id:
            message["task_id"] = self.current_task_id
        if result:
            message["result"] = result
        
        await self.websocket.send(json.dumps(message))
    
    async def run_task(self, task_data: dict):
        test_file = task_data.get("test_file")
        repo_url = task_data.get("repo_url")
        branch = task_data.get("branch", "main")
        client_args = task_data.get("client_args", {})
        
        self.current_task_id = task_data.get("task_id")
        self.current_test_file = test_file
        
        logger.info(f"Executing task: {test_file}")
        
        repo_path = git.clone_repo(repo_url, branch)
        if not repo_path:
            return {"status": "error", "message": "Failed to clone repository"}
        
        venv_path = venv.create_venv(repo_path)
        if not venv_path:
            return {"status": "error", "message": "Failed to create virtual environment"}
        
        venv.install_dependencies(venv_path, repo_path)
        
        result = self.run_pytest(venv_path, test_file, client_args)
        
        if result.get("status") == "passed":
            uploader.upload_results(
                self.server_url,
                self.current_task_id,
                result.get("allure_zip"),
            )
        
        return result
    
    def run_pytest(self, venv_path: Path, test_file: str, client_args: dict) -> dict:
        cmd = [str(venv_path / "bin" / "pytest"), test_file]
        
        timeout = client_args.get("timeout")
        if timeout:
            cmd.extend(["--timeout", str(timeout)])
        
        reruns = client_args.get("reruns")
        if reruns:
            cmd.extend(["--reruns", str(reruns)])
        
        allure_dir = client_args.get("allure_results", "/tmp/allure-results")
        cmd.extend(["--alluredir", allure_dir])
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,
            )
            
            status = "passed" if result.returncode == 0 else "failed"
            
            import zipfile
            import io
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
                allure_results = Path(allure_dir)
                if allure_results.exists():
                    for file in allure_results.rglob("*"):
                        if file.is_file():
                            zf.write(file, file.relative_to(allure_results))
            
            return {
                "status": status,
                "duration": 0.0,
                "passed": 0,
                "failed": 0,
                "error": 0,
                "skipped": 0,
                "allure_zip": zip_buffer.getvalue(),
            }
        except subprocess.TimeoutExpired:
            return {"status": "error", "message": "Test timeout"}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    async def handle_message(self, message: dict):
        action = message.get("action")
        
        if action == "registered":
            logger.info(f"Registration confirmed: {message.get('client_id')}")
        elif action == "task":
            result = await self.run_task(message)
            await self.request_task(result)
        elif action == "no_task":
            logger.info("No pending tasks, waiting...")
            await asyncio.sleep(5)
            await self.request_task()
        elif action == "cancel":
            logger.info(f"Task cancelled: {message.get('task_id')}")
            self.current_task_id = None
    
    async def run(self):
        await self.connect()
        await self.register()
        
        while True:
            try:
                message = await self.websocket.recv()
                data = json.loads(message)
                await self.handle_message(data)
            except websockets.exceptions.ConnectionClosed:
                logger.warning("Connection closed, reconnecting...")
                await self.connect()
                await self.register()


def start_client(server_url: str):
    runner = ClientRunner(server_url)
    asyncio.run(runner.run())