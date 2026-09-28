import io
import json

import pytest

import app as vera_app


@pytest.fixture()
def client():
    vera_app.app.config.update(TESTING=True)
    with vera_app.app.test_client() as test_client:
        yield test_client


def test_home_is_local_indonesian_workspace(client):
    response = client.get("/")
    page = response.get_data(as_text=True)

    assert response.status_code == 200
    assert 'lang="id"' in page
    assert "Apa yang ingin Anda telaah?" in page
    assert "Penelitian baru" in page
    assert "cdn." not in page


def test_status_contract(client, monkeypatch):
    monkeypatch.setattr(
        vera_app,
        "_ollama_status",
        lambda target_model=None: {
            "online": True,
            "model": "gemma4:12b",
            "model_available": True,
            "message": "Model siap digunakan.",
        },
    )

    response = client.get("/api/status")

    assert response.status_code == 200
    assert response.json["backend"] is True
    assert response.json["provider"]["model_available"] is True


def test_empty_chat_is_rejected(client):
    response = client.post("/api/chat", json={"message": "  "})

    assert response.status_code == 400
    assert response.json["error"] == "Pesan tidak boleh kosong."


def test_ollama_models_only_returns_ranked_local_chat_models(client, monkeypatch):
    installed = [
        {"name": "nomic-embed-text:latest"},
        {"name": "gemma4:12b"},
        {"name": "deepseek-v4-pro:cloud"},
        {"name": "qwen3.5:27b"},
    ]
    monkeypatch.setattr(
        vera_app.urllib.request,
        "urlopen",
        lambda *args, **kwargs: io.BytesIO(json.dumps({"models": installed}).encode()),
    )

    response = client.get("/api/ollama_models")

    assert response.status_code == 200
    assert [model["name"] for model in response.json["models"]] == [
        "qwen3.5:27b",
        "gemma4:12b",
    ]


def test_upload_accepts_supported_document(client, monkeypatch, tmp_path):
    monkeypatch.setattr(vera_app, "UPLOAD_DIR", tmp_path)
    response = client.post(
        "/api/upload",
        data={"file": (io.BytesIO(b"catatan riset"), "catatan.txt")},
        content_type="multipart/form-data",
    )

    assert response.status_code == 200
    assert response.json["name"] == "catatan.txt"
    assert response.json["kind"] == "dokumen"
    assert response.json["size"] == 13
    assert (tmp_path / response.json["path"].split("/")[-1]).exists()


def test_upload_rejects_unsupported_file(client, monkeypatch, tmp_path):
    monkeypatch.setattr(vera_app, "UPLOAD_DIR", tmp_path)
    response = client.post(
        "/api/upload",
        data={"file": (io.BytesIO(b"binary"), "program.exe")},
        content_type="multipart/form-data",
    )

    assert response.status_code == 415
    assert not list(tmp_path.iterdir())


def test_upload_rejects_disguised_pdf(client, monkeypatch, tmp_path):
    monkeypatch.setattr(vera_app, "UPLOAD_DIR", tmp_path)
    response = client.post(
        "/api/upload",
        data={"file": (io.BytesIO(b"not really a pdf"), "referensi.pdf")},
        content_type="multipart/form-data",
    )

    assert response.status_code == 415
    assert not list(tmp_path.iterdir())


def test_security_headers_are_present(client):
    response = client.get("/")

    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["Referrer-Policy"] == "no-referrer"
    assert "microphone=(self)" in response.headers["Permissions-Policy"]
    assert "default-src 'self'" in response.headers["Content-Security-Policy"]
