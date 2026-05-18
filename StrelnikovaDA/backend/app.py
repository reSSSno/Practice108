import json
import os
from urllib import error, request

from prometheus_client import CONTENT_TYPE_LATEST, Counter, generate_latest
from flask import Flask, jsonify, request as flask_request

app = Flask(__name__)

SPELLCHECK_REQUESTS = Counter(
    "spellcheck_requests_total",
    "Total number of spellcheck requests created by users",
    ["language"],
)

WORKER_URL = os.getenv("WORKER_URL", "http://worker:8001")
REQUEST_TIMEOUT_SECONDS = float(os.getenv("REQUEST_TIMEOUT_SECONDS", "10"))


def worker_request(method: str, path: str, payload: dict | None = None):
    url = f"{WORKER_URL}{path}"
    data = None
    headers = {"Accept": "application/json"}

    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = request.Request(url=url, data=data, method=method.upper(), headers=headers)

    try:
        with request.urlopen(req, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            body = response.read().decode("utf-8")
            return response.getcode(), json.loads(body)
    except error.HTTPError as exc:
        try:
            body = exc.read().decode("utf-8")
            return exc.code, json.loads(body)
        except json.JSONDecodeError:
            return exc.code, {"error": f"Worker HTTP error {exc.code}"}
    except Exception as exc:  # noqa: BLE001
        return 503, {"error": f"Worker unavailable: {exc}"}


@app.get("/api/health")
def health():
    status_code, worker_payload = worker_request("GET", "/health")
    return jsonify(
        {
            "service": "backend",
            "status": "ok" if status_code == 200 else "degraded",
            "worker": worker_payload,
        }
    ), 200 if status_code == 200 else 503


@app.post("/api/tasks/spellcheck")
def create_spellcheck_task():
    payload = flask_request.get_json(silent=True) or {}
    text = (payload.get("text") or "").strip()
    language = (payload.get("language") or "auto").strip().lower()

    if not text:
        return jsonify({"error": "Поле text обязательно."}), 400

    if language not in {"auto", "ru", "en"}:
        return jsonify({"error": "Допустимые значения language: auto, ru, en."}), 400

    SPELLCHECK_REQUESTS.labels(language=language).inc()
    app.logger.info(
        "Spellcheck request accepted: language=%s, text_length=%s",
        language,
        len(text),
    )

    status_code, worker_payload = worker_request(
        "POST",
        "/tasks/spellcheck",
        {"text": text, "language": language},
    )
    return jsonify(worker_payload), status_code


@app.get("/api/tasks/<task_id>")
def get_task(task_id: str):
    status_code, worker_payload = worker_request("GET", f"/tasks/{task_id}")
    return jsonify(worker_payload), status_code

@app.get("/metrics")
def metrics():
    return generate_latest(), 200, {"Content-Type": CONTENT_TYPE_LATEST}

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
