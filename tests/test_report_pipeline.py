import re
from pathlib import Path

import pytest

from pokecoach import report as report_module
from pokecoach.llm_provider import LLMReportGuidance, PydanticAIRuntimeConfig
from pokecoach.report import generate_post_game_report
from pokecoach.schemas import AuditResult, DraftReport, EvidenceSpan, Mistake, PlayBundle, PlayBundleEvent, TurningPoint
from pokecoach.tools import extract_play_bundles, extract_turn_summary, index_turns

ENGLISH_MARKERS_RE = re.compile(
    r"\b("
    r"observed|knockout|attack|turns? in the log|impact score|bonus|review|practice|rehearse|"
    r"momentum|unknown hidden information"
    r")\b",
    re.IGNORECASE,
)


def test_extract_turn_summary_returns_bullets() -> None:
    path = Path("logs_prueba/battle_logs_ptcgl_spanish.txt")
    content = path.read_text(encoding="utf-8")
    turns = index_turns(content)

    summary = extract_turn_summary(turns[0], content)
    assert summary.turn_number == 1
    assert summary.bullets


def test_generate_post_game_report_contract() -> None:
    path = Path("logs_prueba/battle_logs_ptcgl_spanish_con_ids_1.txt")
    content = path.read_text(encoding="utf-8")

    report = generate_post_game_report(content)

    assert 5 <= len(report.summary) <= 8
    assert 2 <= len(report.turning_points) <= 4
    assert 3 <= len(report.mistakes) <= 6
    assert 3 <= len(report.next_actions) <= 5
    assert all(tp.evidence.raw_lines for tp in report.turning_points)
    assert all(ms.evidence.raw_lines for ms in report.mistakes)


def test_generate_post_game_report_uses_deterministic_fallback_when_llm_unavailable(monkeypatch) -> None:
    path = Path("logs_prueba/battle_logs_ptcgl_spanish_con_ids_1.txt")
    content = path.read_text(encoding="utf-8")

    monkeypatch.setattr(report_module, "maybe_generate_guidance", lambda **_kwargs: None)
    report = generate_post_game_report(content)

    assert report.summary
    assert report.next_actions
    assert all(tp.evidence.raw_lines for tp in report.turning_points)
    assert all(ms.evidence.raw_lines for ms in report.mistakes)


@pytest.mark.parametrize(
    "fixture_path",
    [
        Path("logs_prueba/battle_logs_ptcgl_spanish_con_ids_1.txt"),
        Path("logs_prueba/battle_logs_ptcgl_spanish_con_ids_2.txt"),
    ],
)
def test_match_facts_and_summary_have_zero_discrepancies_for_deterministic_fixtures(
    monkeypatch, fixture_path: Path
) -> None:
    monkeypatch.setattr(report_module, "maybe_generate_guidance", lambda **_kwargs: None)
    report = generate_post_game_report(fixture_path.read_text(encoding="utf-8"))

    first_turn_line = next((item for item in report.summary if item.endswith("tomó el primer turno.")), None)
    if report.match_facts.went_first_player:
        assert first_turn_line is not None
        assert first_turn_line.startswith(report.match_facts.went_first_player)
    else:
        assert first_turn_line is None

    summary_ko_line = next(item for item in report.summary if item.endswith("Fuera de Combate."))
    summary_prize_line = next(item for item in report.summary if item.endswith("cartas de Premio visibles tomadas."))
    summary_turns_line = next(item for item in report.summary if item.endswith("turnos en el registro."))

    summary_ko_match = re.search(r"\d+", summary_ko_line)
    summary_prize_match = re.search(r"\d+", summary_prize_line)
    summary_turns_match = re.search(r"\d+", summary_turns_line)

    assert summary_ko_match is not None
    assert summary_prize_match is not None
    assert summary_turns_match is not None

    summary_ko_count = int(summary_ko_match.group())
    summary_prize_count = int(summary_prize_match.group())
    summary_turns_count = int(summary_turns_match.group())

    assert summary_ko_count == sum(report.match_facts.kos_by_player.values())
    assert summary_prize_count == sum(report.match_facts.observable_prizes_taken_by_player.values())
    assert summary_turns_count == report.match_facts.turns_count


def test_summary_integrity_rewrites_unverifiable_ko_actor_claim_for_log7(monkeypatch) -> None:
    path = Path("logs_prueba/battle_logs_ptcgl_spanish_con_ids_7.txt")
    content = path.read_text(encoding="utf-8")
    monkeypatch.setattr(
        report_module,
        "maybe_generate_guidance",
        lambda **_kwargs: LLMReportGuidance(
            summary=[
                "Mega-Lopunny ex KO Latias ex.",
                "Tempo shifted after that exchange.",
                "Prize pressure increased.",
                "Unknown hidden info remains relevant.",
                "Late game sequencing was decisive.",
            ],
            next_actions=[
                "Review sequencing.",
                "Track prizes.",
                "Plan retreat lines.",
            ],
        ),
    )

    report = generate_post_game_report(content)

    assert all("lopunny ex ko latias ex" not in item.lower() for item in report.summary)
    assert "Fuera de Combate observado: Latias ex quedó Fuera de Combate." in report.summary


def test_summary_integrity_moves_unverifiable_ko_claim_to_unknowns(monkeypatch) -> None:
    path = Path("logs_prueba/battle_logs_ptcgl_spanish_con_ids_1.txt")
    log_text = path.read_text(encoding="utf-8")
    monkeypatch.setattr(
        report_module,
        "maybe_generate_guidance",
        lambda **_kwargs: LLMReportGuidance(
            summary=[
                "Mega-Lopunny ex KO MissingTarget ex.",
                "Tempo was contested.",
                "Prize race mattered.",
                "Opening setup was uneven.",
                "Unknown hand info affected options.",
            ],
            next_actions=[
                "Review opening hands.",
                "Track known resources.",
                "Practice sequencing.",
            ],
        ),
    )

    report = generate_post_game_report(log_text)

    assert all("mega-lopunny ex ko missingtarget ex" not in item.lower() for item in report.summary)
    assert any(
        item.startswith("Afirmación de KO no verificable omitida del resumen: Mega-Lopunny ex KO MissingTarget ex.")
        for item in report.unknowns
    )


def test_spanish_language_gate_prevents_mixed_output_for_spanish_log(monkeypatch) -> None:
    log_text = Path("logs_prueba/battle_logs_ptcgl_spanish_con_ids_1.txt").read_text(encoding="utf-8")

    monkeypatch.setattr(
        report_module,
        "_build_turning_points",
        lambda _log, _spanish_mode: [
            TurningPoint(
                title="TP1",
                impact="Impact score 120: deterministic event impact weight.",
                confidence=0.8,
                depends_on_hidden_info=False,
                evidence=EvidenceSpan(start_line=1, end_line=1, raw_lines=["Turno de [playerName]"]),
            ),
            TurningPoint(
                title="TP2",
                impact="Impact score 90: deterministic event impact weight.",
                confidence=0.8,
                depends_on_hidden_info=False,
                evidence=EvidenceSpan(start_line=2, end_line=2, raw_lines=["Jugador usó Ataque."]),
            ),
        ],
    )
    monkeypatch.setattr(
        report_module,
        "_build_mistakes",
        lambda _log, _spanish_mode: [
            Mistake(
                description="Review decision around attack event.",
                why_it_matters="This sequence affected board pressure and prize race.",
                better_line="Re-evaluate sequencing before committing major actions.",
                confidence=0.8,
                depends_on_hidden_info=False,
                evidence=EvidenceSpan(start_line=1, end_line=1, raw_lines=["Turno de [playerName]"]),
            ),
            Mistake(
                description="Review decision around supporter event.",
                why_it_matters="This sequence affected board pressure and prize race.",
                better_line="Re-evaluate sequencing before committing major actions.",
                confidence=0.8,
                depends_on_hidden_info=False,
                evidence=EvidenceSpan(start_line=2, end_line=2, raw_lines=["Jugador jugó un Partidario."]),
            ),
            Mistake(
                description="Review early setup sequencing.",
                why_it_matters="Early sequencing influences later tempo windows.",
                better_line="Run pre-attack sequencing checklist.",
                confidence=0.8,
                depends_on_hidden_info=False,
                evidence=EvidenceSpan(start_line=3, end_line=3, raw_lines=["Jugador usó Ataque."]),
            ),
        ],
    )
    monkeypatch.setattr(
        report_module,
        "maybe_generate_guidance",
        lambda **_kwargs: LLMReportGuidance(
            summary=[
                "Observed 4 attack events in the log.",
                "Observed 2 knockout events.",
                "Momentum swings were driven by attack-to-KO sequences.",
                "Unknown hidden information may change optimal lines.",
                "Observed 8 turns in the log.",
            ],
            next_actions=[
                "Practice prize mapping before each high-impact attack.",
                "Review supporter sequencing on turns with tempo swings.",
                "Rehearse a pre-commit checklist for attack and retreat decisions.",
            ],
        ),
    )

    report = generate_post_game_report(log_text)

    assert all(ENGLISH_MARKERS_RE.search(item) is None for item in report.summary)
    assert all(ENGLISH_MARKERS_RE.search(item) is None for item in report.next_actions)
    assert all(ENGLISH_MARKERS_RE.search(tp.impact) is None for tp in report.turning_points)
    assert all(ENGLISH_MARKERS_RE.search(ms.description) is None for ms in report.mistakes)
    assert all(ENGLISH_MARKERS_RE.search(ms.why_it_matters) is None for ms in report.mistakes)
    assert all(ENGLISH_MARKERS_RE.search(ms.better_line) is None for ms in report.mistakes)


def test_turning_points_rank_by_impact_score_not_order(monkeypatch) -> None:
    log_text = "\n".join(
        [
            "Turno de [playerName]",
            "Alice usó Golpe Ligero.",
            "¡El (sv1_25) Pikachu de Bob quedó Fuera de Combate!",
            "Alice tomó una carta de Premio.",
            "Turno de [playerName]",
            "Bob usó Ataque Final.",
            "¡El (sv8_220) Latias ex de Alice quedó Fuera de Combate!",
            "Bob tomó 2 cartas de Premio.",
        ]
    )
    monkeypatch.setattr(report_module, "maybe_generate_guidance", lambda **_kwargs: None)

    report = generate_post_game_report(log_text)

    assert "Latias ex" in " ".join(report.turning_points[0].evidence.raw_lines)
    assert "tomó 2 cartas de Premio." in " ".join(report.turning_points[0].evidence.raw_lines)


def _bundle_event(line: int, text: str) -> PlayBundleEvent:
    return PlayBundleEvent(
        line=line,
        text=text,
        evidence=EvidenceSpan(start_line=line, end_line=line, raw_lines=[text]),
    )


def test_bundle_turning_point_prize_trade_1_to_1_has_no_two_prize_swing_bonus() -> None:
    ko_text = "¡El (sv1_25) Pikachu de Bob quedó Fuera de Combate!"
    bundle = PlayBundle(
        turn_number=1,
        actor="Alice",
        window=EvidenceSpan(start_line=1, end_line=4, raw_lines=[ko_text]),
        ko_events=[_bundle_event(2, ko_text)],
        prize_events=[
            _bundle_event(3, "Alice tomó una carta de Premio."),
            _bundle_event(4, "Bob tomó una carta de Premio."),
        ],
    )

    candidate = report_module._build_bundle_turning_point(bundle, spanish_mode=True)

    assert candidate is not None
    score, _, turning_point = candidate
    assert score == report_module.IMPACT_KO_BASE
    assert "Bono por swing de 2 Premios" not in turning_point.impact


def test_bundle_turning_point_true_two_prize_swing_gets_bonus() -> None:
    ko_text = "¡El (sv8_220) Latias ex de Bob quedó Fuera de Combate!"
    bundle = PlayBundle(
        turn_number=1,
        actor="Alice",
        window=EvidenceSpan(start_line=1, end_line=3, raw_lines=[ko_text]),
        ko_events=[_bundle_event(2, ko_text)],
        prize_events=[_bundle_event(3, "Alice tomó 2 cartas de Premio.")],
    )

    candidate = report_module._build_bundle_turning_point(bundle, spanish_mode=True)

    assert candidate is not None
    score, _, turning_point = candidate
    assert score == (
        report_module.IMPACT_KO_BASE
        + report_module.IMPACT_TWO_PRIZE_SWING_BONUS
        + report_module.IMPACT_HIGH_IMPACT_TARGET_BONUS
    )
    assert "Bono por swing de 2 Premios" in turning_point.impact


def test_log7_kirlia_trade_bundle_has_no_two_prize_swing_bonus() -> None:
    log_text = Path("logs_prueba/battle_logs_ptcgl_spanish_con_ids_7.txt").read_text(encoding="utf-8")
    bundles = extract_play_bundles(log_text)
    kirlia_trade_bundle = next(
        (
            bundle
            for bundle in bundles
            if bundle.actor == "Kami-Yan"
            and any("Kirlia de SpicyTaco30" in event.text for event in bundle.ko_events)
            and any("Dusknoir de Kami-Yan" in event.text for event in bundle.ko_events)
            and any(event.text.startswith("SpicyTaco30 tomó una carta de Premio.") for event in bundle.prize_events)
            and any(event.text.startswith("Kami-Yan tomó una carta de Premio.") for event in bundle.prize_events)
        ),
        None,
    )

    assert kirlia_trade_bundle is not None
    candidate = report_module._build_bundle_turning_point(kirlia_trade_bundle, spanish_mode=True)
    assert candidate is not None
    score, _, turning_point = candidate
    assert score == report_module.IMPACT_KO_BASE
    assert "Bono por swing de 2 Premios" not in turning_point.impact


def test_turning_points_log7_include_required_two_prize_ko_targets(monkeypatch) -> None:
    log_text = Path("logs_prueba/battle_logs_ptcgl_spanish_con_ids_7.txt").read_text(encoding="utf-8")
    monkeypatch.setattr(report_module, "maybe_generate_guidance", lambda **_kwargs: None)

    report = generate_post_game_report(log_text)

    assert any(
        "Latias ex" in " ".join(tp.evidence.raw_lines) and "tomó 2 cartas de Premio." in " ".join(tp.evidence.raw_lines)
        for tp in report.turning_points
    )
    assert any(
        "Fezandipiti ex" in " ".join(tp.evidence.raw_lines)
        and "tomó 2 cartas de Premio." in " ".join(tp.evidence.raw_lines)
        for tp in report.turning_points
    )


def test_turning_points_include_endgame_concede_when_present(monkeypatch) -> None:
    log_text = Path("logs_prueba/battle_logs_ptcgl_spanish_con_ids_7.txt").read_text(encoding="utf-8")
    monkeypatch.setattr(report_module, "maybe_generate_guidance", lambda **_kwargs: None)

    report = generate_post_game_report(log_text)

    assert any(tp.title == "Concede closes endgame" for tp in report.turning_points)


def test_summary_fact_only_for_log7_includes_colagrito_latias_two_prize(monkeypatch) -> None:
    log_text = Path("logs_prueba/battle_logs_ptcgl_spanish_con_ids_7.txt").read_text(encoding="utf-8")
    monkeypatch.setattr(report_module, "maybe_generate_guidance", lambda **_kwargs: None)

    report = generate_post_game_report(log_text)
    combined = "\n".join(report.summary)

    assert "Colagrito de SpicyTaco30 noqueó a Latias ex y tomó 2 cartas de Premio." in combined


def test_summary_for_log7_omits_interpretive_spin(monkeypatch) -> None:
    log_text = Path("logs_prueba/battle_logs_ptcgl_spanish_con_ids_7.txt").read_text(encoding="utf-8")
    monkeypatch.setattr(report_module, "maybe_generate_guidance", lambda **_kwargs: None)

    report = generate_post_game_report(log_text)
    combined = " ".join(report.summary).lower()

    assert "presión" not in combined
    assert "ritmo" not in combined
    assert "momentum" not in combined


def test_agentic_first_pass_includes_raw_outputs(monkeypatch) -> None:
    log_text = Path("logs_prueba/battle_logs_ptcgl_spanish_con_ids_1.txt").read_text(encoding="utf-8")
    monkeypatch.setenv("POKECOACH_AGENTIC_COACH_AUDITOR", "1")
    monkeypatch.setenv("POKECOACH_INCLUDE_AGENTIC_TELEMETRY", "1")

    monkeypatch.setattr(
        report_module,
        "load_runtime_config",
        lambda: PydanticAIRuntimeConfig(
            openrouter_api_key="k",
            openrouter_base_url="https://openrouter.ai/api/v1",
            model="baseline/model",
        ),
    )
    monkeypatch.setattr(
        report_module,
        "maybe_generate_guidance_with_raw",
        lambda **_kwargs: (
            LLMReportGuidance(
                summary=[f"s{i}" for i in range(1, 6)],
                next_actions=["a1", "a2", "a3"],
            ),
            '{"summary":["s1"],"next_actions":["a1"]}',
        ),
    )
    monkeypatch.setattr(
        report_module,
        "maybe_generate_audit_result_with_raw",
        lambda **_kwargs: (
            AuditResult(quality_minimum_pass=True, violations=[], patch_plan=[], audit_summary="ok"),
            '{"quality_minimum_pass":true,"violations":[]}',
        ),
    )

    report = generate_post_game_report(log_text)

    assert report.agentic_telemetry is not None
    assert report.agentic_telemetry["agent_a_raw_output"] is not None
    assert report.agentic_telemetry["agent_b_raw_output_first"] is not None


def test_agentic_rewrite_path_includes_second_auditor_raw_output(monkeypatch) -> None:
    log_text = Path("logs_prueba/battle_logs_ptcgl_spanish_con_ids_1.txt").read_text(encoding="utf-8")
    monkeypatch.setenv("POKECOACH_AGENTIC_COACH_AUDITOR", "1")
    monkeypatch.setenv("POKECOACH_INCLUDE_AGENTIC_TELEMETRY", "1")

    monkeypatch.setattr(
        report_module,
        "load_runtime_config",
        lambda: PydanticAIRuntimeConfig(
            openrouter_api_key="k",
            openrouter_base_url="https://openrouter.ai/api/v1",
            model="baseline/model",
        ),
    )
    monkeypatch.setattr(
        report_module,
        "maybe_generate_guidance_with_raw",
        lambda **_kwargs: (
            LLMReportGuidance(
                summary=[f"s{i}" for i in range(1, 6)],
                next_actions=["a1", "a2", "a3"],
            ),
            '{"summary":["s1","s2","s3","s4","s5"],"next_actions":["a1","a2","a3"]}',
        ),
    )

    calls = {"n": 0}

    def fake_auditor(**_kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            return (
                AuditResult(
                    quality_minimum_pass=False,
                    violations=[
                        {
                            "code": "FORMAT_CARDINALITY_SUMMARY",
                            "severity": "major",
                            "field": "summary",
                            "message": "bad",
                            "suggested_fix": "fix",
                        },
                        {
                            "code": "FORMAT_CARDINALITY_ACTIONS",
                            "severity": "major",
                            "field": "next_actions",
                            "message": "bad",
                            "suggested_fix": "fix",
                        },
                    ],
                    patch_plan=[],
                    audit_summary="fail",
                ),
                "first-audit-raw",
            )
        return (
            AuditResult(quality_minimum_pass=True, violations=[], patch_plan=[], audit_summary="ok"),
            "second-audit-raw",
        )

    monkeypatch.setattr(report_module, "maybe_generate_audit_result_with_raw", fake_auditor)
    monkeypatch.setattr(
        report_module,
        "run_openrouter_structured_json",
        lambda **_kwargs: (
            DraftReport(
                summary=[f"s{i}" for i in range(1, 6)],
                next_actions=["a1", "a2", "a3"],
                unknowns=[],
            ),
            "agent-a-rewrite-raw",
        ),
    )

    report = generate_post_game_report(log_text)

    assert report.agentic_telemetry is not None
    assert report.agentic_telemetry["agent_b_raw_output_first"] == "first-audit-raw"
    assert report.agentic_telemetry["agent_b_raw_output_second"] == "second-audit-raw"


def test_agentic_uses_model_env_vars(monkeypatch) -> None:
    log_text = Path("logs_prueba/battle_logs_ptcgl_spanish_con_ids_1.txt").read_text(encoding="utf-8")
    monkeypatch.setenv("POKECOACH_AGENTIC_COACH_AUDITOR", "1")
    monkeypatch.setenv("POKECOACH_INCLUDE_AGENTIC_TELEMETRY", "1")
    monkeypatch.setenv("POKECOACH_AGENT_A_MODEL", "google/gemini-3-flash-preview")
    monkeypatch.setenv("POKECOACH_AGENT_B_MODEL", "mistralai/mistral-large-2512")

    monkeypatch.setattr(
        report_module,
        "load_runtime_config",
        lambda: PydanticAIRuntimeConfig(
            openrouter_api_key="k",
            openrouter_base_url="https://openrouter.ai/api/v1",
            model="baseline/model",
        ),
    )

    captured = {"a": None, "b": None}

    def fake_guidance_with_raw(**kwargs):
        captured["a"] = kwargs["config"].model
        return (
            LLMReportGuidance(summary=[f"s{i}" for i in range(1, 6)], next_actions=["a1", "a2", "a3"]),
            "a-raw",
        )

    def fake_audit_with_raw(**kwargs):
        captured["b"] = kwargs["config"].model
        return (AuditResult(quality_minimum_pass=True, violations=[], patch_plan=[], audit_summary="ok"), "b-raw")

    monkeypatch.setattr(report_module, "maybe_generate_guidance_with_raw", fake_guidance_with_raw)
    monkeypatch.setattr(report_module, "maybe_generate_audit_result_with_raw", fake_audit_with_raw)

    report = generate_post_game_report(log_text)

    assert captured["a"] == "google/gemini-3-flash-preview"
    assert captured["b"] == "mistralai/mistral-large-2512"
    assert report.agentic_telemetry is not None
    assert report.agentic_telemetry["agent_a_model"] == "google/gemini-3-flash-preview"
    assert report.agentic_telemetry["agent_b_model"] == "mistralai/mistral-large-2512"
