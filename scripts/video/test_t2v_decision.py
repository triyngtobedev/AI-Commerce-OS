"""Testes do T2V Decision Engine."""

from scripts.video.t2v_decision import (
    T2VTracker,
    evaluate_t2v_decision,
    MAX_T2V_SCENES,
)


def test_tracker_max_limit():
    tracker = T2VTracker(max_scenes=2)
    assert tracker.can_use_t2v()

    from scripts.video.t2v_decision import T2VDecision
    tracker.record_use(1, T2VDecision(should_use_t2v=True, reason="test"))
    tracker.record_use(2, T2VDecision(should_use_t2v=True, reason="test"))
    assert not tracker.can_use_t2v()
    assert tracker.remaining == 0


def test_t2v_skipped_when_stock_available():
    tracker = T2VTracker()
    decision = evaluate_t2v_decision(
        1,
        {"tipo": "hook", "scene_type": "hook"},
        {"busca": "factory", "tipo": "hook"},
        tracker=tracker,
        stock_failed=False,
        editorial_failed=False,
    )
    assert decision.should_use_t2v is False


def test_t2v_approved_for_hook_when_stock_fails():
    tracker = T2VTracker()
    decision = evaluate_t2v_decision(
        1,
        {"tipo": "hook", "scene_type": "hook", "thumbnail_potential": True},
        {"busca": "dramatic factory", "tipo": "hook"},
        tracker=tracker,
        stock_failed=True,
        editorial_failed=True,
        scene_importance=0.9,
    )
    assert decision.should_use_t2v is True
    assert decision.prompt
    assert decision.negative_prompt


def test_t2v_avoided_for_data_scene():
    tracker = T2VTracker()
    decision = evaluate_t2v_decision(
        3,
        {"scene_type": "data", "tipo": "impacto"},
        {"busca": "sales chart", "tipo": "impacto"},
        tracker=tracker,
        stock_failed=True,
        editorial_failed=False,
    )
    assert decision.should_use_t2v is False


def test_max_t2v_constant():
    assert MAX_T2V_SCENES == 2
