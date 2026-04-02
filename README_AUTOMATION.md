# Automation MCP V1

Base minima para exponer este repo como servidor MCP y permitir que ChatGPT dispare tareas hacia Codex CLI sin copiar y pegar prompts manualmente.

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

Unico paso manual final en ChatGPT web:

1. Crear o editar la conexion MCP y registrar la URL publica final con forma `https://<subdominio-publico>/mcp`.
