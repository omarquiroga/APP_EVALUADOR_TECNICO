# Invariantes Finance

## Roles de los modelos

- `FinancialInputVersion` representa el dato fuente financiero capturado para un `process + bidder`.
- `FinancialAssessment` representa la decision operativa financiera construida sobre un `FinancialInputVersion`.

## Reglas de versionado

- Ambos modelos son append-only.
- No se deben editar ni borrar historicos como mecanismo normal del flujo.
- Cada nueva version debe preservar trazabilidad por `version_no`, `created_at`, `created_by` y, cuando aplique, `supersedes`.

## Vigencia del assessment

- En el flujo controlado de `review`, un `FinancialAssessment` nuevo se crea directamente con `status = confirmed`.
- La vigencia es implicita en ese flujo: el nuevo assessment confirmado queda con `used_in_consolidation = True`.
- Solo puede existir un assessment vigente por proponente para consolidacion.

## Reemplazo y trazabilidad

- Si ya existe un assessment vigente para el mismo `process + bidder`, ese registro debe quedar:
  - `status = obsolete`
  - `used_in_consolidation = False`
- El nuevo assessment debe referenciar en `supersedes` exactamente al assessment vigente reemplazado, no al ultimo cualquiera.

## Revision humana

- El flujo controlado debe asignar siempre `reviewed_by`.
- El flujo controlado debe asignar siempre `reviewed_at`.
- `human_required` debe mantenerse como verdadero en este flujo.

## Restricciones operativas

- No se permiten escrituras financieras en procesos `closed` o `archived`.
- El assessment solo puede confirmarse sobre un insumo financiero en estado `submitted` (`radicado`).
- El contexto siempre es `process -> bidder -> finance`; no se deben seleccionar insumos fuera de ese contexto.
