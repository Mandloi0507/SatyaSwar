"""
Evidence quality evaluator and gatekeeper.
Authoritative source: Implementation.md, Section 7.6

Combines speech duration, estimated SNR, and temporal score agreement.
Hard gate: speech duration < min_speech_s_for_scoring (1.0s) forces 'poor' quality.
"""

from __future__ import annotations

from typing import NamedTuple

import numpy as np

from satyaswar_ml.schemas import QualityLabelType


class EvidenceEvaluation(NamedTuple):
    quality: float              # [0.0, 1.0]
    quality_label: QualityLabelType
    speech_term: float          # [0.0, 1.0]
    snr_term: float             # [0.0, 1.0]
    agreement_term: float       # [0.0, 1.0]
    is_sufficient: bool         # False if hard-gated by insufficient speech duration


def compute_evidence_quality(
    speech_seconds: float,
    snr_db: float,
    recent_scores: list[float] | None = None,
    inter_model_agreement: float | None = None,
    min_speech_s: float = 1.0,
    w_speech: float = 0.45,
    w_snr: float = 0.30,
    w_agreement: float = 0.25,
    good_min: float = 0.70,
    fair_min: float = 0.45,
) -> EvidenceEvaluation:
    """
    Compute evidence quality metric and label.
    """
    # 1. Speech duration term: reaches 1.0 at 3.0s of speech
    speech_term = float(np.clip(speech_seconds / 3.0, 0.0, 1.0))

    # 2. SNR term: reaches 1.0 at 25 dB, 0.0 at 5 dB
    snr_term = float(np.clip((snr_db - 5.0) / 20.0, 0.0, 1.0))

    # 3. Agreement term
    if inter_model_agreement is not None:
        agreement_term = float(np.clip(inter_model_agreement, 0.0, 1.0))
    elif recent_scores and len(recent_scores) >= 2:
        # Standard deviation over recent window scores
        score_std = float(np.std(recent_scores[-3:]))
        agreement_term = float(1.0 - np.clip(score_std / 0.25, 0.0, 1.0))
    else:
        # Initial window default: high consistency expectation
        agreement_term = 0.85

    # 4. Weighted combination
    raw_quality = (
        w_speech * speech_term
        + w_snr * snr_term
        + w_agreement * agreement_term
    )
    quality = float(np.clip(round(raw_quality, 2), 0.0, 1.0))

    # 5. Hard gate: fewer than min_speech_s (1.0s) forces "poor" and is_sufficient=False
    if speech_seconds < min_speech_s:
        quality = min(quality, 0.35)
        label: QualityLabelType = "poor"
        is_sufficient = False
    else:
        is_sufficient = True
        if quality >= good_min:
            label = "good"
        elif quality >= fair_min:
            label = "fair"
        else:
            label = "poor"

    return EvidenceEvaluation(
        quality=quality,
        quality_label=label,
        speech_term=round(speech_term, 2),
        snr_term=round(snr_term, 2),
        agreement_term=round(agreement_term, 2),
        is_sufficient=is_sufficient,
    )
