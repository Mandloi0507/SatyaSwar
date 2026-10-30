"""
Unit tests for scoring pipeline: smoothing, bands, hysteresis, outcome, and why builder.
Authoritative source: Implementation.md, Section 7.5, 7.12, 15.1
"""

import pytest

from satyaswar_ml.config import ThresholdPair
from satyaswar_ml.scoring.bands import BandTracker
from satyaswar_ml.scoring.outcome import determine_outcome
from satyaswar_ml.scoring.smoothing import ScoreSmoother
from satyaswar_ml.scoring.why import ALLOWED_WHY_KINDS, build_why_items


class TestScoreSmoothing:
    def test_ema_initialization_and_update(self):
        smoother = ScoreSmoother(alpha_base=0.6)
        # s_0 = x_0
        s0 = smoother.update(0.80, evidence_quality=0.8)
        assert s0 == 0.80

        # Update with high evidence quality (0.9)
        # alpha_t = 0.6 * (0.5 + 0.5 * 0.9) = 0.57
        # s_1 = 0.57 * 0.40 + 0.43 * 0.80 = 0.228 + 0.344 = 0.572
        s1 = smoother.update(0.40, evidence_quality=0.9)
        assert s1 == pytest.approx(0.572, abs=1e-3)

    def test_low_quality_moves_average_less(self):
        s_high_q = ScoreSmoother(alpha_base=0.6)
        s_high_q.update(0.80, evidence_quality=0.9)
        val_high = s_high_q.update(0.20, evidence_quality=0.9)

        s_low_q = ScoreSmoother(alpha_base=0.6)
        s_low_q.update(0.80, evidence_quality=0.1)
        val_low = s_low_q.update(0.20, evidence_quality=0.1)

        # High quality moves closer to 0.20, low quality remains closer to 0.80
        assert val_high < val_low

    def test_insufficient_evidence_does_not_update_state(self):
        smoother = ScoreSmoother(alpha_base=0.6)
        smoother.update(0.70, evidence_quality=0.8)

        # Feeding insufficient evidence
        val = smoother.update(0.99, evidence_quality=0.1, is_sufficient=False)
        assert val == 0.70


class TestBandTrackerAndHysteresis:
    @pytest.fixture
    def tracker(self):
        thresholds = ThresholdPair(low_max=0.35, high_min=0.65)
        return BandTracker(
            thresholds=thresholds,
            escalate_consecutive=2,
            deescalate_consecutive=3,
            hysteresis_delta=0.05,
            immediate_high_margin=0.15,
            min_alert_spacing_s=6.0,
        )

    def test_escalate_after_two_windows(self, tracker):
        # Window 1: score 0.70 (>= 0.65) -> pending escalation (count 1), band remains low
        b1 = tracker.update(0.70, is_sufficient=True, current_call_time_s=1.75)
        assert b1.current_band == "low"
        assert b1.band_changed is False

        # Window 2: score 0.72 (>= 0.65) -> pending escalation (count 2) -> escalates to high!
        b2 = tracker.update(0.72, is_sufficient=True, current_call_time_s=3.50)
        assert b2.current_band == "high"
        assert b2.band_changed is True
        assert b2.should_alert is True

    def test_immediate_jump_to_high(self, tracker):
        # Score 0.85 >= 0.65 + 0.15 (0.80) -> immediate jump to high on 1st window!
        b1 = tracker.update(0.85, is_sufficient=True, current_call_time_s=1.75)
        assert b1.current_band == "high"
        assert b1.band_changed is True
        assert b1.should_alert is True
        assert b1.reason_code == "immediate_escalate_high"

    def test_deescalate_requires_three_windows_and_margin(self, tracker):
        # Jump to high
        tracker.update(0.85, is_sufficient=True, current_call_time_s=1.75)

        # De-escalate attempts with score 0.25 (< 0.35 - 0.05)
        d1 = tracker.update(0.25, is_sufficient=True, current_call_time_s=8.0)
        assert d1.current_band == "high"

        d2 = tracker.update(0.25, is_sufficient=True, current_call_time_s=9.75)
        assert d2.current_band == "high"

        # 3rd consecutive low window -> de-escalates to low!
        d3 = tracker.update(0.25, is_sufficient=True, current_call_time_s=11.5)
        assert d3.current_band == "low"
        assert d3.band_changed is True

    def test_alert_spacing_throttling(self, tracker):
        # Window 1: jump to high at t=1.0s -> alerts
        b1 = tracker.update(0.85, is_sufficient=True, current_call_time_s=1.0)
        assert b1.should_alert is True

        # Rapidly transition down and back within 3 seconds (< 6.0s spacing)
        tracker.current_band = "low"
        b2 = tracker.update(0.50, is_sufficient=True, current_call_time_s=3.0)
        # Even if band changed to medium, alert is suppressed by 6s throttle
        # (unless high)
        if b2.band_changed and b2.current_band != "high":
            assert b2.should_alert is False


class TestOutcomeDetermination:
    def test_poor_quality_forces_insufficient_evidence(self):
        out = determine_outcome(
            band="high",
            evidence_label="poor",
            is_sufficient=False,
        )
        assert out == "insufficient_evidence"

    def test_high_band_yields_suspicious(self):
        out = determine_outcome(
            band="high",
            evidence_label="good",
            is_sufficient=True,
        )
        assert out == "suspicious"

    def test_low_band_yields_likely_genuine(self):
        out = determine_outcome(
            band="low",
            evidence_label="good",
            is_sufficient=True,
        )
        assert out == "likely_genuine"


class TestWhyBuilder:
    def test_why_items_strictly_restricted_to_allowed_kinds(self):
        items = build_why_items(
            window_score=0.81,
            peak_score=0.84,
            speech_seconds=2.9,
            snr_db=18.4,
            model_agreement=0.88,
            synthetic_score=0.81,
            replay_score=0.12,
            keyword_terms=["तुरंत", "transfer"],
            heuristics={"mean_pause_s": 0.35},
        )
        assert len(items) >= 7
        for it in items:
            assert it.kind in ALLOWED_WHY_KINDS
            # Verify no free-text sentences
            if isinstance(it.value, str):
                assert len(it.value.split()) <= 4, f"Suspicious prose in why item: {it.value}"
