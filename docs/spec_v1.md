# PokeCoach Technical Contract — `spec_v1`

## 1) Purpose and MVP Scope

`spec_v1` defines the canonical, implementation-ready contract for PokeCoach post-game reports.

MVP scope:
- Input: raw Pokémon TCG Live battle log text (`log_text`, Spanish-supported).
- Processing: deterministic tools + LLM orchestration.
- Output: strictly typed `PostGameReport` with evidence-backed claims.

Out of scope (v1):
- Full game-state reconstruction and visual replay.
- Perfect deck/prize inference.
- Strategy claims that depend on hidden information without explicit uncertainty.

---

## 2) Canonical Pydantic Model Contract

> Language rule: code identifiers in English.

### 2.1 `EvidenceSpan`

```python
class EvidenceSpan(BaseModel):
    start_line: int  # 1-indexed, inclusive
    end_line: int    # inclusive, must be >= start_line
    raw_lines: list[str]  # exact log slices used for this claim
```

Constraints:
- `start_line >= 1`
- `end_line >= start_line`
- `len(raw_lines) >= 1`
- `len(raw_lines) == (end_line - start_line + 1)` is recommended; if not exact, must be documented as partial extraction.

---

### 2.2 `TurningPoint`

```python
class TurningPoint(BaseModel):
    title: str
    impact: str  # concise explanation of why momentum changed
    confidence: float  # 0.0..1.0
    depends_on_hidden_info: bool
    evidence: EvidenceSpan
```

Constraints:
- `title.strip()` non-empty.
- `impact.strip()` non-empty.
- `0.0 <= confidence <= 1.0`.
- `evidence` is required (hard rule).

---

### 2.3 `Mistake`

```python
class Mistake(BaseModel):
    description: str
    why_it_matters: str
    better_line: str
    confidence: float  # 0.0..1.0
    depends_on_hidden_info: bool
    evidence: EvidenceSpan
```

Constraints:
- all string fields non-empty after strip.
- `0.0 <= confidence <= 1.0`.
- `evidence` is required (hard rule).

---

### 2.4 `PostGameReport`

```python
class PostGameReport(BaseModel):
    summary: list[str]                 # 5..8
    turning_points: list[TurningPoint] # 2..4
    mistakes: list[Mistake]            # 3..6
    unknowns: list[str]                # >=0
    next_actions: list[str]            # 3..5
```

Constraints:
- `5 <= len(summary) <= 8`
- `2 <= len(turning_points) <= 4`
- `3 <= len(mistakes) <= 6`
- `len(unknowns) >= 0`
- `3 <= len(next_actions) <= 5`
- all string list entries must be non-empty after strip.

---

### 2.5 Internal Helper Models (non-public but recommended)

```python
class TurnSpan(BaseModel):
    turn_number: int
    start_line: int
    end_line: int

class KeyEvent(BaseModel):
    event_type: str  # e.g., KO, PRIZE_TAKEN, ATTACK, SUPPORTER, STADIUM, CONCEDE
    line: int
    text: str

class KeyEventIndex(BaseModel):
    events: list[KeyEvent]

class TurnSummary(BaseModel):
    turn_number: int
    bullets: list[str]
    evidence: list[EvidenceSpan]

class MatchStats(BaseModel):
    went_first: str | None  # "self" | "opponent" | None
    mulligans_self: int | None
    mulligans_opponent: int | None
    observable_prizes_taken_self: int | None
    observable_prizes_taken_opponent: int | None
```

---

## 3) Hard Validation Rules

Machine-checkable rules (must be enforced in model validation and/or post-validation gate):

1. Cardinality:
   - `summary`: 5–8
   - `turning_points`: 2–4
   - `mistakes`: 3–6
   - `next_actions`: 3–5
2. `TurningPoint.evidence` required.
3. `Mistake.evidence` required.
4. Confidence bounds: `[0.0, 1.0]`.
5. Empty strings are invalid in all user-facing text fields.
6. Evidence line order and bounds must be valid (`start_line <= end_line`, both >=1).

If any hard rule fails, report generation is invalid and must not be returned as final.

---

## 4) Evidence Policy and Rejection Policy

Evidence policy:
- A claim is admissible only if linked to concrete `EvidenceSpan` from the source log.
- Evidence must be sufficient for human audit (line range + raw lines).

Rejection policy:
- If a potential `TurningPoint` or `Mistake` lacks evidence:
  - Do **not** emit it in that section.
  - Move reasoning to `unknowns` when uncertainty explains missing evidence.
  - Otherwise drop the claim.

Non-negotiable rule:
- No actionable claim without evidence.

---

## 5) Unknowns Policy

`unknowns` must explicitly capture limits from hidden information, including but not limited to:
- Opponent hand content not revealed.
- Prize cards not observed/revealed.
- Unrevealed opponent list/tech choices.
- Ambiguous board-state transitions due to noisy log lines.

When hidden information materially affects a claim, set:
- `depends_on_hidden_info = True`
- lower `confidence`
- add corresponding item in `unknowns`.

---

## 6) Confidence Policy

Range:
- `0.0` (purely speculative) to `1.0` (strongly supported by evidence).

Calibration guidance:
- `0.80–1.00`: directly observed event chain with minimal ambiguity.
- `0.55–0.79`: plausible interpretation with moderate ambiguity.
- `0.00–0.54`: high uncertainty; should usually be reframed into `unknowns`.

Must lower confidence when:
- hidden info could invert decision quality,
- multiple plausible interpretations exist,
- key lines are missing/fragmented.

---

## 7) Tool Contracts (Deterministic Layer)

### 7.1 `index_turns`

Signature:
```python
def index_turns(log_text: str) -> list[TurnSpan]
```
Guarantees:
- Returns turn-ordered spans.
- Spans are non-overlapping and within log bounds.
- If turn markers are noisy, returns best-effort spans + records ambiguity via RAW handling.

### 7.2 `find_key_events`

Signature:
```python
def find_key_events(log_text: str) -> KeyEventIndex
```
Guarantees:
- Extracts observable events: KO, prizes, concede, supporter usage, stadium changes, attacks.
- Preserves source `line` and `text` for each event.
- Unknown event formats do not crash extraction.

### 7.3 `extract_turn_summary`

Signature:
```python
def extract_turn_summary(turn_span: TurnSpan, log_text: str) -> TurnSummary
```
Guarantees:
- Produces concise per-turn bullet summary.
- Attaches at least one evidence element for major bullet claims.
- Best-effort behavior on partially parseable turns.

### 7.4 `compute_basic_stats`

Signature:
```python
def compute_basic_stats(log_text: str) -> MatchStats
```
Guarantees:
- Computes observable stats only (mulligans, who went first, observable prize progression).
- Uses `None` when not observable.
- Never fabricates missing values.

---

## 8) Fail-Open and RAW Preservation Rules

Fail-open behavior:
- Parsing errors in one segment must not invalidate the full report pipeline.
- Unparsed/ambiguous lines must be preserved as RAW artifacts for audit.

RAW rules:
- Keep original text unchanged in RAW storage.
- Preserve line numbers for every RAW block.
- RAW can inform `unknowns`, but not direct high-confidence claims.

---

## 9) Output Examples

### 9.1 Valid minimal example

```json
{
  "summary": [
    "You maintained early tempo and attached energy on curve.",
    "A turn-4 sequence shifted board control to the opponent.",
    "Prize race became unfavorable after a key KO.",
    "Supporter timing reduced your ability to stabilize.",
    "Endgame outs were limited by unknown prizes."
  ],
  "turning_points": [
    {
      "title": "Turn 4 momentum swing",
      "impact": "A KO plus prize claim shifted race pressure.",
      "confidence": 0.84,
      "depends_on_hidden_info": false,
      "evidence": {
        "start_line": 120,
        "end_line": 122,
        "raw_lines": [
          "Opponent used X attack...",
          "Your Active Pokémon was Knocked Out.",
          "Opponent took a Prize card."
        ]
      }
    },
    {
      "title": "Supporter sequencing window missed",
      "impact": "Resource access was delayed by one turn.",
      "confidence": 0.63,
      "depends_on_hidden_info": true,
      "evidence": {
        "start_line": 98,
        "end_line": 99,
        "raw_lines": [
          "You played Supporter A.",
          "No additional draw effect resolved."
        ]
      }
    }
  ],
  "mistakes": [
    {
      "description": "Delayed prize mapping before committing attacker.",
      "why_it_matters": "Reduced clarity on optimal trade plan.",
      "better_line": "Check revealed prizes and route damage for 2-turn race.",
      "confidence": 0.71,
      "depends_on_hidden_info": true,
      "evidence": {
        "start_line": 95,
        "end_line": 97,
        "raw_lines": [
          "You attached Energy to Bench Pokémon.",
          "You promoted Active Pokémon B.",
          "Opponent took lead in prize race."
        ]
      }
    },
    {
      "description": "Committed attack into unfavorable response window.",
      "why_it_matters": "Enabled a return KO with prize advantage.",
      "better_line": "Force a lower-value knockout and preserve key attacker.",
      "confidence": 0.82,
      "depends_on_hidden_info": false,
      "evidence": {
        "start_line": 118,
        "end_line": 122,
        "raw_lines": [
          "You attacked for 180 damage.",
          "Opponent evolved Active Pokémon.",
          "Opponent used X attack...",
          "Your Active Pokémon was Knocked Out.",
          "Opponent took a Prize card."
        ]
      }
    },
    {
      "description": "Used draw Supporter after committing board action.",
      "why_it_matters": "Lowered chance to find optimal pivot line in time.",
      "better_line": "Resolve draw/search first, then commit attacker.",
      "confidence": 0.66,
      "depends_on_hidden_info": false,
      "evidence": {
        "start_line": 88,
        "end_line": 90,
        "raw_lines": [
          "You benched Pokémon C.",
          "You played Supporter B.",
          "You drew 2 cards."
        ]
      }
    }
  ],
  "unknowns": [
    "Opponent hand composition was not fully revealed.",
    "Your remaining prize map was partially hidden."
  ],
  "next_actions": [
    "Practice turn-by-turn prize mapping before first major attack.",
    "Run 10 reps of supporter sequencing with pre-commit checklist.",
    "Review logs focusing on KO + prize swing turns only."
  ]
}
```

### 9.2 Invalid example (and why)

```json
{
  "summary": ["Only one bullet"],
  "turning_points": [
    {
      "title": "Speculative pivot",
      "impact": "Probably game-losing",
      "confidence": 1.2,
      "depends_on_hidden_info": true
    }
  ],
  "mistakes": [],
  "unknowns": [],
  "next_actions": ["Do better"]
}
```

Why invalid:
- `summary` cardinality < 5.
- `turning_points[0].confidence` out of range (>1.0).
- `turning_points[0].evidence` missing.
- `mistakes` cardinality < 3.
- `next_actions` cardinality < 3.

---

## 10) Step 2 Acceptance Criteria (Definition of Done)

Step 2 is complete only if:
1. `docs/spec_v1.md` exists and covers all required sections in this contract.
2. Public model contract is unambiguous and implementation-ready.
3. Hard rules are explicitly machine-checkable.
4. Evidence, unknowns, confidence, and fail-open policies are explicit and non-contradictory.
5. Tool IO signatures and guarantees are documented.
6. Valid + invalid output examples are present and consistent with validators.
7. OpenRouter configuration notes are present.

---

## 11) OpenRouter Configuration Notes (v1)

Inference provider for v1: OpenRouter.

Required environment variables (recommended):
- `OPENROUTER_API_KEY`: OpenRouter credential.
- `POKECOACH_MODEL`: model identifier (fully configurable, no hardcoded model in business logic).

Optional environment variables:
- `OPENROUTER_BASE_URL` (default: `https://openrouter.ai/api/v1`).
- `POKECOACH_TEMPERATURE` (optional tuning).

Contract rules:
- Provider/model selection must be configuration-driven.
- Parser/tool outputs remain deterministic regardless of model selection.
- If model call fails, pipeline should return explicit failure context and preserve intermediate evidence artifacts.

---

## Invariants Self-Check (Spec Compliance)

- Invariant A: No turning point without evidence -> enforced in §2.2, §3, §4.
- Invariant B: No mistake without evidence -> enforced in §2.3, §3, §4.
- Invariant C: Cardinalities fixed -> enforced in §2.4, §3.
- Invariant D: Unknown hidden info must be explicit -> enforced in §5.
- Invariant E: Confidence bounded and calibrated -> enforced in §2.2/§2.3, §6.
- Invariant F: Parse failures do not break report -> enforced in §8.
- Invariant G: OpenRouter is initial provider, model configurable -> enforced in §11.
