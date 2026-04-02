# Tasks

## Backlog tecnico actual

- Consolidar la V1 de automatizacion MCP con pruebas de integracion controladas en un entorno donde Codex CLI pueda ejecutarse sin restricciones del host.
- Definir el siguiente modulo fuera del admin despues de Finance.
- Decidir si la siguiente fase funcional debe priorizar:
  - endurecimiento adicional de permisos
  - nuevo flujo controlado en `documents`
  - nuevo flujo controlado en `rup`

## Tareas abiertas

- Conectar la futura app MCP de ChatGPT al endpoint local `/mcp`.
- Validar en un equipo operador el comando exacto de continuacion de Codex si el CLI cambia de version.
- Definir si la automatizacion debe restringirse a un solo workspace o a una allowlist corta.
- Evaluar si conviene emitir artefactos mas estructurados por tarea, por ejemplo resumen final, logs separados o metadatos de commit.
- Normalizar textos visibles fuera de Finance donde aun queden inconsistencias de espanol operativo o codificacion.

## Riesgos

- La V1 depende de que Codex CLI este instalado y autenticado localmente fuera del repo.
- En este entorno de desarrollo la invocacion directa de `codex.exe` desde PowerShell puede estar restringida; por eso el comando queda configurable por `.env`.
- El estado de tareas corre en JSON local y memoria del proceso, asi que un reinicio del servidor durante una ejecucion puede dejar sesiones en estado intermedio hasta reconciliacion manual.
- Si se abre otro flujo de escritura sin repetir el patron de permisos, puede reintroducir dependencia de `login_required` como unico control.

## Siguiente paso recomendado

Conectar ChatGPT web o la futura app MCP al endpoint local `http://127.0.0.1:8765/mcp` y probar un flujo corto con:

1. `start_eval_task`
2. `get_eval_task_status`
3. `continue_eval_task`

Si ese flujo queda estable en el equipo operador, la siguiente mejora deberia ser endurecer la persistencia y el seguimiento de sesiones en `automation/` antes de ampliar alcance funcional.
