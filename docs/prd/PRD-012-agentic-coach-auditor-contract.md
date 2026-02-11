# PRD-012 — Agentic Coach + Auditor Contract (v1)

## Problema
El flujo actual mezcla generación de narrativa con controles de calidad en una sola pasada, lo que dificulta separar:
- calidad de coaching,
- veracidad/evidencia,
- y causas exactas de fallos por modelo.

## Objetivo
Definir un contrato de dos agentes:
- **Agente A (Coach):** genera borrador útil, orientado a acción.
- **Agente B (Auditor Red Team):** valida factualidad, formato e idioma, y propone parches.

## No-objetivos (v1)
- No introducir loops ilimitados de reescritura.
- No bloquear la respuesta con fallback determinista por calidad.
- No cambiar parser/tools deterministas existentes.

## Flujo funcional
1. `coach_draft = AgentA(facts, candidates, evidence, format_rules)`
2. `audit = AgentB(coach_draft, log_text, candidates, format_rules)`
3. Si `quality_minimum_pass == true` → retornar `coach_draft`.
4. Si `quality_minimum_pass == false` → **1 iteración máxima**:
   - `coach_rewrite = AgentA(coach_draft, violations, patch_plan, facts, candidates)`
   - retornar `coach_rewrite` (sin nueva iteración).

## Regla de iteración (hard)
- `max_rewrites = 1`
- Si tras la reescritura persisten violaciones, se retorna igual la salida de A con metadatos de auditoría.

## Contrato de entrada/salida (tipado)

### Input para Agent A
- `match_facts` (determinista)
- `turning_point_candidates` (determinista)
- `mistake_candidates` (determinista)
- `evidence_map` (líneas/rangos válidos)
- `format_rules`:
  - summary: 5–8 bullets
  - next_actions: 3–6 bullets
  - idioma objetivo

### Output de Agent A (`DraftReport`)
- `summary: list[str]`
- `next_actions: list[str]`
- `turning_points_picks: list[str]` (ids o claves de candidatos elegidos)
- `mistakes_picks: list[str]`
- `unknowns: list[str]`

### Input para Agent B
- `draft_report: DraftReport`
- `log_text: str`
- `deterministic_candidates`
- `format_rules`

### Output de Agent B (`AuditResult`)
- `quality_minimum_pass: bool`
- `violations: list[Violation]`
- `patch_plan: list[PatchAction]`
- `audit_summary: str`

## Definición de quality_minimum (v1)
`quality_minimum_pass = true` solo si:
1. No hay violaciones `critical`.
2. `summary` cumple 5–8 bullets.
3. `next_actions` cumple 3–6 bullets.
4. No hay claims sin evidencia o sin `unknown` cuando aplique.
5. Idioma consistente con `format_rules.language`.

## Output al usuario
- Siempre retornar salida de A (original o reescrita una vez).
- Adjuntar metadatos internos opcionales:
  - `audit_status: pass|fail`
  - `violations_count`
  - `top_violations` (hasta 3)

## Telemetría interna
Por run almacenar:
- `model_name_a`, `model_name_b`
- `audit_pass_first_try`
- `rewrite_used`
- `violations_by_code`
- `latency_ms_a`, `latency_ms_b`, `latency_ms_total`
- `token_usage_a`, `token_usage_b`

## Criterios de aceptación
- Existe contrato escrito y versionado para Agent A/B.
- El flujo deja explícito `max_rewrites=1`.
- Se puede auditar por qué B rechazó una salida (violations + patch_plan).
