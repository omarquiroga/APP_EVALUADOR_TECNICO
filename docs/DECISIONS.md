# Decisions

## Decisiones confirmadas

### Arquitectura

- Django monolito modular.
- PostgreSQL como base principal.
- Django templates + HTMX para la UI operativa.
- Django Admin como canal de carga/edicion controlada.
- `review` como espacio de operacion fuera del admin solo donde el admin ya no basta.

### Alcance descartado

- No crear API separada.
- No migrar a SPA.
- No introducir React o Vue.
- No abrir edicion libre general fuera del admin.
- No extender aun un sistema grande de roles globales.

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

### Fase 2B de Finance

Decisiones cerradas e implementadas en este hilo:

- `used_in_consolidation` ya no es editable en el formulario.
- Al confirmar un nuevo assessment:
  - `status = confirmed`
  - `used_in_consolidation = True`
- Si existe assessment vigente anterior:
  - queda `obsolete`
  - queda con `used_in_consolidation = False`
  - el nuevo assessment lo referencia en `supersedes`
- `supersedes` apunta al vigente reemplazado, no al ultimo cualquiera.
- `reviewed_by` y `reviewed_at` se asignan siempre en ese flujo.

### Permisos finos

Primera capa de permisos finos aprobada e implementada solo en Finance dentro de `review`:

- lectura separada de escritura
- permiso especifico para registrar insumos
- permiso especifico para confirmar evaluaciones
- implementacion con permisos estandar de Django y checks directos en vistas

## Convenciones acordadas

- Validar primero el estado real del repo antes de cambios grandes.
- Plan corto antes de implementar cambios de alcance no trivial.
- Mantener superficie de cambio pequena.
- Reportar siempre validacion tecnica despues de cambios funcionales.
- Usar Playwright cuando se necesite validar UI real.

## Cosas descartadas y por que

- Sistema de roles grande en esta fase: descartado para no abrir complejidad transversal innecesaria.
- Apertura de otro modulo fuera del admin antes de cerrar Finance: descartado para evitar deriva.
- Cambios amplios de dominio: descartados salvo ajuste minimo imprescindible.

## Inferencias marcadas

- Es razonable consolidar grupos de Django para Finance sobre los permisos ya definidos, pero esa configuracion no quedo automatizada en el codigo actual.
