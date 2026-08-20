from fastapi.testclient import TestClient

from app.api import benchmark as benchmark_module
from app.api.main import app

client = TestClient(app)


def test_benchmark_route_exists():
    response = client.get("/openapi.json")

    assert response.status_code == 200
    assert "/benchmark/scifact" in response.json()["paths"]


def test_benchmark_rejects_invalid_split():
    response = client.post(
        "/benchmark/scifact",
        json={"split": "invalid"},
    )

    assert response.status_code == 422


def test_benchmark_rejects_invalid_threshold():
    response = client.post(
        "/benchmark/scifact",
        json={"threshold": 1.5},
    )

    assert response.status_code == 422


def test_benchmark_missing_data(monkeypatch):
    def fake_prepare(split):
        raise FileNotFoundError(f"Missing SciFact split: {split}")

    monkeypatch.setattr(benchmark_module, "prepare_dataset", fake_prepare)

    response = client.post(
        "/benchmark/scifact",
        json={"split": "dev"},
    )

    assert response.status_code == 400
    assert "Missing SciFact split" in response.json()["detail"]


def test_benchmark_returns_metrics(monkeypatch):
    fake_rows = [
        ("SUPPORT", 0.92, 0.88, 0.90),
        ("CONTRADICT", 0.85, 0.80, 0.82),
        ("NEUTRAL", 0.70, 0.65, 0.67),
        ("NOT_ENOUGH_INFO", 0.60, 0.55, 0.57),
    ]

    def fake_prepare(split):
        return [{"claim": "c1", "gold": "SUPPORT", "sentences": []}]

    def fake_evaluate(dataset, threshold, show_progress=True):
        return fake_rows, 0.7675, 0.7200, 0.7400

    monkeypatch.setattr(benchmark_module, "prepare_dataset", fake_prepare)
    monkeypatch.setattr(benchmark_module, "evaluate", fake_evaluate)

    response = client.post(
        "/benchmark/scifact",
        json={"split": "dev", "threshold": 0.70},
    )

    assert response.status_code == 200

    data = response.json()

    assert data["split"] == "dev"
    assert data["threshold"] == 0.70
    assert data["claims_count"] == 1
    assert len(data["labels"]) == 4
    assert data["labels"][0]["label"] == "SUPPORT"
    assert data["macro"]["precision"] == 0.7675
    assert data["macro"]["recall"] == 0.72
    assert data["macro"]["f1"] == 0.74
