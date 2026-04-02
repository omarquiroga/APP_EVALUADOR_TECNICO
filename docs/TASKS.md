# Tasks

## Backlog actual

### Prioridad alta

- Definir el siguiente modulo fuera del admin despues de Finance.
- Decidir si la siguiente fase debe ser:
  - endurecimiento adicional de permisos
  - nuevo flujo controlado en `Documents`
  - nuevo flujo controlado en `RUP`

### Prioridad media

- Normalizar textos visibles fuera de Finance donde aun queden inconsistencias de espanol operativo o codificacion.
- Evaluar si conviene documentar un mapeo estable de grupos Django para Finance.
- Revisar si hace falta un documento corto de invariantes para otros modelos sensibles ademas de Finance.

### Prioridad baja

- Mejoras UX menores en `review` solo si aparecen fricciones reales en uso o validacion.

## Tareas abiertas confirmadas

- No existe todavia otro flujo de escritura fuera de Finance en `review`.
- No hay sistema global de permisos finos para todos los modulos.
- No hay API separada ni frontend SPA.

## Riesgos actuales

- Si se abre otro flujo sin repetir el patron de permisos, puede reintroducir dependencia de `login_required` como unico control.
- Todavia hay algunos templates con problemas de codificacion/acentos heredados.
- La configuracion de grupos por rol no esta persistida todavia como seed o comando; la base tecnica actual usa permisos estandar y tests.

## Proximos pasos sugeridos

### Recomendacion principal

Abrir el siguiente flujo controlado fuera del admin en un modulo menos sensible que `evaluation`.

Opciones recomendadas:

- `Documents`
- `RUP`

### Secuencia sugerida

1. elegir un solo modulo siguiente
2. hacer diagnostico corto del estado real
3. definir solo lectura o escritura controlada minima
4. replicar patron de:
   - contexto `process -> bidder -> modulo`
   - restricciones operativas
   - permisos minimos
   - tests

## Vacios pendientes de confirmacion

- Cual sera el siguiente modulo priorizado por negocio.
- Si conviene formalizar grupos Django persistentes desde ahora o mantener permisos directos por mas tiempo.
- Si se quiere una ronda dedicada de saneamiento de codificacion de templates antes de abrir otro flujo.
