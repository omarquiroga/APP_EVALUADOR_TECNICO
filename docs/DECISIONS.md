# Decisions

## Decisiones tecnicas detectadas

### Arquitectura principal

- Django monolito modular.
- PostgreSQL como base principal.
- Django templates + HTMX para la UI operativa.
- Django Admin como canal de carga y edicion controlada.
- `review` como espacio de operacion fuera del admin solo donde el admin ya no basta.

### Automatizacion V1

- La automatizacion se implementa fuera del runtime Django, en `automation/`.
- El servidor expone un MCP HTTP minimo en la ruta `/mcp`.
- El `healthcheck` HTTP expone tambien el resultado de un precheck del comando configurado para Codex, para distinguir entre servidor sano y runner realmente ejecutable.
- La automatizacion usa Codex CLI como motor de ejecucion en lugar de integrar logica de negocio dentro del servidor MCP.
- El estado de sesiones se persiste en archivos JSON locales para mantener la base simple y sin base adicional.
- La continuacion de sesiones usa el identificador local de la sesion y, cuando se detecta, el `codex_session_id` observado en `~/.codex/sessions`.
- La configuracion operativa se resuelve desde variables de entorno y `.env`, sin secretos versionados.
- Si `AUTOMATION_STATE_DIR` o `AUTOMATION_LOG_DIR` estan vacios, el servidor usa los defaults `automation/.state` y `automation/logs`.

### Dominio y seguridad operativa

- El sistema no reemplaza el criterio profesional.
- No automatiza decisiones juridicas complejas.
- Los historicos sensibles son append-only.
- No se deben borrar historicos como solucion funcional.
- Las escrituras financieras se bloquean en procesos cerrados o archivados.

### Finance

- `FinancialInputVersion` representa dato fuente.
- `FinancialAssessment` representa decision operativa financiera.
- Finance fue el primer flujo de escritura fuera del admin.
- La UI visible de Finance se normalizo al espanol operativo.

## Convenciones

- Validar primero el estado real del repo antes de cambios grandes.
- Mantener superficie de cambio pequena y reversible.
- Documentar decisiones operativas nuevas en `docs/`.
- No introducir nuevos secretos en git.
- Preferir rutas locales explicitas en Windows para arranque operativo.
- Mantener la automatizacion como adaptador tecnico y no como nueva capa de dominio.
- Permitir configuracion por variables de entorno cuando el CLI local varie entre equipos.

## Descartes razonables

- No crear frontend para la automatizacion en esta fase.
- No crear API REST propia aparte del endpoint MCP.
- No introducir una cola externa, Redis o base de datos dedicada para la V1.
- No acoplar el servidor MCP a modelos Django ni a permisos del dominio mientras solo se necesite disparo de tareas de Codex.
- No asumir un contrato demasiado rigido del CLI de Codex; por eso la composicion de comandos queda parametrizable.
- No extender aun un sistema grande de roles globales.

## Inferencias marcadas

- Es razonable que una futura app MCP para ChatGPT consuma `start_eval_task`, `continue_eval_task` y `get_eval_task_status` como primera capa suficiente.
- Es razonable que una V2 reemplace el almacenamiento JSON por una persistencia mas robusta si se necesita resiliencia tras reinicios del servidor.
