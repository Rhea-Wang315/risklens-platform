from fastapi.testclient import TestClient

from risklens.api.main import app


def test_metrics_endpoint_exposes_risklens_metrics() -> None:
    client = TestClient(app)
    resp = client.get("/metrics")
    assert resp.status_code == 200
    body = resp.text
    assert "risklens_evaluate_requests_total" in body
    assert "risklens_evaluate_latency_seconds" in body
    assert "risklens_decisions_total" in body
