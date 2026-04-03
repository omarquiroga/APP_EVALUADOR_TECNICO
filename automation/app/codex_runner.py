from __future__ import annotations

import json
import subprocess
import threading
from pathlib import Path
from typing import Any

try:
    from app.settings import AppSettings
    from app.state import SessionStore, utc_now_iso
except ModuleNotFoundError:
    from automation.app.settings import AppSettings
    from automation.app.state import SessionStore, utc_now_iso


def _quote(value: str) -> str:
    return subprocess.list2cmdline([value])


class CodexRunner:
    def __init__(self, settings: AppSettings, store: SessionStore) -> None:
        self.settings = settings
        self.store = store
        self._threads: dict[str, threading.Thread] = {}

    def start_task(self, prompt: str, workspace: str | None = None) -> dict[str, Any]:
        resolved_workspace = self.settings.resolve_workspace(workspace)
        record = self.store.create_session(prompt=prompt, workspace=resolved_workspace)
        self._launch(
            session_id=record["session_id"],
            prompt=prompt,
            workspace=resolved_workspace,
            continue_existing=False,
        )
        return self.get_status(record["session_id"])

    def continue_task(
        self,
        session_id: str,
        prompt: str,
        workspace: str | None = None,
    ) -> dict[str, Any]:
        session = self.store.get_session(session_id)
        if session["status"] == "running":
            raise ValueError(f"La sesion {session_id} sigue en ejecucion.")

        resolved_workspace = self.settings.resolve_workspace(workspace or session["workspace"])
        consistency = self.inspect_session_workspace(session_id, resolved_workspace)
        if not consistency["ok"]:
            raise ValueError(consistency["detail"])
        self.store.update_session(
            session_id,
            last_prompt=prompt,
            workspace=str(resolved_workspace),
            status="pending",
            completed_at=None,
            exit_code=None,
            error=None,
        )
        self._launch(
            session_id=session_id,
            prompt=prompt,
            workspace=resolved_workspace,
            continue_existing=True,
        )
        return self.get_status(session_id)

    def get_status(self, session_id: str) -> dict[str, Any]:
        session = self.store.get_session(session_id)
        thread = self._threads.get(session_id)
        if thread is not None and not thread.is_alive() and session["status"] == "running":
            session = self.store.update_session(session_id, status="unknown")

        session["log_tail"] = self.store.get_log_tail(session_id)
        return session

    def probe_command(self) -> dict[str, Any]:
        command = f"{_quote(self.settings.codex_command)} --version"
        try:
            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                shell=True,
                timeout=15,
            )
        except Exception as exc:
            return {
                "ok": False,
                "command": self.settings.codex_command,
                "detail": str(exc),
            }

        output = (completed.stdout or completed.stderr or "").strip()
        detail = output or f"returncode={completed.returncode}"
        return {
            "ok": completed.returncode == 0,
            "command": self.settings.codex_command,
            "detail": detail,
        }

    def probe_write_within_workspace(self, workspace: str | None = None) -> dict[str, Any]:
        resolved_workspace = self.settings.resolve_workspace(workspace)
        probe_path = resolved_workspace / "automation" / ".state" / ".write_probe.tmp"
        try:
            probe_path.parent.mkdir(parents=True, exist_ok=True)
            probe_path.write_text("write probe ok", encoding="utf-8")
            probe_path.unlink(missing_ok=True)
        except Exception as exc:
            return {
                "ok": False,
                "workspace": str(resolved_workspace),
                "detail": str(exc),
            }

        return {
            "ok": True,
            "workspace": str(resolved_workspace),
            "detail": "create-delete probe completed inside workspace",
        }

    def inspect_session_workspace(self, session_id: str, workspace: Path | str | None = None) -> dict[str, Any]:
        session = self.store.get_session(session_id)
        resolved_workspace = self.settings.resolve_workspace(workspace or session["workspace"])
        stored_workspace = Path(session["workspace"]).resolve()
        if stored_workspace != resolved_workspace:
            return {
                "ok": False,
                "detail": (
                    f"La sesion {session_id} fue creada para {stored_workspace} y no para "
                    f"{resolved_workspace}. Debe abrirse una sesion nueva."
                ),
            }

        codex_session_id = session.get("codex_session_id")
        if not codex_session_id:
            return {"ok": True, "detail": "No codex_session_id persisted yet; workspace matches session record."}

        metadata = self._read_session_meta_by_id(codex_session_id)
        if not metadata:
            return {
                "ok": True,
                "detail": "No session metadata file was found for the persisted codex_session_id.",
            }

        metadata_cwd = Path(metadata.get("cwd", "")).resolve()
        if metadata_cwd != resolved_workspace:
            return {
                "ok": False,
                "detail": (
                    f"La sesion de Codex {codex_session_id} esta anclada a {metadata_cwd} y no a "
                    f"{resolved_workspace}. Debe abrirse una sesion nueva."
                ),
            }

        return {
            "ok": True,
            "detail": f"Codex session {codex_session_id} is anchored to {resolved_workspace}.",
        }

    def execution_diagnostics(self) -> dict[str, Any]:
        write_probe = self.probe_write_within_workspace()
        return {
            "default_workspace": str(self.settings.default_workspace),
            "allowed_workspaces": [str(path) for path in self.settings.allowed_workspaces],
            "effective_sandbox_mode": self.settings.codex_sandbox_mode,
            "effective_approval_policy": self.settings.codex_approval_policy,
            "write_within_workspace_ok": write_probe["ok"],
            "write_within_workspace_detail": write_probe["detail"],
        }

    def _launch(
        self,
        session_id: str,
        prompt: str,
        workspace: Path,
        continue_existing: bool,
    ) -> None:
        worker = threading.Thread(
            target=self._run_task,
            kwargs={
                "session_id": session_id,
                "prompt": prompt,
                "workspace": workspace,
                "continue_existing": continue_existing,
            },
            daemon=True,
        )
        self._threads[session_id] = worker
        worker.start()

    def _run_task(
        self,
        session_id: str,
        prompt: str,
        workspace: Path,
        continue_existing: bool,
    ) -> None:
        session = self.store.get_session(session_id)
        command = self._build_command(
            prompt=prompt,
            codex_session_id=session.get("codex_session_id"),
            continue_existing=continue_existing,
            output_path=session.get("output_path", ""),
            workspace=workspace,
        )
        log_path = Path(session["log_path"])
        log_path.parent.mkdir(parents=True, exist_ok=True)
        started_at = utc_now_iso()
        probe = self.probe_command()

        self.store.update_session(
            session_id,
            status="running",
            started_at=started_at,
            command=command,
        )

        before_files = self._candidate_session_files(workspace)

        try:
            with log_path.open("a", encoding="utf-8", errors="replace") as handle:
                handle.write(f"[{started_at}] COMMAND {command}\n")
                if not probe["ok"]:
                    handle.write(f"[{started_at}] PRECHECK {probe['detail']}\n")
                    handle.flush()
                    self.store.update_session(
                        session_id,
                        status="failed",
                        completed_at=utc_now_iso(),
                        pid=None,
                        exit_code=127,
                        error=(
                            "No fue posible ejecutar el comando de Codex configurado. "
                            f"Detalle: {probe['detail']}"
                        ),
                    )
                    return
                handle.flush()

                process = subprocess.Popen(
                    command,
                    cwd=str(workspace),
                    stdin=subprocess.PIPE,
                    stdout=handle,
                    stderr=subprocess.STDOUT,
                    text=True,
                    encoding="utf-8",
                    shell=True,
                )
                self.store.update_session(session_id, pid=process.pid)
                _, _ = process.communicate(prompt)
                exit_code = process.returncode

            codex_session_id = self._discover_codex_session_id(workspace, before_files)
            final_status = "completed" if exit_code == 0 else "failed"
            self.store.update_session(
                session_id,
                status=final_status,
                exit_code=exit_code,
                completed_at=utc_now_iso(),
                pid=None,
                codex_session_id=codex_session_id or session.get("codex_session_id"),
            )
        except Exception as exc:
            self.store.update_session(
                session_id,
                status="failed",
                completed_at=utc_now_iso(),
                pid=None,
                error=str(exc),
            )

    def _build_command(
        self,
        prompt: str,
        codex_session_id: str | None,
        continue_existing: bool,
        output_path: str,
        workspace: Path,
    ) -> str:
        template = self.settings.codex_start_template
        if continue_existing:
            template = (
                self.settings.codex_continue_template
                if codex_session_id
                else self.settings.codex_continue_fallback_template
            )

        values = {
            "codex_command": _quote(self.settings.codex_command),
            "prompt": _quote(prompt),
            "codex_session_id": _quote(codex_session_id or ""),
            "session_id": _quote(codex_session_id or ""),
            "output_path": _quote(output_path),
            "workspace_path": _quote(str(workspace.resolve())),
            "sandbox_mode": self.settings.codex_sandbox_mode,
            "approval_policy": self.settings.codex_approval_policy,
        }
        return template.format(**values)

    def _candidate_session_files(self, workspace: Path) -> set[Path]:
        base = Path.home() / ".codex" / "sessions"
        if not base.exists():
            return set()
        return set(base.rglob("*.jsonl"))

    def _read_session_meta_by_id(self, codex_session_id: str) -> dict[str, Any] | None:
        base = Path.home() / ".codex" / "sessions"
        if not base.exists():
            return None

        for path in sorted(base.rglob("*.jsonl"), key=lambda item: item.stat().st_mtime, reverse=True):
            metadata = self._read_session_meta(path)
            if metadata and metadata.get("id") == codex_session_id:
                return metadata
        return None

    def _discover_codex_session_id(
        self,
        workspace: Path,
        before_files: set[Path],
    ) -> str | None:
        base = Path.home() / ".codex" / "sessions"
        if not base.exists():
            return None

        candidates = sorted(
            set(base.rglob("*.jsonl")) - before_files,
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )

        for path in candidates:
            metadata = self._read_session_meta(path)
            if metadata and Path(metadata.get("cwd", "")).resolve() == workspace.resolve():
                return metadata.get("id")

        return None

    def _read_session_meta(self, path: Path) -> dict[str, Any] | None:
        try:
            with path.open("r", encoding="utf-8", errors="ignore") as handle:
                first_line = handle.readline().strip()
        except OSError:
            return None

        if not first_line:
            return None

        try:
            payload = json.loads(first_line)
        except json.JSONDecodeError:
            return None

        if payload.get("type") != "session_meta":
            return None

        return payload.get("payload")
