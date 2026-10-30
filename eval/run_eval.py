"""
Evaluation harness and fairness benchmark execution across slices.
Authoritative source: Implementation.md, Section 11.2, 11.3 & Critical Requirement 2.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

ROOT_DIR = Path(__file__).parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from eval.calibrate import calibrate_thresholds
from eval.metrics import (
    compute_eer,
    compute_mindcf,
    compute_rates_at_threshold,
    evaluate_slice_fairness,
)


def run_evaluation_suite(
    records: list[dict[str, Any]],
    output_dir: str | Path = "eval/results",
) -> dict[str, Any]:
    """
    Run full evaluation and fairness analysis over provided manifest records.
    Outputs:
    - eval/results/fairness_summary.json
    - eval/results/slice_metrics.csv
    """
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    y_true = np.array([r["label"] for r in records], dtype=int)
    y_scores = np.array([r["score"] for r in records], dtype=float)

    # 1. Overall Headline Metrics
    overall_eer, opt_thresh = compute_eer(y_true, y_scores)
    overall_mindcf = compute_mindcf(y_true, y_scores)
    rates_065 = compute_rates_at_threshold(y_true, y_scores, threshold=0.65)
    low_max, high_min, _ = calibrate_thresholds(y_true, y_scores)

    # 2. Slice Breakdown (Language, Codec, Attack Type, Noise)
    lang_slices = evaluate_slice_fairness(records, slice_key="language", threshold=0.65)
    codec_slices = evaluate_slice_fairness(records, slice_key="codec", threshold=0.65)
    attack_slices = evaluate_slice_fairness(records, slice_key="attack_type", threshold=0.65)
    noise_slices = evaluate_slice_fairness(records, slice_key="noise_condition", threshold=0.65)

    summary = {
        "headline": {
            "n_total": len(records),
            "n_genuine": int(np.sum(y_true == 0)),
            "n_spoof": int(np.sum(y_true == 1)),
            "overall_eer": overall_eer,
            "overall_mindcf": overall_mindcf,
            "optimal_threshold": opt_thresh,
            "calibrated_thresholds": {"low_max": low_max, "high_min": high_min},
            "far_at_065": rates_065["far"],
            "frr_at_065": rates_065["frr"],
        },
        "fairness_by_language": lang_slices,
        "robustness_by_codec": codec_slices,
        "performance_by_attack_type": attack_slices,
        "performance_by_noise": noise_slices,
    }

    # Save summary JSON
    json_path = out_path / "fairness_summary.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    # Build CSV for table display
    rows = []
    for category, slices in [
        ("Language", lang_slices),
        ("Codec", codec_slices),
        ("Attack Type", attack_slices),
        ("Noise Condition", noise_slices),
    ]:
        for slice_name, metrics in slices.items():
            rows.append({
                "Category": category,
                "Slice": slice_name,
                "Samples (N)": metrics["n_samples"],
                "Genuine N": metrics["n_genuine"],
                "Spoof N": metrics["n_spoof"],
                "EER (%)": round(metrics["eer"] * 100, 2),
                "FAR (%)": round(metrics["far"] * 100, 2),
                "FRR (%)": round(metrics["frr"] * 100, 2),
                "Statistically Sound": metrics["is_statistically_sound"],
            })

    df = pd.DataFrame(rows)
    csv_path = out_path / "slice_metrics.csv"
    df.to_csv(csv_path, index=False)

    return summary


def get_demo_records() -> list[dict[str, Any]]:
    np.random.seed(42)
    records = []

    # 1. Genuine English & Hindi (clean, phone, noisy)
    for lang in ["en", "hi"]:
        for _ in range(50):
            score = float(np.clip(np.random.beta(1.5, 8.0), 0.02, 0.50))
            records.append({
                "label": 0,
                "score": score,
                "language": lang,
                "codec": "clean",
                "attack_type": "none",
                "noise_condition": "clean",
            })
        for _ in range(30):
            # Telephony compression adds slight variance
            score = float(np.clip(np.random.beta(2.0, 7.0), 0.05, 0.60))
            records.append({
                "label": 0,
                "score": score,
                "language": lang,
                "codec": "g711_ulaw",
                "attack_type": "none",
                "noise_condition": "clean",
            })

    # 2. Synthetic Clones (English & Hindi)
    for lang in ["en", "hi"]:
        for _ in range(50):
            score = float(np.clip(np.random.beta(8.0, 2.0), 0.50, 0.98))
            records.append({
                "label": 1,
                "score": score,
                "language": lang,
                "codec": "clean",
                "attack_type": "synthetic_speech",
                "noise_condition": "clean",
            })

    # 3. Replay Attacks
    for lang in ["en", "hi"]:
        for _ in range(30):
            score = float(np.clip(np.random.beta(7.5, 2.5), 0.45, 0.95))
            records.append({
                "label": 1,
                "score": score,
                "language": lang,
                "codec": "g711_ulaw",
                "attack_type": "replay_attack",
                "noise_condition": "clean",
            })

    return records


if __name__ == "__main__":
    records = get_demo_records()
    res = run_evaluation_suite(records)
    print("Evaluation completed successfully! Results written to eval/results/")

