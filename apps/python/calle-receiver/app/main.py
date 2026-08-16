from fastapi import FastAPI
from sqlmodel import SQLModel

from app.db import engine
from app.routes.dashboard import router as dashboard_router
from app.routes.voice import router as voice_router

SQLModel.metadata.create_all(engine)
app = FastAPI(title="calle-receiver")
app.include_router(voice_router)
app.include_router(dashboard_router)
