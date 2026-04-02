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
    from app.settings import get_settings
    from app.state import SessionStore
except ModuleNotFoundError:
    from automation.app.codex_runner import CodexRunner
    from automation.app.settings import get_settings
    from automation.app.state import SessionStore


settings = get_settings()
store = SessionStore(settings.state_dir, settings.log_dir)
runner = CodexRunner(settings, store)

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
    stateless_http=True,
    json_response=True,
    streamable_http_path="/",
    transport_security=transport_security,
)


@mcp.tool()
def start_eval_task(prompt: str, workspace: str | None = None) -> dict:
    """Inicia una tarea de Codex sobre este proyecto o un workspace permitido."""
    return runner.start_task(prompt=prompt, workspace=workspace)


@mcp.tool()
def continue_eval_task(session_id: str, prompt: str, workspace: str | None = None) -> dict:
    """Continua una sesion previa de Codex usando el mismo id local."""
    return runner.continue_task(session_id=session_id, prompt=prompt, workspace=workspace)


@mcp.tool()
def get_eval_task_status(session_id: str) -> dict:
    """Consulta estado, log reciente y metadatos de una sesion."""
    return runner.get_status(session_id=session_id)


async def healthcheck(_: object) -> JSONResponse:
    codex_probe = runner.probe_command()
    return JSONResponse(
        {
            "status": "ok",
            "mcp_path": settings.mcp_path,
            "default_workspace": str(settings.default_workspace),
            "codex_command": codex_probe["command"],
            "codex_command_ok": codex_probe["ok"],
            "codex_command_detail": codex_probe["detail"],
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
