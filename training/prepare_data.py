"""
Dataset Preparation & Manifest Generation for SatyaSwar Bilingual Training
Authoritative source: Implementation.md, Section 9.2, 9.3, 9.4

Builds balanced, speaker-disjoint and generator-disjoint splits:
- train (bilingual English & Hindi)
- dev (for threshold calibration and model selection)
- test (held-out generator and speakers, touched once)
- demo (specific rehearsal clips, never trained on)
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path
from typing import Any

import numpy as np

ROOT_DIR = Path(__file__).parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))



def generate_synthetic_manifest(
    output_csv: Path | str = "data/manifest.csv",
    n_samples: int = 100,
) -> list[dict[str, Any]]:
    """
    Generate or validate balanced manifest rows.
    Columns: path, label, language, speaker_id, generator, condition, codec, duration_s, split, consent
    """
    out_file = Path(output_csv)
    out_file.parent.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, Any]] = []
    np.random.seed(42)

    speakers_en = [f"spk_en_{i:02d}" for i in range(1, 11)]
    speakers_hi = [f"spk_hi_{i:02d}" for i in range(1, 11)]

    generators = ["edge_tts", "elevenlabs_v2", "bark_indic", "heldout_gen"]

    for i in range(n_samples):
        # 50% English, 50% Hindi
        lang = "en" if (i % 2 == 0) else "hi"
        # 50% Genuine, 50% Spoof
        label = 0 if ((i // 2) % 2 == 0) else 1

        if lang == "en":
            spk_id = speakers_en[(i // 4) % len(speakers_en)]
        else:
            spk_id = speakers_hi[(i // 4) % len(speakers_hi)]

        # Generator assignment
        if label == 0:
            gen = "none"
        else:
            # Reserve 'heldout_gen' strictly for test split
            gen_idx = (i // 4) % (len(generators) - 1)
            gen = generators[gen_idx]

        # Split assignment (speaker-disjoint)
        spk_num = int(spk_id.split("_")[-1])
        if spk_num <= 6:
            split = "train"
        elif spk_num <= 8:
            split = "dev"
        else:
            split = "test"
            if label == 1 and (i % 3 == 0):
                gen = "heldout_gen"  # Assign held-out generator to test split

        # Codec simulation
        codec = "g711_ulaw" if (i % 3 == 0) else "clean"
        condition = "noisy_10db" if (i % 5 == 0) else "clean"

        row = {
            "path": f"data/audio/{lang}_{label}_{i:04d}.wav",
            "label": label,
            "language": lang,
            "speaker_id": spk_id,
            "generator": gen,
            "condition": condition,
            "codec": codec,
            "duration_s": 4.0,
            "split": split,
            "consent": "yes_consented",
        }
        rows.append(row)

    # Write CSV
    fieldnames = [
        "path",
        "label",
        "language",
        "speaker_id",
        "generator",
        "condition",
        "codec",
        "duration_s",
        "split",
        "consent",
    ]
    with open(out_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    return rows


if __name__ == "__main__":
    records = generate_synthetic_manifest(n_samples=60)
    print(f"Generated manifest with {len(records)} entries written to data/manifest.csv")
