from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.rest import router as rest_router
from app.api.ws import router as ws_router
from app.pipeline.event_bus import EventBus
from app.pipeline.pipeline_manager import PipelineManager


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.event_bus = EventBus()
    app.state.pipeline = PipelineManager(app.state.event_bus)
    try:
        yield
    finally:
        await app.state.pipeline.stop()
        app.state.event_bus.close()


app = FastAPI(title="LANvideo Cam Lab", version="0.1.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

app.include_router(rest_router)
app.include_router(ws_router)


@app.get("/")
def root() -> dict:
    return {"name": "LANvideo Cam Lab", "status": "ok"}
