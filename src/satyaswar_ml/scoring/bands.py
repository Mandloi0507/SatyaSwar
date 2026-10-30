"""
Risk bands, hysteresis debouncing, and alert gating.
Authoritative source: Implementation.md, Section 7.5
"""

from __future__ import annotations

from typing import NamedTuple

from satyaswar_ml.config import ThresholdPair
from satyaswar_ml.schemas import BandType


class BandState(NamedTuple):
    current_band: BandType
    previous_band: BandType | None
    band_changed: bool
    should_alert: bool
    reason_code: str


class BandTracker:
    """
    Stateful risk band tracker with hysteresis and debounce.
    Prevents alert flapping on noisy boundary sequences.
    """

    def __init__(
        self,
        thresholds: ThresholdPair,
        escalate_consecutive: int = 2,
        deescalate_consecutive: int = 3,
        hysteresis_delta: float = 0.05,
        immediate_high_margin: float = 0.15,
        min_alert_spacing_s: float = 6.0,
    ):
        self.thresholds = thresholds
        self.escalate_consecutive = escalate_consecutive
        self.deescalate_consecutive = deescalate_consecutive
        self.hysteresis_delta = hysteresis_delta
        self.immediate_high_margin = immediate_high_margin
        self.min_alert_spacing_s = min_alert_spacing_s

        self.current_band: BandType = "low"
        self.previous_band: BandType | None = None
        self.pending_band: BandType | None = None
        self.pending_count: int = 0
        self.last_alert_time_s: float = -999.0

    def _band_rank(self, band: BandType) -> int:
        ranks = {"low": 0, "insufficient": 1, "medium": 2, "high": 3}
        return ranks.get(band, 0)

    def _classify_raw_band(self, score: float | None, is_sufficient: bool) -> BandType:
        if not is_sufficient or score is None:
            return "insufficient"
        if score < self.thresholds.low_max:
            return "low"
        if score >= self.thresholds.high_min:
            return "high"
        return "medium"

    def update(
        self,
        smoothed_score: float | None,
        is_sufficient: bool,
        current_call_time_s: float,
    ) -> BandState:
        """
        Evaluate new window score, updating debounced band state.
        """
        target_band = self._classify_raw_band(smoothed_score, is_sufficient)
        prev_band = self.current_band
        band_changed = False
        should_alert = False
        reason = "steady_state"

        # Check immediate escalation override to HIGH
        if (
            smoothed_score is not None
            and smoothed_score >= (self.thresholds.high_min + self.immediate_high_margin)
            and is_sufficient
        ):
            if self.current_band != "high":
                self.previous_band = self.current_band
                self.current_band = "high"
                band_changed = True
                should_alert = True
                self.last_alert_time_s = current_call_time_s
                self.pending_band = None
                self.pending_count = 0
                return BandState(
                    current_band="high",
                    previous_band=self.previous_band,
                    band_changed=True,
                    should_alert=True,
                    reason_code="immediate_escalate_high",
                )

        if target_band == self.current_band:
            self.pending_band = None
            self.pending_count = 0
        else:
            # Check if pending transition is in progress
            if target_band == self.pending_band:
                self.pending_count += 1
            else:
                self.pending_band = target_band
                self.pending_count = 1

            current_rank = self._band_rank(self.current_band)
            target_rank = self._band_rank(target_band)

            # Escalation
            if target_rank > current_rank:
                if self.pending_count >= self.escalate_consecutive:
                    self.previous_band = self.current_band
                    self.current_band = target_band
                    band_changed = True
                    reason = f"escalate_{target_band}"
                    self.pending_band = None
                    self.pending_count = 0
            else:
                # De-escalation: requires deescalate_consecutive AND hysteresis margin
                passed_margin = True
                if smoothed_score is not None:
                    if self.current_band == "high":
                        passed_margin = smoothed_score < (self.thresholds.high_min - self.hysteresis_delta)
                    elif self.current_band == "medium":
                        passed_margin = smoothed_score < (self.thresholds.low_max - self.hysteresis_delta)

                if self.pending_count >= self.deescalate_consecutive and passed_margin:
                    self.previous_band = self.current_band
                    self.current_band = target_band
                    band_changed = True
                    reason = f"deescalate_{target_band}"
                    self.pending_band = None
                    self.pending_count = 0

        # Check alert throttling: at least min_alert_spacing_s between alerts
        if band_changed:
            if (current_call_time_s - self.last_alert_time_s) >= self.min_alert_spacing_s:
                should_alert = True
                self.last_alert_time_s = current_call_time_s
            elif self.current_band == "high":
                # High alerts bypass spacing throttle for immediate safety
                should_alert = True
                self.last_alert_time_s = current_call_time_s

        return BandState(
            current_band=self.current_band,
            previous_band=self.previous_band,
            band_changed=band_changed,
            should_alert=should_alert,
            reason_code=reason,
        )

    def reset(self) -> None:
        self.current_band = "low"
        self.previous_band = None
        self.pending_band = None
        self.pending_count = 0
        self.last_alert_time_s = -999.0
