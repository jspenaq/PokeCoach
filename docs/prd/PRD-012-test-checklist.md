# PRD-012 — Supplemental Test Checklist (Coach+Auditor One-Iteration Flow)

## Scope
This checklist supplements `docs/prd/PRD-012-agentic-coach-auditor-contract.md` with concrete edge cases for the bounded flow:
- Initial draft by Coach (Agent A)
- Single audit by Auditor (Agent B)
- At most one rewrite (`max_rewrites=1`)
- Return rewritten output even if violations remain

## Expected Evaluation Rules
- `quality_minimum_pass=false` when any `critical` violation exists.
- `quality_minimum_pass=false` when 2 or more `major` violations exist.
- `quality_minimum_pass=true` with only `minor` violations.

## Edge Cases

### A) Evidence

| ID | Edge Case | Expected Violation Codes | Expected Rewrite Behavior (One Iteration) |
|---|---|---|---|
| E-01 | Summary claims a specific topdeck card that is not present in `log_text`. | `HALLUCINATED_CARD (critical)` | Replace claim with deterministic candidate evidence if available; otherwise rewrite as uncertainty and move detail to `unknowns`. |
| E-02 | Next action claims exact causal intent ("opponent conceded because they feared KO") but log only shows concede event. | `EVIDENCE_MISSING (critical)` | Remove unverifiable causality; rewrite to observable fact only (concede occurred) or explicit unknown. |
| E-03 | Draft includes evidence span lines outside log bounds for a factual bullet. | `EVIDENCE_SPAN_INVALID (major)` and optionally `EVIDENCE_MISSING (critical)` if claim has no valid support | Rebind bullet to valid line range from `evidence_map`; if no valid span exists, replace with supported candidate or unknown-safe wording. |

### B) Format Cardinality

| ID | Edge Case | Expected Violation Codes | Expected Rewrite Behavior (One Iteration) |
|---|---|---|---|
| F-01 | `summary` has 4 bullets (below minimum 5). | `FORMAT_CARDINALITY_SUMMARY (major)` | Add 1+ evidence-grounded bullets from deterministic candidates until 5–8 range is met. |
| F-02 | `next_actions` has 7 bullets (above maximum 6). | `FORMAT_CARDINALITY_ACTIONS (major)` | Merge or remove lowest-priority items, preserving evidence-backed actions, until 3–6 range is met. |
| F-03 | `summary` has 9 bullets and `next_actions` has 2 bullets in same draft. | `FORMAT_CARDINALITY_SUMMARY (major)`, `FORMAT_CARDINALITY_ACTIONS (major)` | In single rewrite, trim `summary` to <=8 and expand `next_actions` to >=3; expected first-audit fail due to 2 majors, rewrite should target both fields together. |

### C) Language Consistency

| ID | Edge Case | Expected Violation Codes | Expected Rewrite Behavior (One Iteration) |
|---|---|---|---|
| L-01 | `format_rules.language=es` and all bullets are in English. | `LANGUAGE_MISMATCH (critical)` | Rewrite all user-facing fields to Spanish while preserving factual meaning and candidate alignment. |
| L-02 | Mixed-language bullets (Spanish + English fragments) in `summary` and `next_actions`. | `LANGUAGE_MISMATCH (critical)` | Normalize all bullets to configured target language; keep identifiers and card names unchanged when needed. |
| L-03 | Body is Spanish but `unknowns` contains English explanatory sentences. | `LANGUAGE_MISMATCH (critical)` | Rewrite `unknowns` in target language with explicit uncertainty wording; no factual expansion allowed. |

### D) Hallucination

| ID | Edge Case | Expected Violation Codes | Expected Rewrite Behavior (One Iteration) |
|---|---|---|---|
| H-01 | Coach references a card not appearing anywhere in log/candidates (not a typo of existing card). | `HALLUCINATED_CARD (critical)` | Replace with valid deterministic candidate or remove claim; do not invent alternate cards. |
| H-02 | Coach states an action sequence absent from log (e.g., "used Boss, gusted benched target, KO") with no matching event chain. | `HALLUCINATED_ACTION (critical)` | Replace with observed action sequence from candidates/evidence; if absent, drop sequence and keep only verified facts. |
| H-03 | Coach picks turning point ID not in deterministic candidate list. | `CANDIDATE_DRIFT (major)` and may include `EVIDENCE_MISSING (critical)` if unsupported narrative is added | Rewrite `turning_points_picks` to valid candidate IDs and update linked narrative bullets to match selected candidates. |

### E) Orchestration Limits

| ID | Edge Case | Expected Violation Codes | Expected Rewrite Behavior (One Iteration) |
|---|---|---|---|
| O-01 | First audit finds 1 critical + 1 major violation in different fields. | Example: `EVIDENCE_MISSING (critical)`, `FORMAT_CARDINALITY_SUMMARY (major)` | Trigger exactly one rewrite pass that applies both fixes from `patch_plan`; no second rewrite even if one issue remains. |
| O-02 | Rewrite resolves critical issues but leaves 2 major issues unresolved. | Example remaining: `FORMAT_CARDINALITY_ACTIONS (major)`, `CANDIDATE_DRIFT (major)` | Return rewritten output with `audit_status=fail` metadata and persisted `violations_by_code`; do not run extra iteration. |
| O-03 | Rewrite introduces new critical issue while fixing originals (regression). | Example new: `HALLUCINATED_ACTION (critical)` | Return rewritten output as-is (bounded flow), include updated violation list/top violations; orchestration must enforce `max_rewrites=1` strictly. |

## Execution Notes
- For each case, test both:
  1. Auditor detection correctness (`violations[]`, severities, fields).
  2. Coach rewrite compliance with `patch_plan` under the one-iteration cap.
- Validate telemetry for each run:
  - `audit_pass_first_try`
  - `rewrite_used`
  - `violations_by_code`
  - `top_violations`
