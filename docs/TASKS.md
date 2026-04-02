# Tasks

## Backlog tecnico actual

- Consolidar la V1 de automatizacion MCP con pruebas de integracion controladas en un entorno donde Codex CLI pueda ejecutarse sin restricciones del host.
- Definir el siguiente modulo fuera del admin despues de Finance.
- Decidir si la siguiente fase funcional debe priorizar:
  - endurecimiento adicional de permisos
  - nuevo flujo controlado en `documents`
  - nuevo flujo controlado en `rup`

## Tareas abiertas

- Exponer el servidor MCP local mediante una URL publica HTTPS terminada en `/mcp` para poder registrarlo en ChatGPT.
- Validar en un equipo operador el comando exacto de continuacion de Codex si el CLI cambia de version.
- Definir si la automatizacion debe restringirse a un solo workspace o a una allowlist corta.
- Evaluar si conviene emitir artefactos mas estructurados por tarea, por ejemplo resumen final, logs separados o metadatos de commit.
- Normalizar textos visibles fuera de Finance donde aun queden inconsistencias de espanol operativo o codificacion.

## Riesgos

- La V1 depende de que Codex CLI este instalado y autenticado localmente fuera del repo.
- En este entorno de desarrollo la invocacion directa de `codex.exe` desde PowerShell puede estar restringida; por eso el comando queda configurable por `.env`.
- El `healthcheck` ya expone esa limitacion como `codex_command_ok=false` cuando el host no puede invocar `CODEX_COMMAND`.
- Si el alias `codex` de Windows falla pero existe `~/.codex/.sandbox-bin/codex.exe`, la V1 ya puede autodetectarlo sin cambio manual de `.env`.
- El estado de tareas corre en JSON local y memoria del proceso, asi que un reinicio del servidor durante una ejecucion puede dejar sesiones en estado intermedio hasta reconciliacion manual.
- Si se abre otro flujo de escritura sin repetir el patron de permisos, puede reintroducir dependencia de `login_required` como unico control.

## Siguiente paso recomendado

Levantar el servidor MCP local en el puerto configurado, publicarlo con un tunel HTTPS y registrar en ChatGPT la URL publica terminada en `/mcp`.

Secuencia operativa minima:

1. `start_eval_task`
2. `get_eval_task_status`
3. `continue_eval_task`

Si ese flujo queda estable en el equipo operador, la siguiente mejora deberia ser endurecer la persistencia y el seguimiento de sesiones en `automation/` antes de ampliar alcance funcional.

## Conexion ChatGPT

Arranque local del servidor:

```powershell
Set-Location "C:\PROYECTOS\Evaluador Tecnico LFVU\automation"
& '.\run.ps1'
```

Tunel HTTPS con ngrok:

```powershell
ngrok http 8765
```

Registro del conector en ChatGPT:

- copiar la URL HTTPS publica que entregue ngrok
- agregar `/mcp` al final
- registrar en ChatGPT la URL final con forma `https://<subdominio-publico>/mcp`
- no registrar `http://127.0.0.1:8765/mcp` porque `localhost` no es accesible desde ChatGPT
