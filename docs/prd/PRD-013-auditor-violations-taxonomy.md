# PRD-013 — Auditor Violations Taxonomy (v1)

## Objetivo
Estandarizar códigos de violación del Auditor para medir calidad de forma consistente entre modelos.

## Estructura de violación
```json
{
  "code": "EVIDENCE_MISSING",
  "severity": "critical|major|minor",
  "field": "summary[2]",
  "message": "Claim sin evidencia verificable",
  "suggested_fix": "Reemplazar por claim candidato TP-03 o mover a unknowns"
}
```

## Catálogo de códigos

### Critical
- `HALLUCINATED_CARD`: carta inexistente en log.
- `HALLUCINATED_ACTION`: acción/evento inexistente en log.
- `EVIDENCE_MISSING`: claim factual sin evidencia ni unknown.
- `LANGUAGE_MISMATCH`: idioma incumple regla configurada.

### Major
- `FORMAT_CARDINALITY_SUMMARY`: summary fuera de 5–8.
- `FORMAT_CARDINALITY_ACTIONS`: next_actions fuera de 3–6.
- `EVIDENCE_SPAN_INVALID`: rangos inválidos o líneas fuera de log.
- `CANDIDATE_DRIFT`: picks no corresponden a candidatos deterministas.

### Minor
- `STYLE_VERBOSE`: bullets demasiado largos/no atómicos.
- `STYLE_REDUNDANT`: repeticiones fuertes entre bullets.
- `WORDING_AMBIGUOUS`: texto poco concreto pero no falso.

## Reglas de pass/fail
- `quality_minimum_pass = false` si existe >=1 `critical`.
- `quality_minimum_pass = false` si existe >=2 `major`.
- `quality_minimum_pass = true` con `minor` solamente.

## Patch plan (salida esperada)
```json
[
  {
    "target": "summary[2]",
    "action": "replace",
    "replacement_source": "turning_point_candidates[1]",
    "reason": "EVIDENCE_MISSING"
  }
]
```

## Ejemplos (log Pokémon)
1. Claim: “Kami-Yan topdeckeó Boss en turno final” sin línea de robo -> `EVIDENCE_MISSING`.
2. Claim menciona carta no presente (p.ej. Iono si no existe) -> `HALLUCINATED_CARD`.
3. Summary con 4 bullets -> `FORMAT_CARDINALITY_SUMMARY`.
4. Recomendación en inglés con modo español -> `LANGUAGE_MISMATCH`.
5. Pick de turning point no presente en candidatos -> `CANDIDATE_DRIFT`.

## Métricas derivadas
- `violations_total`
- `violations_critical_rate`
- `violations_by_code`
- `% runs with rewrite`
