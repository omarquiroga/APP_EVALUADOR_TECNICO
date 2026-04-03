from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path
from typing import Any

try:
    from app.codex_runner import CodexRunner
    from app.settings import AppSettings
    from app.state import SessionStore
except ModuleNotFoundError:
    from automation.app.codex_runner import CodexRunner
    from automation.app.settings import AppSettings
    from automation.app.state import SessionStore


CONTEXT_FILES = [
    "AGENTS.md",
    "docs/PROJECT_CONTEXT.md",
    "docs/DECISIONS.md",
    "docs/TASKS.md",
]


class HighLevelOrchestrator:
    def __init__(self, settings: AppSettings, store: SessionStore, runner: CodexRunner) -> None:
        self.settings = settings
        self.store = store
        self.runner = runner

    def run_and_wait(
        self,
        *,
        objective: str,
        scope: str | None = None,
        constraints: str | None = None,
        validations: list[str] | None = None,
        workspace: str | None = None,
        timeout_seconds: int | None = None,
        poll_interval_seconds: int | None = None,
    ) -> dict[str, Any]:
        prompt = self._build_prompt(
            objective=objective,
            scope=scope,
            constraints=constraints,
            validations=validations,
            is_continuation=False,
        )
        status = self.runner.start_task(prompt=prompt, workspace=workspace)
        session_id = status["session_id"]
        self.store.update_session(
            session_id,
            high_level_request={
                "objective": objective,
                "scope": scope,
                "constraints": constraints,
                "validations": validations or [],
                "mode": "run_and_wait",
                "git_status_before": self._git_status_snapshot(self.settings.resolve_workspace(workspace)),
            },
        )
        return self._wait_and_summarize(
            session_id=session_id,
            timeout_seconds=timeout_seconds,
            poll_interval_seconds=poll_interval_seconds,
        )

    def continue_and_wait(
        self,
        *,
        session_id: str,
        objective: str,
        scope: str | None = None,
        constraints: str | None = None,
        validations: list[str] | None = None,
        workspace: str | None = None,
        timeout_seconds: int | None = None,
        poll_interval_seconds: int | None = None,
    ) -> dict[str, Any]:
        prompt = self._build_prompt(
            objective=objective,
            scope=scope,
            constraints=constraints,
            validations=validations,
            is_continuation=True,
        )
        self.store.update_session(
            session_id,
            high_level_request={
                "objective": objective,
                "scope": scope,
                "constraints": constraints,
                "validations": validations or [],
                "mode": "continue_and_wait",
                "git_status_before": self._git_status_snapshot(
                    self.settings.resolve_workspace(workspace or self.store.get_session(session_id)["workspace"])
                ),
            },
        )
        self.runner.continue_task(session_id=session_id, prompt=prompt, workspace=workspace)
        return self._wait_and_summarize(
            session_id=session_id,
            timeout_seconds=timeout_seconds,
            poll_interval_seconds=poll_interval_seconds,
        )

    def review_result(self, session_id: str, focus: str | None = None) -> dict[str, Any]:
        session = self.runner.get_status(session_id)
        result = session.get("high_level_result")
        if result:
            review = {
                "session_id": session_id,
                "status": result.get("status", session["status"]),
                "executive_summary": result.get("summary", ""),
                "changes_realized": result.get("files_changed", []),
                "validations": result.get("validations_run", []),
                "risks": result.get("risks", []),
                "recommend_action": result.get("next_step", ""),
            }
        else:
            parsed = self._parse_structured_output(self._read_final_output(session))
            review = {
                "session_id": session_id,
                "status": session["status"],
                "executive_summary": parsed.get("summary") or "Sin resumen estructurado disponible.",
                "changes_realized": parsed.get("files_changed", []),
                "validations": parsed.get("validations_run", []),
                "risks": parsed.get("risks", []),
                "recommend_action": parsed.get("next_step", "Revisar log y decidir si continuar o cerrar."),
            }

        if focus:
            review["focus"] = focus
        review["log_tail"] = session.get("log_tail", "")
        return review

    def _wait_and_summarize(
        self,
        *,
        session_id: str,
        timeout_seconds: int | None,
        poll_interval_seconds: int | None,
    ) -> dict[str, Any]:
        timeout = timeout_seconds or 600
        poll_interval = max(2, poll_interval_seconds or 5)
        deadline = time.time() + timeout

        session = self.runner.get_status(session_id)
        while session["status"] in {"pending", "running"} and time.time() < deadline:
            time.sleep(poll_interval)
            session = self.runner.get_status(session_id)

        result_status = session["status"]
        if session["status"] in {"pending", "running"}:
            result_status = "timeout"

        structured = self._build_structured_result(session, result_status)
        self.store.update_session(session_id, high_level_result=structured)
        return structured

    def _build_structured_result(self, session: dict[str, Any], result_status: str) -> dict[str, Any]:
        raw_output = self._read_final_output(session)
        parsed = self._parse_structured_output(raw_output)
        request = session.get("high_level_request", {})
        workspace = Path(session["workspace"])
        before = set(request.get("git_status_before", []))
        after = set(self._git_status_snapshot(workspace))
        changed = sorted(after - before)
        files_changed = parsed.get("files_changed") or changed

        result = {
            "session_id": session["session_id"],
            "status": result_status,
            "plan_corto": parsed.get("plan_corto", []),
            "summary": parsed.get("summary", ""),
            "files_changed": files_changed,
            "validations_run": parsed.get("validations_run", []),
            "risks": parsed.get("risks", []),
            "next_step": parsed.get("next_step", ""),
            "raw_codex_output": raw_output,
        }
        if session.get("error"):
            result["risks"] = list(result["risks"]) + [session["error"]]
        return result

    def _read_final_output(self, session: dict[str, Any]) -> str:
        output_path = Path(session.get("output_path", ""))
        if output_path.exists():
            return output_path.read_text(encoding="utf-8", errors="replace").strip()
        return session.get("log_tail", "")

    def _parse_structured_output(self, raw_output: str) -> dict[str, Any]:
        if not raw_output:
            return {}

        text = raw_output.strip()
        for candidate in (text, self._extract_json_object(text)):
            if not candidate:
                continue
            try:
                payload = json.loads(candidate)
            except json.JSONDecodeError:
                continue
            if isinstance(payload, dict):
                return payload
        return {}

    def _extract_json_object(self, text: str) -> str | None:
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            return None
        return text[start : end + 1]

    def _git_status_snapshot(self, workspace: Path) -> list[str]:
        try:
            completed = subprocess.run(
                ["git", "status", "--short"],
                cwd=str(workspace),
                capture_output=True,
                text=True,
                timeout=20,
                shell=False,
            )
        except Exception:
            return []

        if completed.returncode != 0:
            return []

        return [line.strip() for line in completed.stdout.splitlines() if line.strip()]

    def _build_prompt(
        self,
        *,
        objective: str,
        scope: str | None,
        constraints: str | None,
        validations: list[str] | None,
        is_continuation: bool,
    ) -> str:
        validations_block = validations or [
            "manage.py check",
            "manage.py makemigrations --check --dry-run",
            "manage.py test",
        ]
        mode_text = (
            "Esta solicitud continua una sesion previa. Retoma el contexto existente sin pedir un prompt tecnico largo."
            if is_continuation
            else "Esta solicitud inicia una tarea nueva. Interpreta el objetivo de negocio y conviertelo en trabajo tecnico ejecutable."
        )
        context_bundle = self._project_context_bundle()
        return f"""
Actua como Codex ejecutando trabajo tecnico en este repositorio.

{mode_text}

Objetivo del usuario:
{objective}

Scope opcional:
{scope or "Sin alcance adicional; determina el alcance minimo necesario."}

Constraints opcionales:
{constraints or "Aplicar intervencion minima, segura y reversible."}

Validaciones esperadas:
{json.dumps(validations_block, ensure_ascii=False)}

Instrucciones de orquestacion:
- Usa el contexto del proyecto incluido abajo en lugar de pedirle al usuario un prompt tecnico largo.
- Si el objetivo ya es claro, ejecuta directamente.
- Si haces cambios funcionales, corre las validaciones pertinentes y reporta cuales ejecutaste.
- Mantén compatibilidad con la arquitectura actual.
- Devuelve tu MENSAJE FINAL como un JSON valido, sin fences ni texto adicional, con esta forma exacta:
{{
  "plan_corto": ["paso 1", "paso 2"],
  "summary": "resumen ejecutivo breve",
  "files_changed": ["ruta/o/archivo.py"],
  "validations_run": ["comando 1", "comando 2"],
  "risks": ["riesgo 1"],
  "next_step": "siguiente paso recomendado"
}}
- Si no cambias archivos, usa "files_changed": [].
- Si no corres validaciones, deja "validations_run": [] y explicalo dentro de "risks" o "summary".

Contexto del proyecto:
{context_bundle}
""".strip()

    def _project_context_bundle(self) -> str:
        chunks: list[str] = []
        for relative in CONTEXT_FILES:
            path = self.settings.project_root / relative
            if not path.exists():
                continue
            content = path.read_text(encoding="utf-8", errors="replace")
            chunks.append(f"## {relative}\n{content}")
        return "\n\n".join(chunks)
