from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from sqlmodel import SQLModel

from app.db import get_engine
from app.routes.dashboard import router as dashboard_router
from app.routes.demo import router as demo_router
from app.routes.voice import router as voice_router


@asynccontextmanager
async def lifespan(_: FastAPI):
    SQLModel.metadata.create_all(get_engine())
    yield


app = FastAPI(title="calle-receiver", lifespan=lifespan)
app.include_router(voice_router)
app.include_router(dashboard_router)
app.include_router(demo_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/", include_in_schema=False)
def root() -> RedirectResponse:
    return RedirectResponse("/demo")
