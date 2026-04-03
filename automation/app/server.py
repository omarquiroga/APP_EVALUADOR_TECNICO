from __future__ import annotations

import contextlib

import uvicorn
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from starlette.applications import Starlette
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route

try:
    from app.codex_runner import CodexRunner
    from app.high_level import HighLevelOrchestrator
    from app.settings import get_settings
    from app.state import SessionStore
except ModuleNotFoundError:
    from automation.app.codex_runner import CodexRunner
    from automation.app.high_level import HighLevelOrchestrator
    from automation.app.settings import get_settings
    from automation.app.state import SessionStore


settings = get_settings()
store = SessionStore(settings.state_dir, settings.log_dir)
runner = CodexRunner(settings, store)
orchestrator = HighLevelOrchestrator(settings, store, runner)

transport_security = TransportSecuritySettings(
    # Quick tunnels like trycloudflare rotate hostname on each restart, so
    # a static allowlist becomes brittle during local development.
    enable_dns_rebinding_protection=False,
    allowed_hosts=[
        "localhost:*",
        "127.0.0.1:*",
        "surveillance-personal-representatives-storm.trycloudflare.com:*",
    ],
    allowed_origins=[
        "http://localhost:*",
        "http://127.0.0.1:*",
        "https://surveillance-personal-representatives-storm.trycloudflare.com",
    ],
)

mcp = FastMCP(
    "evaluador-tecnico-automation",
    instructions=(
        "Prefer the orchestration tools when the user wants the system to plan, execute, review, and "
        "iterate on a business objective until completion. Use the simpler high-level tools when a single "
        "Codex execution is enough. Keep the low-level tools for debugging, manual orchestration, or "
        "advanced recovery workflows."
    ),
    stateless_http=True,
    json_response=True,
    streamable_http_path="/",
    transport_security=transport_security,
)


@mcp.tool()
def start_eval_task(prompt: str, workspace: str | None = None) -> dict:
    """Use this when you need a low-level or debug primitive to start a Codex task with a fully prepared technical prompt."""
    return runner.start_task(prompt=prompt, workspace=workspace)


@mcp.tool()
def continue_eval_task(session_id: str, prompt: str, workspace: str | None = None) -> dict:
    """Use this when you need a low-level or debug primitive to continue a specific local session with a manually written technical prompt."""
    return runner.continue_task(session_id=session_id, prompt=prompt, workspace=workspace)


@mcp.tool()
def get_eval_task_status(session_id: str) -> dict:
    """Use this when you need low-level or debug visibility into the raw status, log tail, and metadata of a local session."""
    return runner.get_status(session_id=session_id)


@mcp.tool()
def run_eval_task_and_wait(
    objective: str,
    scope: str | None = None,
    constraints: str | None = None,
    validations: list[str] | None = None,
    workspace: str | None = None,
    timeout_seconds: int | None = None,
    poll_interval_seconds: int | None = None,
) -> dict:
    """Use this when the user wants to implement, fix, validate, or evolve the project from a natural-language objective and should not need to write a long technical prompt."""
    return orchestrator.run_and_wait(
        objective=objective,
        scope=scope,
        constraints=constraints,
        validations=validations,
        workspace=workspace,
        timeout_seconds=timeout_seconds,
        poll_interval_seconds=poll_interval_seconds,
    )


@mcp.tool()
def continue_eval_task_and_wait(
    session_id: str,
    objective: str,
    scope: str | None = None,
    constraints: str | None = None,
    validations: list[str] | None = None,
    workspace: str | None = None,
    timeout_seconds: int | None = None,
    poll_interval_seconds: int | None = None,
) -> dict:
    """Use this when a previous high-level task already exists and ChatGPT should continue it from a new natural-language objective without manual polling or prompt choreography."""
    return orchestrator.continue_and_wait(
        session_id=session_id,
        objective=objective,
        scope=scope,
        constraints=constraints,
        validations=validations,
        workspace=workspace,
        timeout_seconds=timeout_seconds,
        poll_interval_seconds=poll_interval_seconds,
    )


@mcp.tool()
def review_eval_result(session_id: str, focus: str | None = None) -> dict:
    """Use this when ChatGPT needs a high-level synthesis or audit of a previous session, including status, summary, validations, risks, and whether to continue or close."""
    return orchestrator.review_result(session_id=session_id, focus=focus)


@mcp.tool()
def run_goal_until_done(
    objective: str,
    constraints: str | None = None,
    validations: list[str] | None = None,
    workspace: str | None = None,
    max_iterations: int = 4,
    timeout_seconds: int = 900,
) -> dict:
    """Use this when the user wants the system to fully plan, execute, review, and iterate on a change until it is done, blocked, or reaches the configured limits without writing a technical prompt."""
    return orchestrator.run_goal_until_done(
        objective=objective,
        constraints=constraints,
        validations=validations,
        workspace=workspace,
        max_iterations=max_iterations,
        timeout_seconds=timeout_seconds,
    )


@mcp.tool()
def continue_goal_until_done(
    orchestration_id: str,
    objective: str | None = None,
    constraints: str | None = None,
    validations: list[str] | None = None,
    workspace: str | None = None,
    max_iterations: int = 3,
    timeout_seconds: int = 900,
) -> dict:
    """Use this when a previous orchestration already exists and ChatGPT should resume the planner-reviewer-executor loop without rebuilding the technical context manually."""
    return orchestrator.continue_goal_until_done(
        orchestration_id=orchestration_id,
        objective=objective,
        constraints=constraints,
        validations=validations,
        workspace=workspace,
        max_iterations=max_iterations,
        timeout_seconds=timeout_seconds,
    )


@mcp.tool()
def review_orchestration_result(orchestration_id: str, focus: str | None = None) -> dict:
    """Use this when ChatGPT needs an executive and technical summary of a completed or in-progress orchestration, including whether to continue, stop, or unblock it."""
    return orchestrator.review_orchestration_result(
        orchestration_id=orchestration_id,
        focus=focus,
    )


async def healthcheck(_: object) -> JSONResponse:
    codex_probe = runner.probe_command()
    exec_probe = runner.execution_diagnostics()
    return JSONResponse(
        {
            "status": "ok",
            "mcp_path": settings.mcp_path,
            "default_workspace": str(settings.default_workspace),
            "allowed_workspaces": exec_probe["allowed_workspaces"],
            "codex_command": codex_probe["command"],
            "codex_command_ok": codex_probe["ok"],
            "codex_command_detail": codex_probe["detail"],
            "effective_sandbox_mode": exec_probe["effective_sandbox_mode"],
            "effective_approval_policy": exec_probe["effective_approval_policy"],
            "write_within_workspace_ok": exec_probe["write_within_workspace_ok"],
            "write_within_workspace_detail": exec_probe["write_within_workspace_detail"],
        }
    )


@contextlib.asynccontextmanager
async def lifespan(_: Starlette):
    async with mcp.session_manager.run():
        yield


starlette_app = Starlette(
    routes=[
        Route("/health", endpoint=healthcheck),
        Mount(settings.mcp_path, app=mcp.streamable_http_app()),
    ],
    lifespan=lifespan,
)

app = CORSMiddleware(
    starlette_app,
    allow_origins=[
        "http://localhost",
        "http://127.0.0.1",
        "https://surveillance-personal-representatives-storm.trycloudflare.com",
    ],
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["Mcp-Session-Id"],
)


def main() -> None:
    uvicorn.run(app, host=settings.host, port=settings.port)


if __name__ == "__main__":
    main()
