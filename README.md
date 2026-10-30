# SatyaSwar: Real-Time AI/ML Voice Integrity & Impersonation Risk Engine

[![CI](https://github.com/satya-swar/satyaswar-ml/actions/workflows/ci.yml/badge.svg)](https://github.com/satya-swar/satyaswar-ml/actions)
[![Python 3.10](https://img.shields.io/badge/python-3.10-blue.svg)](https://www.python.org/downloads/release/python-3100/)
[![PyTorch 2.9](https://img.shields.io/badge/PyTorch-2.9%2Bcu128-EE4C2C.svg)](https://pytorch.org/)
[![Tests](https://img.shields.io/badge/tests-224%20passed-brightgreen.svg)](tests/)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Latency](https://img.shields.io/badge/p95%20latency-104.3%20ms-success.svg)](docs/baseline-timings.md)

> **Smart India Hackathon (SIH 2026), Problem Statement 26104**  
> **Theme:** Blockchain & Cybersecurity | **Organization:** AICTE Cyber Security Cell  
> **Subsystem Ownership:** Member 3 (AI/ML & ML Integration)

SatyaSwar is an AI/ML-driven voice-integrity and impersonation-risk analysis prototype designed to detect and mitigate voice-cloning fraud during ongoing telephone and VoIP calls. Rather than acting as a naive black-box binary classifier, SatyaSwar provides a four-stage pipeline: **Detect, Score, Decide, and Verify**.

---

## 🏛️ System Architecture

```
[ Incoming Call Audio (PCM16, 16 kHz Mono) ]
                     │
                     ▼
       ┌───────────────────────────┐
       │ In-Memory Circular Buffer │ (Ephemeral RAM, 8.0s RingBuffer)
       └─────────────┬─────────────┘
                     ▼ (3.5s window, 1.75s hop)
       ┌───────────────────────────┐
       │ Silero VAD & SNR Analyzer │ ──> Usable speech seconds, SNR (dB)
       └─────────────┬─────────────┘
                     ├─────────────────────────────────────────┐
                     ▼                                         ▼
       ┌───────────────────────────┐             ┌───────────────────────────┐
       │  Multilingual XLS-R 300M  │             │ Physical Loudspeaker PAD  │
       │  Neural Anti-Spoof Head   │             │ Enclosure Resonance & HF  │
       └─────────────┬─────────────┘             └─────────────┬─────────────┘
                     ▼                                         ▼
              (synthetic_score)                          (replay_score)
                     └───────────────────┬─────────────────────┘
                                         ▼
                     ┌───────────────────────────────────────┐
                     │ Evidence-Weighted Smoothing & Bands   │
                     │ (Hysteresis, Debounce, 6s Throttle)   │
                     └───────────────────┬───────────────────┘
                                         ▼
                     ┌───────────────────────────────────────┐
                     │ Reference Decision Function           │ <── Claimed Context &
                     │ Sensitive Action Hold Matrix          │     Out-of-band Push
                     └───────────────────┬───────────────────┘
                                         ▼
        [ Real-Time Downstream Events to Mobile Client & Live Dashboard ]
```

---

## 🏆 Critical Challenge Hurdles Implemented

In addition to core speech classification, SatyaSwar fulfills the four critical real-world security and privacy challenge requirements:

| # | Challenge Hurdle | Technical Solution & Proof | Key File |
|---|---|---|---|
| **1** | **Detect Synthetic Speech & Replay Attacks** | Decoupled acoustic analysis: separates AI vocoder artifacts (`synthetic_score`) from loudspeaker enclosure resonance & high-frequency rolloff (`replay_score`, `replay_detected`). | [`src/.../detection/replay.py`](src/satyaswar_ml/detection/replay.py) |
| **2** | **Bilingual Fairness & Real Telephony** | Multilingual self-supervised front-end (XLS-R) achieves cross-lingual parity between English (1.25% EER) and Hindi (0.00% EER). Tested against 8 kHz G.711 mu-law compression. Untested regional accents explicitly disclosed. | [`docs/fairness_and_evaluation_report.md`](docs/fairness_and_evaluation_report.md) |
| **3** | **Sensitive Action Verification Gating** | Voice score is a risk signal, not identity proof. High-stakes actions (money transfers, OTPs) are strictly blocked (`no_indicators_verify_before_transfer`) until verified via out-of-band push with fresh 2-digit match codes. | [`src/.../decision/verification.py`](src/satyaswar_ml/decision/verification.py) |
| **4** | **Verifiable Zero-Retention Audio Privacy** | Audio is processed exclusively in transient volatile memory (RAM) and purged immediately post-evaluation. Automated tests verify zero `.wav`/`.pcm` files written to disk. `ML_ENV=demo` prevents debug dumps. | [`docs/privacy_and_data_retention.md`](docs/privacy_and_data_retention.md) |

---

## 🚀 Quick Start

### 1. Installation
SatyaSwar ML requires **Python 3.10**.
```bash
# Clone the repository
git clone https://github.com/satya-swar/satyaswar-ml.git
cd satyaswar-ml

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate       # On Linux/macOS
.venv\Scripts\Activate.ps1       # On Windows PowerShell

# Install dependencies and editable package
pip install -r requirements.txt
pip install -e .
```

### 2. Interactive Hackathon Showcase Runner
Run the judge-ready demonstration script that walks through all 4 challenge hurdles with live output:
```bash
python scripts/demo_showcase.py
```

### 3. Run Real-Time Stream Simulation
Start the standalone WebSocket server and simulate an incoming call:
```bash
# Terminal 1: Start ML Server
uvicorn satyaswar_ml.adapters.ws_app:app --host 127.0.0.1 --port 8100

# Terminal 2: Stream audio clip through telephony filter
python scripts/stream_wav.py assets/scenarios/clone_hi_01.wav --telephony g711_ulaw
```

### 4. Run Test Suite
```bash
pytest -v
```
*(All 224 unit, contract, and integration tests execute in ~11 seconds).*

### 5. Benchmark Latency
```bash
python scripts/bench_latency.py
```
*(Runs 100 windows through telephony, VAD, detector, and scoring; updates `docs/baseline-timings.md`).*

---

## 📦 Integration Contract

SatyaSwar ML provides a single core engine with two integration interfaces:

### In-Process Library (Python Backend)
```python
from satyaswar_ml import AnalysisEngine, SessionConfig, Contact

# Load once at startup and warm up
engine = AnalysisEngine.from_config("configs/default.yaml")
await engine.warmup()

# Start session
session, ready_ev = engine.start_session(
    call_id="call_999",
    config=SessionConfig(mode="chunks", telephony_profile="g711_ulaw"),
    contacts=[Contact(contact_id="c1", display_name="Priyanka Sharma", aliases=["Priti"])],
)

# Push binary audio chunk (12-byte header + PCM16LE samples)
events = await session.push_audio(binary_frame)
for ev in events:
    print(ev.model_dump_json())

# End session and retrieve summary
summary = await session.end()
```

### Binary Audio Framing Format
Audio is transmitted over WebSocket as binary frames:
- **Header (12 bytes):**
  - `uint32 seq` (4 bytes, little-endian sequence number)
  - `uint64 client_ts_ms` (8 bytes, little-endian millisecond timestamp)
- **Payload:** Raw 16 kHz 16-bit Mono PCMLE samples.
  - Chunk mode: 28,000 samples (1.75 s = 56,000 bytes)
  - Window mode: 56,000 samples (3.5 s = 112,000 bytes)

---

## 📊 Key Performance Metrics

| Metric | Measured Value | Standard Target | Status |
|---|---|---|---|
| **EER (Clean Speech)** | **0.00%** | < 5.0% | Exceeded |
| **EER (G.711 Phone Line)** | **0.83%** | < 10.0% | Exceeded |
| **p95 Total Latency** | **104.3 ms** | < 500 ms | Exceeded |
| **Real-Time Factor (RTF)** | **0.0298** | < 1.00 | Real-Time Validated |
| **False Alarms on Genuine (0.65 th)** | **0.00%** | < 2.0% | Zero False Alarms |

---

## 📚 Repository Structure & Documentation

```
satyaswar_ml/
├── assets/
│   ├── alerts/             # 12 Bilingual WAV alerts (EN & HI)
│   ├── fixtures/events/    # 12 Validated contract JSON fixtures
│   └── scenarios/          # 6 Realistic audio scenarios (genuine, clone, noisy)
├── configs/
│   ├── default.yaml        # Core engine & VAD parameters
│   ├── thresholds.yaml     # Calibrated low_max / high_min thresholds
│   ├── keywords.yaml       # Multilingual context lexicon (EN, Hinglish, Devanagari)
│   └── scenarios.json      # Scenario manifest
├── docs/
│   ├── contract.md         # Full REST/WebSocket integration specification
│   ├── events.schema.json  # Exported JSON Schema for mobile & backend
│   ├── openapi.json        # Exported OpenAPI 3.1 specification
│   ├── baseline-timings.md # Hardware latency benchmark reports
│   ├── fairness_and_evaluation_report.md # Fairness and slice evaluation
│   └── privacy_and_data_retention.md     # Zero-retention privacy policy
├── eval/
│   ├── calibrate.py        # low_max and high_min threshold calibration
│   ├── metrics.py          # EER, minDCF, slice fairness math
│   ├── report.py           # Markdown generator & DET curve plotter
│   └── run_eval.py         # Slice evaluation harness
├── scripts/
│   ├── bench_latency.py    # 100-window latency benchmark
│   ├── demo_showcase.py    # Official hackathon showcase script
│   ├── export_schemas.py   # Schema & OpenAPI exporter
│   ├── make_alert_audio.py # Bilingual TTS alert generator
│   ├── make_scenarios.py   # Scenario WAV synthesizer
│   └── stream_wav.py       # Client audio stream simulator
├── src/satyaswar_ml/       # Core ML subsystem
│   ├── audio/              # I/O, windowing, ring buffer, telephony
│   ├── decision/           # Decision matrix & verification workflow
│   ├── detection/          # Replay & acoustic presentation attack detection
│   ├── detector/           # XLS-R detector wrapper & registry
│   ├── scoring/            # Smoothing, hysteresis, risk bands, why builder
│   ├── nlp/ & asr/         # Transliteration, keywords, contact matching, Whisper
│   └── adapters/           # In-process engine, mock adapter, FastAPI WS service
├── tests/                  # 224 automated unit, contract, and integration tests
└── training/               # Data preparation, augmentation, and DeepFense configs
```

---

## ⚖️ License & Ethical Declaration

Distributed under the **Apache 2.0 License**. See [LICENSE](LICENSE) for details.

**Ethical AI & Consent:**
- Voice synthesis models are restricted strictly to defensive detection benchmarks.
- No public figure or non-consenting individual voiceprints were collected or stored.
- Audio streams are processed strictly in volatile memory in alignment with the **Digital Personal Data Protection (DPDP) Act 2023** data minimization principles.
