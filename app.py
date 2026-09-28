"""Local web entrypoint for V.E.R.A.

The interface is available before the AI stack finishes loading. Heavy
research, vision, and speech dependencies are imported only when needed.
"""

from __future__ import annotations

import os
import re
import secrets
import tempfile
import threading
import urllib.error
import urllib.request
import uuid
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, g, jsonify, render_template, request
from werkzeug.utils import secure_filename


BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")
if not os.getenv("GEMINI_API_KEY") and os.getenv("GOOGLE_API_KEY"):
    os.environ["GEMINI_API_KEY"] = os.getenv("GOOGLE_API_KEY")
UPLOAD_DIR = BASE_DIR / "uploads"
ALLOWED_UPLOADS = {
    ".txt": "dokumen",
    ".md": "dokumen",
    ".csv": "data",
    ".py": "kode",
    ".pdf": "dokumen",
    ".docx": "dokumen",
    ".jpg": "gambar",
    ".jpeg": "gambar",
    ".png": "gambar",
    ".webp": "gambar",
}
ALLOWED_AUDIO = {".wav", ".mp3", ".m4a", ".webm", ".ogg"}
SESSION_ID_PATTERN = re.compile(r"[^a-zA-Z0-9_-]")
MODEL_NAME = os.getenv("VERA_MODEL", "gemma4:12b")
OLLAMA_CHAT_MODELS = (
    "qwen3.5:27b",
    "muse-glimmer:latest",
    "gpt-oss:20b",
    "gemma4:12b",
    "mistral-nemo:latest",
    "ornith-1.5:9b",
    "granite4.2:3b",
)

app = Flask(__name__)
app.config.update(MAX_CONTENT_LENGTH=25 * 1024 * 1024, JSON_AS_ASCII=False)

_backend_lock = threading.Lock()


def _json_error(message: str, status: int):
    return jsonify({"error": message}), status


def _safe_session_id(value: object) -> str:
    session_id = SESSION_ID_PATTERN.sub("", str(value or "default_session"))[:80]
    return session_id or "default_session"


def _valid_upload_content(uploaded, extension: str) -> bool:
    head = uploaded.stream.read(4096)
    uploaded.stream.seek(0)
    signatures = {
        ".pdf": lambda value: value.startswith(b"%PDF"),
        ".png": lambda value: value.startswith(b"\x89PNG\r\n\x1a\n"),
        ".jpg": lambda value: value.startswith(b"\xff\xd8\xff"),
        ".jpeg": lambda value: value.startswith(b"\xff\xd8\xff"),
        ".webp": lambda value: value.startswith(b"RIFF") and value[8:12] == b"WEBP",
        ".docx": lambda value: value.startswith(b"PK\x03\x04"),
    }
    if extension in signatures:
        return signatures[extension](head)
    return b"\x00" not in head


def _ollama_status(target_model: str = None) -> dict[str, object]:
    model_name = target_model or MODEL_NAME
    try:
        with urllib.request.urlopen("http://127.0.0.1:11434/api/tags", timeout=1.2) as response:
            payload = __import__("json").loads(response.read().decode("utf-8"))
        models = [item.get("name", "") for item in payload.get("models", [])]
        available = any(model_name == m or m.startswith(model_name) or model_name.startswith(m.split(":")[0]) for m in models)
        return {
            "online": True,
            "model": model_name,
            "model_available": available,
            "installed_models": models,
            "message": f"Model Ollama ({model_name}) siap digunakan." if available else f"Ollama aktif. Model {model_name} belum terpasang di perangkat.",
        }
    except (OSError, ValueError, urllib.error.URLError):
        return {
            "online": False,
            "model": model_name,
            "model_available": False,
            "installed_models": [],
            "message": "Ollama lokal tidak terhubung.",
        }


def _provider_status(provider: str = None, model: str = None) -> dict[str, object]:
    google_key = os.getenv("GOOGLE_API_KEY", "").strip()
    gemini_ready = bool(google_key and len(google_key) > 10)
    
    selected_provider = (provider or os.getenv("VERA_PROVIDER", "ollama")).lower()
    selected_model = model or (os.getenv("VERA_MODEL", "gemma4:12b") if selected_provider == "ollama" else ("gemini-3.6-flash" if selected_provider in ("gemini", "google") else MODEL_NAME))

    if selected_provider in ("gemini", "google", "google_genai"):
        if gemini_ready:
            return {
                "online": True,
                "provider": "gemini",
                "model": selected_model,
                "model_available": True,
                "cloud": True,
                "message": f"Model Cloud ({selected_model}) siap digunakan.",
            }
        else:
            return {
                "online": False,
                "provider": "gemini",
                "model": selected_model,
                "model_available": False,
                "cloud": True,
                "message": "GOOGLE_API_KEY belum dikonfigurasi di file .env.",
            }
    elif selected_provider == "openai":
        openai_key = os.getenv("OPENAI_API_KEY", "").strip()
        openai_ready = bool(openai_key and len(openai_key) > 10)
        return {
            "online": openai_ready,
            "provider": "openai",
            "model": selected_model,
            "model_available": openai_ready,
            "cloud": True,
            "message": f"Model OpenAI ({selected_model}) siap digunakan." if openai_ready else "OPENAI_API_KEY belum dikonfigurasi di file .env.",
        }
    else:
        ollama_stat = _ollama_status(target_model=selected_model)
        return {
            **ollama_stat,
            "provider": "ollama",
            "cloud": False,
        }


@app.get("/")
def index():
    return render_template("index.html", model_name=MODEL_NAME)


@app.get("/api/status")
def status():
    p = request.args.get("provider")
    m = request.args.get("model")
    return jsonify({"backend": True, "provider": _provider_status(provider=p, model=m)})


@app.get("/api/ollama_models")
def ollama_models():
    try:
        with urllib.request.urlopen("http://127.0.0.1:11434/api/tags", timeout=1.2) as response:
            payload = __import__("json").loads(response.read().decode("utf-8"))
        models_by_name = {item.get("name"): item for item in payload.get("models", [])}
        models = [models_by_name[name] for name in OLLAMA_CHAT_MODELS if name in models_by_name]
        return jsonify({"online": True, "models": models})
    except Exception:
        return jsonify({"online": False, "models": []})


@app.post("/api/chat")
def chat():
    data = request.get_json(silent=True) or {}
    user_message = str(data.get("message", "")).strip()
    if not user_message:
        return _json_error("Pesan tidak boleh kosong.", 400)
    if len(user_message) > 20_000:
        return _json_error("Pesan terlalu panjang. Batas maksimum 20.000 karakter.", 413)

    provider = data.get("provider")
    model = data.get("model")

    try:
        from VERA_backend import ask_vera

        with _backend_lock:
            vera_result = ask_vera(
                user_message,
                session_id=_safe_session_id(data.get("session_id")),
                provider=provider,
                model=model,
                auto_fallback=bool(data.get("auto_fallback", True)),
            )
    except Exception as exc:
        app.logger.exception("V.E.R.A. gagal memproses permintaan")
        return _json_error(
            f"Inti AI gagal memproses: {exc}. Pastikan API Key Cloud atau Ollama telah terpasang.",
            503,
        )

    if isinstance(vera_result, dict):
        response_text = vera_result.get("response", "")
        if not response_text:
            return _json_error("V.E.R.A. tidak menghasilkan jawaban. Coba ulangi permintaan.", 502)
        return jsonify({
            "response": response_text,
            "model": vera_result.get("model_used", model),
            "provider": vera_result.get("provider_used", provider),
            "fallback": vera_result.get("fallback_occurred", False),
            "fallback_from": vera_result.get("fallback_from"),
            "fallback_from_provider": vera_result.get("fallback_from_provider"),
        })

    if not vera_result:
        return _json_error("V.E.R.A. tidak menghasilkan jawaban. Coba ulangi permintaan.", 502)
    return jsonify({"response": str(vera_result)})


@app.post("/api/upload")
def upload_file():
    uploaded = request.files.get("file")
    if uploaded is None or not uploaded.filename:
        return _json_error("Pilih berkas yang ingin ditelaah.", 400)

    original_name = Path(uploaded.filename).name
    extension = Path(original_name).suffix.lower()
    if extension not in ALLOWED_UPLOADS:
        supported = ", ".join(sorted(ALLOWED_UPLOADS))
        return _json_error(f"Jenis berkas tidak didukung. Gunakan: {supported}.", 415)
    if not _valid_upload_content(uploaded, extension):
        return _json_error("Isi berkas tidak sesuai dengan jenisnya atau tidak aman untuk diproses.", 415)

    clean_name = secure_filename(original_name)
    if not clean_name:
        clean_name = f"berkas{extension}"
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    target = (UPLOAD_DIR / f"{uuid.uuid4().hex[:10]}-{clean_name}").resolve()
    if UPLOAD_DIR.resolve() not in target.parents:
        return _json_error("Nama berkas tidak aman.", 400)

    uploaded.save(target)
    return jsonify(
        {
            "name": original_name,
            "path": target.as_posix(),
            "kind": ALLOWED_UPLOADS[extension],
            "size": target.stat().st_size,
        }
    )


@app.get("/api/select_file")
def select_file():
    """Compatibility endpoint for the original desktop file-picker flow."""
    if os.name != "nt":
        return _json_error("Pemilih berkas desktop hanya tersedia di Windows.", 501)
    try:
        import tkinter as tk
        from tkinter import filedialog

        root = tk.Tk()
        root.attributes("-topmost", True)
        root.withdraw()
        file_path = filedialog.askopenfilename(title="V.E.R.A. — Pilih dokumen")
        root.destroy()
    except Exception:
        app.logger.exception("Dialog berkas gagal dibuka")
        return _json_error("Dialog berkas tidak dapat dibuka. Gunakan tombol unggah.", 500)
    if not file_path:
        return _json_error("Pemilihan berkas dibatalkan.", 400)
    return jsonify({"path": Path(file_path).as_posix()})


@app.post("/api/transcribe")
def transcribe():
    audio_file = request.files.get("audio")
    if audio_file is None or not audio_file.filename:
        return _json_error("Tidak ada audio yang dikirim.", 400)
    suffix = Path(audio_file.filename).suffix.lower()
    if suffix not in ALLOWED_AUDIO:
        return _json_error("Format audio tidak didukung.", 415)

    temp_path = ""
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
            temp_path = temp_file.name
        audio_file.save(temp_path)
        from VERA_backend import transcribe_audio

        text = transcribe_audio.func(temp_path)
        clean_text = str(text or "").strip()
        if not clean_text or "tidak ada suara" in clean_text.lower():
            return jsonify({"text": "", "detected": False})
        return jsonify({"text": clean_text, "detected": True})
    except Exception:
        app.logger.exception("Transkripsi gagal")
        return _json_error("Audio belum dapat ditranskripsi. Periksa model Whisper dan coba kembali.", 500)
    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)


@app.errorhandler(413)
def file_too_large(_error):
    return _json_error("Berkas terlalu besar. Batas unggahan adalah 25 MB.", 413)


def csp_nonce():
    """One random nonce per request, so exactly one inline script (the Three.js
    import map, which the spec only allows inline) can be allowed in the CSP
    without opening script-src to 'unsafe-inline' generally."""
    if "csp_nonce" not in g:
        g.csp_nonce = secrets.token_urlsafe(16)
    return g.csp_nonce


app.jinja_env.globals["csp_nonce"] = csp_nonce


@app.after_request
def add_security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "camera=(), geolocation=(), microphone=(self)"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "img-src 'self' data:; "
        "style-src 'self'; "
        f"script-src 'self' 'nonce-{csp_nonce()}'; "
        "connect-src 'self'; "
        "media-src 'self' blob:; "
        "font-src 'self'; "
        "base-uri 'none'; "
        "form-action 'self'; "
        "frame-ancestors 'none'"
    )
    return response


if __name__ == "__main__":
    app.run(
        host=os.getenv("VERA_HOST", "127.0.0.1"),
        port=int(os.getenv("VERA_PORT", "5000")),
        debug=os.getenv("VERA_DEBUG", "0") == "1",
        use_reloader=False,
        threaded=True,
    )
