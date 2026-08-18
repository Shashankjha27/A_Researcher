from fastapi import FastAPI

from app.api.config import router as config_router
from app.api.health import router as health_router

app = FastAPI(title="A_Researcher")

app.include_router(health_router)
app.include_router(config_router)
