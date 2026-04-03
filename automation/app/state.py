from __future__ import annotations

import json
import threading
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


class SessionStore:
    def __init__(self, state_dir: Path, log_dir: Path) -> None:
        self.state_dir = state_dir
        self.log_dir = log_dir
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.sessions_path = self.state_dir / "sessions.json"
        self._lock = threading.Lock()

        if not self.sessions_path.exists():
            self.sessions_path.write_text("{}", encoding="utf-8")

    def create_session(self, prompt: str, workspace: Path) -> dict[str, Any]:
        session_id = uuid.uuid4().hex
        now = utc_now_iso()
        record = {
            "session_id": session_id,
            "status": "pending",
            "workspace": str(workspace),
            "created_at": now,
            "updated_at": now,
            "started_at": None,
            "completed_at": None,
            "last_prompt": prompt,
            "codex_session_id": None,
            "command": None,
            "pid": None,
            "exit_code": None,
            "error": None,
            "log_path": str(self.log_dir / f"{session_id}.log"),
            "output_path": str(self.log_dir / f"{session_id}.final.txt"),
        }

        with self._lock:
            sessions = self._read_all_unlocked()
            sessions[session_id] = record
            self._write_all_unlocked(sessions)

        return record

    def get_session(self, session_id: str) -> dict[str, Any]:
        with self._lock:
            sessions = self._read_all_unlocked()
            try:
                return dict(sessions[session_id])
            except KeyError as exc:
                raise KeyError(f"Sesion no encontrada: {session_id}") from exc

    def update_session(self, session_id: str, **changes: Any) -> dict[str, Any]:
        with self._lock:
            sessions = self._read_all_unlocked()
            if session_id not in sessions:
                raise KeyError(f"Sesion no encontrada: {session_id}")

            sessions[session_id].update(changes)
            sessions[session_id]["updated_at"] = utc_now_iso()
            self._write_all_unlocked(sessions)
            return dict(sessions[session_id])

    def get_log_tail(self, session_id: str, lines: int = 20) -> str:
        session = self.get_session(session_id)
        log_path = Path(session["log_path"])
        if not log_path.exists():
            return ""

        content = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
        return "\n".join(content[-lines:])

    def _read_all_unlocked(self) -> dict[str, Any]:
        raw = self.sessions_path.read_text(encoding="utf-8")
        return json.loads(raw or "{}")

    def _write_all_unlocked(self, sessions: dict[str, Any]) -> None:
        self.sessions_path.write_text(
            json.dumps(sessions, indent=2, sort_keys=True),
            encoding="utf-8",
        )
