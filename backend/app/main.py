from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.rest import router as rest_router
from app.api.ws import router as ws_router
from app.pipeline.event_bus import EventBus
from app.pipeline.pipeline_manager import PipelineManager

app = FastAPI(title="LANvideo Cam Lab", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

app.state.event_bus = EventBus()
app.state.pipeline = PipelineManager(app.state.event_bus)

app.include_router(rest_router)
app.include_router(ws_router)


@app.get("/")
def root() -> dict:
    return {"name": "LANvideo Cam Lab", "status": "ok"}
