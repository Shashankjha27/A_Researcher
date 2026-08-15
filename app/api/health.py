from fastapi import APIRouter

from app.models.registry import ModelRegistry

router = APIRouter()


@router.get("/health")
def health() -> dict:
    return {"status": "ok", "models": ModelRegistry().health_status()}
