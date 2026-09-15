import base64

import pytest
from fastapi.testclient import TestClient

from traceharbor.server import MAX_REQUEST_BYTES, make_app


@pytest.fixture
def client(tmp_path):
    app = make_app(tmp_path / "api-vault", token="test-session-token", port=8742)
    with TestClient(
        app, base_url="http://127.0.0.1:8742", headers={"Authorization": "Bearer test-session-token"}
    ) as client:
        yield client


def new_case(client):
    result = client.post("/api/cases", json={"title": "API training", "purpose": "Tests only"})
    assert result.status_code == 201
    return result.json()


def test_api_authorization(client):
    client.headers.pop("authorization")
    assert client.get("/api/health").status_code == 200
    assert client.get("/api/cases").status_code == 401
    assert client.get("/api/status").status_code == 401
    assert client.post("/api/cases", json={"title": "bad"}).status_code == 401


def test_cross_origin_and_dns_rebinding(client):
    assert client.get("/api/cases", headers={"Host": "evil.example"}).status_code == 403
    assert client.get("/api/cases", headers={"Origin": "https://evil.example"}).status_code == 403
    assert client.get("/api/cases", headers={"Sec-Fetch-Site": "cross-site"}).status_code == 403
    assert client.get("/api/cases", headers={"Origin": "http://127.0.0.1:8742"}).status_code == 200


def test_static_security_headers(client):
    result = client.get("/")
    assert result.status_code == 200
    assert "script-src 'self'" in result.headers["content-security-policy"]
    assert result.headers["x-content-type-options"] == "nosniff"
    assert result.headers["cache-control"] == "no-store"
    assert client.get("/style.css").status_code == 200
    assert client.get("/app.js").status_code == 200
    assert client.get("/anything-private").status_code == 404


def test_json_and_body_limits(client):
    assert client.post("/api/cases", content="{}", headers={"Content-Type": "text/plain"}).status_code == 415
    assert (
        client.post(
            "/api/cases",
            content="{}",
            headers={"Content-Type": "application/json", "Content-Length": str(MAX_REQUEST_BYTES + 1)},
        ).status_code
        == 413
    )
    assert client.post("/api/cases", json=[]).status_code == 400
    assert (
        client.post("/api/cases", content="bad", headers={"Content-Type": "application/json"}).status_code
        == 400
    )


def test_full_case_workflow(client):
    c = new_case(client)
    route = f"/api/cases/{c['id']}"
    payload = {
        "kind": "file",
        "title": "test.txt",
        "filename": "test.txt",
        "data_base64": base64.b64encode(b"evidence").decode(),
    }
    entry = client.post(route + "/entries", json=payload)
    assert entry.status_code == 201
    assert client.get(f"/api/entries/{entry.json()['id']}/original").content == b"evidence"
    assert client.get(route + "/verify").json()["valid"]
    assert client.get(route + "/export").headers["content-type"] == "application/zip"
    assert client.patch(route, json={"status": "archived"}).status_code == 200
    assert client.post(route + "/entries", json=payload).status_code == 400
    assert client.patch(route, json={"status": "active"}).status_code == 200
    assert client.get("/api/cases").json()["cases"][0]["counts"]["file"] == 1


@pytest.mark.parametrize("data", ["bad%%", None, "", 123])
def test_bad_file_payloads(client, data):
    assert client.post("/api/analyze", json={"filename": "test", "data_base64": data}).status_code == 400


def test_api_input_shapes(client):
    c = new_case(client)
    route = f"/api/cases/{c['id']}"
    assert client.post(route + "/entries", json={"kind": [], "title": "bad"}).status_code == 400
    assert client.patch(route, json={"status": []}).status_code == 400
    assert client.post("/api/inspect-url", json={"url": None}).status_code == 400
    assert client.post("/api/public-leads", json={"username": 55}).status_code == 400
    assert client.get("/api/cases/invalid").status_code == 400
    assert client.get("/api/cases/" + "a" * 32).status_code == 404


def test_analysis_does_not_persist(client):
    response = client.post(
        "/api/analyze", json={"filename": "test.txt", "data_base64": base64.b64encode(b"private").decode()}
    )
    assert response.status_code == 200
    assert not list(client.app.state.store.blobs.iterdir())
    assert client.get("/api/cases").json()["cases"] == []
