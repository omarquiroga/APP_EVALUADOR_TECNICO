# Automation MCP V1

Base minima para exponer este repo como servidor MCP y permitir que ChatGPT dispare tareas hacia Codex CLI sin copiar y pegar prompts manualmente.

## Filosofia actual

La superficie MCP ya no esta pensada solo como primitivas operativas. La capa recomendada es de ALTO NIVEL:

- el usuario expresa el objetivo en lenguaje natural
- ChatGPT decide la estrategia y llama una tool high-level
- la app MCP construye internamente el prompt tecnico con `AGENTS.md` y `docs/*`
- Codex ejecuta, valida y devuelve un resultado estructurado
- el planner/reviewer decide si la tarea ya esta hecha, si necesita otra iteracion o si quedo bloqueada

Las tools low-level siguen existiendo por compatibilidad y depuracion, pero el flujo recomendado ya no depende de polling manual ni de prompts tecnicos extensos redactados por el usuario.

## Tools recomendadas

### High-level

- `run_goal_until_done`
  - usar cuando el usuario quiera que el sistema planifique, ejecute, revise y siga iterando hasta completar o bloquear un cambio
  - corre el loop planner/reviewer <-> Codex executor sin pedir un prompt tecnico largo
  - devuelve `final_status`, `iterations`, `planner_summary`, `codex_summary`, `reviewer_summary`, `files_changed`, `validations_run`, `risks`, `next_step` y `session_ids`
- `continue_goal_until_done`
  - usar cuando ya existe una orquestacion previa y ChatGPT debe retomarla sin reconstruir el contexto manualmente
- `review_orchestration_result`
  - usar cuando ChatGPT quiera una vision ejecutiva y tecnica de una orquestacion ya corrida

- `run_eval_task_and_wait`
  - usar cuando una sola ejecucion de Codex suele ser suficiente y no hace falta un loop iterativo completo
  - inicia la tarea, espera internamente y devuelve un resultado estructurado final
- `continue_eval_task_and_wait`
  - usar cuando ya existe una sesion previa y ChatGPT necesita continuarla desde un nuevo objetivo natural
  - evita que el usuario tenga que redactar un prompt tecnico de seguimiento
- `review_eval_result`
  - usar cuando ChatGPT quiera resumir, auditar o decidir si conviene seguir o cerrar una sesion individual

La UX recomendada pasa primero por `run_goal_until_done`.

### Low-level

- `start_eval_task`
- `continue_eval_task`
- `get_eval_task_status`

Estas tres quedan como herramientas de bajo nivel para depuracion, recuperacion manual o casos avanzados de orquestacion.

## Flujo recomendado desde ChatGPT

1. El usuario escribe un objetivo corto en lenguaje natural.
2. ChatGPT llama `run_goal_until_done`.
3. La app MCP arma el prompt tecnico usando `AGENTS.md`, `docs/PROJECT_CONTEXT.md`, `docs/DECISIONS.md` y `docs/TASKS.md`.
4. Un planner/reviewer propone la siguiente instruccion tecnica.
5. Codex ejecuta el trabajo tecnico y devuelve una salida estructurada.
6. El reviewer decide `done`, `needs_revision` o `blocked`.
7. Si corresponde, la app itera automaticamente hasta completion, bloqueo, `max_iterations` o `timeout`.
8. ChatGPT resume el resultado final al usuario y, si hace falta, llama `continue_goal_until_done` o `review_orchestration_result`.

## Arquitectura de orquestacion GPT <-> Codex

- Planner/Reviewer agent
  - toma `objective`, `constraints` y `validations`
  - construye el prompt tecnico para Codex
  - revisa la salida de cada iteracion
  - decide `done`, `needs_revision` o `blocked`
- Codex executor adapter
  - ejecuta Codex CLI sobre el workspace del proyecto
  - soporta inicio y continuacion de sesion
  - devuelve resultados estructurados y conserva `session_id`
- Orchestrator loop
  - coordina planner -> executor -> reviewer
  - itera automaticamente hasta cumplir el objetivo o llegar a limites
  - registra trazabilidad basica por iteracion

## Criterios de cierre

- `done`: el reviewer considera que el objetivo quedo cumplido con cambios y validaciones suficientes
- `needs_revision`: el reviewer detecta que falta una iteracion adicional y genera el siguiente objetivo tecnico
- `blocked`: hay un error, una limitacion o un riesgo que impide seguir con seguridad

## Limites operativos

- `run_goal_until_done` usa por defecto `max_iterations=4` y `timeout_seconds=900`
- `continue_goal_until_done` usa por defecto `max_iterations=3` y `timeout_seconds=900`
- si se alcanza el limite de iteraciones o el timeout, la orquestacion termina con estado controlado y recomendacion de siguiente paso

Ejemplos de intencion del usuario:

- `Corrige la integracion MCP para que el host publico no falle y valida todo.`
- `Implementa el siguiente ajuste en finance con cambios minimos y ejecuta validaciones.`
- `Revisa la sesion previa y dime si conviene seguir o cerrar.`

## Levantar el servidor MCP

```powershell
Set-Location "C:\PROYECTOS\Evaluador Tecnico LFVU\automation"
Copy-Item .env.example .env -Force
& '.\run.ps1'
```

Por defecto el servidor escucha en:

- host: `127.0.0.1`
- puerto: `8765`
- endpoint MCP local: `http://127.0.0.1:8765/mcp`

Ese endpoint local sirve para pruebas del operador, no para registrar directamente en ChatGPT.

## Workspace real del executor

El servidor arranca desde `automation/`, pero el workspace real que se pasa a Codex para escribir cambios es siempre la raiz del repo:

```text
C:\PROYECTOS\Evaluador Tecnico LFVU
```

Eso evita que archivos como `review/forms.py`, `review/views.py` o `review/tests.py` queden fuera del proyecto por usar `automation/` como raiz equivocada. Las instrucciones al executor deben formular rutas relativas a la raiz del repo, por ejemplo `review/views.py`, no rutas absolutas ni rutas relativas a `automation/`.

## Sandbox y aprobaciones efectivas

La capa MCP fuerza el modo operativo de `codex exec` con estas opciones:

- workspace: `C:\PROYECTOS\Evaluador Tecnico LFVU`
- sandbox efectivo: `workspace-write`
- aprobaciones efectivas: `never`

Las plantillas normalizadas usan `-C <workspace>`, `-s workspace-write` y `-c approval_policy=never` para evitar que `codex exec` caiga en el default `read-only` del host.

Existe un `.codex/config.toml` repo-local como referencia segura para operadores humanos, pero la configuracion efectiva del servidor MCP no depende de ese archivo; el runner pasa los flags explicitamente en cada ejecucion.

## Diagnosticar "writing outside of the project"

Si vuelve a aparecer ese error, revisar en este orden:

1. `GET /health`
2. `default_workspace`
3. `effective_sandbox_mode`
4. `effective_approval_policy`
5. `write_within_workspace_ok`
6. `command` y `workspace` de la sesion en `get_eval_task_status`

El caso problematico observado en este proyecto no venia de un `cwd` en `automation/`, sino de sesiones `codex exec` arrancadas con sandbox `read-only`. En ese estado, Codex reportaba `patch rejected: writing outside of the project; rejected by user approval settings` aunque el `cwd` ya apuntara a `C:\PROYECTOS\Evaluador Tecnico LFVU`.

## Abrir ngrok

ChatGPT necesita una URL publica HTTPS. Una forma simple es exponer el puerto local con ngrok:

```powershell
ngrok http 8765
```

ngrok devolvera una URL publica similar a:

```text
https://abc123.ngrok-free.app
```

La URL que se debe registrar en ChatGPT es:

```text
https://abc123.ngrok-free.app/mcp
```

## Registrar el conector en ChatGPT

1. Levantar el servidor MCP local.
2. Abrir el tunel HTTPS.
3. Copiar la URL publica HTTPS del tunel.
4. Anexar `/mcp`.
5. Registrar esa URL final en ChatGPT.

## Nota operativa

- Si `ngrok` no esta instalado en el equipo, hay que instalarlo primero o usar otro tunel HTTPS equivalente.
- ngrok v3 ya no sirve sin cuenta verificada y `authtoken`; si falta ese dato, el comando falla con `ERR_NGROK_4018`.
- ChatGPT no debe apuntar a `localhost`.
- La URL registrada debe terminar exactamente en `/mcp`.

## Bloque final operativo

Arranque del servidor MCP:

```powershell
Set-Location "C:\PROYECTOS\Evaluador Tecnico LFVU\automation"
& ".\run.ps1"
```

El servidor queda escuchando localmente en `http://127.0.0.1:8765`, con `healthcheck` en `http://127.0.0.1:8765/health` y el endpoint MCP montado en `http://127.0.0.1:8765/mcp` que redirige a `http://127.0.0.1:8765/mcp/`.

En `http://127.0.0.1:8765/health` debe verse `codex_command_ok: true` para confirmar que el runner tambien puede ejecutar Codex. Si `CODEX_COMMAND=codex` falla en Windows, el servidor intenta resolver automaticamente un binario usable en `~/.codex/.sandbox-bin/codex.exe` antes de exigir ajuste manual.

Abrir el tunel HTTPS:

```powershell
ngrok http 8765
```

Si ngrok no tiene `authtoken`, una alternativa inmediata sin credenciales extra es `cloudflared` quick tunnel:

```powershell
cloudflared tunnel --url http://127.0.0.1:8765
```

`cloudflared` imprimira una URL publica HTTPS tipo `https://<subdominio>.trycloudflare.com`. La URL exacta a registrar en ChatGPT sera:

```text
https://<subdominio>.trycloudflare.com/mcp
```

URL exacta a registrar en ChatGPT:

```text
https://<subdominio-publico>/mcp
```

ChatGPT no debe conectarse a `localhost`; siempre debe usarse una URL publica HTTPS terminada exactamente en `/mcp`.

Si se usa un tunel publico distinto, el host HTTPS de ese tunel debe estar permitido en la configuracion `transport_security` del servidor MCP (`allowed_hosts` y `allowed_origins`) para evitar errores como `Invalid Host header`. En desarrollo con `trycloudflare`, como el subdominio cambia en cada arranque, la proteccion de DNS rebinding puede desactivarse temporalmente para no bloquear `/mcp`.

Unico paso manual final en ChatGPT web:

1. Crear o editar la conexion MCP y registrar la URL publica final con forma `https://<subdominio-publico>/mcp`.

## Estado operativo actual

Metodo de tunel recomendado en este equipo:

```powershell
cloudflared tunnel --url http://127.0.0.1:8765
```

Verificacion publica minima:

```powershell
curl.exe -i https://<subdominio>.trycloudflare.com/health
curl.exe -I https://<subdominio>.trycloudflare.com/mcp
curl.exe -I https://<subdominio>.trycloudflare.com/mcp/
```

URL publica a registrar en cada corrida:

```text
https://<subdominio>.trycloudflare.com/mcp/
```

Esa URL es temporal. Si `cloudflared` se reinicia, el subdominio `trycloudflare.com` cambia y hay que volver a registrar la nueva URL publica en ChatGPT. Antes de pegarla en ChatGPT, conviene verificar al menos `https://<subdominio>.trycloudflare.com/health`.

No reutilices una URL vieja de `trycloudflare.com`: cada Quick Tunnel nuevo puede emitir un subdominio distinto y ChatGPT debe apuntar siempre a la URL HTTPS vigente de esa corrida.

Unico paso manual final en ChatGPT web para esta corrida:

1. Crear o editar el conector MCP y pegar la URL HTTPS publica vigente terminada en `/mcp/`.

## Ejemplos reales de uso desde ChatGPT

Ejemplo recomendado para ejecutar trabajo tecnico:

- usuario: `Corrige la integracion MCP para que ChatGPT pueda usarla y valida el proyecto.`
- ChatGPT: llama `run_eval_task_and_wait(objective=..., constraints=..., validations=...)`
- Codex: ejecuta y devuelve `session_id`, `status`, `summary`, `files_changed`, `validations_run`, `risks` y `next_step`

Ejemplo recomendado para una orquestacion completa:

- usuario: `Implementa el ajuste en automation para que GPT planifique, Codex ejecute y el sistema siga iterando hasta terminar.`
- ChatGPT: llama `run_goal_until_done(objective=..., constraints=..., validations=..., max_iterations=4, timeout_seconds=900)`
- la app MCP: planifica, ejecuta, revisa, reitera si hace falta y devuelve un solo resultado final estructurado

Ejemplo recomendado para continuar una sesion:

- usuario: `Sigue con la sesion anterior, pero ahora sin tocar Django fuera de automation/.`
- ChatGPT: llama `continue_eval_task_and_wait(session_id=..., objective=...)`

Ejemplo recomendado para revisar o auditar:

- usuario: `Resume esa sesion y dime si conviene cerrar o seguir.`
- ChatGPT: llama `review_eval_result(session_id=..., focus=...)`
