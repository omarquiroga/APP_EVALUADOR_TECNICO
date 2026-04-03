from __future__ import annotations

import json
import subprocess
import tempfile
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


DEFAULT_VALIDATIONS = [
    "manage.py check",
    "manage.py makemigrations --check --dry-run",
    "manage.py test",
]

CONTEXT_FILES = [
    "AGENTS.md",
    "docs/PROJECT_CONTEXT.md",
    "docs/DECISIONS.md",
    "docs/TASKS.md",
]


def _json_block(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2)


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
        prompt = self._build_executor_prompt(
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
        prompt = self._build_executor_prompt(
            objective=objective,
            scope=scope,
            constraints=constraints,
            validations=validations,
            is_continuation=True,
        )
        resolved_workspace = self.settings.resolve_workspace(
            workspace or self.store.get_session(session_id)["workspace"]
        )
        self.store.update_session(
            session_id,
            high_level_request={
                "objective": objective,
                "scope": scope,
                "constraints": constraints,
                "validations": validations or [],
                "mode": "continue_and_wait",
                "git_status_before": self._git_status_snapshot(resolved_workspace),
            },
        )
        self.runner.continue_task(session_id=session_id, prompt=prompt, workspace=str(resolved_workspace))
        return self._wait_and_summarize(
            session_id=session_id,
            timeout_seconds=timeout_seconds,
            poll_interval_seconds=poll_interval_seconds,
        )

    def review_result(self, session_id: str, focus: str | None = None) -> dict[str, Any]:
        session = self.runner.get_status(session_id)
        result = session.get("high_level_result")
        payload = result or self._build_structured_result(session, session["status"])
        review = {
            "session_id": session_id,
            "status": payload.get("status", session["status"]),
            "executive_summary": payload.get("summary", ""),
            "changes_realized": payload.get("files_changed", []),
            "validations": payload.get("validations_run", []),
            "risks": payload.get("risks", []),
            "recommend_action": payload.get("next_step", ""),
            "log_tail": session.get("log_tail", ""),
        }
        if focus:
            review["focus"] = focus
        return review

    def run_goal_until_done(
        self,
        *,
        objective: str,
        constraints: str | None = None,
        validations: list[str] | None = None,
        workspace: str | None = None,
        max_iterations: int = 4,
        timeout_seconds: int = 900,
    ) -> dict[str, Any]:
        resolved_workspace = self.settings.resolve_workspace(workspace)
        orchestration = self.store.create_orchestration(
            objective=objective,
            workspace=resolved_workspace,
            constraints=constraints,
            validations=validations or DEFAULT_VALIDATIONS,
            max_iterations=max_iterations,
            timeout_seconds=timeout_seconds,
        )
        return self._run_orchestration_loop(
            orchestration_id=orchestration["orchestration_id"],
            objective=objective,
            constraints=constraints,
            validations=validations or DEFAULT_VALIDATIONS,
            workspace=resolved_workspace,
            max_iterations=max_iterations,
            timeout_seconds=timeout_seconds,
        )

    def continue_goal_until_done(
        self,
        *,
        orchestration_id: str,
        objective: str | None = None,
        constraints: str | None = None,
        validations: list[str] | None = None,
        workspace: str | None = None,
        max_iterations: int = 3,
        timeout_seconds: int = 900,
    ) -> dict[str, Any]:
        orchestration = self.store.get_orchestration(orchestration_id)
        resolved_workspace = self.settings.resolve_workspace(workspace or orchestration["workspace"])
        return self._run_orchestration_loop(
            orchestration_id=orchestration_id,
            objective=objective or orchestration["objective"],
            constraints=constraints if constraints is not None else orchestration.get("constraints"),
            validations=validations or orchestration.get("validations") or DEFAULT_VALIDATIONS,
            workspace=resolved_workspace,
            max_iterations=max_iterations,
            timeout_seconds=timeout_seconds,
        )

    def review_orchestration_result(
        self,
        *,
        orchestration_id: str,
        focus: str | None = None,
    ) -> dict[str, Any]:
        orchestration = self.store.get_orchestration(orchestration_id)
        result = orchestration.get("final_result") or self._summarize_orchestration(orchestration)
        review = {
            "orchestration_id": orchestration_id,
            "final_status": result.get("final_status", orchestration.get("status", "unknown")),
            "iterations": result.get("iterations", len(orchestration.get("iterations", []))),
            "summary": result.get("summary", ""),
            "final_reviewer_assessment": result.get("final_reviewer_assessment", ""),
            "files_changed": result.get("files_changed", []),
            "validations_run": result.get("validations_run", []),
            "risks": result.get("risks", []),
            "next_step": result.get("next_step", ""),
            "session_ids": result.get("session_ids", orchestration.get("session_ids", [])),
        }
        if focus:
            review["focus"] = focus
        return review

    def _run_orchestration_loop(
        self,
        *,
        orchestration_id: str,
        objective: str,
        constraints: str | None,
        validations: list[str],
        workspace: Path,
        max_iterations: int,
        timeout_seconds: int,
    ) -> dict[str, Any]:
        start = time.time()
        orchestration = self.store.get_orchestration(orchestration_id)
        existing_iterations = orchestration.get("iterations", [])
        session_ids = list(orchestration.get("session_ids", []))
        current_objective = objective
        final_status = "max_iterations_reached"

        for iteration_number in range(len(existing_iterations) + 1, len(existing_iterations) + max_iterations + 1):
            remaining = int(timeout_seconds - (time.time() - start))
            if remaining <= 0:
                final_status = "timeout"
                break

            planner = self._planner_step(
                orchestration=orchestration,
                current_objective=current_objective,
                constraints=constraints,
                validations=validations,
                iteration_number=iteration_number,
                workspace=workspace,
                timeout_seconds=min(remaining, 180),
            )

            executor_result = self._executor_step(
                planner=planner,
                current_objective=current_objective,
                constraints=constraints,
                validations=validations,
                workspace=workspace,
                session_ids=session_ids,
                timeout_seconds=min(remaining, max(60, remaining - 30)),
            )
            if executor_result["session_id"] not in session_ids:
                session_ids.append(executor_result["session_id"])

            remaining = int(timeout_seconds - (time.time() - start))
            reviewer = self._reviewer_step(
                orchestration=orchestration,
                planner=planner,
                executor_result=executor_result,
                iteration_number=iteration_number,
                workspace=workspace,
                timeout_seconds=min(max(remaining, 30), 180),
            )

            iteration_record = {
                "iteration": iteration_number,
                "planner": planner,
                "executor": {
                    "session_id": executor_result["session_id"],
                    "status": executor_result["status"],
                    "summary": executor_result.get("summary", ""),
                    "files_changed": executor_result.get("files_changed", []),
                    "validations_run": executor_result.get("validations_run", []),
                    "risks": executor_result.get("risks", []),
                },
                "reviewer": reviewer,
            }
            existing_iterations.append(iteration_record)
            orchestration = self.store.update_orchestration(
                orchestration_id,
                status="running",
                objective=objective,
                constraints=constraints,
                validations=validations,
                max_iterations=max_iterations,
                timeout_seconds=timeout_seconds,
                iterations=existing_iterations,
                session_ids=session_ids,
            )

            decision = reviewer.get("decision", "blocked")
            if decision == "done":
                final_status = "completed"
                break
            if decision == "blocked":
                final_status = "blocked"
                break

            current_objective = reviewer.get("next_objective") or current_objective

        final_result = self._summarize_orchestration(orchestration)
        final_result["final_status"] = final_status
        self.store.update_orchestration(
            orchestration_id,
            status=final_status,
            completed_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            final_result=final_result,
            session_ids=session_ids,
        )
        return final_result

    def _planner_step(
        self,
        *,
        orchestration: dict[str, Any],
        current_objective: str,
        constraints: str | None,
        validations: list[str],
        iteration_number: int,
        workspace: Path,
        timeout_seconds: int,
    ) -> dict[str, Any]:
        history = orchestration.get("iterations", [])
        prompt = f"""
Actua como planner tecnico y reviewer previo a la ejecucion.

Tu trabajo es convertir un objetivo del usuario en una instruccion clara para Codex executor.

Objetivo actual:
{current_objective}

Constraints:
{constraints or "Aplicar cambios minimos, reversibles y compatibles con la arquitectura actual."}

Validaciones deseadas:
{_json_block(validations)}

Historial resumido de iteraciones previas:
{_json_block(history[-2:])}

Contexto del proyecto:
{self._project_context_bundle()}

Devuelve JSON valido con esta forma exacta:
{{
  "planner_summary": "que haras y por que",
  "executor_objective": "instruccion tecnica breve para Codex executor",
  "executor_constraints": "restricciones tecnicas concretas",
  "validations_to_run": ["comando 1", "comando 2"]
}}
""".strip()
        return self._run_codex_json_step(
            role="planner",
            prompt=prompt,
            workspace=workspace,
            timeout_seconds=timeout_seconds,
        )

    def _reviewer_step(
        self,
        *,
        orchestration: dict[str, Any],
        planner: dict[str, Any],
        executor_result: dict[str, Any],
        iteration_number: int,
        workspace: Path,
        timeout_seconds: int,
    ) -> dict[str, Any]:
        prompt = f"""
Actua como reviewer de una iteracion de orquestacion GPT <-> Codex.

Objetivo global:
{orchestration["objective"]}

Iteracion:
{iteration_number}

Salida del planner:
{_json_block(planner)}

Resultado del executor:
{_json_block(executor_result)}

Decide si:
- done
- needs_revision
- blocked

Devuelve JSON valido con esta forma exacta:
{{
  "decision": "done|needs_revision|blocked",
  "reviewer_summary": "evaluacion ejecutiva breve",
  "next_objective": "solo si hace falta otra iteracion",
  "risks": ["riesgo 1"],
  "next_step": "siguiente paso recomendado"
}}
""".strip()
        return self._run_codex_json_step(
            role="reviewer",
            prompt=prompt,
            workspace=workspace,
            timeout_seconds=timeout_seconds,
        )

    def _executor_step(
        self,
        *,
        planner: dict[str, Any],
        current_objective: str,
        constraints: str | None,
        validations: list[str],
        workspace: Path,
        session_ids: list[str],
        timeout_seconds: int,
    ) -> dict[str, Any]:
        prompt = self._build_executor_prompt(
            objective=planner.get("executor_objective") or current_objective,
            scope=None,
            constraints=planner.get("executor_constraints") or constraints,
            validations=planner.get("validations_to_run") or validations,
            is_continuation=bool(session_ids),
        )
        if session_ids:
            latest_session_id = session_ids[-1]
            latest_status = self.runner.get_status(latest_session_id)
            latest_workspace = self.runner.inspect_session_workspace(latest_session_id, workspace)
            if latest_status["status"] not in {"pending", "running"} and latest_workspace["ok"]:
                self.store.update_session(
                    latest_session_id,
                    high_level_request={
                        "objective": planner.get("executor_objective") or current_objective,
                        "scope": None,
                        "constraints": planner.get("executor_constraints") or constraints,
                        "validations": planner.get("validations_to_run") or validations,
                        "mode": "orchestration_continue",
                        "git_status_before": self._git_status_snapshot(workspace),
                    },
                )
                self.runner.continue_task(session_id=latest_session_id, prompt=prompt, workspace=str(workspace))
                return self._wait_and_summarize(
                    session_id=latest_session_id,
                    timeout_seconds=timeout_seconds,
                    poll_interval_seconds=5,
                )

        status = self.runner.start_task(prompt=prompt, workspace=str(workspace))
        self.store.update_session(
            status["session_id"],
            high_level_request={
                "objective": planner.get("executor_objective") or current_objective,
                "scope": None,
                "constraints": planner.get("executor_constraints") or constraints,
                "validations": planner.get("validations_to_run") or validations,
                "mode": "orchestration_start",
                "git_status_before": self._git_status_snapshot(workspace),
            },
        )
        return self._wait_and_summarize(
            session_id=status["session_id"],
            timeout_seconds=timeout_seconds,
            poll_interval_seconds=5,
        )

    def _run_codex_json_step(
        self,
        *,
        role: str,
        prompt: str,
        workspace: Path,
        timeout_seconds: int,
    ) -> dict[str, Any]:
        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=f".{role}.json",
            dir=str(self.settings.log_dir),
        ) as handle:
            output_path = Path(handle.name)

        command = (
            f'{subprocess.list2cmdline([self.settings.codex_command])} '
            f'exec -C {subprocess.list2cmdline([str(workspace.resolve())])} '
            f'-s {self.settings.codex_sandbox_mode} -c approval_policy={self.settings.codex_approval_policy} '
            f'-o {subprocess.list2cmdline([str(output_path)])} -'
        )
        completed = subprocess.run(
            command,
            cwd=str(workspace),
            input=prompt,
            text=True,
            encoding="utf-8",
            capture_output=True,
            shell=True,
            timeout=timeout_seconds,
        )
        raw_output = ""
        if output_path.exists():
            raw_output = output_path.read_text(encoding="utf-8", errors="replace").strip()
            output_path.unlink(missing_ok=True)

        parsed = self._parse_structured_output(raw_output)
        if not parsed:
            parsed = {
                "decision": "blocked" if role == "reviewer" else None,
                "planner_summary": "No se pudo estructurar el objetivo." if role == "planner" else None,
                "executor_objective": prompt[:500] if role == "planner" else None,
                "executor_constraints": None,
                "validations_to_run": [],
                "reviewer_summary": "No se pudo interpretar una respuesta JSON valida." if role == "reviewer" else None,
                "next_objective": None,
                "risks": [f"La etapa {role} no devolvio JSON estructurado valido."],
                "next_step": "Revisar raw_output y stderr_tail de la etapa para diagnostico.",
            }
        parsed["raw_output"] = raw_output
        parsed["command_status"] = completed.returncode
        parsed["stderr_tail"] = (completed.stderr or "").strip()[-1000:]
        return parsed

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

    def _summarize_orchestration(self, orchestration: dict[str, Any]) -> dict[str, Any]:
        iterations = orchestration.get("iterations", [])
        files_changed: list[str] = []
        validations_run: list[str] = []
        risks: list[str] = []
        for item in iterations:
            for path in item.get("executor", {}).get("files_changed", []):
                if path not in files_changed:
                    files_changed.append(path)
            for command in item.get("executor", {}).get("validations_run", []):
                if command not in validations_run:
                    validations_run.append(command)
            for risk in item.get("reviewer", {}).get("risks", []) + item.get("executor", {}).get("risks", []):
                if risk not in risks:
                    risks.append(risk)

        last_iteration = iterations[-1] if iterations else {}
        planner_summary = last_iteration.get("planner", {}).get("planner_summary", "")
        codex_summary = last_iteration.get("executor", {}).get("summary", "")
        reviewer_summary = last_iteration.get("reviewer", {}).get("reviewer_summary", "")

        return {
            "orchestration_id": orchestration["orchestration_id"],
            "final_status": orchestration.get("status", "unknown"),
            "iterations": len(iterations),
            "planner_summary": planner_summary,
            "codex_summary": codex_summary,
            "reviewer_summary": reviewer_summary,
            "summary": reviewer_summary or codex_summary or planner_summary,
            "final_reviewer_assessment": reviewer_summary,
            "files_changed": files_changed,
            "validations_run": validations_run,
            "risks": risks,
            "next_step": last_iteration.get("reviewer", {}).get("next_step", ""),
            "session_ids": orchestration.get("session_ids", []),
        }

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

    def _build_executor_prompt(
        self,
        *,
        objective: str,
        scope: str | None,
        constraints: str | None,
        validations: list[str] | None,
        is_continuation: bool,
    ) -> str:
        validations_block = validations or DEFAULT_VALIDATIONS
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
- Manten compatibilidad con la arquitectura actual.
- Usa como workspace real la raiz del repo `{self.settings.project_root}`.
- Formula y aplica cambios con rutas relativas a esa raiz, por ejemplo `review/views.py`.
- No intentes escribir con rutas absolutas ni fuera del workspace del repo.
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
