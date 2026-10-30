"""
Deterministic Mock Engine Adapter.
Authoritative source: Implementation.md, Section 6.7

Simulates scripted call trajectories (genuine, clone, noisy, short) from configs/scenarios.json.
Guarantees that EVERY emitted event strictly carries `"mock": true`.
"""

from __future__ import annotations

import time

from satyaswar_ml.schemas import (
    AlertEvent,
    BilingualText,
    CallSummaryEvent,
    EvidenceModel,
    LanguageModel,
    LatencyBreakdown,
    ModelMeta,
    SatyaSwarEvent,
    ScoreEvent,
    WindowBounds,
)


class MockCallSession:
    """
    Scripted mock session returning pre-recorded event sequences.
    """

    def __init__(self, call_id: str, scenario_id: str = "gen_hi_01"):
        self.call_id = call_id
        self.scenario_id = scenario_id
        self.window_index = 0
        self.start_time = time.time()
        self.is_clone = "clone" in scenario_id
        self.is_noisy = "noisy" in scenario_id
        self.is_short = "short" in scenario_id

    async def push_audio(
        self,
        data: bytes,
        seq: int | None = None,
        client_ts_ms: int | None = None,
    ) -> list[SatyaSwarEvent]:
        """Generate scripted event sequence based on scenario type."""
        self.window_index += 1
        now_ms = int(time.time() * 1000)
        events: list[SatyaSwarEvent] = []

        start_ms = (self.window_index - 1) * 1750
        end_ms = start_ms + 3500

        # Scenario trajectories
        if self.is_clone:
            # Escalates to high
            raw_score = 0.82 if self.window_index >= 2 else 0.55
            band = "high" if self.window_index >= 2 else "medium"
            outcome = "suspicious" if self.window_index >= 2 else "likely_genuine"
            ev_quality = 0.85
            speech_s = 2.9
            snr = 19.5
        elif self.is_noisy or self.is_short:
            # Low evidence quality forces insufficient_evidence
            raw_score = None
            band = "insufficient"
            outcome = "insufficient_evidence"
            ev_quality = 0.32
            speech_s = 0.6 if self.is_short else 1.2
            snr = 3.5 if self.is_noisy else 12.0
        else:
            # Genuine caller stays low
            raw_score = 0.12
            band = "low"
            outcome = "likely_genuine"
            ev_quality = 0.88
            speech_s = 3.1
            snr = 22.0

        score_ev = ScoreEvent(
            call_id=self.call_id,
            window_index=self.window_index,
            window=WindowBounds(start_ms=start_ms, end_ms=end_ms),
            spoof_score=raw_score,
            smoothed_score=raw_score,
            band=band,
            previous_band="low" if self.window_index > 1 else None,
            band_changed=(self.window_index == 2 and self.is_clone),
            outcome=outcome,
            evidence=EvidenceModel(
                speech_seconds=speech_s,
                snr_db=snr,
                agreement=0.92,
                quality=ev_quality,
                quality_label="good" if ev_quality >= 0.70 else "poor",
                synthetic_score=raw_score,
                replay_score=0.10,
                replay_detected=False,
            ),
            language=LanguageModel(code="hi", confidence=0.94, source="asr"),
            telephony_profile="none",
            latency_ms=LatencyBreakdown(
                decode=1.5, telephony=0.0, vad=12.0, detector=110.0, total=123.5
            ),
            client_ts_ms=client_ts_ms or now_ms,
            server_recv_ts_ms=now_ms,
            server_send_ts_ms=now_ms + 120,
            model=ModelMeta(name="mock_scripted_model", version="1.0-mock"),
            why=[],
            mock=True,  # STRICT CONTRACT REQUIREMENT
        )
        events.append(score_ev)

        # Emit alert if clone escalated
        if self.window_index == 2 and self.is_clone:
            events.append(
                AlertEvent(
                    call_id=self.call_id,
                    level="high",
                    reason_code="mock_escalate_high",
                    text=BilingualText(
                        en="Warning. This voice may be synthetic. Verify the caller now.",
                        hi="सावधान! यह आवाज़ नकली हो सकती है। अभी कॉलर की पुष्टि करें।",
                    ),
                    audio_key=BilingualText(en="alert_high_en", hi="alert_high_hi"),
                )
            )

        return events

    async def end(self) -> CallSummaryEvent:
        return CallSummaryEvent(
            call_id=self.call_id,
            peak_score=0.82 if self.is_clone else 0.12,
            mean_score=0.75 if self.is_clone else 0.12,
            final_band="high" if self.is_clone else "low",
            final_outcome="suspicious" if self.is_clone else "likely_genuine",
            time_in_band_s={"low": 1.75, "medium": 0.0, "high": 5.25, "insufficient": 0.0},
            evidence_quality_mean=0.85,
            languages_seen=["hi"],
            context_categories=["urgency"] if self.is_clone else [],
            windows_scored=self.window_index,
            windows_insufficient=0,
            latency_ms={"p50": 120.0, "p95": 140.0},
            mock=True,
        )
