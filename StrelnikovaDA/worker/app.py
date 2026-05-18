from __future__ import annotations

import os
import sqlite3
import threading
import traceback
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

from flask import Flask, jsonify, request

from logic.spellchecker import SpellCheckService

app = Flask(__name__)
executor = ThreadPoolExecutor(max_workers=4)
spell_service = SpellCheckService()
DB_PATH = os.getenv("DB_PATH", "/data/tasks.db")
DB_LOCK = threading.Lock()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_connection() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    connection = sqlite3.connect(DB_PATH, check_same_thread=False)
    connection.row_factory = sqlite3.Row
    return connection


def init_db() -> None:
    with DB_LOCK:
        conn = get_connection()
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS tasks (
                task_id TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                language TEXT NOT NULL,
                input_text TEXT NOT NULL,
                result_json TEXT,
                error_text TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.commit()
        conn.close()


@app.before_request
def ensure_db_ready() -> None:
    init_db()


@app.get("/health")
def health():
    return jsonify({"service": "worker", "status": "ok"})


@app.post("/tasks/spellcheck")
def create_task():
    payload = request.get_json(silent=True) or {}
    text = (payload.get("text") or "").strip()
    language = (payload.get("language") or "auto").strip().lower()

    if not text:
        return jsonify({"error": "Поле text обязательно."}), 400

    if language not in {"auto", "ru", "en"}:
        return jsonify({"error": "Допустимые значения language: auto, ru, en."}), 400

    task_id = str(uuid.uuid4())
    now = utc_now()

    with DB_LOCK:
        conn = get_connection()
        conn.execute(
            """
            INSERT INTO tasks(task_id, status, language, input_text, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (task_id, "queued", language, text, now, now),
        )
        conn.commit()
        conn.close()

    executor.submit(process_task, task_id)
    return jsonify({"task_id": task_id, "status": "queued"}), 202


@app.get("/tasks/<task_id>")
def get_task(task_id: str):
    with DB_LOCK:
        conn = get_connection()
        row = conn.execute("SELECT * FROM tasks WHERE task_id = ?", (task_id,)).fetchone()
        conn.close()

    if row is None:
        return jsonify({"error": "Задача не найдена."}), 404

    payload = {
        "task_id": row["task_id"],
        "status": row["status"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }

    if row["result_json"]:
        import json

        payload["result"] = json.loads(row["result_json"])
    if row["error_text"]:
        payload["error"] = row["error_text"]

    return jsonify(payload)


def process_task(task_id: str) -> None:
    with DB_LOCK:
        conn = get_connection()
        row = conn.execute("SELECT * FROM tasks WHERE task_id = ?", (task_id,)).fetchone()
        if row is None:
            conn.close()
            return
        conn.execute(
            "UPDATE tasks SET status = ?, updated_at = ? WHERE task_id = ?",
            ("processing", utc_now(), task_id),
        )
        conn.commit()
        conn.close()

    try:
        result = spell_service.check_text(row["input_text"], row["language"])
        import json

        with DB_LOCK:
            conn = get_connection()
            conn.execute(
                """
                UPDATE tasks
                SET status = ?, result_json = ?, error_text = NULL, updated_at = ?
                WHERE task_id = ?
                """,
                ("done", json.dumps(result, ensure_ascii=False), utc_now(), task_id),
            )
            conn.commit()
            conn.close()
    except Exception as exc:  # noqa: BLE001
        message = f"{exc}\n{traceback.format_exc()}"
        with DB_LOCK:
            conn = get_connection()
            conn.execute(
                "UPDATE tasks SET status = ?, error_text = ?, updated_at = ? WHERE task_id = ?",
                ("failed", message, utc_now(), task_id),
            )
            conn.commit()
            conn.close()


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=8001, debug=True, threaded=True)
