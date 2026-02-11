# PydanticAI Implementation Notes: Multi-Agent Coach + Auditor

## Scope
This note defines a minimal, bounded multi-agent pattern for PokeCoach using PydanticAI:
- `CoachAgent`: produces structured coaching output from deterministic evidence.
- `AuditorAgent`: validates evidence linkage, unknowns, and policy constraints.
- One orchestration pass only (no open-ended self-reflection loop).

## 1. Typed Model I/O Patterns
Use strict Pydantic models at every boundary.

- Input model (to `CoachAgent`): include only deterministic parser outputs and metadata.
- Coach output model: structured recommendations + explicit `evidence_spans` + `unknowns`.
- Auditor input model: coach output + original deterministic facts/summaries.
- Auditor output model: `approved: bool`, `findings`, `severity`, `repair_instructions`.

Recommended pattern:
- `Agent[DepsType, OutputType]` with explicit `output_type`.
- Add `@agent.output_validator` to reject outputs missing evidence or with hidden assumptions.
- Use union output for controlled failure modes (e.g., `CoachReport | CoachFailure`).

## 2. Retry + One-Iteration Orchestration
Use retries locally, orchestration globally bounded.

- Agent-level retries: small (`retries=1..2`).
- Tool/output-validator `ModelRetry`: only for recoverable schema or evidence-link errors.
- Orchestration loop: exactly one auditor pass after coach pass.
- Optional one repair pass only if auditor returns actionable fix and retry budget remains.

Practical rule:
- Max passes = 2 total coach generations (`initial + one repair`).
- If still invalid, return deterministic fallback summary + explicit failure metadata.

## 3. Model Settings + Timeout Guidance
Keep settings conservative and predictable for post-game analysis.

- Prefer low temperature (`0.0-0.3`) for consistency.
- Set provider HTTP timeout explicitly (e.g., 20-30s).
- Use `UsageLimits` on each run:
  - `request_limit` to cap retries/tool churn.
  - `tool_calls_limit` to bound tool fan-out.
  - `response_tokens_limit` to prevent verbose drift.
- Use short message history or history processors to avoid context bloat.

Suggested starting envelope:
- `retries=1` (agent), selected tools `retries=1-2`.
- `UsageLimits(request_limit=4, tool_calls_limit=8, response_tokens_limit=<team cap>)`.
- Fail fast on timeout, do not re-enter orchestration automatically.

## 4. Failure Handling (No Infinite Loops)
Treat failures as terminal states with explicit status.

- Catch and classify:
  - `UnexpectedModelBehavior`
  - `UsageLimitExceeded`
  - provider timeout/network exceptions
- Never run unbounded `while` retry loops.
- Enforce hard counters in orchestrator (`max_coach_runs`, `max_audits`).
- On terminal failure:
  - emit deterministic fallback report,
  - include `failure_reason`,
  - include `attempt_counts`,
  - preserve captured run messages for audit/debug.

## 5. Suggested Tracing Fields for Audits
Persist per-run trace rows (or structured logs) with:

- `match_id`, `run_id`, `correlation_id`, `timestamp_utc`
- `agent_name` (`coach`/`auditor`), `agent_version`, `prompt_version`
- `model_name`, `provider`, `model_settings_hash`
- `usage`: input/output tokens, request count, tool call count
- `retry_counts`: agent/tool/output-validator
- `usage_limits` and which limit triggered (if any)
- `result_status`: `approved|repaired|failed|fallback`
- `evidence_coverage_ratio` (claims with evidence / total claims)
- `unknowns_count` and categories
- `failure_reason`, `exception_type`, `exception_message` (sanitized)
- `message_trace_ref` (pointer to stored `capture_run_messages` payload)

## 6. Minimal Pseudocode (Bounded Coach+Auditor)
```python
coach_result = run_coach(input_payload, retries=1, usage_limits=LIMITS)
if coach_result.failed:
    return deterministic_fallback("coach_failed", coach_result.meta)

audit_result = run_auditor(
    coach_output=coach_result.output,
    facts=input_payload.match_facts,
    retries=1,
    usage_limits=LIMITS,
)

if audit_result.approved:
    return finalize("approved", coach_result.output, trace=collect_trace())

if audit_result.can_repair and coach_result.repair_attempts == 0:
    repaired = run_coach(
        input_payload.with_repair_instructions(audit_result.repair_instructions),
        retries=1,
        usage_limits=LIMITS,
    )
    if repaired.succeeded:
        second_audit = run_auditor(repaired.output, input_payload.match_facts, retries=1, usage_limits=LIMITS)
        if second_audit.approved:
            return finalize("repaired", repaired.output, trace=collect_trace())

return deterministic_fallback("audit_not_approved", trace=collect_trace())
```

## 7. Mapping to Existing PokeCoach Constraints
- Preserve deterministic parser as source of truth.
- Require `EvidenceSpan` for all turning points/mistakes before approval.
- Force unknown/hidden information into explicit `unknowns`.
- Keep business logic provider-agnostic; provider/model via environment config.

## Context7 References
- PydanticAI agents, retries, usage limits, and error handling:
  - https://github.com/pydantic/pydantic-ai/blob/v1.0.5/docs/agents.md
- PydanticAI structured output and validators:
  - https://github.com/pydantic/pydantic-ai/blob/v1.0.5/docs/output.md
- PydanticAI multi-agent handoff patterns:
  - https://github.com/pydantic/pydantic-ai/blob/v1.0.5/docs/multi-agent-applications.md
- PydanticAI message history controls:
  - https://github.com/pydantic/pydantic-ai/blob/v1.0.5/docs/message-history.md
- Provider/model transport configuration example (custom HTTP client timeout):
  - https://github.com/pydantic/pydantic-ai/blob/v1.0.5/docs/models/openai.md
