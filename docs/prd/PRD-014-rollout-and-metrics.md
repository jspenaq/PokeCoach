# PRD-014 — Rollout & Metrics for Coach+Auditor

## Objetivo
Desplegar Coach+Auditor de forma incremental, midiendo calidad, latencia y costo por modelo.

## Fases

### Fase A — Shadow audit (sin bloquear)
- Ejecutar B en paralelo para recolectar `violations[]`.
- Retornar salida directa de A.
- Duración sugerida: 3–5 días.

### Fase B — One-iteration on fail (regla activa)
- Si B falla mínimo, A reescribe 1 vez con `patch_plan`.
- Retornar salida reescrita sin tercera pasada.
- Duración sugerida: 1–2 semanas.

### Fase C — Optimización por modelo
- Comparar modelos por:
  - pass@first_audit
  - rewrite_rate
  - violations_critical_rate
  - latency_total
  - cost_per_report

## KPIs principales
- `pass_first_audit_rate` (objetivo inicial >= 70%)
- `critical_violation_rate` (objetivo <= 5%)
- `rewrite_rate` (objetivo <= 35%)
- `p95_latency_ms_total` (objetivo definido por SLA)
- `cost_usd_per_report` (control presupuestal)

## Guardrails de latencia/costo
- Timeout por agente (A/B) configurado.
- Presupuesto máximo de requests por run.
- `max_rewrites=1` para evitar costo explosivo.
- Abort/return cuando se exceda presupuesto de tiempo.

## Plan de benchmark
- Dataset fijo (logs 7, 8, 9, 10 + casos adversariales).
- Correr mismos inputs para cada modelo.
- Registrar:
  - salida de A
  - resultado de B
  - necesidad de rewrite
  - salida final

## Eventos de observabilidad recomendados
- `coach_run_started`
- `coach_run_completed`
- `audit_run_completed`
- `audit_failed_quality_minimum`
- `rewrite_started`
- `rewrite_completed`
- `report_returned`

Campos mínimos por evento:
- `trace_id`, `run_id`, `model`, `stage`, `latency_ms`, `token_usage`, `violations_count`, `quality_minimum_pass`.

## Criterios de éxito de rollout
- Disminución sostenida de violaciones críticas.
- Estabilidad de formato (cardinalidades) > 98%.
- Mejora de utilidad percibida sin degradar factualidad.
