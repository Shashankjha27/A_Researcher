from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api.benchmark import router as benchmark_router
from app.api.claims import router as claims_router
from app.api.config import router as config_router
from app.api.extract import router as extract_router
from app.api.health import router as health_router
from app.api.ingest import router as ingest_router
from app.api.report import router as report_router
from app.api.verify import router as verify_router
from app.ui.routes import router as ui_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(
    title="A_Researcher",
    lifespan=lifespan,
)

STATIC_DIR = Path(__file__).resolve().parent.parent / "ui" / "static"

app.mount(
    "/static",
    StaticFiles(directory=str(STATIC_DIR)),
    name="static",
)

app.include_router(config_router)
app.include_router(health_router)
app.include_router(ingest_router)
app.include_router(extract_router)
app.include_router(claims_router)
app.include_router(report_router)
app.include_router(benchmark_router)
app.include_router(verify_router)
app.include_router(ui_router)
