from typing import List, Optional

from fastapi import APIRouter, FastAPI, HTTPException, UploadFile
from loguru import logger

from swarm.server import task as task_manager
from swarm.server.models import (
    Client,
    ClientStatus,
    Task,
    TaskCreateRequest,
    TaskResponse,
    TaskStatus,
)

router = APIRouter()


@router.post("/api/tasks", response_model=TaskResponse)
async def create_task(request: TaskCreateRequest):
    logger.info(f"Creating task: {request.name}")
    task = task_manager.create_task(
        name=request.name,
        repo_url=request.repo_url,
        branch=request.branch,
        test_paths=request.test_paths,
        filter_args=request.filter_args,
        client_args=request.client_args,
    )
    return TaskResponse(id=task.id, status=task.status, message="Task created")


@router.get("/api/tasks", response_model=List[Task])
async def list_tasks(status: Optional[TaskStatus] = None):
    if status:
        return task_manager.list_tasks_by_status(status)
    return task_manager.list_tasks()


@router.get("/api/tasks/{task_id}", response_model=Task)
async def get_task(task_id: str):
    task = task_manager.load_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.delete("/api/tasks/{task_id}", response_model=TaskResponse)
async def cancel_task(task_id: str):
    task = task_manager.load_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    if task.status in (TaskStatus.COMPLETED, TaskStatus.CANCELLED):
        raise HTTPException(status_code=400, detail="Task cannot be cancelled")
    
    task_manager.update_task_status(task_id, TaskStatus.CANCELLED)
    return TaskResponse(id=task_id, status=TaskStatus.CANCELLED, message="Task cancelled")


@router.post("/api/tasks/{task_id}/retry", response_model=TaskResponse)
async def retry_task(task_id: str):
    task = task_manager.load_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    if task.status not in (TaskStatus.FAILED, TaskStatus.CANCELLED):
        raise HTTPException(status_code=400, detail="Task can only be retried if failed or cancelled")
    
    task_manager.update_task_status(task_id, TaskStatus.PENDING)
    return TaskResponse(id=task_id, status=TaskStatus.PENDING, message="Task retried")


@router.post("/api/tasks/{task_id}/upload")
async def upload_results(task_id: str, file: UploadFile):
    import io
    from fastapi import HTTPException as FastAPIHTTPException
    from swarm.server import report as report_manager
    task = task_manager.load_task(task_id)
    if not task:
        raise FastAPIHTTPException(status_code=404, detail="Task not found")
    
    content = await file.read()
    success = report_manager.save_allure_results(task_id, content)
    if success:
        report_manager.generate_report(task_id)
        return {"message": "Results uploaded and report generated"}
    raise FastAPIHTTPException(status_code=500, detail="Failed to save results")


@router.get("/api/clients", response_model=List[Client])
async def list_clients():
    from swarm.server import client as client_mgr
    return client_mgr.list_clients()


@router.get("/api/clients/{client_id}", response_model=Client)
async def get_client(client_id: str):
    from swarm.server import client as client_mgr
    client = client_mgr.load_client(client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    return client


def create_api_routes(app: FastAPI) -> None:
    app.include_router(router)