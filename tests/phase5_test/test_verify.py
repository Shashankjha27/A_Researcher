from fastapi.testclient import TestClient

from app.api.main import app

client = TestClient(app)


def test_verify_route_exists():
    response = client.get("/openapi.json")

    assert response.status_code == 200
    assert "/verify" in response.json()["paths"]


def test_verify_requires_papers():
    response = client.post(
        "/verify",
        json={
            "papers": [],
        },
    )

    assert response.status_code == 422


def test_verify_missing_paper():
    response = client.post(
        "/verify",
        json={
            "papers": [
                {
                    "paper_path": "/does/not/exist.pdf",
                    "paper_id": "paper-test",
                    "title": "Test Paper",
                    "authors": ["Test Author"],
                    "year": 2026,
                }
            ]
        },
    )

    assert response.status_code == 400
    assert "Paper not found" in response.json()["detail"]


def test_verify_rejects_invalid_threshold():
    response = client.post(
        "/verify",
        json={
            "papers": [
                {
                    "paper_path": "test.pdf",
                    "paper_id": "paper-test",
                    "title": "Test Paper",
                    "year": 2026,
                }
            ],
            "pair_threshold": 2.0,
        },
    )

    assert response.status_code == 422


def test_verify_rejects_invalid_top_k():
    response = client.post(
        "/verify",
        json={
            "papers": [
                {
                    "paper_path": "test.pdf",
                    "paper_id": "paper-test",
                    "title": "Test Paper",
                    "year": 2026,
                }
            ],
            "evidence_top_k": 0,
        },
    )

    assert response.status_code == 422


def test_verify_rejects_invalid_year():
    response = client.post(
        "/verify",
        json={
            "papers": [
                {
                    "paper_path": "test.pdf",
                    "paper_id": "paper-test",
                    "title": "Test Paper",
                    "year": 1500,
                }
            ]
        },
    )

    assert response.status_code == 422
