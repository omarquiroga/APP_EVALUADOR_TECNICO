from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path


AUTOMATION_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = AUTOMATION_ROOT.parent


def _load_dotenv(dotenv_path: Path) -> None:
    if not dotenv_path.exists():
        return

    for raw_line in dotenv_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def _split_paths(raw_value: str | None, default: list[Path]) -> tuple[Path, ...]:
    if not raw_value:
        return tuple(path.resolve() for path in default)

    paths: list[Path] = []
    for chunk in raw_value.split(";"):
        item = chunk.strip()
        if item:
            paths.append(Path(item).resolve())
    return tuple(paths)


def _env_value(name: str, default: str) -> str:
    value = os.getenv(name)
    if value is None:
        return default

    normalized = value.strip()
    return normalized or default


def _is_command_usable(command: str) -> bool:
    try:
        completed = subprocess.run(
            [command, "--version"],
            capture_output=True,
            text=True,
            timeout=15,
            shell=False,
        )
    except Exception:
        return False

    return completed.returncode == 0


def _resolve_codex_command(configured_command: str) -> str:
    # Respect explicit non-default overrides so the operator can force a custom wrapper.
    if configured_command and configured_command != "codex":
        return configured_command

    candidates = [
        configured_command,
        str(Path.home() / ".codex" / ".sandbox-bin" / "codex.exe"),
        str(Path.home() / ".codex" / ".sandbox-bin" / "codex"),
    ]

    seen: set[str] = set()
    for candidate in candidates:
        if not candidate or candidate in seen:
            continue
        seen.add(candidate)
        if _is_command_usable(candidate):
            return candidate

    return configured_command


def _normalize_start_template(template: str) -> str:
    legacy_values = {
        "{codex_command} exec {prompt}",
        "{codex_command} exec -o {output_path} {prompt}",
    }
    if template in legacy_values:
        return "{codex_command} exec -o {output_path} -"
    return template


def _normalize_continue_template(template: str) -> str:
    legacy_values = {
        "{codex_command} resume {codex_session_id} {prompt}",
        "{codex_command} exec resume -o {output_path} {codex_session_id} {prompt}",
    }
    if template in legacy_values:
        return "{codex_command} exec resume -o {output_path} {codex_session_id} -"
    return template


def _normalize_continue_fallback_template(template: str) -> str:
    legacy_values = {
        "{codex_command} resume --last {prompt}",
        "{codex_command} exec resume -o {output_path} --last {prompt}",
    }
    if template in legacy_values:
        return "{codex_command} exec resume -o {output_path} --last -"
    return template


@dataclass(frozen=True)
class AppSettings:
    host: str
    port: int
    mcp_path: str
    automation_root: Path
    project_root: Path
    default_workspace: Path
    allowed_workspaces: tuple[Path, ...]
    state_dir: Path
    log_dir: Path
    codex_command: str
    codex_start_template: str
    codex_continue_template: str
    codex_continue_fallback_template: str

    def resolve_workspace(self, workspace: str | None) -> Path:
        candidate = Path(workspace).resolve() if workspace else self.default_workspace

        for allowed in self.allowed_workspaces:
            try:
                candidate.relative_to(allowed)
                return candidate
            except ValueError:
                continue

        allowed_values = ", ".join(str(path) for path in self.allowed_workspaces)
        raise ValueError(f"Workspace no permitido: {candidate}. Permitidos: {allowed_values}")


def get_settings() -> AppSettings:
    _load_dotenv(AUTOMATION_ROOT / ".env")

    default_workspace = Path(
        os.getenv("AUTOMATION_DEFAULT_WORKSPACE", str(PROJECT_ROOT))
    ).resolve()
    allowed_workspaces = _split_paths(
        os.getenv("AUTOMATION_ALLOWED_WORKSPACES"),
        [default_workspace],
    )

    state_dir = Path(_env_value("AUTOMATION_STATE_DIR", str(AUTOMATION_ROOT / ".state"))).resolve()
    log_dir = Path(_env_value("AUTOMATION_LOG_DIR", str(AUTOMATION_ROOT / "logs"))).resolve()

    return AppSettings(
        host=os.getenv("AUTOMATION_HOST", "127.0.0.1"),
        port=int(os.getenv("AUTOMATION_PORT", "8765")),
        mcp_path=os.getenv("AUTOMATION_MCP_PATH", "/mcp"),
        automation_root=AUTOMATION_ROOT,
        project_root=PROJECT_ROOT,
        default_workspace=default_workspace,
        allowed_workspaces=allowed_workspaces,
        state_dir=state_dir,
        log_dir=log_dir,
        codex_command=_resolve_codex_command(_env_value("CODEX_COMMAND", "codex")),
        codex_start_template=_normalize_start_template(
            _env_value(
                "CODEX_START_TEMPLATE",
                "{codex_command} exec -o {output_path} -",
            )
        ),
        codex_continue_template=_normalize_continue_template(
            _env_value(
                "CODEX_CONTINUE_TEMPLATE",
                "{codex_command} exec resume -o {output_path} {codex_session_id} -",
            )
        ),
        codex_continue_fallback_template=_normalize_continue_fallback_template(
            _env_value(
                "CODEX_CONTINUE_FALLBACK_TEMPLATE",
                "{codex_command} exec resume -o {output_path} --last -",
            )
        ),
    )
