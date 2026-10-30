"""
Three-way outcome logic for SatyaSwar ML subsystem.
Authoritative source: Implementation.md, Section 7.5

Outputs:
- 'insufficient_evidence': If quality label is 'poor' or active speech < min threshold.
- 'suspicious': If band is 'high', or 'medium' with rising trajectory under fair/good evidence.
- 'likely_genuine': If band is 'low' or steady 'medium' with adequate evidence.
"""

from __future__ import annotations

from satyaswar_ml.schemas import BandType, OutcomeType, QualityLabelType


def determine_outcome(
    band: BandType,
    evidence_label: QualityLabelType,
    is_sufficient: bool,
    recent_smoothed_scores: list[float] | None = None,
) -> OutcomeType:
    """
    Compute three-way decision outcome.
    """
    # 1. Honest abstain state: poor quality or insufficient speech
    if not is_sufficient or evidence_label == "poor" or band == "insufficient":
        return "insufficient_evidence"

    # 2. High risk band -> suspicious
    if band == "high":
        return "suspicious"

    # 3. Medium band: suspicious only if score has been steadily rising for 2 windows
    if band == "medium":
        if recent_smoothed_scores and len(recent_smoothed_scores) >= 3:
            s1, s2, s3 = recent_smoothed_scores[-3:]
            if s3 > s2 > s1:
                return "suspicious"
        return "likely_genuine"

    # 4. Low band -> likely genuine
    return "likely_genuine"
