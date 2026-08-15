from fastapi.testclient import TestClient

from app.api.main import app
from app.models.registry import ModelRegistry


def test_health() -> None:
    ModelRegistry.reset()
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["models"] == {"nli": False, "embeddings": False, "contriever": False}


def test_registry_is_singleton() -> None:
    ModelRegistry.reset()
    assert ModelRegistry() is ModelRegistry()
