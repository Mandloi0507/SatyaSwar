"""
Evidence-weighted Exponential Moving Average (EMA) score smoothing.
Authoritative source: Implementation.md, Section 7.5

Formula:
  alpha_t = alpha_base * (0.5 + 0.5 * q_t)
  s_t = alpha_t * x_t + (1 - alpha_t) * s_{t-1}
  s_0 = x_0

Windows with insufficient evidence do not update smoothed state.
"""

from __future__ import annotations


class ScoreSmoother:
    """
    Stateful evidence-weighted exponential moving average score smoother.
    """

    def __init__(self, alpha_base: float = 0.6):
        self.alpha_base = alpha_base
        self.smoothed_score: float | None = None
        self.raw_history: list[float] = []
        self.smoothed_history: list[float] = []

    def update(
        self,
        raw_score: float | None,
        evidence_quality: float,
        is_sufficient: bool = True,
    ) -> float | None:
        """
        Update EMA smoothed score with current window score.
        If is_sufficient is False or raw_score is None, state is NOT updated.
        """
        if not is_sufficient or raw_score is None:
            # Insufficient evidence does not update rolling smoothed state
            return self.smoothed_score

        self.raw_history.append(raw_score)

        if self.smoothed_score is None:
            # s_0 = x_0
            self.smoothed_score = raw_score
        else:
            # Lower evidence quality moves the average less
            alpha_t = self.alpha_base * (0.5 + 0.5 * float(evidence_quality))
            self.smoothed_score = alpha_t * raw_score + (1.0 - alpha_t) * self.smoothed_score

        self.smoothed_score = round(self.smoothed_score, 4)
        self.smoothed_history.append(self.smoothed_score)
        return self.smoothed_score

    def reset(self) -> None:
        self.smoothed_score = None
        self.raw_history.clear()
        self.smoothed_history.clear()
