# Project Context

## Arquitectura actual

Proyecto Django monolitico modular con PostgreSQL como base principal.

Patron de interfaz confirmado:

- Django Admin para carga y edicion controlada
- aplicacion `review` fuera del admin para operacion guiada
- templates server-rendered
- HTMX para bloques parciales y navegacion ligera

No existe API separada ni SPA. React y Vue fueron descartados para esta fase.

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

Validacion confirmada en este hilo:

- `manage.py check` OK
- `manage.py makemigrations --check --dry-run` OK
- `manage.py test` OK

## Modulos implementados

- `procurement`: contexto del proceso contractual
- `normative`: snapshots y binding normativo
- `rules`: definiciones/versiones de reglas
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
- no borrar historicos/versiones como flujo normal
- append-only en entidades sensibles/versionadas
- bloquear escritura en procesos `closed` o `archived`
- mantener cambios pequenos y bien validados

## Permisos actuales en Finance

Primera capa de permisos finos confirmada solo para Finance en `review`:

- lectura financiera:
  - `finance.view_financialinputversion`
  - `finance.view_financialassessment`
- registro de insumos:
  - lectura financiera
  - `finance.add_financialinputversion`
- confirmacion de evaluacion:
  - lectura financiera
  - `finance.add_financialassessment`

Inferencia marcada:

- A futuro, estos permisos pueden mapearse facilmente a grupos estables de operacion, pero en el estado actual la implementacion usa checks directos con permisos estandar de Django.
