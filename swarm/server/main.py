from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from loguru import logger

from swarm.server.config import ensure_directories, get_report_dir, settings
from swarm.server import api as swarm_api
from swarm.server import websocket as ws_handler


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Swarm Server...")
    ensure_directories()
    logger.info(f"Data directory: {settings.data_dir}")
    logger.info(f"Server will listen on {settings.host}:{settings.port}")
    yield
    logger.info("Shutting down Swarm Server...")


def create_app() -> FastAPI:
    app = FastAPI(
        title="Swarm Server",
        description="Distributed automated test execution framework",
        version="0.1.0",
        lifespan=lifespan,
    )
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    swarm_api.create_api_routes(app)
    app.add_api_websocket_route("/ws/{client_id}", ws_handler.websocket_endpoint)
    
    @app.get("/api/reports/{task_id}")
    async def get_report(task_id: str):
        report_dir = get_report_dir(task_id)
        index_file = report_dir / "index.html"
        if index_file.exists():
            return HTMLResponse(content=index_file.read_text())
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Report not found")
    
    return app


app = create_app()


@app.get("/")
async def root():
    return {"message": "Swarm Server is running", "version": "0.1.0"}


@app.get("/health")
async def health():
    return {"status": "healthy"}