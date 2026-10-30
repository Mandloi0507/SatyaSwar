"""
Core Analysis Engine and CallSession Implementation.
Authoritative source: Implementation.md, Section 6.6, 7.14
"""

from __future__ import annotations

import asyncio
import struct
import time
from typing import Any

import numpy as np

from satyaswar_ml.audio.io import pcm16le_to_float32
from satyaswar_ml.audio.snr import compute_snr_db
from satyaswar_ml.audio.telephony import apply_telephony_profile
from satyaswar_ml.audio.windowing import AudioWindow, WindowEmitter, prepare_model_input
from satyaswar_ml.config import SatyaSwarConfig, load_config
from satyaswar_ml.detection.replay import ReplayAttackDetector
from satyaswar_ml.detector.base import Detector
from satyaswar_ml.detector.registry import get_detector
from satyaswar_ml.nlp.contacts import ContactMatcher
from satyaswar_ml.nlp.keywords import KeywordMatcher
from satyaswar_ml.schemas import (
    AlertEvent,
    BilingualText,
    CallSummaryEvent,
    Contact,
    ErrorEvent,
    EvidenceModel,
    InfoEvent,
    LanguageModel,
    LatencyBreakdown,
    ModelMeta,
    SatyaSwarEvent,
    ScoreEvent,
    SessionReadyEvent,
    WindowBounds,
)
from satyaswar_ml.scoring.bands import BandTracker
from satyaswar_ml.scoring.evidence import compute_evidence_quality
from satyaswar_ml.scoring.outcome import determine_outcome
from satyaswar_ml.scoring.smoothing import ScoreSmoother
from satyaswar_ml.scoring.why import build_why_items
from satyaswar_ml.vad.silero_vad import SileroVAD


class SessionConfig:
    """Session configuration parameters."""
    def __init__(
        self,
        mode: str = "chunks",
        telephony_profile: str = "none",
        language_hint: str | None = None,
        max_pending_windows: int = 2,
    ):
        self.mode = mode
        self.telephony_profile = telephony_profile
        self.language_hint = language_hint
        self.max_pending_windows = max_pending_windows


class CallSession:
    """
    Stateful analysis session for an active phone call stream.
    Processes audio frames in memory and emits verified contract events.
    """

    def __init__(
        self,
        call_id: str,
        config: SessionConfig,
        contacts: list[Contact],
        engine_config: SatyaSwarConfig,
        detector: Detector,
        vad: SileroVAD,
        replay_detector: ReplayAttackDetector,
        keyword_matcher: KeywordMatcher,
        asr=None,
    ):
        self.call_id = call_id
        self.config = config
        self.contacts = contacts
        self.engine_config = engine_config
        self.detector = detector
        self.vad = vad
        self.replay_detector = replay_detector
        self.keyword_matcher = keyword_matcher
        self.asr = asr

        # Audio windowing
        self.emitter = WindowEmitter(
            sample_rate=engine_config.audio.sample_rate,
            window_s=engine_config.audio.window_s,
            hop_s=engine_config.audio.hop_s,
            ring_buffer_s=engine_config.audio.ring_buffer_s,
            mode=config.mode,
        )

        # Scoring state
        self.smoother = ScoreSmoother(alpha_base=engine_config.scoring.alpha_base)
        self.band_tracker = BandTracker(
            thresholds=engine_config.thresholds.default,
            escalate_consecutive=engine_config.scoring.escalate_consecutive,
            deescalate_consecutive=engine_config.scoring.deescalate_consecutive,
            hysteresis_delta=engine_config.scoring.hysteresis_delta,
            immediate_high_margin=engine_config.scoring.immediate_high_margin,
            min_alert_spacing_s=engine_config.scoring.min_alert_spacing_s,
        )

        # Contact matching
        self.contact_matcher = ContactMatcher(contacts)

        # Lifecycle & state tracking
        self.session_start_time = time.time()
        self.last_activity_time = time.time()
        self.seen_seqs: set[int] = set()
        self.peak_score: float | None = None
        self.scored_raw_scores: list[float] = []
        self.evidence_qualities: list[float] = []
        self.latencies_total: list[float] = []
        self.windows_scored = 0
        self.windows_insufficient = 0
        self.time_in_bands: dict[str, float] = {"low": 0.0, "medium": 0.0, "high": 0.0, "insufficient": 0.0}
        self.languages_seen: set[str] = set()
        self.context_categories_spotted: set[str] = set()
        self.current_language: str | None = config.language_hint

        # Speech accumulation for ASR triggering
        self.accumulated_speech_s = 0.0
        self.asr_triggered_6s = False
        self.asr_triggered_12s = False

        # Alert localization dictionary (Appendix C)
        self.alert_strings = {
            "low": {
                "en": "No synthetic signs found so far. This is not proof of identity. Verify before sending money.",
                "hi": "अब तक नकली आवाज़ के संकेत नहीं मिले। यह पहचान का प्रमाण नहीं है। पैसे भेजने से पहले पुष्टि करें।",
            },
            "medium": {
                "en": "This voice shows some warning signs. Be careful and consider verifying the caller.",
                "hi": "इस आवाज़ में कुछ चेतावनी के संकेत हैं। सावधान रहें और कॉलर की पुष्टि करने पर विचार करें।",
            },
            "high": {
                "en": "Warning. This voice may be synthetic. Do not share money or codes. Verify the caller now.",
                "hi": "सावधान! यह आवाज़ नकली हो सकती है। पैसे या कोड न दें। अभी कॉलर की पुष्टि करें।",
            },
            "insufficient": {
                "en": "Not enough clear audio to judge. Verify the caller before any sensitive action.",
                "hi": "आवाज़ का आकलन करने के लिए साफ़ ऑडियो पर्याप्त नहीं है। कोई भी संवेदनशील काम करने से पहले कॉलर की पुष्टि करें।",
            },
        }

    async def update_config(self, telephony_profile: str | None = None) -> None:
        if telephony_profile:
            self.config.telephony_profile = telephony_profile

    async def push_audio(
        self,
        data: bytes,
        seq: int | None = None,
        client_ts_ms: int | None = None,
    ) -> list[SatyaSwarEvent]:
        """
        Ingest binary frame:
        Parses 12-byte header (seq: uint32, client_ts_ms: uint64) if header is present in data.
        """
        recv_ts_ms = int(time.time() * 1000)
        self.last_activity_time = time.time()
        events: list[SatyaSwarEvent] = []

        # 1. Parse 12-byte binary header if data length indicates header presence
        pcm_bytes = data
        if seq is None:
            if len(data) < 12:
                return [
                    ErrorEvent(
                        call_id=self.call_id,
                        code="invalid_frame_header",
                        message=f"Frame size {len(data)} is less than mandatory 12-byte header",
                        recoverable=True,
                    )
                ]
            try:
                seq, client_ts_ms = struct.unpack("<IQ", data[:12])
                pcm_bytes = data[12:]
            except Exception as e:
                return [
                    ErrorEvent(
                        call_id=self.call_id,
                        code="invalid_frame_header",
                        message=f"Header unpack failed: {e}",
                        recoverable=True,
                    )
                ]


        if seq is not None:
            if seq in self.seen_seqs:
                # Duplicate frame: ignore safely per Section 6.3
                return []
            self.seen_seqs.add(seq)

        # 2. Reject odd byte counts
        try:
            audio_samples = pcm16le_to_float32(pcm_bytes)
        except ValueError as e:
            return [
                ErrorEvent(
                    call_id=self.call_id,
                    code="bad_frame",
                    message=str(e),
                    recoverable=True,
                )
            ]

        # 3. Buffer audio and emit windows
        windows = self.emitter.push(audio_samples)
        if not windows:
            return []

        # Handle backpressure: if windows > max_pending_windows (2), drop oldest
        if len(windows) > self.config.max_pending_windows:
            dropped_count = len(windows) - self.config.max_pending_windows
            events.append(
                InfoEvent(
                    call_id=self.call_id,
                    code="windows_dropped",
                    message=f"Dropped {dropped_count} oldest pending windows to keep latency real-time",
                )
            )
            windows = windows[dropped_count:]

        # 4. Process each window
        for win in windows:
            win_events = await self._process_window(win, client_ts_ms, recv_ts_ms)
            events.extend(win_events)

        return events

    async def _process_window(
        self,
        win: AudioWindow,
        client_ts_ms: int | None,
        recv_ts_ms: int,
    ) -> list[SatyaSwarEvent]:
        events: list[SatyaSwarEvent] = []
        t0 = time.perf_counter()

        # Stage 1: Decode
        audio = win.audio
        t_decode = (time.perf_counter() - t0) * 1000

        # Stage 2: Telephony Simulation
        t1 = time.perf_counter()
        if self.config.telephony_profile != "none":
            audio = apply_telephony_profile(audio, self.config.telephony_profile)
        t_telephony = (time.perf_counter() - t1) * 1000

        # Stage 3: VAD and SNR
        t2 = time.perf_counter()
        vad_res = self.vad.detect(audio)
        snr_db = compute_snr_db(audio, vad_res.speech_mask)
        t_vad = (time.perf_counter() - t2) * 1000

        # Accumulate speech for ASR triggering
        self.accumulated_speech_s += vad_res.speech_seconds

        # Evaluate evidence quality
        ev = compute_evidence_quality(
            speech_seconds=vad_res.speech_seconds,
            snr_db=snr_db,
            recent_scores=self.scored_raw_scores,
            min_speech_s=self.engine_config.audio.min_speech_s_for_scoring,
        )
        self.evidence_qualities.append(ev.quality)

        # Stage 4: Detector Inference (Synthetic Voice)
        t3 = time.perf_counter()
        raw_spoof_prob: float | None = None
        detector_raw: dict[str, Any] = {}

        if ev.is_sufficient:
            # Model input prep: repeat pad to 64,600 samples
            model_input = prepare_model_input(
                audio,
                target_samples=self.engine_config.audio.model_input_samples,
                pad_mode=self.engine_config.audio.pad_mode,
            )
            det_out = self.detector.predict(model_input)
            raw_spoof_prob = det_out.spoof_prob
            detector_raw = det_out.raw
            self.scored_raw_scores.append(raw_spoof_prob)
            if self.peak_score is None or raw_spoof_prob > self.peak_score:
                self.peak_score = raw_spoof_prob
            self.windows_scored += 1
        else:
            self.windows_insufficient += 1

        t_detector = (time.perf_counter() - t3) * 1000

        # Stage 5: Replay / Presentation Attack Detection
        replay_res = self.replay_detector.analyze(audio, vad_res.speech_mask)

        # Stage 6: Score Smoothing
        smoothed = self.smoother.update(
            raw_score=raw_spoof_prob,
            evidence_quality=ev.quality,
            is_sufficient=ev.is_sufficient,
        )

        # Stage 7: Bands and Hysteresis
        call_time_s = win.end_ms / 1000.0
        band_state = self.band_tracker.update(
            smoothed_score=smoothed,
            is_sufficient=ev.is_sufficient,
            current_call_time_s=call_time_s,
        )

        # Track time in band
        hop_s = self.engine_config.audio.hop_s
        self.time_in_bands[band_state.current_band] = (
            self.time_in_bands.get(band_state.current_band, 0.0) + hop_s
        )

        # Stage 8: Three-way Outcome
        outcome = determine_outcome(
            band=band_state.current_band,
            evidence_label=ev.quality_label,
            is_sufficient=ev.is_sufficient,
            recent_smoothed_scores=self.smoother.smoothed_history,
        )

        # Stage 9: Why Flagged Items
        why_items = build_why_items(
            window_score=raw_spoof_prob,
            peak_score=self.peak_score,
            speech_seconds=vad_res.speech_seconds,
            snr_db=snr_db,
            synthetic_score=raw_spoof_prob,
            replay_score=replay_res.replay_score if replay_res.is_conclusive else None,
        )

        # Stage 10: Score Event Construction
        t_total = (time.perf_counter() - t0) * 1000
        self.latencies_total.append(t_total)
        send_ts_ms = int(time.time() * 1000)

        score_ev = ScoreEvent(
            call_id=self.call_id,
            window_index=win.index,
            window=WindowBounds(start_ms=win.start_ms, end_ms=win.end_ms),
            spoof_score=raw_spoof_prob,
            smoothed_score=smoothed,
            band=band_state.current_band,
            previous_band=band_state.previous_band,
            band_changed=band_state.band_changed,
            outcome=outcome,
            evidence=EvidenceModel(
                speech_seconds=vad_res.speech_seconds,
                snr_db=snr_db,
                agreement=ev.agreement_term,
                quality=ev.quality,
                quality_label=ev.quality_label,
                synthetic_score=raw_spoof_prob,
                replay_score=replay_res.replay_score if replay_res.is_conclusive else None,
                replay_detected=replay_res.replay_detected if replay_res.is_conclusive else None,
            ),
            language=LanguageModel(
                code=self.current_language,
                confidence=0.90 if self.current_language else None,
                source="asr" if self.current_language else None,
            ),
            telephony_profile=self.config.telephony_profile,
            latency_ms=LatencyBreakdown(
                decode=round(t_decode, 1),
                telephony=round(t_telephony, 1),
                vad=round(t_vad, 1),
                detector=round(t_detector, 1),
                total=round(t_total, 1),
            ),
            client_ts_ms=client_ts_ms,
            server_recv_ts_ms=recv_ts_ms,
            server_send_ts_ms=send_ts_ms,
            model=ModelMeta(
                name=self.detector.name,
                version=self.detector.version,
            ),
            why=why_items,
            mock=detector_raw.get("mock", False),
        )
        events.append(score_ev)

        # Stage 11: Alert Event on committed band transition
        if band_state.should_alert:
            alert_lvl = band_state.current_band
            texts = self.alert_strings.get(alert_lvl, self.alert_strings["medium"])
            events.append(
                AlertEvent(
                    call_id=self.call_id,
                    level=alert_lvl,
                    reason_code=band_state.reason_code,
                    text=BilingualText(en=texts["en"], hi=texts["hi"]),
                    audio_key=BilingualText(en=f"alert_{alert_lvl}_en", hi=f"alert_{alert_lvl}_hi"),
                )
            )

        # Stage 12: Trigger ASR off critical path if speech thresholds crossed
        if self.asr and self.asr.is_available:
            should_run_asr = False
            is_final_asr = False
            if self.accumulated_speech_s >= 6.0 and not self.asr_triggered_6s:
                should_run_asr = True
                self.asr_triggered_6s = True
            elif self.accumulated_speech_s >= 12.0 and not self.asr_triggered_12s:
                should_run_asr = True
                self.asr_triggered_12s = True
                is_final_asr = True

            if should_run_asr:
                loop = asyncio.get_event_loop()
                # Run ASR on latest accumulated window audio without delaying score
                loop.run_in_executor(
                    None,
                    self._run_background_asr,
                    audio,
                    is_final_asr,
                    win.start_ms,
                    win.end_ms,
                )

        return events

    def _run_background_asr(self, audio: np.ndarray, is_final: bool, start_ms: int, end_ms: int):
        """Executed in background worker to spot speech, keywords, and identity."""
        try:
            asr_res = self.asr.transcribe(
                audio,
                contacts=self.contacts,
                is_final=is_final,
                start_ms=start_ms,
                end_ms=end_ms,
            )
            if asr_res and asr_res.text:
                if asr_res.language:
                    self.current_language = asr_res.language
                    self.languages_seen.add(asr_res.language)

                # Scan keywords
                flags = self.keyword_matcher.scan(asr_res.text, at_ms=start_ms)
                for f in flags:
                    self.context_categories_spotted.add(f.category)

                # Match contacts
                self.contact_matcher.match(asr_res.text, call_id=self.call_id)
        except Exception:
            pass

    async def end(self) -> CallSummaryEvent:
        """
        End call session:
        - Flush unscored remaining audio.
        - Compute final aggregated summary.
        - Strictly clean and free all transient audio buffers.
        """
        # Flush if >= 1.5s remaining
        final_win = self.emitter.flush(min_unscored_s=1.5)
        if final_win:
            await self._process_window(final_win, None, int(time.time() * 1000))

        # Calculate latency statistics
        p50 = float(np.percentile(self.latencies_total, 50)) if self.latencies_total else 0.0
        p95 = float(np.percentile(self.latencies_total, 95)) if self.latencies_total else 0.0
        mean_score = float(np.mean(self.scored_raw_scores)) if self.scored_raw_scores else None
        mean_evidence = float(np.mean(self.evidence_qualities)) if self.evidence_qualities else 0.0

        summary = CallSummaryEvent(
            call_id=self.call_id,
            peak_score=round(self.peak_score, 3) if self.peak_score is not None else None,
            mean_score=round(mean_score, 3) if mean_score is not None else None,
            final_band=self.band_tracker.current_band,
            final_outcome=determine_outcome(
                band=self.band_tracker.current_band,
                evidence_label="good" if mean_evidence >= 0.70 else ("fair" if mean_evidence >= 0.45 else "poor"),
                is_sufficient=self.windows_scored > 0,
            ),
            time_in_band_s={k: round(v, 1) for k, v in self.time_in_bands.items()},
            evidence_quality_mean=round(mean_evidence, 2),
            languages_seen=sorted(list(self.languages_seen)),
            context_categories=sorted(list(self.context_categories_spotted)),
            windows_scored=self.windows_scored,
            windows_insufficient=self.windows_insufficient,
            latency_ms={"p50": round(p50, 1), "p95": round(p95, 1)},
            mock=self.detector.name == "mock_detector",
        )

        # Free all in-memory audio buffers
        self.emitter.ring_buffer.clear()
        self.scored_raw_scores.clear()
        self.evidence_qualities.clear()
        self.latencies_total.clear()

        return summary


class AnalysisEngine:
    """
    Central analysis engine managing models, warm-up, and call sessions.
    Single instance created once at application startup.
    """

    def __init__(self, config: SatyaSwarConfig):
        self.config = config
        self.detector: Detector = get_detector(
            config.detector.primary if not config.mock_mode else "mock_detector",
            device=config.detector.device,
            precision=config.detector.precision,
            checkpoint_path=config.detector.checkpoint_path,
        )
        self.vad = SileroVAD(
            threshold=config.vad.threshold,
            min_speech_ms=config.vad.min_speech_ms,
            min_silence_ms=config.vad.min_silence_ms,
            sample_rate=config.audio.sample_rate,
        )
        self.replay_detector = ReplayAttackDetector(sample_rate=config.audio.sample_rate)
        self.keyword_matcher = KeywordMatcher()
        self.asr = None
        self.active_sessions: dict[str, CallSession] = {}
        self._warmup_time_ms = 0.0

    @classmethod
    def from_config(cls, config_path: str | None = None) -> AnalysisEngine:
        cfg = load_config(config_path)
        return cls(cfg)

    async def warmup(self) -> float:
        """Run warm-up on detection models and VAD."""
        t0 = time.perf_counter()
        self.detector.warmup()
        # Prime VAD
        dummy_audio = np.zeros(self.config.audio.model_input_samples, dtype=np.float32)
        self.vad.detect(dummy_audio[:16000])
        self.replay_detector.analyze(dummy_audio[:16000])
        self._warmup_time_ms = (time.perf_counter() - t0) * 1000.0
        return self._warmup_time_ms

    def start_session(
        self,
        call_id: str,
        config: SessionConfig | None = None,
        contacts: list[Contact] | None = None,
        resume: bool = False,
    ) -> tuple[CallSession, SessionReadyEvent]:

        """
        Start or resume a call session.
        If resume is True and existing session exists within 60s, resumes it.
        """
        now = time.time()
        if resume and call_id in self.active_sessions:
            sess = self.active_sessions[call_id]
            if (now - sess.last_activity_time) <= self.config.session.resume_window_s:
                ready_event = SessionReadyEvent(
                    call_id=call_id,
                    model={"name": self.detector.name, "version": self.detector.version},
                    device=self.config.detector.device,
                    warmup_ms=round(self._warmup_time_ms, 1),
                    contacts_loaded=len(sess.contacts),
                )
                return sess, ready_event

        cfg = config or SessionConfig(mode=self.config.audio.mode_default)
        session = CallSession(
            call_id=call_id,
            config=cfg,
            contacts=contacts or [],
            engine_config=self.config,
            detector=self.detector,
            vad=self.vad,
            replay_detector=self.replay_detector,
            keyword_matcher=self.keyword_matcher,
            asr=self.asr,
        )
        self.active_sessions[call_id] = session

        ready_event = SessionReadyEvent(
            call_id=call_id,
            model={"name": self.detector.name, "version": self.detector.version},
            device=self.config.detector.device,
            warmup_ms=round(self._warmup_time_ms, 1),
            contacts_loaded=len(session.contacts),
        )
        return session, ready_event

    def get_session(self, call_id: str) -> CallSession | None:
        return self.active_sessions.get(call_id)

    async def end_session(self, call_id: str) -> CallSummaryEvent | None:
        if call_id in self.active_sessions:
            sess = self.active_sessions.pop(call_id)
            return await sess.end()
        return None
