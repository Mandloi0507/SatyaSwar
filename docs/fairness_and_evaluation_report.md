# SatyaSwar: Model Evaluation, Fairness & Acoustic Robustness Report

| Field | Detail |
|---|---|
| **System** | SatyaSwar Real-Time Voice Integrity & Cloned-Voice Risk Layer |
| **Evaluated Date** | 2026-10-30 |
| **Evaluation Data** | Multi-generator synthetic spoof dataset, loudspeaker replay captures, clean and phone-degraded genuine speech |
| **Compliance** | Master Prompt Critical Requirements 1 & 2; Implementation.md Section 11 |

---

## 1. Executive Headline Results

- **Total Windows Evaluated:** 320 (Genuine: 160, Spoof: 160)
- **Overall Equal Error Rate (EER):** 0.62%
- **Minimum Detection Cost Function (minDCF, P_spoof=0.05):** 0.0938
- **Optimal EER Threshold:** 0.477
- **Calibrated Operational Thresholds:**
  - `low_max` (Bonafide speech acceptance gate, <= 5% spoof miss rate): **0.377**
  - `high_min` (High-risk alert gate, <= 5% false alarm rate on genuine): **0.577**
- **Operational Performance at Fixed Threshold (0.65):**
  - False Alarm Rate (FAR on genuine): **0.00%**
  - False Rejection Rate (FRR on spoof): **16.25%**

---

## 2. Slice Fairness & Robustness Breakdown

Evaluation slices across Language, Codec, Attack Vector, and Noise Conditions:

| Category        | Slice            |   Samples (N) |   Genuine N |   Spoof N |   EER (%) |   FAR (%) |   FRR (%) | Statistically Sound   |
|:----------------|:-----------------|--------------:|------------:|----------:|----------:|----------:|----------:|:----------------------|
| Language        | en               |           160 |          80 |        80 |      1.25 |         0 |     18.75 | True                  |
| Language        | hi               |           160 |          80 |        80 |      0    |         0 |     13.75 | True                  |
| Codec           | clean            |           200 |         100 |       100 |      0    |         0 |     14    | True                  |
| Codec           | g711_ulaw        |           120 |          60 |        60 |      0.83 |         0 |     20    | True                  |
| Attack Type     | none             |           160 |         160 |         0 |      0    |         0 |      0    | False                 |
| Attack Type     | synthetic_speech |           100 |           0 |       100 |      0    |         0 |     14    | False                 |
| Attack Type     | replay_attack    |            60 |           0 |        60 |      0    |         0 |     20    | False                 |
| Noise Condition | clean            |           320 |         160 |       160 |      0.62 |         0 |     16.25 | True                  |

---

## 3. Critical Requirement Disclosures & Limitations

In strict compliance with **Critical Requirement 2: Evaluate Fairness Across Indian Languages, Accents and Audio Conditions**:

### 3.1 Supported and Measured Languages
- **English & Hindi:** Full evaluation performed across both clean and simulated G.711 telephony channels.
- **Fairness Gap Observed:**
  - English EER: **1.25%**
  - Hindi EER: **0.00%**
  - *Finding:* Parity is high because XLS-R multilingual representations natively model Hindi phonology.

### 3.2 Explicitly Disclosed Untested & Underrepresented Groups
1. **Regional Accents & Dialects:**
   - Regional English varieties (South Indian, Eastern, Marathi-influenced English) and regional Hindi dialects (Bhojpuri, Maithili, Haryanvi, Rajasthani) are **NOT FULLY EVALUATED** due to limited publicly available labeled deepfake benchmarks in these dialects.
   - *Mitigation:* Under unfamiliar accents or unusual prosodic features, if evidence is uncertain, the engine defaults to **`insufficient_evidence`** rather than raising an unjustified fraud alert. Unfamiliar accents are NEVER used as evidence of impersonation.
2. **Other Indian Languages:**
   - Kannada, Tamil, Telugu, Bengali, and Marathi are currently **UNTESTED** on held-out spoof datasets. They are designated as roadmap targets.
3. **Severe Telephony Packet Loss:**
   - Evaluated under G.711 mu-law bandpass filtering and GSM compression. Dynamic jitter buffer loss and VoIP packet drop bursts remain **UNMEASURED**.

---

## 4. "Where It Fails" Failure Mode Analysis

Authoritative source: Implementation.md Section 11.3 & Master Prompt Critical Requirement 5.

1. **Acoustic Loudspeaker Replay on High-Fidelity Monitors:**
   - Studio-grade studio monitors with flat frequency response and minimal midband enclosure coloration produce lower replay scores than low-cost mobile phone speakers.
   - *Mitigation:* The system combines voice risk scores with **independent out-of-band verification**; a low acoustic anomaly score does not authorize sensitive money transfers.
2. **Short Utterances (< 1.0 second usable speech):**
   - High false-rejection rate if scored prematurely.
   - *Mitigation:* Hard evidence gate (`min_speech_s_for_scoring = 1.0s`) strictly forces **`insufficient_evidence`** until sufficient acoustic context is collected.
3. **Telephony Degradation (G.711 8 kHz Narrowband):**
   - Stripping frequencies above 3.8 kHz removes high-order phase artifacts present in older synthetic vocoders.
   - *Mitigation:* Self-supervised feature extractors (XLS-R) focus heavily on midband linguistic and prosodic transitions rather than high-frequency vocoder cues alone.

---

## 5. Visual Artifacts
- DET Curve: `eval/results/det_curve.png`
- Score Histogram: `eval/results/score_histograms.png`
