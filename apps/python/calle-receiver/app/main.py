from fastapi import FastAPI
from sqlmodel import SQLModel

from app.db import engine
from app.routes.voice import router

SQLModel.metadata.create_all(engine)
app = FastAPI(title="calle-receiver")
app.include_router(router)
