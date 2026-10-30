"""
Auditable 'Why Flagged' evidence builder.
Authoritative source: Implementation.md, Section 7.12 & AGENTS.md Anti-hallucination rules.

Strictly restricted to computed measurements.
Natural-language prose or free-form text explanations are strictly forbidden.
"""

from __future__ import annotations

from satyaswar_ml.schemas import WhyItem

ALLOWED_WHY_KINDS = {
    "window_score",
    "speech_seconds",
    "snr_db",
    "model_agreement",
    "synthetic_score",
    "replay_score",
    "context_keyword",
    "supporting_heuristic",
}


def build_why_items(
    window_score: float | None = None,
    peak_score: float | None = None,
    speech_seconds: float | None = None,
    snr_db: float | None = None,
    model_agreement: float | None = None,
    synthetic_score: float | None = None,
    replay_score: float | None = None,
    keyword_terms: list[str] | None = None,
    heuristics: dict[str, float] | None = None,
) -> list[WhyItem]:
    """
    Construct auditable list of computed explanation signals.
    """
    items: list[WhyItem] = []

    if window_score is not None:
        items.append(
            WhyItem(
                kind="window_score",
                text_key="window_score",
                value=round(window_score, 3),
            )
        )

    if peak_score is not None and peak_score > (window_score or 0.0):
        items.append(
            WhyItem(
                kind="window_score",
                text_key="peak_window",
                value=round(peak_score, 3),
            )
        )

    if speech_seconds is not None:
        items.append(
            WhyItem(
                kind="speech_seconds",
                text_key="speech_duration",
                value=round(speech_seconds, 2),
            )
        )

    if snr_db is not None:
        items.append(
            WhyItem(
                kind="snr_db",
                text_key="snr_level",
                value=round(snr_db, 1),
            )
        )

    if model_agreement is not None:
        items.append(
            WhyItem(
                kind="model_agreement",
                text_key="inter_model_consistency",
                value=round(model_agreement, 3),
            )
        )

    # Critical requirement: distinguish synthetic from replay
    if synthetic_score is not None:
        items.append(
            WhyItem(
                kind="synthetic_score",
                text_key="ai_synthesis_prob",
                value=round(synthetic_score, 3),
            )
        )

    if replay_score is not None:
        items.append(
            WhyItem(
                kind="replay_score",
                text_key="loudspeaker_replay_prob",
                value=round(replay_score, 3),
            )
        )

    if keyword_terms:
        for term in keyword_terms[:3]:  # Cap at top 3 keywords
            items.append(
                WhyItem(
                    kind="context_keyword",
                    text_key="scam_keyword_spotted",
                    value=term,
                )
            )

    if heuristics:
        for k, v in heuristics.items():
            items.append(
                WhyItem(
                    kind="supporting_heuristic",
                    text_key=k,
                    value=round(v, 3) if isinstance(v, float) else v,
                )
            )

    return items
