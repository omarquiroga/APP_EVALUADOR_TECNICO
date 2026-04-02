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
- ChatGPT no debe apuntar a `localhost`.
- La URL registrada debe terminar exactamente en `/mcp`.
