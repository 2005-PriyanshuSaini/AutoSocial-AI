import importlib
import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    """
    Provide a TestClient with an isolated sqlite database and mocked network calls.
    """
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")
    monkeypatch.setenv("DB_SSLMODE", "")
    monkeypatch.setenv("DB_ECHO", "false")

    # Ensure modules pick up the patched env vars.
    import settings as settings_module
    import db as db_module
    import ai as ai_module
    import social as social_module
    import main as main_module

    importlib.reload(settings_module)
    importlib.reload(db_module)
    importlib.reload(ai_module)
    importlib.reload(social_module)
    importlib.reload(main_module)

    # Mock AI calls to avoid external requests
    def fake_askall_models(prompt: str):
        return {"ChatGPT": f"mock:{prompt}", "Gemini": f"mock:{prompt}", "Llama-4": f"mock:{prompt}"}

    main_module.query_all_models = fake_askall_models

    # Mock social network calls
    def fake_post_to_x(content: str):
        return {"ok": True, "platform": "twitter", "content": content}

    def fake_post_to_linkedin(content: str, urn_type=None):
        return {"ok": True, "platform": "linkedin", "content": content, "urn_type": urn_type}

    main_module.post_to_x = fake_post_to_x
    main_module.post_to_linkedin = fake_post_to_linkedin

    # Ensure DB schema exists
    db_module.create_all_tables()

    return TestClient(main_module.app)


def test_healthz(client: TestClient):
    r = client.get("/healthz")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"


def test_generate_content(client: TestClient):
    r = client.post("/generate-content/", json={"prompt": "hello"})
    assert r.status_code == 200
    data = r.json()
    assert data["prompt"] == "hello"
    assert "model_responses" in data
    assert "ChatGPT" in data["model_responses"]


def test_save_edit_review_and_list_posts(client: TestClient):
    # Save
    r = client.post("/save-generated-content/?model=ChatGPT&content=hi")
    assert r.status_code == 200
    post_id = r.json()["id"]

    # Edit
    r = client.post("/edit-generated-content/", json={"post_id": post_id, "new_content": "hi2"})
    assert r.status_code == 200

    # Review approve
    r = client.post("/review-content/", json={"post_id": post_id, "status": "approved"})
    assert r.status_code == 200
    assert r.json()["status"] == "approved"

    # List (include_all=false should include approved)
    r = client.get("/generated-posts/")
    assert r.status_code == 200
    posts = r.json()
    assert any(p["id"] == post_id for p in posts)

    # List include_all=true includes pending too (we have only approved)
    r = client.get("/generated-posts/?include_all=true")
    assert r.status_code == 200
    posts = r.json()
    assert any(p["id"] == post_id for p in posts)


def test_post_content_twitter(client: TestClient):
    r = client.post("/save-generated-content/?model=ChatGPT&content=hello")
    post_id = r.json()["id"]
    client.post("/review-content/", json={"post_id": post_id, "status": "approved"})

    r = client.post(
        "/post-content/",
        json={"post_id": post_id, "platform": "twitter", "content": "hello", "urn_type": None},
    )
    assert r.status_code == 200
    data = r.json()
    assert "result" in data
    assert "twitter" in data["result"]


def test_post_content_multi_platform(client: TestClient):
    r = client.post("/save-generated-content/?model=ChatGPT&content=hello")
    post_id = r.json()["id"]
    client.post("/review-content/", json={"post_id": post_id, "status": "approved"})

    r = client.post(
        "/post-content/",
        json={"post_id": post_id, "platform": ["twitter", "linkedin"], "content": "hello", "urn_type": "author"},
    )
    assert r.status_code == 200
    result = r.json()["result"]
    assert "twitter" in result
    assert "linkedin" in result


def test_watch_session_invalid_path(client: TestClient):
    r = client.post("/start-watch-session/", json={"path": "/nope", "duration": 1, "duration_unit": "minutes"})
    assert r.status_code == 400
    assert r.json()["error"] == "Invalid path"

