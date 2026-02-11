# ROADMAP — PokeCoach

## North Star
Construir un coach post-game para Pokémon TCG Live que entregue reportes accionables **sin inventar**: todo claim importante debe tener evidencia de líneas del log.

## Estado actual (2026-02-10)
- ✅ Fase 0 completada.
- ✅ Fase 1 completada.
- ✅ Fase 2 completada (incluye hardening de eventos compuestos + golden minimum tests).
- ✅ Fase 3 completada para MVP (report pipeline + guardrails evidence/confidence/cardinality).
- ✅ Fase 4 completada (CLI `run_report.py` + JSON/Markdown + `--output` + `--deterministic-only` + tests + docs).
- ✅ Fase 5 completada en bloque principal (golden baselines, architecture contracts, checklist y KPI checker determinista).
- ⏳ Fase 6 pendiente (observabilidad opcional).
- 🔄 Sprint de iteración de output en curso (post-Fase 5):
  - PRD-002 Actor & Phase Filtering (cerrado)
  - PRD-003 KO Attribution Lookback (cerrado)
  - PRD-004 Claim Integrity Gate (cerrado)
  - PRD-005 Play Bundles (cerrado)
  - PRD-006 Turning Points by Impact Score (cerrado, pendiente refinamiento de swing neto)
  - PRD-007 Output Language Consistency (cerrado)
  - PRD-008 Summary Fact-Only Claims (cerrado)

## Principios no negociables
- **Evidence or it didn’t happen**.
- **Unknowns first-class** (mano/prizes/revelaciones incompletas).
- **Fail-open**: si algo no parsea, conservar RAW.
- **Output tipado y estable** con Pydantic.
- **Proveedor inicial de inferencia:** **OpenRouter**.

---

## Fase 0 — Foundations (ahora)
**Objetivo:** dejar base técnica y de gobierno para construir rápido sin deuda tóxica.

### Entregables
- Dependencias base: `pydantic` + `pydantic-ai`.
- PoC de salida estructurada (`PoCReport`) con modo mock y modo real.
- Blindaje del repo:
  - `Idea_inicial.md` ignorado.
  - `logs_prueba/` ignorado.
- Definición operativa: Codex implementa, Bigotes orquesta.

### DoD
- PoC corre en local sin API key (fallback mock).
- PoC soporta ejecución real con OpenRouter vía variables de entorno.

---

## Fase 1 — Contrato de Dominio (spec-first)
**Objetivo:** fijar contrato antes de parser/agent para evitar drift.

### Entregables
- `docs/spec_v1.md` con modelos:
  - `PostGameReport`
  - `TurningPoint`
  - `Mistake`
  - `EvidenceSpan`
  - (opcionales internos) `TurnSpan`, `KeyEventIndex`, `MatchStats`
- Reglas de validación:
  - `TurningPoint`/`Mistake` sin `EvidenceSpan` => inválido.
  - claims no verificables => `unknowns`.
  - límites de cardinalidad (5–8 summary, etc.).

### DoD
- Se puede validar un JSON de salida automáticamente contra schema.
- Reglas anti-alucinación documentadas y testeables.

---

## Fase 2 — Parser determinista v1 (tools)
**Objetivo:** extraer estructura confiable del log.

### Entregables
- `index_turns(log_text) -> list[TurnSpan]`
- `find_key_events(log_text) -> KeyEventIndex`
- `extract_turn_summary(turn_span) -> TurnSummary`
- `compute_basic_stats(log_text) -> MatchStats`
- Conservación de segmentos no parseados como RAW.

### DoD
- Corre sobre set inicial de logs sin romper.
- Cobertura de eventos clave mínima aceptable (baseline definida en evaluación).

---

## Fase 3 — Orquestación con PydanticAI (OpenRouter)
**Objetivo:** componer herramientas + LLM en reporte final auditable.

### Entregables
- Agente que use outputs deterministas para construir `PostGameReport`.
- Instrucciones de sistema orientadas a evidencia (no inventar).
- Campo de confianza para recomendaciones.
- Manejo explícito de incertidumbre.

### OpenRouter (v1)
- Variable de proveedor/modelo por entorno.
- Modelo inicial configurable (sin hardcode irreversible).
- Documentación de configuración local.

### DoD
- Reportes estables y válidos por schema.
- Cero claims accionables sin evidencia.

---

## Fase 4 — CLI y DX mínima
**Objetivo:** entregar flujo de uso real.

### Entregables
- CLI: `python run_report.py <match_log.txt>`
- Salida JSON (canónica) + opción markdown legible.
- Mensajes de error claros cuando falte contexto.

### DoD
- Usuario puede correr end-to-end con 1 comando.

---

## Fase 5 — Evaluación y guardrails de calidad
**Objetivo:** medir utilidad y reducir regresiones.

### Entregables
- Dataset de 10–20 logs de prueba (fuera de git si contienen ruido sensible).
- Golden outputs parciales para validación manual/automática.
- Métricas:
  - Hallucination rate (objetivo ~0%).
  - Evidence coverage.
  - Turning point precision.
  - Usefulness score (manual).

### DoD
- Checklist de release con métricas mínimas.
- No merge si rompe contrato de evidencia.

---

## Fase 6 — Observabilidad (opcional temprana, recomendada)
**Objetivo:** poder depurar rápido iteraciones de modelo/tools.

### Entregables
- Trazas de pipeline (Langfuse).
- Logs estructurados/spans por etapa (Logfire).
- Señales de alerta: caída de cobertura, aumento de unknowns, latencia.

---

## Riesgos y mitigaciones
- **Variaciones de formato/idioma del log** → parser tolerante + RAW fallback.
- **Ambigüedad de entidades** → no inferir sin evidencia, elevar a unknowns.
- **Sobreconfianza del agente** → confidence acotada y dependiente de info observable.
- **Drift por cambios de modelo** → pruebas de regresión con golden outputs.

---

## KPIs de cierre (release gate)
- Hallucination rate (claims accionables sin evidencia): **0.0%** objetivo.
- Evidence coverage (TurningPoint + Mistake con evidencia válida): **100%** obligatorio.
- CI quality gate: **ruff + pytest en verde** en push/PR a `main`.
- Cobertura de tests (objetivo inicial): **>=85%** en `src/pokecoach/`.
- Golden stability: **100%** del set `tests/golden/expected_minimums.json` en verde.

## Backlog inmediato (siguiente sprint)
1. Corregir scoring de swing neto en turning points (delta real actor-oponente en premios por bundle).
2. Consolidar `play_bundles` en unidades compuestas reales por turno/ventana (eliminar duplicación de micro-eventos).
3. Mejorar evidencia de `window.raw_lines` con líneas reales reproducibles (no placeholders de ventana).
4. Añadir medición automática de coverage en CI (umbral >=85%).
5. Evaluar Fase 6 (Langfuse/Logfire) según costo-beneficio.
6. PRD-012: Contrato Agentic Coach + Auditor (quality minimum + 1 iteración máxima).
7. PRD-013: Taxonomía de violaciones del Auditor (severidades, thresholds y patch_plan).
8. PRD-014: Rollout y métricas (latencia/costo/calidad por modelo).
9. Prompt 002 del Auditor Red Team con pruebas adversariales.
10. PRD-015: integración de Coach+Auditor con `llm_provider` real y flag de telemetría.
11. TODO: definir política de fallback de Agent A para errores técnicos (404/timeout/conexión).

---

## Decisiones vigentes
- Nombre del producto: **PokeCoach**.
- Proveedor inicial: **OpenRouter**.
- Estrategia: **spec-first + tools deterministas + agent orchestration**.
- Política de verdad: **evidencia obligatoria por claim crítico**.
