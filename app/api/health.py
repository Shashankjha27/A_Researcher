from fastapi import APIRouter

from app.models.registry import ModelRegistry

router = APIRouter()


@router.get("/health")
def health() -> dict:
    return {"status": "ok", "models": ModelRegistry().health_status()}


@router.post("/health/warmup")
def warmup() -> dict:
    from app.models.warmup import warm_models

    models = warm_models()

    return {"status": "warmed", "models": models}
