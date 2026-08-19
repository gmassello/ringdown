from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlmodel import SQLModel

from app.db import get_engine
from app.routes.dashboard import router as dashboard_router
from app.routes.voice import router as voice_router


@asynccontextmanager
async def lifespan(_: FastAPI):
    SQLModel.metadata.create_all(get_engine())
    yield


app = FastAPI(title="calle-receiver", lifespan=lifespan)
app.include_router(voice_router)
app.include_router(dashboard_router)
