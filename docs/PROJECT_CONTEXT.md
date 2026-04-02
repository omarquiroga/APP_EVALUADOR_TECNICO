# Project Context

## Arquitectura actual

Proyecto Django monolitico modular con PostgreSQL como base principal.

Patron de interfaz confirmado:

- Django Admin para carga y edicion controlada
- aplicacion `review` fuera del admin para operacion guiada
- templates server-rendered
- HTMX para bloques parciales y navegacion ligera

No existe API separada ni SPA. React y Vue fueron descartados para esta fase.

Adicion tecnica nueva en esta V1:

- carpeta `automation/` fuera del runtime Django
- servidor MCP Python minimo montado en `/mcp`
- `healthcheck` HTTP con diagnostico del comando de Codex
- autodeteccion del binario de Codex en `~/.codex/.sandbox-bin` cuando el alias por defecto de Windows no es invocable
- ejecucion de tareas mediante Codex CLI sobre el mismo workspace del repo
- estado local persistido en JSON para sesiones de automatizacion

## Estado funcional

Estado confirmado a la fecha de este documento:

- dominio principal modelado y migrado
- admin operativo y endurecido
- `review` operativo para navegacion por procesos, proponentes y expediente
- bloques HTMX implementados para documents, RUP, experience, validations, causals y consolidation
- Finance implementado como primer flujo fuera del admin:
  - overview
  - detalle de insumo
  - alta controlada de `FinancialInputVersion`
  - creacion y confirmacion controlada de `FinancialAssessment`
  - permisos finos iniciales por accion en Finance dentro de `review`
- `automation/` implementado como V1 minima para disparar y continuar tareas de Codex desde un futuro cliente MCP conectado a ChatGPT
- defaults operativos de automatizacion:
  - estado local en `automation/.state`
  - logs locales en `automation/logs`

## Modulos implementados

- `common`: utilidades y base comun del proyecto
- `procurement`: contexto del proceso contractual
- `normative`: snapshots y binding normativo
- `rules`: definiciones y versiones de reglas
- `bidders`: proponentes e integrantes
- `documents`: documentos, versiones y referencias
- `rup`: informacion RUP
- `experience`: experiencia y metricas
- `finance`: insumos y evaluaciones financieras
- `external_checks`: consultas externas
- `evaluation`: registros de decision de validacion
- `causals`: causales de rechazo
- `consolidation`: resultados consolidados
- `audit`: eventos auditables
- `review`: UI operativa fuera del admin

## Restricciones importantes

- revision humana obligatoria en puntos sensibles
- no automatizar decisiones juridicas complejas
- no borrar historicos o versiones como flujo normal
- append-only en entidades sensibles o versionadas
- bloquear escritura en procesos `closed` o `archived`
- mantener cambios pequenos y bien validados
- la automatizacion V1 no debe modificar el dominio por integracion directa; solo dispara trabajo a Codex CLI
- la automatizacion V1 depende de una instalacion local funcional de Codex CLI y de autenticacion local ya resuelta fuera del repo

## Arranque local de automatizacion en Windows

```powershell
Set-Location "C:\PROYECTOS\Evaluador Tecnico LFVU\automation"
Copy-Item .env.example .env -Force
C:\Python314\python.exe -m venv .\.venv
& '.\.venv\Scripts\python.exe' -m pip install -r .\requirements.txt
& '.\run.ps1'
```

Endpoint previsto para el futuro cliente MCP:

- local para pruebas del operador: `http://127.0.0.1:8765/mcp`
- para ChatGPT: URL publica HTTPS terminada en `/mcp`, por ejemplo `https://<subdominio-publico>/mcp`

Validacion operativa reciente:

- `run.ps1` levanta el servidor en `127.0.0.1:8765`
- `/health` responde OK y reporta si el comando local de Codex es ejecutable
- en este host concreto, el alias `codex` de `WindowsApps` responde `Acceso denegado.`, pero el binario funcional existe en `~/.codex/.sandbox-bin/codex.exe`
