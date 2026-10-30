"""
Threshold calibration workflow for SatyaSwar ML risk engine.
Authoritative source: Implementation.md, Section 11.4
"""

from __future__ import annotations

import numpy as np

from eval.metrics import compute_eer


def calibrate_thresholds(
    y_true: np.ndarray,
    y_scores: np.ndarray,
    target_fpr: float = 0.05,
    target_fnr: float = 0.05,
) -> tuple[float, float, float]:
    """
    Calibrate (low_max, high_min, eer) on dev split:
    - high_min is set where FPR on genuine speech is <= target_fpr (e.g. 5%).
    - low_max is set where FNR on spoof speech is <= target_fnr (e.g. 5%).
    """
    eer, eer_thresh = compute_eer(y_true, y_scores)

    genuine_scores = y_scores[y_true == 0]
    spoof_scores = y_scores[y_true == 1]

    if len(genuine_scores) > 0:
        # 95th percentile of genuine scores -> false alarms on genuine <= 5%
        high_min = float(np.percentile(genuine_scores, 100.0 * (1.0 - target_fpr)))
    else:
        high_min = max(0.65, eer_thresh + 0.15)

    if len(spoof_scores) > 0:
        # 5th percentile of spoof scores -> misses on spoof <= 5%
        low_max = float(np.percentile(spoof_scores, 100.0 * target_fnr))
    else:
        low_max = min(0.35, eer_thresh - 0.15)

    # Ensure low_max < high_min with sensible bounds
    if low_max >= high_min:
        low_max = max(0.10, eer_thresh - 0.10)
        high_min = min(0.90, eer_thresh + 0.10)

    return round(low_max, 3), round(high_min, 3), round(eer, 3)
