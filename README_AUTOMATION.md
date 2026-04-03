# Automation MCP V1

Base minima para exponer este repo como servidor MCP y permitir que ChatGPT dispare tareas hacia Codex CLI sin copiar y pegar prompts manualmente.

## Filosofia actual

La superficie MCP ya no esta pensada solo como primitivas operativas. La capa recomendada es de ALTO NIVEL:

- el usuario expresa el objetivo en lenguaje natural
- ChatGPT decide la estrategia y llama una tool high-level
- la app MCP construye internamente el prompt tecnico con `AGENTS.md` y `docs/*`
- Codex ejecuta, valida y devuelve un resultado estructurado

Las tools low-level siguen existiendo por compatibilidad y depuracion, pero el flujo recomendado ya no depende de polling manual ni de prompts tecnicos extensos redactados por el usuario.

## Tools recomendadas

### High-level

- `run_eval_task_and_wait`
  - usar cuando el usuario quiera implementar, corregir, validar o evolucionar el proyecto desde una intencion natural
  - inicia la tarea, espera internamente y devuelve un resultado estructurado final
- `continue_eval_task_and_wait`
  - usar cuando ya existe una sesion previa y ChatGPT necesita continuarla desde un nuevo objetivo natural
  - evita que el usuario tenga que redactar un prompt tecnico de seguimiento
- `review_eval_result`
  - usar cuando ChatGPT quiera resumir, auditar o decidir si conviene seguir o cerrar una sesion

### Low-level

- `start_eval_task`
- `continue_eval_task`
- `get_eval_task_status`

Estas tres quedan como herramientas de bajo nivel para depuracion, recuperacion manual o casos avanzados de orquestacion.

## Flujo recomendado desde ChatGPT

1. El usuario escribe un objetivo corto en lenguaje natural.
2. ChatGPT llama `run_eval_task_and_wait`.
3. La app MCP arma el prompt tecnico usando `AGENTS.md`, `docs/PROJECT_CONTEXT.md`, `docs/DECISIONS.md` y `docs/TASKS.md`.
4. Codex ejecuta el trabajo tecnico y devuelve una salida estructurada.
5. ChatGPT resume el resultado al usuario y, si hace falta, llama `continue_eval_task_and_wait` o `review_eval_result`.

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

Unico paso manual final en ChatGPT web para esta corrida:

1. Crear o editar el conector MCP y pegar la URL HTTPS publica vigente terminada en `/mcp/`.

## Ejemplos reales de uso desde ChatGPT

Ejemplo recomendado para ejecutar trabajo tecnico:

- usuario: `Corrige la integracion MCP para que ChatGPT pueda usarla y valida el proyecto.`
- ChatGPT: llama `run_eval_task_and_wait(objective=..., constraints=..., validations=...)`
- Codex: ejecuta y devuelve `session_id`, `status`, `summary`, `files_changed`, `validations_run`, `risks` y `next_step`

Ejemplo recomendado para continuar una sesion:

- usuario: `Sigue con la sesion anterior, pero ahora sin tocar Django fuera de automation/.`
- ChatGPT: llama `continue_eval_task_and_wait(session_id=..., objective=...)`

Ejemplo recomendado para revisar o auditar:

- usuario: `Resume esa sesion y dime si conviene cerrar o seguir.`
- ChatGPT: llama `review_eval_result(session_id=..., focus=...)`
