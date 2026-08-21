import logging
import os
import threading
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)

from app.api.benchmark import router as benchmark_router
from app.api.claims import router as claims_router
from app.api.config import router as config_router
from app.api.debate import router as debate_router
from app.api.demo import router as demo_router
from app.api.extract import router as extract_router
from app.api.feedback import router as feedback_router
from app.api.health import router as health_router
from app.api.ingest import router as ingest_router
from app.api.jobs import router as jobs_router
from app.api.papers import router as papers_router
from app.api.report import router as report_router
from app.api.verify import router as verify_router
from app.store.demo_seed import ensure_demo_data
from app.ui.routes import router as ui_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    ensure_demo_data()

    if os.environ.get("AR_WARM_MODELS") == "1":
        from app.models.warmup import warm_models

        threading.Thread(target=warm_models, daemon=True).start()

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
app.include_router(debate_router)
app.include_router(report_router)
app.include_router(benchmark_router)
app.include_router(verify_router)
app.include_router(jobs_router)
app.include_router(papers_router)
app.include_router(feedback_router)
app.include_router(demo_router)
app.include_router(ui_router)

WEB_DIST = Path(__file__).resolve().parents[2] / "web" / "dist"

if WEB_DIST.exists():
    app.mount(
        "/assets",
        StaticFiles(directory=str(WEB_DIST / "assets")),
        name="assets",
    )

    @app.get("/{full_path:path}", include_in_schema=False)
    def spa_fallback(full_path: str) -> FileResponse:
        candidate = (WEB_DIST / full_path).resolve()

        if (
            full_path
            and candidate.is_relative_to(WEB_DIST.resolve())
            and candidate.is_file()
        ):
            return FileResponse(candidate)

        return FileResponse(WEB_DIST / "index.html")
