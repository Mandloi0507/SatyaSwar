"""
Evaluation metrics for voice integrity and anti-spoofing detection.
Authoritative source: Implementation.md, Section 11.1 & Critical Requirement 2.

Calculates:
- Equal Error Rate (EER) and operating threshold.
- Minimum Detection Cost Function (minDCF) with Pspoof=0.05.
- FAR and FRR at fixed risk thresholds.
- Confusion matrix and abstain rate.
- Fairness breakdown across language, accent, and channel slices.
"""

from __future__ import annotations

from typing import Any

import numpy as np
from sklearn.metrics import confusion_matrix, roc_curve


def compute_eer(
    y_true: np.ndarray,
    y_scores: np.ndarray,
) -> tuple[float, float]:
    """
    Compute Equal Error Rate (EER) and optimal operating threshold.
    y_true: binary labels (0 = genuine/bonafide, 1 = spoof/replay).
    y_scores: continuous scores in [0.0, 1.0], higher = more likely spoof.
    Returns (eer, threshold).
    """
    if len(y_true) == 0 or len(np.unique(y_true)) < 2:
        return 0.0, 0.5

    fpr, tpr, thresholds = roc_curve(y_true, y_scores, pos_label=1)
    fnr = 1.0 - tpr

    # Find the operating point where |fpr - fnr| is minimized
    idx = np.nanargmin(np.abs(fpr - fnr))
    eer = float((fpr[idx] + fnr[idx]) / 2.0)
    thresh = float(thresholds[idx]) if idx < len(thresholds) else 0.5
    return round(eer, 4), round(thresh, 4)


def compute_mindcf(
    y_true: np.ndarray,
    y_scores: np.ndarray,
    p_spoof: float = 0.05,
    c_miss: float = 1.0,
    c_fa: float = 1.0,
) -> float:
    """
    Compute Normalized Minimum Detection Cost Function (minDCF).
    Standard ASVspoof cost metric.
    """
    if len(y_true) == 0 or len(np.unique(y_true)) < 2:
        return 0.0

    fpr, tpr, _ = roc_curve(y_true, y_scores, pos_label=1)
    fnr = 1.0 - tpr

    dcf = c_miss * p_spoof * fnr + c_fa * (1.0 - p_spoof) * fpr
    dcf_default = min(c_miss * p_spoof, c_fa * (1.0 - p_spoof))
    min_dcf = float(np.min(dcf) / dcf_default)
    return round(min_dcf, 4)


def compute_rates_at_threshold(
    y_true: np.ndarray,
    y_scores: np.ndarray,
    threshold: float,
) -> dict[str, float]:
    """
    Compute False Acceptance Rate (FAR/FPR) and False Rejection Rate (FRR/FNR)
    at a specific operational decision threshold.
    """
    if len(y_true) == 0:
        return {"far": 0.0, "frr": 0.0, "accuracy": 0.0}

    y_pred = (y_scores >= threshold).astype(int)
    cm = confusion_matrix(y_true, y_pred, labels=[0, 1])
    tn, fp, fn, tp = cm.ravel()

    far = float(fp / (tn + fp)) if (tn + fp) > 0 else 0.0
    frr = float(fn / (tp + fn)) if (tp + fn) > 0 else 0.0
    acc = float((tp + tn) / len(y_true))

    return {
        "far": round(far, 4),
        "frr": round(frr, 4),
        "accuracy": round(acc, 4),
        "tp": int(tp),
        "tn": int(tn),
        "fp": int(fp),
        "fn": int(fn),
    }


def evaluate_slice_fairness(
    eval_records: list[dict[str, Any]],
    slice_key: str = "language",
    threshold: float = 0.65,
) -> dict[str, dict[str, Any]]:
    """
    Break down performance metrics across demographic and acoustic slices:
    - Language (English, Hindi, Hinglish)
    - Regional accent / speech variety
    - Audio channel (clean, telephone, noisy)
    - Attack category (synthetic speech vs replay attack)
    """
    slices: dict[str, list[dict[str, Any]]] = {}
    for r in eval_records:
        val = str(r.get(slice_key, "unknown"))
        slices.setdefault(val, []).append(r)

    results: dict[str, dict[str, Any]] = {}
    for slice_val, records in slices.items():
        y_true = np.array([r["label"] for r in records], dtype=int)
        y_scores = np.array([r["score"] for r in records], dtype=float)

        n_genuine = int(np.sum(y_true == 0))
        n_spoof = int(np.sum(y_true == 1))

        eer, opt_thresh = compute_eer(y_true, y_scores)
        rates = compute_rates_at_threshold(y_true, y_scores, threshold)

        results[slice_val] = {
            "n_samples": len(records),
            "n_genuine": n_genuine,
            "n_spoof": n_spoof,
            "eer": eer,
            "optimal_threshold": opt_thresh,
            "far": rates["far"],
            "frr": rates["frr"],
            "accuracy": rates["accuracy"],
            "is_statistically_sound": (n_genuine >= 10 and n_spoof >= 10),
        }

    return results
