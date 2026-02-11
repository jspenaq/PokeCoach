# PRD-015 — Coach+Auditor Integration with llm_provider

## Objetivo
Conectar el flujo Agentic Coach+Auditor con `llm_provider` real para que Agent A use guidance LLM y Agent B aplique validación de calidad mínima con una sola iteración de reescritura.

## Alcance inicial
- Agent A usa `maybe_generate_guidance(...)` como fuente primaria de `summary/next_actions`.
- Si Agent A no aporta guidance, usar salida determinista como draft inicial.
- Agent B audita cardinalidad, idioma y consistencia mínima con reglas PRD-013.
- Si falla mínimo: 1 rewrite máximo y retorno final.

## Entregables
1. Wiring estable en `report.py` mediante `run_one_iteration_coach_auditor`.
2. Telemetría opcional exportable en CLI (`--agentic-telemetry`).
3. Pruebas de integración para:
   - modo default (sin agentic)
   - modo agentic con auditor pass
   - modo agentic con auditor fail + rewrite.

## Riesgos
- Aumento de latencia por doble auditoría cuando hay rewrite.
- Variabilidad por proveedor/modelo en Agent A.

## Mitigación
- Mantener `max_rewrites=1`.
- Exponer telemetría para comparar modelos y ajustar thresholds.

## Criterio de cierre
- Flujo agentic activable por flag/env sin romper pipeline actual.
- Reporte final válido por schema en ambos modos.
