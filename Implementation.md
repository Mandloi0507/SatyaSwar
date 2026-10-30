# SatyaSwar: AI/ML Implementation Plan

| | |
| --- | --- |
| **Project** | SatyaSwar, real-time voice integrity layer (SIH 2026, PS 26104) |
| **Owner of this document** | Member 3, AI/ML and ML integration |
| **Source of truth for product behaviour** | `SatyaSwar_Complete_Solution_Document_1.md` |
| **Source of truth for ML implementation** | This file |
| **Source of truth for integration** | Section 6 (contract). Members 1 and 2 build against it |
| **Primary languages** | English and Hindi (Kannada is an optional stretch) |
| **Status** | Draft v1. Everything marked *suggested default* or *placeholder* must be confirmed by measurement or team agreement |

---

## 0. How to use this document

This file has three readers:

1. **You**, to plan and track the ML work.
2. **The setup-guide AI** that walks you through environment setup. Give it Sections 2 to 4, and use the ready-made prompt in 3.8.
3. **The Antigravity agent** that writes the code. Give it Sections 1, 2, 4, 6, 7 and the prompt pack in Section 17, one milestone at a time.

Conventions:

- **MUST** means required for the demo. **SHOULD** means do it unless time runs out. **MAY** means optional.
- *Suggested default* means a number or choice I picked as a sensible starting point, not a measured result. Change it when your data says otherwise.
- *Placeholder* means the value is a stand-in until calibration on your own clips (for example risk thresholds).
- Package versions are deliberately not pinned here. Pin them yourself in Phase 0 after the verification scripts in 3.6 pass, then freeze with `pip freeze`.
- Model and dataset names in Section 2.2 and Section 9 were confirmed to exist on their public pages or package listings while writing this plan. **Their accuracy, licences and access conditions were not tested.** Check each before relying on it.

---

## 1. Scope, ownership and boundaries

### 1.1 What you own

| # | Deliverable | Section |
| --- | --- | --- |
| 1 | Audio preprocessing, windowing, VAD, SNR and evidence quality | 7 |
| 2 | Anti-spoofing detector (baseline bake-off, fine-tuning, wrapper) in English and Hindi | 7, 8, 10 |
| 3 | Score smoothing, risk bands with hysteresis, three-way outcome | 7 |
| 4 | ASR (faster-whisper) with language detection, keyword and context rules in English, Hinglish and Devanagari | 7 |
| 5 | Claimed-identity matching against a caller-supplied contact list | 7 |
| 6 | Telephony simulation (8 kHz codec chains) | 7 |
| 7 | "Why flagged" evidence builder (computed items only) | 7 |
| 8 | Bilingual alert text and alert audio clips | 7, 12 |
| 9 | Evaluation harness and the honest results slide | 11 |
| 10 | Demo scenario audio (genuine and consented clones, English and Hindi) | 12 |
| 11 | The integration package: schemas, mock mode, Python API, WebSocket adapter, stream simulator | 6 |
| 12 | Reference decision function (hand-over to Member 2) | Appendix D |

### 1.2 What you do not own

Flutter app and web dashboard (Member 1). Firebase, auth, invite linking, verification state machine, Firestore rules, the production WebSocket server and history storage (Member 2). You provide them a clean, tested ML package and a contract.

### 1.3 Definition of "integration-ready"

The ML side is integration-ready when all of these are true:

- [ ] A single installable Python package (`pip install -e ml/`) exposes `AnalysisEngine` and `CallSession` (6.6).
- [ ] Every message in and out is defined as a Pydantic model, with exported JSON Schema and an OpenAPI file committed to `ml/docs/`.
- [ ] A **mock mode** returns scripted, clearly labelled results with no GPU, so Members 1 and 2 are never blocked on you.
- [ ] A **stream simulator** script behaves like the Flutter app (sends a WAV as chunks over WebSocket) and prints every event and latency.
- [ ] `GET /ml/health` reports model loaded, device, versions and warm-up latency.
- [ ] Config is entirely in YAML plus environment variables. No constants buried in code.
- [ ] No audio and no transcript is ever written to disk or logs by default.
- [ ] Contract tests pass in CI or a local `make test` run, and any contract change bumps `schema_version`.

### 1.4 Deviations from the solution document (agree these with the team)

| # | Solution document | This plan | Why |
| --- | --- | --- | --- |
| V1 | Hindi and Kannada evaluated | **English and Hindi are the primary targets**; Kannada only if time remains | Your demo is in English and Hindi |
| V2 | App sends each 3.5 s window (1.75 s hop), so audio overlaps 50% | **Recommended: app sends non-overlapping 1.75 s chunks and the engine builds the 3.5 s windows.** Window mode stays supported | Halves upload bandwidth, makes windowing a server concern, same timing (first score at 3.5 s, then every 1.75 s) |
| V3 | One global threshold set | Global thresholds plus **optional per-language threshold sets**, used only if evaluation shows it helps | Score distributions often shift by language |
| V4 | Decision function in the backend | Backend owns it in production; ML provides a **reference implementation and tests** (Appendix D) and flags gaps in the table | Avoids two diverging copies |
| V5 | ML runs inside the FastAPI server | ML is a **library first, service second**: one engine with two adapters (in-process, standalone WebSocket) | Lets the backend choose without rework |

---

## 2. Technology stack

### 2.1 Stack table

| Layer | Choice | Role | Fallback | Notes |
| --- | --- | --- | --- | --- |
| Language | **Python 3.10** | Everything ML | 3.11 if all packages install | DeepFense documents 3.10. Stay on it |
| Deep learning | **PyTorch 2.x**, torchaudio | Detector, resampling | CPU build | Install from the official selector for your CUDA version |
| Detector framework | **DeepFense** (`pip install deepfense`) | YAML-configured training and evaluation, pretrained checkpoints via Hugging Face Hub | Plain PyTorch plus `transformers` | Pure Python/PyTorch, no fairseq needed. Frontends include Wav2Vec2, WavLM, HuBERT. Backends include AASIST, Nes2Net, ECAPA-TDNN, RawNet2, MLP, TCM |
| Detector front-end | **XLS-R 300M** (`facebook/wav2vec2-xls-r-300m`) | Multilingual self-supervised features (pretrained on many languages including Hindi) | WavLM-base or wav2vec2-base for CPU speed | Main reason for good Hindi behaviour |
| Detector head | **AASIST** (default), Nes2Net or SLS-style as experiments | Spoof/bonafide classifier | MLP head | Keep head swappable through the registry |
| Model loading | `transformers`, `safetensors`, `huggingface_hub` | Download and load checkpoints | | Needs a Hugging Face token for gated models |
| VAD | **Silero VAD** (`silero-vad`) | Speech segments, usable speech seconds | WebRTC VAD (`webrtcvad`) | Run on CPU |
| ASR | **faster-whisper** (CTranslate2) | Transcript, language ID, claimed name, keywords | Whisper on CPU int8 | Benchmark `small`, `medium`, `large-v3-turbo` style models on your own Hindi lines |
| Fuzzy matching | **rapidfuzz** | Contact name matching | `difflib` | |
| Transliteration | **indic-transliteration** | Devanagari to Latin keys | Hand-written map for the 200 most common Indian names | Pick one library, test with 30 real names |
| Audio I/O | `soundfile`, `numpy`, `scipy`, `librosa` | Read/write WAV, resample, F0 and pause stats | | |
| Codec simulation | **ffmpeg** plus Python `audioop` (3.10 only) | G.711 mu-law/A-law in memory, AMR/Opus/GSM through ffmpeg | G.711 only | Check `ffmpeg -encoders` for AMR support |
| Schemas | **Pydantic v2** | The contract | | Export JSON Schema |
| Service adapter | **FastAPI**, Uvicorn, `websockets` | Standalone WebSocket service and REST for ML | | Same framework as the backend, so mounting is trivial |
| Data tooling | `datasets`, `pandas`, `scikit-learn`, `jiwer`, `matplotlib` | Dataset loading (streaming), EER and confusion matrices, ASR WER, plots | | |
| Synthetic data (consented use only) | `edge-tts`, open Indic TTS models, a commercial cloning tool free tier | Generate Hindi and English spoof clips | See Section 9 | Check each tool's licence and terms |
| Testing | `pytest`, `pytest-asyncio`, `httpx`, `websockets` client | Unit, contract, integration | | |
| Code quality | `ruff`, `mypy` (light) | Lint, types | | Keep it cheap |
| Training compute | **Colab or Kaggle GPU**, or local GPU | Fine-tuning | Frozen front-end training on a smaller GPU | Time-box to 2 to 3 hours |
| IDE and agent | **Google Antigravity** | Code generation from this plan | | Keep prompts small and milestone-based (Section 17) |
| Experiment records | CSV and JSON files committed under `ml/eval/results/` | Reproducible numbers for the slides | Optional: TensorBoard | Do not add a heavy tracker |

### 2.2 Detector candidates for the bake-off

These are starting points to test, not recommendations on accuracy.

| Candidate | Where | What it is | Watch out for |
| --- | --- | --- | --- |
| DeepFense pretrained checkpoints | Hugging Face org `DeepFense` (use `deepfense download list-models --filter Wav2Vec2`) | Many checkpoints, each trained on a single dataset such as ASVspoof 2019 or CtrSVDD | Single-dataset training tends to overfit to its domain; DeepFense's own paper reports domain overfitting. One listed model uses XLS-R-2B and is about 25 GB, so skip it |
| `eliya/forensics_0.3B_xlsr_wild_deepfake_classifier` | Hugging Face | XLS-R 300M plus AASIST, safetensors, described as tuned for real-world audio, 16 kHz mono, padded or trimmed to 5 s | Read its licence and access terms; claims are the author's |
| `sukhdeveyash/XLS-R-SLS-Deepfake-Detection` (v1) | Hugging Face | Reproduction of the XLS-R plus SLS classifier paper; model card says MIT; trained on English ASVspoof data | Needs fairseq and an old PyTorch, which is painful. Try it only if you have spare time; if it wins clearly, budget at most one hour to run it in a separate environment |
| `SpeechAntiSpoofingBenchmarks/XLSR-SLS` | Hugging Face | Another XLS-R 300M plus SLS packaging | Also fairseq-based |
| **Your own fine-tune** | Section 10 | XLS-R 300M plus AASIST trained on English plus Hindi plus telephony augmentation | Needs data work, but is the only option that targets Hindi and phone audio directly |

### 2.3 Which plan fits your machine

| Your laptop | Detector plan | ASR plan | Notes |
| --- | --- | --- | --- |
| NVIDIA GPU with 6 GB or more VRAM | XLS-R 300M fp16 | faster-whisper `small` or `medium` on GPU | Best case. Both models fit |
| NVIDIA GPU under 6 GB | XLS-R 300M fp16, Whisper on CPU int8 | `small` on CPU | Whisper is off the critical path, so CPU is acceptable |
| No NVIDIA GPU (Mac or integrated) | Smaller WavLM-base or wav2vec2-base detector, or run XLS-R on a cloud GPU endpoint you control | `small` on CPU | Expect weaker generalisation; say so honestly. Measure per-window time against the 1.75 s hop |

If you are on Windows with an NVIDIA GPU, WSL2 with Ubuntu is usually the smoothest route for CUDA, ffmpeg and Python tooling. Native Windows also works but has more version-matching friction (CUDA and cuDNN for PyTorch versus CTranslate2).

---

## 3. Environment setup

You do this part yourself with the setup-guide AI. Do the steps in order and do not skip the verification scripts.

### 3.1 Accounts and access

- [ ] Hugging Face account and an access token (read). Accept terms for any gated model or dataset you plan to use.
- [ ] Google account for Colab, and optionally Kaggle (free GPU quota).
- [ ] GitHub repository shared with Members 1 and 2. You work in the `ml/` folder only.
- [ ] Google Antigravity installed and signed in.

### 3.2 System tools

- [ ] Git
- [ ] Python 3.10 (via `pyenv`, conda or the system installer)
- [ ] **ffmpeg** on PATH (`ffmpeg -version` works)
- [ ] NVIDIA driver and CUDA runtime that match the PyTorch build you will install (`nvidia-smi` works). Skip if no GPU.
- [ ] A free disk budget of at least 40 GB (models, dataset subsets, checkpoints)

### 3.3 Create the environment

```bash
# from the repo root
mkdir -p ml && cd ml
python3.10 -m venv .venv            # or: conda create -n satyaswar-ml python=3.10
source .venv/bin/activate           # Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install --upgrade pip wheel setuptools
```

### 3.4 Install order (order matters)

1. **PyTorch and torchaudio** from the official selector at pytorch.org for your CUDA version (or the CPU build).
2. Core ML libraries:
   ```bash
   pip install transformers safetensors huggingface_hub datasets soundfile librosa scipy numpy pandas scikit-learn matplotlib jiwer pyyaml python-dotenv
   ```
3. Detector framework: `pip install deepfense`
4. Audio and NLP: `pip install silero-vad faster-whisper rapidfuzz indic-transliteration edge-tts`
5. Service and tests: `pip install fastapi "uvicorn[standard]" websockets pydantic httpx pytest pytest-asyncio ruff`
6. Log in to Hugging Face: `huggingface-cli login` (or `hf auth login`, depending on the installed version).
7. Freeze versions once everything works: `pip freeze > requirements.lock.txt`.

If a package conflicts with PyTorch, stop and fix it before continuing. Do not install fairseq unless Section 2.2 sends you there.

### 3.5 Project skeleton

Create the folder layout from Section 4 (empty files are fine), `git init` or commit to the shared repo, add `.gitignore` entries for `.venv/`, `data/`, `models/`, `*.wav` outside `assets/`, `.env`.

### 3.6 Verification scripts (all must pass before Phase 1)

| ID | Check | Command or action | Expected |
| --- | --- | --- | --- |
| V1 | Python | `python --version` | 3.10.x |
| V2 | ffmpeg | `ffmpeg -version` and `ffmpeg -encoders \| grep -i -E "amr\|opus\|gsm"` | Version prints; note which codecs exist |
| V3 | GPU | `python -c "import torch;print(torch.__version__, torch.cuda.is_available())"` | `True` on a GPU machine |
| V4 | Hugging Face | `huggingface-cli whoami` | Your username |
| V5 | DeepFense | `deepfense list` and `deepfense download list-models --filter WavLM` | Component lists and model names print |
| V6 | XLS-R load | Load `facebook/wav2vec2-xls-r-300m` with `transformers`, run one 4 s random tensor, print output shape and time | Shape `[1, ~200, 1024]`; first call slow, second call fast |
| V7 | VAD | Run Silero VAD on a 10 s recording of you speaking Hindi, then English | Speech segments found, silence excluded |
| V8 | ASR | Transcribe a 10 s Hindi clip and a 10 s English clip with faster-whisper; print detected language and time | Correct languages; note latency |
| V9 | rapidfuzz and transliteration | Transliterate `प्रिया` and `अभिषेक`; fuzzy-match to `Priya` and `Abhishek` | Match score above 80 |
| V10 | Audio round trip | Read a WAV, resample to 16 kHz mono, write it, open it in an audio player | Plays correctly |
| V11 | Test runner | `pytest -q` on an empty test | Exits cleanly |

Write the printed results of V6 and V8 into `ml/docs/baseline-timings.md`. They seed the latency budget in Section 13.

### 3.7 Common failures

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| `torch.cuda.is_available()` is False | CPU wheel installed or driver mismatch | Reinstall PyTorch from the selector for your CUDA version |
| faster-whisper crashes on GPU with a cuDNN or cuBLAS error | CUDA and cuDNN versions needed by CTranslate2 differ from PyTorch's | Follow the faster-whisper README for its CUDA requirements, or run Whisper on CPU with `compute_type="int8"` |
| Hugging Face download returns 401 or 403 | Not logged in or terms not accepted | Log in; open the model page and accept terms |
| `audioop` import error | Python 3.13 removed it | Stay on Python 3.10, or switch the G.711 code to ffmpeg |
| Out of memory loading XLS-R | Another process holds the GPU | Close it; use fp16; reduce batch size to 1 for inference |
| Windows path or ffmpeg not found inside the IDE | PATH not inherited by the IDE terminal | Restart the IDE after changing PATH |

### 3.8 Prompt for the setup-guide AI

Paste this, fill in the brackets, then attach Sections 2 to 4 of this file.

```text
You are guiding me through setting up a Python ML development environment, one step at a time.

My machine: OS = [Windows 11 / Ubuntu / macOS], GPU = [model and VRAM, or none], RAM = [x GB], free disk = [x GB].
Goal: the environment described in the attached sections 2, 3 and 4 (Python 3.10, PyTorch, DeepFense, Silero VAD, faster-whisper, rapidfuzz, ffmpeg, FastAPI, pytest).

Rules:
1. Give me ONE step at a time, with the exact command for my OS. Wait for me to paste the output before the next step.
2. After each install group, give me a verification command and tell me exactly what output means success or failure.
3. If something fails, diagnose from my pasted error before suggesting anything new. Do not guess package versions; ask me to run `pip index versions <pkg>` or check the official install page if unsure.
4. Follow the install order in section 3.4 and run the verification table V1 to V11 from section 3.6.
5. Never ask me to install fairseq unless I say I am testing the SLS candidate.
6. At the end, produce a summary of the final working versions so I can pin them.
```

---

## 4. Repository layout

Everything you own lives under `ml/`. Names below are the target; Antigravity should create exactly this.

```text
ml/
├── pyproject.toml                  # package metadata, deps, pytest and ruff config
├── README.md                       # how to run mock mode, real mode, tests
├── Makefile                        # make setup | test | mock | serve | stream | eval
├── .env.example                    # ML_DEVICE, ML_MOCK, HF_TOKEN, ML_LOG_LEVEL ...
├── configs/
│   ├── default.yaml                # audio, vad, detector, scoring, asr, privacy (Appendix A)
│   ├── thresholds.yaml             # default, hi, en threshold sets (placeholders until calibrated)
│   ├── keywords.yaml               # context lexicon (Appendix B)
│   ├── telephony.yaml              # codec profiles
│   └── scenarios.json              # demo scenario manifest (Section 12)
├── src/satyaswar_ml/
│   ├── __init__.py
│   ├── config.py                   # load YAML + env, validate
│   ├── schemas.py                  # Pydantic models = the contract (Section 6)
│   ├── engine.py                   # AnalysisEngine, CallSession
│   ├── audio/
│   │   ├── io.py                   # PCM16 bytes <-> float32, resample, load/save
│   │   ├── windowing.py            # RingBuffer, window emitter, model-input prep
│   │   ├── snr.py                  # SNR estimate from VAD mask
│   │   └── telephony.py            # G.711 in memory, ffmpeg profiles
│   ├── vad/silero_vad.py
│   ├── detector/
│   │   ├── base.py                 # Detector protocol, DetectorOutput
│   │   ├── registry.py             # name -> constructor
│   │   ├── deepfense_backend.py    # XLS-R + AASIST via DeepFense
│   │   ├── hf_backend.py           # plain transformers wrapper for other checkpoints
│   │   └── ensemble.py             # optional two-model agreement
│   ├── scoring/
│   │   ├── smoothing.py            # evidence-weighted EMA
│   │   ├── bands.py                # thresholds, hysteresis, band-change events
│   │   ├── evidence.py             # evidence quality
│   │   ├── outcome.py              # likely_genuine | suspicious | insufficient_evidence
│   │   └── why.py                  # "why flagged" builder (computed items only)
│   ├── asr/whisper_asr.py          # faster-whisper wrapper, language ID, name prompt
│   ├── nlp/
│   │   ├── keywords.py             # context flags
│   │   ├── translit.py             # Devanagari <-> Latin phonetic keys
│   │   └── contacts.py             # claimed-identity candidate ranking
│   ├── heuristics/prosody.py       # F0 and pause stats, labelled supporting
│   ├── alerts/texts.py             # bilingual alert strings and audio keys
│   ├── decision/decide.py          # reference decision function (Appendix D)
│   └── adapters/
│       ├── ws_app.py               # FastAPI router: WS /ml/ws/{call_id}, REST /ml/*
│       └── mock.py                 # scripted mock engine
├── scripts/
│   ├── stream_wav.py               # simulates the Flutter app
│   ├── bakeoff.py                  # Phase 1 candidate comparison
│   ├── make_scenarios.py           # builds demo clips + manifest
│   ├── make_alert_audio.py         # EN/HI alert clips
│   ├── bench_latency.py
│   └── export_schemas.py           # writes docs/events.schema.json and docs/openapi.json
├── training/
│   ├── prepare_data.py             # builds manifests, splits by speaker and generator
│   ├── augment.py                  # codec, noise, re-recording helpers
│   ├── configs/*.yaml              # DeepFense configs
│   └── colab_finetune.ipynb        # thin notebook that calls the scripts
├── eval/
│   ├── metrics.py                  # EER, minDCF, FAR/FRR, confusion matrix
│   ├── run_eval.py                 # per-language, codec, noise, generator, duration slices
│   ├── report.py                   # tables, DET curve, score histograms
│   └── results/                    # committed CSV/JSON + PNG for slides
├── tests/
│   ├── unit/ ...
│   ├── contract/ ...
│   └── integration/ ...
├── assets/
│   ├── fixtures/                   # tiny WAVs for tests (consented, short)
│   └── alerts/                     # alert audio clips
├── data/                           # gitignored
├── models/                         # gitignored
└── docs/
    ├── contract.md                 # human-readable copy of Section 6
    ├── events.schema.json
    ├── openapi.json
    └── baseline-timings.md
```

---

## 5. Decisions to agree with Members 1 and 2 (do this first)

Hold a 20-minute sync and record the answers at the top of `ml/docs/contract.md`. Recommended answers are given.

| ID | Decision | Recommended | If they disagree |
| --- | --- | --- | --- |
| D1 | What does the app send? | Non-overlapping **1.75 s chunks** (28,000 samples), engine builds 3.5 s windows | Window mode: app sends full 3.5 s windows; engine scores each as received |
| D2 | Where does ML run? | **In-process library** inside Member 2's FastAPI server on the demo laptop | Standalone ML service on another port using `adapters/ws_app.py` |
| D3 | Direction and range of the score | `spoof_score` in [0, 1], **higher means more likely synthetic** | Never invert silently; if changed, bump `schema_version` |
| D4 | Band names | `low`, `medium`, `high`, plus outcome `insufficient_evidence` | |
| D5 | Who plays alerts and decides when | Engine emits `alert` events (level, bilingual text, audio key) only on band change with hysteresis; **app plays them** | |
| D6 | Who passes the contact list | **Backend passes contacts per session start** (id, display name, aliases). ML stores nothing | |
| D7 | Where is the decision function | Backend owns it; ML supplies the reference module (Appendix D) | |
| D8 | Which languages do alerts and text support | English and Hindi from day one; alert language follows the app's language setting, not the detected call language | |
| D9 | Schema version | `schema_version: "1.0"` in every JSON message | |

---

## 6. Integration contract

### 6.1 Integration modes (one engine, two adapters)

| Mode | How | Use when |
| --- | --- | --- |
| **A. In-process (default)** | Backend imports `satyaswar_ml`, creates `AnalysisEngine` once at startup, one `CallSession` per call | Single laptop demo, lowest latency |
| **B. Standalone service** | Run `uvicorn satyaswar_ml.adapters.ws_app:app --port 8100`; backend or app connects to `WS /ml/ws/{call_id}` | Backend wants isolation, or ML runs on a different machine |

Both modes call the same `CallSession` code, so behaviour and tests are identical.

### 6.2 Audio format and framing

- Sample format: **PCM16 little-endian, 16 kHz, mono**.
- Binary frame layout (little-endian): `uint32 seq` | `uint64 client_ts_ms` | `PCM16 payload`.
- Chunk mode (D1): payload is 28,000 samples (56,000 bytes), `seq` increments by 1 per chunk, starting at 0.
- Window mode: payload is 56,000 samples; same header.
- The engine accepts any payload length (it buffers), but the recommended sizes keep latency predictable.
- Control and results travel as **JSON text frames**.

### 6.3 Session lifecycle

1. **Start.** Client or backend sends a `session_start` JSON message (6.4.1). Engine replies `session_ready`.
2. **Stream.** Binary frames up. Engine emits `score` (after the first 3.5 s of audio, then every 1.75 s), plus `transcript`, `context`, `claim`, `alert` events as they occur.
3. **Config change.** `config_update` message (for example turn the telephony profile on or off from the dashboard). Applies from the next window.
4. **End.** `session_end` message or socket close. Engine emits one `call_summary` and frees all buffers.
5. **Reconnect.** A reconnecting client sends `session_start` with the same `call_id` and `resume: true`. The engine keeps session state for 60 s after a drop. Frames with an already-seen `seq` are ignored.

### 6.4 Message schemas

All messages carry `schema_version` and `type`. Field lists below are the contract. Implement them as Pydantic models in `schemas.py`, and generate JSON Schema from them.

#### 6.4.1 Up (client or backend to ML)

```json
{
  "schema_version": "1.0",
  "type": "session_start",
  "call_id": "c_01HZX...",
  "mode": "chunks",
  "language_hint": null,
  "telephony_profile": "none",
  "contacts": [
    {"contact_id": "uid_abc", "display_name": "Priyanka Sharma",
     "aliases": ["Priti", "प्रीति"], "label": "Sister"}
  ],
  "resume": false
}
```

`config_update`: `{"type":"config_update","telephony_profile":"g711_ulaw"}`. `session_end`: `{"type":"session_end"}`.

#### 6.4.2 Down: `score`

```json
{
  "schema_version": "1.0",
  "type": "score",
  "call_id": "c_01HZX...",
  "window_index": 3,
  "window": {"start_ms": 5250, "end_ms": 8750},
  "spoof_score": 0.81,
  "smoothed_score": 0.74,
  "band": "high",
  "previous_band": "medium",
  "band_changed": true,
  "outcome": "suspicious",
  "evidence": {
    "speech_seconds": 2.9,
    "snr_db": 18.4,
    "agreement": 0.88,
    "quality": 0.79,
    "quality_label": "good"
  },
  "language": {"code": "hi", "confidence": 0.93, "source": "asr"},
  "telephony_profile": "none",
  "latency_ms": {"decode": 2, "telephony": 0, "vad": 18, "detector": 212, "total": 241},
  "client_ts_ms": 1730300000123,
  "server_recv_ts_ms": 1730300000290,
  "server_send_ts_ms": 1730300000531,
  "model": {"name": "xlsr300m_aasist_ft", "version": "2026-10-30a"},
  "why": [
    {"kind": "window_score", "text_key": "peak_window", "value": 0.81},
    {"kind": "speech_seconds", "value": 2.9},
    {"kind": "snr_db", "value": 18.4},
    {"kind": "model_agreement", "value": 0.88}
  ],
  "mock": false
}
```

Rules: when `outcome` is `insufficient_evidence`, `spoof_score` and `smoothed_score` may be `null`, and the app MUST show the abstain state rather than a number. `language.code` is `null` until ASR has decided.

#### 6.4.3 Down: other events

| `type` | Key fields | When |
| --- | --- | --- |
| `session_ready` | `call_id`, `model`, `device`, `warmup_ms`, `contacts_loaded` | After `session_start` |
| `transcript` | `text`, `language`, `is_final`, `start_ms`, `end_ms` | After ASR runs on early speech. Dashboard only. Never stored |
| `context` | `flags: [{category, term, language, at_ms}]` | When keyword rules match. Categories: `urgency`, `secrecy`, `money`, `otp_credentials`, `authority`, `family_emergency` |
| `claim` | `candidates: [{contact_id, matched_on, score, rank}]`, `ambiguous`, `no_match` | After the transcript names someone. Never auto-select |
| `alert` | `level` (`low`, `medium`, `high`, `insufficient`), `reason_code`, `text: {en, hi}`, `audio_key: {en, hi}` | Only on band change, with hysteresis |
| `info` | `code`, `message` | For example `windows_dropped`, `asr_unavailable`, `telephony_on` |
| `error` | `code`, `message`, `recoverable` | Model not loaded, bad frame, and so on |
| `call_summary` | `peak_score`, `mean_score`, `final_band`, `final_outcome`, `time_in_band_s: {low, medium, high, insufficient}`, `evidence_quality_mean`, `languages_seen`, `context_categories`, `windows_scored`, `windows_insufficient`, `latency_ms: {p50, p95}` | Once at session end. **No transcript, no audio** |

`call_summary` is deliberately shaped to fill Member 2's scores-only history entry.

### 6.5 REST endpoints (adapter in `ws_app.py`)

| Endpoint | Purpose |
| --- | --- |
| `GET /ml/health` | `{status, model_loaded, device, versions, warmup_ms, mock}` |
| `GET /ml/model-info` | Model name, version, thresholds in use, languages evaluated |
| `POST /ml/analyze-window` | Dev and test only. Body: one WAV window (multipart). Returns one `score` event. Disabled unless `ML_ENABLE_DEV_ENDPOINTS=1` |
| `POST /ml/contacts/match` | Body: `{text, contacts}`. Returns a `claim` event. Used by the backend or for tests |
| `WS /ml/ws/{call_id}` | Standalone streaming mode |

### 6.6 Python API (for in-process mode)

```python
from satyaswar_ml import AnalysisEngine, SessionConfig, Contact

engine = AnalysisEngine.from_config("ml/configs/default.yaml")   # call once at startup
await engine.warmup()                                            # first inference is slow; do it here

session = engine.start_session(
    call_id="c_01...",
    config=SessionConfig(mode="chunks", telephony_profile="none"),
    contacts=[Contact(contact_id="uid_abc", display_name="Priyanka Sharma", aliases=["Priti"])],
)

# per received binary frame:
events = await session.push_audio(pcm16_bytes, seq=seq, client_ts_ms=ts)
for ev in events:                      # list of Pydantic event models
    await ws.send_text(ev.model_dump_json())

await session.update_config(telephony_profile="g711_ulaw")
summary = await session.end()          # returns the call_summary event, frees buffers
```

`push_audio` never blocks the event loop: inference runs in a dedicated worker thread (Section 13).

### 6.7 Mock mode

Set `ML_MOCK=1`. The engine replays scripted score trajectories from `configs/scenarios.json` (genuine, clone, noisy, short, no-match), including bands, evidence quality, transcript lines, claims and alerts, **every event carrying `"mock": true`**. The dashboard MUST show a visible "MOCK DATA" banner when it sees this flag. Mock mode exists so the app and backend can be built and demoed on machines without a GPU. It is never used silently: if the real engine fails, the system emits an `error` event and does not fall back to mock.

### 6.8 Errors, backpressure, truth

- If the detector cannot keep up (queue of unprocessed windows greater than 2), drop the **oldest** pending windows and emit `info: windows_dropped` with a count. Never invent scores.
- If ASR is unavailable, emit `info: asr_unavailable`. Scoring continues. The manual contact picker remains the primary path.
- Bad frame (wrong length, odd byte count): emit `error` with `recoverable: true`, skip the frame.
- Model not loaded: `session_ready` is not sent; an `error` with `recoverable: false` is.

### 6.9 Versioning and change control

- Any field addition that old clients can ignore: keep `schema_version` and note it in `docs/contract.md`.
- Any rename, removal or meaning change: bump to `1.1` or `2.0`, update `events.schema.json`, and tell both members in writing before merging.
- Contract tests (Section 15) fail the build if the models and the committed JSON Schema drift apart.

### 6.10 What the other members must do (put this in your hand-over message)

**Member 2 (backend):** create one engine at startup and await `warmup()`; call `start_session` with the contact list; forward binary frames to `push_audio`; fan out events to the app and `/ws/dashboard`; store `call_summary` as the history entry; run the decision function (Appendix D) using the final `outcome`, verification state and action type; open the firewall port.

**Member 1 (app and dashboard):** send audio in the agreed format; render `insufficient_evidence` as its own state; play alerts only from `alert` events (the engine already applies hysteresis); show the "MOCK DATA" banner when `mock` is true; show per-window scores, evidence quality, transcript and latency on the dashboard from the events above; show the language of alerts according to the app language setting.

---

## 7. Module specifications

Each module lists purpose, inputs and outputs, algorithm, parameters (in `configs/default.yaml`), and failure behaviour.

### 7.1 Audio I/O and framing (`audio/io.py`)

- Decode PCM16LE bytes to `float32` in [-1, 1]. Reject odd byte counts.
- `load_audio(path) -> (np.ndarray, 16000)`: read with `soundfile`, convert to mono, resample to 16 kHz with `torchaudio.functional.resample` (or `scipy.signal.resample_poly`).
- Do not apply extra amplitude normalisation in the engine. Per-utterance normalisation (zero mean, unit variance) is applied **inside the detector wrapper** only if the checkpoint expects it (7.4).

### 7.2 Windowing (`audio/windowing.py`)

- `RingBuffer` keeps the last 8 s per session.
- **Chunk mode:** append each chunk. When the buffer holds at least `window_s` (3.5 s) and at least `hop_s` (1.75 s) of new audio has arrived since the last window, emit the latest 3.5 s as a window. First window therefore appears after 3.5 s of audio, then one every 1.75 s.
- **Window mode:** each received payload is one window, scored as is.
- **End of call:** if at least 1.5 s of unscored audio remains, emit one final padded window.
- **Model input prep** (`prepare_model_input`):
  1. Optionally keep only speech segments (concatenate VAD speech), controlled by `trim_silence_for_model` (suggested default: true). This reduces the known tendency of detectors to key on silence length.
  2. Pad to `model_input_samples` (64,600 samples, about 4.04 s) by **repeat-padding** (tile and cut). Window is 56,000 samples, so padding is almost always needed.
  3. Add a bake-off experiment comparing repeat-padding and zero-padding on your own clips; keep the better one.
- Unit tests: lengths, hop timing, sequence numbers, overlap correctness, end-of-call flush, very short input.

### 7.3 VAD and evidence inputs (`vad/silero_vad.py`, `audio/snr.py`)

- Silero VAD on CPU over the 16 kHz window. Parameters (suggested defaults): threshold 0.5, minimum speech 250 ms, minimum silence 100 ms.
- Output: speech segments, `speech_seconds`, speech mask per 10 ms frame.
- **SNR estimate:** mean power over speech frames divided by mean power over non-speech frames, in dB. If there are no non-speech frames, use the 10th percentile of frame energy as the noise floor. Treat the number as rough and say so on the slide.
- If `speech_seconds < min_speech_s_for_scoring` (suggested default 1.0 s), skip the detector for this window and emit `outcome: insufficient_evidence`. This saves latency and is honest.

### 7.4 Detector (`detector/`)

```python
class DetectorOutput(NamedTuple):
    spoof_prob: float        # [0,1], higher = more likely synthetic (contract D3)
    raw: dict                # logits or backend-specific values, for debugging only

class Detector(Protocol):
    name: str
    version: str
    input_samples: int
    def warmup(self) -> None: ...
    def predict(self, wav: np.ndarray) -> DetectorOutput: ...    # wav: float32, 16 kHz, len == input_samples
```

Requirements:

- **Registry:** `detector.primary` in YAML selects an implementation by name. Adding a candidate must not require editing `engine.py`.
- **Label mapping:** each backend maps its own class index to `spoof_prob`. Cover it with a unit test using one known genuine and one known synthetic fixture (a swapped mapping is the classic bug).
- **Normalisation parity:** Hugging Face wav2vec2 models use a feature extractor that normalises the waveform; other pipelines do not. Follow the checkpoint's model card. Add a **parity test**: score the same file with the reference inference script from the model repo and with the wrapper; absolute difference must be below 1e-3.
- **Inference settings:** `torch.inference_mode()`, model in `eval()`, fp16 on GPU (`autocast`), batch size 1, model loaded once, `warmup()` runs one dummy window.
- **Threading:** all detector calls go through one single-worker executor with a lock so GPU use is serial and the asyncio loop stays free.
- **Ensemble (optional, `ensemble.py`):** run two detectors, output the mean score and set `agreement = 1 - |s1 - s2|`. Use only if latency stays under budget.

### 7.5 Smoothing, bands and outcome (`scoring/`)

**Smoothing (evidence-weighted EMA).** For each scored window with raw score `x_t` and evidence quality `q_t`:

```text
alpha_t = alpha_base * (0.5 + 0.5 * q_t)          # lower quality moves the average less
s_t     = alpha_t * x_t + (1 - alpha_t) * s_{t-1}   # s_0 = x_0
```

Suggested default `alpha_base = 0.6`. Windows marked `insufficient_evidence` do not update `s_t`.

**Bands.** Two thresholds per threshold set: `low_max` and `high_min` (placeholders in `thresholds.yaml` until calibrated, see 11.4). `low` below `low_max`, `high` at or above `high_min`, `medium` between.

**Hysteresis and debounce** (to avoid alert flapping):

- Escalate one band only after `escalate_consecutive` windows (suggested default 2) in the higher band, except that a smoothed score above `high_min + 0.15` escalates to `high` immediately.
- De-escalate only after `deescalate_consecutive` windows (suggested default 3) and when the score is below the threshold minus `hysteresis_delta` (suggested default 0.05).
- The engine sets `band_changed` and emits an `alert` only on an actual committed change, with at least 6 s between alerts except for an escalation to `high`.

**Outcome.** `insufficient_evidence` if evidence quality label is `poor` or speech seconds are under the minimum; else `suspicious` if band is `high`; else `likely_genuine`. A `medium` band with `fair` or `good` evidence maps to `suspicious` only if smoothed score is rising for two windows, otherwise `likely_genuine`. (Rule is a suggested default; the decision function in the backend treats `medium` as "uncertain".)

**Language-specific thresholds (V3).** `thresholds.yaml` contains `default`, `hi` and `en` sets. Use `hi` or `en` only once ASR reports that language with confidence of at least 0.7; otherwise use `default`. Keep per-language sets only if evaluation (11.4) shows they beat the single set; otherwise copy `default` into both.

### 7.6 Evidence quality (`scoring/evidence.py`)

```text
speech_term    = clip(speech_seconds / 3.0, 0, 1)
snr_term       = clip((snr_db - 5) / 20, 0, 1)
agreement_term = 1 - clip(std(last 3 raw scores) / 0.25, 0, 1)      # or model agreement if ensemble
quality        = 0.45 * speech_term + 0.30 * snr_term + 0.25 * agreement_term
label          = "good" if quality >= 0.70, "fair" if >= 0.45, else "poor"
```

Weights and cut-offs are suggested defaults. Hard gate: fewer than 1.0 s of speech forces `poor`. Test with synthetic cases: silence, white noise, clean speech, very short clip.

### 7.7 ASR and language ID (`asr/whisper_asr.py`)

- Load one `faster-whisper` model at startup (see 2.3 for device and `compute_type`: `float16` on GPU, `int8` on CPU).
- **Run off the critical path** in its own worker. Trigger when a session has accumulated at least 6 s of speech, and again at 12 s, over the **first 12 s of speech only**. Emit `transcript` events with `is_final` false then true.
- **Language:** detect with Whisper's language detection and accept only `en` or `hi` (if neither is top, take the better of the two when its probability is at least 0.3; otherwise report `null`). Check the installed faster-whisper version's `detect_language` signature, since it has changed across releases. Use the result for `language.code`, for per-language thresholds, and for transcription language.
- **Name biasing:** pass the session's contact display names and aliases (Latin and Devanagari) in `initial_prompt`, for example `"Names: Priyanka, Priti, प्रिया, Abhishek, अभिषेक."`.
- Other settings (suggested defaults): `beam_size=1`, `condition_on_previous_text=False`, `vad_filter=False` (you already ran VAD), `temperature=0`.
- **Model choice by measurement:** on 10 to 20 of your own Hindi lines and 10 to 20 English lines, compute word error rate with `jiwer` and latency for `small`, `medium` and the largest model your hardware can run. Pick the smallest model whose Hindi WER is acceptable for **name and keyword spotting** (you do not need a perfect transcript).
- Hinglish (mixed Hindi and English) will make language ID flip; the 0.7 confidence rule and the fallback to default thresholds cover this.
- Transcripts are sent to the client and then dropped. Never log them.

### 7.8 Context keyword rules (`nlp/keywords.py`)

- Lexicon in `configs/keywords.yaml` (starter in Appendix B), six categories: `urgency`, `secrecy`, `money`, `otp_credentials`, `authority`, `family_emergency`.
- Each entry has forms in English, romanised Hindi (Hinglish), and Devanagari.
- **Normalise** transcript and lexicon the same way: lowercase, strip punctuation, Devanagari to Latin phonetic key (7.9), collapse repeated letters.
- **Match:** exact token or phrase match first; for terms of 5 or more characters also accept `rapidfuzz.fuzz.partial_ratio >= 85` to survive ASR spelling noise. Short terms (such as `otp`) need exact match.
- Output flags with the matched term and time. Flags are context only. They never change the voice score. They go to the dashboard and to the decision function.

### 7.9 Transliteration and contact matching (`nlp/translit.py`, `nlp/contacts.py`)

Goal: take a transcript such as "मैं प्रिया बोल रही हूँ" or "Hi, Priti here" and rank the **user's own contacts** by likelihood. The candidate set is small, which is why this is robust.

**Phonetic key function `key(text)`:**

1. If Devanagari, transliterate to a Latin scheme with `indic-transliteration`.
2. Lowercase, remove punctuation and honorifics (`ji`, `sir`, `madam`, `bhai`, `didi` kept as separate tokens, not part of the name key).
3. Collapse spelling variants: long vowels to short (`aa`→`a`, `ee`/`ii`→`i`, `oo`/`uu`→`u`), `w`→`v`, `z`→`j`, `ph`→`f`, aspirated stops to plain (`th`→`t`, `dh`→`d`, `kh`→`k`, `gh`→`g`, `bh`→`b`), drop trailing schwa `a`, collapse double letters.

**Ranking:**

- For each contact, build a set of keys from `display_name`, every alias, and each name token.
- For each transcript n-gram (1 to 3 tokens), compute `rapidfuzz.fuzz.ratio` and `token_set_ratio` against each contact key; contact score is the maximum.
- Return the top 5 with score of at least 75 (suggested default). `ambiguous = true` if the top two are within 5 points or two contacts share a name token. `no_match = true` if nothing passes.
- **Never auto-select.** The `claim` event is a ranked suggestion only. The app shows duplicates with labels and the manual picker remains the primary path.
- Unit tests: exact match, nickname (Priti vs Priyanka), Devanagari input against Latin contact, duplicate names (two "Rahul"), no match, empty transcript.

### 7.10 Telephony simulation (`audio/telephony.py`)

| Profile | Chain | Implementation |
| --- | --- | --- |
| `none` | pass-through | |
| `g711_ulaw` | 16k → 8k → mu-law encode/decode → 16k | `audioop.lin2ulaw` and `ulaw2lin` in memory (Python 3.10) |
| `g711_alaw` | same with A-law | `audioop.lin2alaw` and `alaw2lin` |
| `amr_nb` | 8 kHz AMR-NB narrowband | ffmpeg, only if `ffmpeg -encoders` lists an AMR-NB encoder |
| `gsm` | GSM full rate | ffmpeg native `gsm` codec (fallback when AMR is unavailable) |
| `opus_8k` | low-bitrate Opus at 8 kHz | ffmpeg `libopus` |

- Apply to the assembled window **before** VAD and detector so the detector sees what it would see on a phone line.
- Run ffmpeg as a subprocess with pipes (`-f s16le -ar 16000 -ac 1 -i pipe:0 ... -f s16le -ar 16000 pipe:1`). Process start costs time, so prefer the in-memory G.711 path for the live toggle and keep ffmpeg profiles for dataset augmentation and evaluation.
- The same functions are reused by `training/augment.py` and `eval/run_eval.py`. One implementation, three uses.

### 7.11 Supporting heuristics (`heuristics/prosody.py`)

- F0 contour (`librosa.yin` or `pyin` over speech frames), pause count and mean pause length, from the VAD mask.
- Output only as raw numbers in `why`, labelled `supporting_heuristic`. Do not generate prose such as "unnatural pitch" unless a stored rule on a measured value produced it. These features must not feed the risk score unless evaluation shows they add value.

### 7.12 "Why flagged" builder (`scoring/why.py`)

Only these items may appear: per-window score timeline and highest-scoring window, speech seconds, SNR, model agreement, keyword flags, optional F0 and pause numbers. Each item is `{kind, value, text_key}`; the UI maps `text_key` to localised text. Add a test that fails if `why` contains a free-text field.

### 7.13 Alerts (`alerts/texts.py`)

Fixed set, each with English and Hindi text and an audio key (texts in Appendix C): `low`, `medium`, `high`, `insufficient`, plus the verification outcomes `denied` and `confirmed` for Member 1 to reuse. Generate audio with `scripts/make_alert_audio.py` (7.14 and Section 12), check on the demo phone's speaker.

### 7.14 Engine (`engine.py`)

Per `CallSession.push_audio`:

1. Parse and validate the frame, record timestamps.
2. Append to ring buffer; emit windows as they complete.
3. For each window: telephony (if on) → VAD → evidence gate → detector → smoothing → bands and hysteresis → outcome → `why` → `score` event; maybe `alert` event.
4. Schedule ASR when speech thresholds are crossed; on its completion emit `transcript`, `context`, `claim`, and update the language used for thresholds.
5. Record per-stage latency and the timestamps defined in 6.4.2.
6. On `end`: build `call_summary`, clear buffers (`del` arrays, reset session), emit summary.

---

## 8. Bilingual strategy: English and Hindi

This is the reason the project exists, so it gets its own plan.

### 8.1 Why Hindi needs deliberate work

- Many detectors are trained on English or Chinese benchmark data. The IndicSynth authors found that detectors trained in one language lose accuracy on out-of-domain languages, which is the gap you are targeting.
- The XLS-R front-end was pretrained on many languages including Hindi, so it is a better starting point than English-only front-ends.
- Hindi phone speech adds code-mixing (Hinglish), regional accents, and heavy compression, none of which are in standard benchmarks.

### 8.2 What "supports Hindi" means for this project (acceptance wording)

You may claim Hindi support only when all of these have numbers on your own test set:

1. Per-language EER for English and Hindi, clean and telephony-simulated (11.3).
2. Hindi consented clones from at least two different generators, one of them **held out** from training.
3. Hindi genuine speech from at least five different speakers recorded on the demo phone.
4. ASR language ID correct on your Hindi and English demo lines.
5. Hindi alert text and audio tested on the demo phone.

### 8.3 Tactics

| Area | Tactic |
| --- | --- |
| Front-end | Keep XLS-R 300M multilingual (do not switch to an English-only model for speed unless forced) |
| Training data | Balanced English and Hindi batches; Hindi spoof from IndicSynth plus your own generators; Hindi genuine from public corpora plus your own recordings |
| Augmentation | Same codec, noise and re-recording chain for both languages |
| Thresholds | Global set first; per-language sets only if they help (7.5) |
| Language ID | Whisper language detection, restricted to `en` and `hi`, with confidence gating |
| Evaluation | Always report English and Hindi separately; report the gap between them |
| Code-mixing | Include Hinglish lines in your own recordings and in keyword tests |
| Alerts | Both languages, chosen by app language setting |
| Honesty | Report on "our small test set"; show the Hindi versus English delta even when it is unflattering |

---

## 9. Data plan

All dataset licences and access terms MUST be checked before download. Prefer streaming and small subsets. Never use a real person's voice for cloning without that person's written consent (a chat message from the teammate is enough for the team, keep it).

### 9.1 Sources

| Purpose | Language | Source | Notes |
| --- | --- | --- | --- |
| Spoof, large and multilingual | Hindi (and others) | **IndicSynth** on Hugging Face: `vdivyasharma/IndicSynth`, config name `Hindi` (the ACL 2025 paper describes about 4,000 hours, 989 speakers, 12 Indian languages, with mimicry and diversity subsets) | Full download is tens of GB. Use `load_dataset(..., name="Hindi", split="train", streaming=True)` and `.take(N)`; save only the N clips you need |
| Bona fide | Hindi | Corpora named in the IndicSynth paper as bona fide source (IndicSUPERB or similar); Mozilla Common Voice Hindi | Verify access and licence; Common Voice needs login and terms acceptance and ships MP3 |
| Bona fide and spoof | English | English anti-spoofing sets available through DeepFense's Hugging Face datasets (run `deepfense download list-datasets`), such as ASVspoof 2019 LA and In-the-Wild if listed | Pick the sets that are actually available; check licences |
| Bona fide | English (Indian accent) | Common Voice English with Indian accent filter, if available | Helps match your demo accents |
| Spoof (own) | Hindi and English | Clips you generate: `edge-tts` voices (for example Hindi and Indian-English neural voices), open Indic TTS and voice-cloning models, a commercial cloning tool free tier | Use at least **two different generators**; hold one out. Record the generator name per clip |
| Bona fide (own) | Hindi and English | Teammates reading scripted lines on the **demo phone** | Core domain data |
| Channel realism (own) | Both | Play genuine and spoof clips through a phone speaker and record with the demo phone mic | Small but valuable test slice |

### 9.2 Own recording protocol

- At least 5 speakers (teammates, friends with consent). Gender and accent variety if possible.
- Each speaker records **20 Hindi and 20 English lines** (6 to 12 s each) in 3 conditions: quiet room, noisy room (fan or street), phone held normally. Aim for natural phrasing, including some Hinglish.
- Consented clones: for each consenting speaker, create clones from 10 to 30 s of their reference audio using each generator, then synthesise the same scripted lines.
- Scripted lines must include the demo scripts (Section 12) **in the test split only**.
- Save as 16 kHz mono WAV plus a row in `data/manifest.csv`: `path, label, language, speaker_id, generator, condition, codec, duration_s, split, consent`.

### 9.3 Splits (prevent leakage)

- Split by **speaker** (no speaker appears in two splits) and by **generator** (hold one generator out entirely for a generalisation test).
- Splits: `train`, `dev` (threshold calibration and model choice), `test` (touched once for reported numbers), `demo` (the exact demo clips, never trained on).
- Keep each language balanced in `dev` and `test`. If you cannot reach 100 bona fide and 100 spoof clips per language, say so with the actual counts on the slide.

### 9.4 Data scripts

- `training/prepare_data.py`: download subsets, resample, trim, write manifest, assign splits, apply codec and noise variants as separate manifest rows with a `condition` and `codec` field.
- `training/augment.py`: reusable functions for G.711, AMR or GSM, Opus 8 kHz, additive noise at SNR 5, 10, 20 dB, room impulse response if available, and speaker-to-mic re-recording as an offline step.
- Quality checks: sample ten random clips per language and listen; confirm labels; confirm no clipping; confirm durations.

---

## 10. Model and fine-tuning plan

### 10.1 Phase 1: baseline bake-off (decide before training anything)

`scripts/bakeoff.py` scores the `dev` split with each candidate in 2.2 (and with each padding mode) and writes `eval/results/bakeoff.csv`. Metrics per candidate: EER and minDCF per language, clean and G.711-simulated, plus mean per-window latency on your machine.

**Suggested go/no-go rule** (adjust with the team):

- **Go with the baseline** if macro-average EER over English and Hindi is at most 15% on clean `dev` and at most 25% on telephony-simulated `dev`, and Hindi is not more than 10 points worse than English.
- **Otherwise fine-tune** (10.2).
- **If fine-tuning also fails** to meet the rule on `dev`, ship the best model anyway, widen the `insufficient_evidence` band, lean on the verification layer, and present the numbers honestly.

### 10.2 Phase 2: fine-tune (only if the baseline fails)

**Plan A (default, feasible in 2 to 3 GPU hours): frozen XLS-R 300M front-end plus trained AASIST head, via DeepFense.**

- Front-end: Hugging Face `facebook/wav2vec2-xls-r-300m`, frozen.
- Backend: AASIST (try Nes2Net as a second run if time).
- Loss: cross-entropy or OC-Softmax (try both if time; keep the one that wins on `dev`).
- Augmentations: RawBoost, codec, additive noise, speed perturbation (all available in DeepFense), plus your G.711 or GSM chain.
- Data size (suggested start): 3,000 to 5,000 clips per language, balanced bona fide and spoof, 4 s crops at 16 kHz.
- Hyperparameters (suggested start): learning rate 1e-4 for the head, batch size 16 (reduce on small GPUs), 3 to 8 epochs, early stop on `dev` EER.
- Evaluate after every epoch on `dev` by language; keep the best checkpoint by **macro EER over English and Hindi**, not by training loss.
- Run by following the DeepFense commands: `python train.py --config training/configs/xlsr_aasist_bilingual.yaml`, then `python test.py --config ... --checkpoint ...`. Check the installed version's CLI before relying on these exact flags.

**Plan B (only if A underperforms and time remains): partial unfreezing or LoRA** on the top transformer layers with a small learning rate (1e-5), custom training loop written by the agent using `transformers` and `peft`. Higher overfitting risk, so use the held-out generator test to decide.

**Colab or Kaggle workflow:** one notebook that mounts storage, installs pinned requirements, pulls the manifest and clips, runs training, writes checkpoint and `eval/results/` to Drive, and prints the dev metrics table. Time-box to 3 hours. Start it early so it runs while you build the engine.

### 10.3 Phase 3: calibrate and freeze

1. Choose the checkpoint by `dev` macro EER.
2. Compute thresholds on `dev` (11.4) and write them to `thresholds.yaml`.
3. Run the `test` split **once** and save `eval/results/final_test.json`.
4. Run the `demo` clips and confirm they behave as expected (genuine low band, clone high band). If a demo clone does not separate, replace the clone clip or generator rather than touching the threshold.
5. Tag the model with a version string (for example `2026-10-30a`), copy the checkpoint to `models/`, and record its SHA-256 in `docs/model-card.md`.

### 10.4 Rules that keep the claims honest

- Never tune on `test`. Never train on `demo`.
- Compare fine-tuned against baseline on the same held-out slices; if it does not win, use the baseline.
- State the sizes of every evaluation set next to every number.
- Keep a short `docs/model-card.md`: training data, languages, known failure modes, licences of every dataset and tool used.

---

## 11. Evaluation

### 11.1 Metrics

| Metric | Definition | Where used |
| --- | --- | --- |
| EER | Operating point where false accept and false reject rates are equal | Headline per slice |
| minDCF | Minimum detection cost, `Pspoof = 0.05` as in DeepFense's example config | Secondary |
| FAR and FRR at the chosen thresholds | Spoof accepted as genuine; genuine flagged as spoof | Bank-style false alarm view |
| Confusion matrix | At the `high` band threshold | Slides |
| Abstain rate and abstain correctness | Share of very short or noisy clips marked `insufficient_evidence`, and share of those that really were poor | Honest behaviour |
| Time to first score, per-window latency (p50, p95) | From `client_ts_ms` to `server_send_ts_ms`, and detector time alone | Real-time claim |
| ASR: WER, language ID accuracy, name hit rate, keyword recall | `jiwer` and simple counters | Identity and context |
| Contact matching: top-1 and top-3 accuracy, no-match correctness | On your scripted lines and distractor contacts | Identity |

### 11.2 Slices

`eval/run_eval.py` must report every metric by:

- language (English, Hindi, and Hinglish if you have it)
- codec (clean, G.711 mu-law, G.711 A-law, GSM or AMR if available)
- noise (clean, SNR 20, 10, 5 dB)
- generator (each seen generator, and the held-out one)
- duration bucket (under 1.5 s, 1.5 to 3 s, over 3 s)
- channel (direct recording versus phone speaker to phone mic)
- model (baseline versus fine-tuned versus ensemble)

Output: `eval/results/*.csv`, `eval/results/*.json`, DET curve and score-histogram PNGs.

### 11.3 Required results table (fill with real numbers before the demo)

| Slice | Genuine n | Spoof n | EER baseline | EER fine-tuned |
| --- | --- | --- | --- | --- |
| English clean | | | | |
| Hindi clean | | | | |
| English G.711 | | | | |
| Hindi G.711 | | | | |
| Held-out generator | | | | |
| Phone speaker to mic | | | | |

Add one slide called "Where it fails", built from this table and the worst slices.

### 11.4 Threshold calibration (`eval/calibrate.py`)

1. Using `dev` only, compute the EER threshold for the detector.
2. Set `high_min` near the point where false alarms on genuine speech are acceptable (suggested starting target: genuine flagged `high` in at most 5% of windows) and `low_max` near the point where at most 5% of spoof windows land in `low` (suggested starting target). Adjust with the team.
3. Compute these separately for English and Hindi; adopt per-language sets only if the same targets give clearly different thresholds and the per-language set improves false alarms or misses on `dev`.
4. Optionally fit Platt scaling (logistic regression on raw scores) to produce a score that behaves more like a probability **on your data**. If you do, label it "calibrated on our dev set", never "probability of fraud".
5. Write results into `configs/thresholds.yaml` with the date, dataset sizes and model version in comments.
6. Re-run the whole `test` split once with the frozen thresholds and save the result.

### 11.5 Pipeline-level evaluation (beyond the detector)

- **Stream replay:** run `scripts/stream_wav.py` on every `demo` and `test` clip; record the full band timeline; check that genuine clips settle `low` and clones settle `high` within the expected number of windows, and that alerts fire once per band change.
- **Time to alert:** seconds from first audio to the first `high` alert for each clone clip.
- **Flap rate:** number of band changes per minute on genuine clips (target near zero).

---

## 12. Demo assets

### 12.1 Scenario manifest (`configs/scenarios.json`)

```json
{
  "schema_version": "1.0",
  "scenarios": [
    {"id": "gen_hi_01", "title": "Genuine Hindi call", "language": "hi", "label": "genuine",
     "claimed_caller": "Abhishek", "file": "assets/scenarios/gen_hi_01.wav",
     "expected_band_final": "low", "transcript_hint": "meeting time change"},
    {"id": "clone_hi_01", "title": "Cloned Hindi emergency", "language": "hi", "label": "clone",
     "claimed_caller": "Priyanka", "file": "assets/scenarios/clone_hi_01.wav",
     "expected_band_final": "high", "transcript_hint": "urgent money, do not tell anyone"},
    {"id": "gen_en_01", "title": "Genuine English call", "language": "en", "label": "genuine",
     "claimed_caller": "Rahul", "file": "assets/scenarios/gen_en_01.wav",
     "expected_band_final": "low", "transcript_hint": "project update"},
    {"id": "clone_en_01", "title": "Cloned English CEO request", "language": "en", "label": "clone",
     "claimed_caller": "Rahul", "file": "assets/scenarios/clone_en_01.wav",
     "expected_band_final": "high", "transcript_hint": "urgent transfer, confidential"},
    {"id": "noisy_hi_01", "title": "Noisy Hindi call", "language": "hi", "label": "genuine",
     "claimed_caller": "Abhishek", "file": "assets/scenarios/noisy_hi_01.wav",
     "expected_band_final": "insufficient_evidence", "transcript_hint": "street noise"},
    {"id": "short_en_01", "title": "Very short call", "language": "en", "label": "genuine",
     "claimed_caller": "Unknown", "file": "assets/scenarios/short_en_01.wav",
     "expected_band_final": "insufficient_evidence", "transcript_hint": "two seconds only"}
  ]
}
```

Replace claimed names with the contacts your team will actually create in the demo accounts.

### 12.2 Scripted lines (record and clone these; keep out of training)

| ID | Language | Line |
| --- | --- | --- |
| gen_hi_01 | Hindi | "हाय, मैं अभिषेक बोल रहा हूँ। कल की मीटिंग का समय बदल गया है, शाम चार बजे रखते हैं।" |
| clone_hi_01 | Hindi | "मैं प्रिया बोल रही हूँ। मैं बहुत मुसीबत में हूँ, मुझे अभी पचास हज़ार रुपये ट्रांसफर करो और किसी को मत बताना।" |
| gen_en_01 | English | "Hi, this is Rahul. Just checking in on the project update before tomorrow's review." |
| clone_en_01 | English | "Hi, this is Rahul. I need you to transfer fifty thousand rupees right now. It is urgent and confidential, please do not tell anyone." |
| hinglish_01 (extra) | Hinglish | "Yaar, main Priya bol rahi hoon, abhi turant OTP bhej do, bahut zaruri hai." |

Aim for 8 to 15 seconds per clip so the dashboard shows at least three windows. Record the genuine lines on the demo phone; generate the clone lines with two generators and keep the better separated one for the live demo and the other as backup.

### 12.3 Alert audio (`scripts/make_alert_audio.py`)

- Generate each alert in English and Hindi from the strings in Appendix C using `edge-tts` (Hindi and Indian-English voices) or recorded teammate voice.
- Output 16 kHz mono WAV, normalised, under 4 s each, into `assets/alerts/{key}_{en|hi}.wav`.
- Test on the demo phone speaker at demo volume. Check that the clip does not overlap the call audio badly (Member 1 lowers call volume while an alert plays).
- Keep the on-device text-to-speech fallback strings identical to the clip text.

### 12.4 Backup artefacts

- Pre-recorded screen capture of the dashboard processing each demo clip (use the stream simulator, so it works even if the phone fails).
- A frozen copy of `eval/results/` and the model card in the repo.

---

## 13. Performance and latency

### 13.1 Targets (suggested defaults; measure and replace)

| Stage | Target on a GPU laptop | Notes |
| --- | --- | --- |
| Decode and resample | under 10 ms | |
| Telephony G.711 | under 20 ms | ffmpeg profiles cost more, so keep them for offline use |
| VAD | under 40 ms per window | CPU |
| Detector (XLS-R 300M, about 4 s, fp16) | under 300 ms | Estimate for a mid-range GPU, **measure it** |
| Smoothing, bands, `why` | under 5 ms | |
| Server total per window | under 500 ms | Must stay well under the 1.75 s hop |
| Time to first score | about 3.5 s of audio plus under 0.5 s | State this number honestly |
| ASR (off critical path) | under 3 s for the first 12 s of speech on GPU | Runs in parallel |

On CPU the XLS-R 300M detector may take more than the 1.75 s hop. If `bench_latency.py` shows `total_p95 > hop`, switch to a smaller detector or run on a GPU machine. Do not demo something that falls behind the audio.

### 13.2 Engineering rules

- Load all models once at startup; `warmup()` before the first call.
- One single-worker executor for the detector, a separate one for ASR, so ASR never delays a score.
- Cap queues: at most 2 pending windows; drop oldest and report (6.8).
- No per-window allocations that scale with call length; ring buffer is fixed size.
- `scripts/bench_latency.py` runs 100 windows through the engine and prints p50, p95, p99 per stage, and per-window real-time factor. Run it on the actual demo laptop on battery and on mains power.
- Keep GPU memory headroom: detector fp16 plus Whisper should fit in the VRAM with at least 1 GB free.

---

## 14. Privacy and security

- **Audio** is processed in memory only. No audio is written to disk or logged. `ML_DEBUG_DUMP_AUDIO` exists for development, defaults to off, and the service refuses to start with it on when `ML_ENV=demo`.
- **Transcripts** are emitted over the socket and dropped. Not stored, not logged. Logs contain only call ID, sequence numbers, durations, bands and error codes.
- **Contacts** passed in `session_start` live only in session memory and are freed at session end.
- **`call_summary`** is the only persisted-by-backend ML output and contains no audio or text.
- Training and evaluation data live in `data/` (gitignored) and are never committed. Consent records for cloned voices are kept outside the repo or in a private note.
- Validate every input: frame size, sequence numbers, JSON schema; reject oversized frames (more than 10 s of audio per frame).
- Authentication of the WebSocket is the backend's job (Firebase ID token); the standalone ML adapter binds to localhost by default and accepts a shared secret header if exposed on the LAN.
- Do not claim compliance. Say the design follows data-minimisation principles and that a DPDP Act 2023 review is needed before real deployment, as in the solution document.

---

## 15. Testing

### 15.1 Unit tests (`tests/unit/`)

| Module | Tests |
| --- | --- |
| `audio.io` | PCM16 decode, odd length rejected, resample length, mono conversion |
| `audio.windowing` | First window at 3.5 s, then every 1.75 s; correct hop; padding; end-of-call flush; window mode; short input |
| `audio.snr` | White noise gives low SNR; clean speech fixture gives high SNR; no non-speech frames path |
| `audio.telephony` | G.711 output length and band-limiting (energy above 4 kHz drops); profile toggle |
| `vad` | Silence yields zero speech; speech fixture yields segments |
| `detector` | Label mapping on one genuine and one spoof fixture; **parity with reference script within 1e-3**; output range [0,1] |
| `scoring.smoothing` | Low-quality windows move the average less; insufficient windows do not update |
| `scoring.bands` | Threshold edges; escalate after 2, de-escalate after 3; immediate high jump; minimum alert spacing; no flapping on noisy sequence |
| `scoring.evidence` | Hard gate under 1 s; weights; labels |
| `scoring.why` | Only allowed `kind` values; no free text |
| `asr` | Language restricted to `en` or `hi`; name prompt built correctly; unavailable path emits `info` |
| `nlp.keywords` | Each category in English, Hinglish, Devanagari; ASR-misspelling tolerance; short-term exact rule |
| `nlp.contacts` | Exact, nickname, Devanagari vs Latin, duplicates, no match, empty text, ambiguity flag |
| `decision.decide` | Every row of the table in Appendix D plus action-type variants |

### 15.2 Contract tests (`tests/contract/`)

- Every event model serialises, validates against the committed `events.schema.json`, and round-trips.
- `export_schemas.py` output equals the committed files (fails if someone changed a model without regenerating).
- Fixtures for each event type are valid and loadable by Members 1 and 2 (they can copy them).
- Mock mode produces events that pass the same schemas and all carry `mock: true`.

### 15.3 Integration tests (`tests/integration/`)

- Start the standalone adapter in a test process; run `stream_wav.py` logic against it with a genuine fixture and a spoof fixture; assert score events arrive in order, band timeline is sensible, one `call_summary` arrives, and nothing is written to disk.
- Reconnect test: drop the socket mid-call, reconnect with `resume: true`, confirm sequence continuity and duplicate frame rejection.
- Backpressure test: send frames faster than real time; confirm `windows_dropped` info and no crash.
- Failure tests: ASR disabled, detector exception (inject), wrong frame size, model not loaded.

### 15.4 Joint tests with the other members

Run the full path: ring, accept, stream, score, alert, contact selection, verification, outcome, history. Scenario matrix: genuine Hindi, genuine English, clone Hindi, clone English, noisy, short, no contact match. Measure end-to-end latency on the hotspot with the real phone.

### 15.5 Definition of done for the ML side

1. Section 1.3 checklist is fully ticked.
2. Bake-off results and the chosen model are committed with a model card.
3. Required results table (11.3) is filled with real numbers.
4. `bench_latency.py` shows per-window p95 below the hop on the demo laptop.
5. Demo clips separate correctly on three consecutive runs through the real stack.
6. Hindi and English alerts play on the demo phone.
7. Every claim on the ML slides maps to a result file or is labelled roadmap.

---

## 16. Phased plan with gates

Times are estimates for one person working with Antigravity; run the Colab fine-tune in the background from Phase 1.

| Phase | Work | Output | Gate |
| --- | --- | --- | --- |
| **P0. Setup** (2 to 4 h) | Section 3 end to end; repo skeleton; pull small data subsets; start recording sessions with teammates | V1 to V11 pass; `baseline-timings.md`; first recordings | Environment works on the demo laptop |
| **P1. Contract and mock** (2 to 3 h, in parallel with P0 data pulls) | Sync on D1 to D9; write `schemas.py`; export schemas; mock engine; stream simulator | Members 1 and 2 can build against mock | **Contract signed off and mock running** |
| **P2. Bake-off** (2 h) | Prepare `dev` split; run candidates and padding modes; produce `bakeoff.csv` | Chosen baseline | **Go/no-go on 10.1 rule** |
| **P3. Fine-tune** (background, 2 to 3 h GPU) | Build bilingual training set with augmentation; train Plan A; evaluate on `dev` | Candidate checkpoint | Beats baseline on `dev` macro EER, or baseline kept |
| **P4. Core engine** (4 to 6 h) | Windowing, VAD, evidence, detector wrapper, scoring, bands, engine, adapter | Real scores flowing through the contract | First end-to-end result with Member 2 |
| **P5. Identity and context** (3 to 4 h) | ASR with language ID, keyword rules, contact matching, transliteration | `transcript`, `context`, `claim` events | Name match works on scripted Hindi and English lines |
| **P6. Telephony and calibration** (2 to 3 h) | Telephony profiles; threshold calibration; per-language decision | `thresholds.yaml` filled | Calibrated on `dev`, frozen |
| **P7. Evaluation and assets** (3 to 4 h) | Full evaluation; scenario clips; alert audio; results table; "where it fails" slide | `eval/results/`, `assets/` | Required results table complete |
| **P8. Hardening** (2 to 3 h) | Latency benchmark; backpressure; reconnect; privacy checks; docs | Passing integration tests | Definition of done (15.5) |
| **P9. Joint rehearsal** | Full stack with Members 1 and 2; fix integration issues; rehearse in both languages | Backup video | Three clean runs in a row |

**Cut list if behind (cut in this order):** ensemble, per-language thresholds, F0 and pause heuristics, Plan B, AMR/Opus profiles, Hinglish extras, Platt calibration. **Never cut:** contract and mock, bake-off, evidence quality and abstain state, Hindi evaluation, honest results table.

---

## 17. Antigravity prompt pack

### 17.1 Project rules (give once; put in the agent's project instructions)

Keep this short text in the project rules or instructions file for the agent (check the Antigravity documentation for the exact file name and mechanism).

```text
You are implementing the AI/ML package of SatyaSwar in the folder ml/ of this repository.
Read ml/docs/Implementation.md (sections 1, 2, 4, 6, 7) before writing code. Follow its folder layout and contract exactly.
Rules:
- Python 3.10. Type hints everywhere. Pydantic v2 models for every message in the contract.
- All parameters come from configs/*.yaml or environment variables. No magic constants in code.
- Never write audio or transcripts to disk or logs. Logs contain ids, durations, bands, codes only.
- Never fabricate model results. If a model or dependency is unavailable, raise a clear error. Mock behaviour only when ML_MOCK=1 and every event then carries mock=true.
- Every module gets pytest tests in the same change. Run ruff and pytest before finishing a task.
- Do not change the contract in schemas.py without bumping schema_version and updating docs/contract.md.
- Small, reviewable changes: one milestone per task. Tell me what you ran and what passed.
```

### 17.2 Milestone prompts (use one per task, in order)

**M0. Skeleton, config, schemas**
```text
Create the ml/ package skeleton from section 4. Implement config.py (YAML plus env overrides, validated with Pydantic) and schemas.py with every message in section 6.4 (session_start, config_update, session_end, session_ready, score, transcript, context, claim, alert, info, error, call_summary). Add scripts/export_schemas.py that writes docs/events.schema.json and docs/openapi.json. Add contract tests that fail if the committed schema differs from the models. Acceptance: pytest passes; schemas export; a fixture JSON for every event validates.
```

**M1. Audio, windowing, telephony**
```text
Implement audio/io.py, audio/windowing.py, audio/telephony.py per sections 7.1, 7.2 and 7.10. Chunk mode and window mode, ring buffer, end-of-call flush, model input prep with repeat-padding and optional silence trimming, G.711 mu-law and A-law in memory, ffmpeg profiles behind a capability check. Acceptance: unit tests for first window at 3.5 s, hop 1.75 s, padding to 64600 samples, short input, G.711 band-limiting.
```

**M2. VAD, SNR, evidence quality**
```text
Implement vad/silero_vad.py, audio/snr.py and scoring/evidence.py per 7.3 and 7.6. Return speech segments, speech_seconds, snr_db and evidence quality with the hard gate under 1.0 s. Acceptance: tests with synthetic silence, white noise, a clean speech fixture and a very short clip.
```

**M3. Detector wrapper**
```text
Implement detector/base.py, registry.py and deepfense_backend.py (and hf_backend.py for other checkpoints) per 7.4. The primary detector is chosen by detector.primary in default.yaml. Include warmup(), fp16 on GPU, single-worker executor, correct label mapping so spoof_prob is higher for synthetic speech, and a parity test against the reference inference script for the chosen checkpoint (difference below 1e-3). Acceptance: tests pass on one genuine and one spoof fixture; device and timing are reported by /ml/health later.
```

**M4. Scoring**
```text
Implement scoring/smoothing.py, bands.py, outcome.py and why.py per 7.5, 7.6 and 7.12. Evidence-weighted EMA, thresholds from thresholds.yaml (default, hi, en sets), hysteresis and debounce, alert spacing, outcome rule, why items restricted to the allowed kinds. Acceptance: tests for threshold edges, escalate-after-2, de-escalate-after-3, immediate high jump, no flapping on a noisy sequence, why contains no free text.
```

**M5. Engine, mock and adapter**
```text
Implement engine.py (AnalysisEngine, CallSession) per 7.14 and 6.6, adapters/mock.py per 6.7 and adapters/ws_app.py per 6.3 and 6.5. Session lifecycle with resume for 60 s, backpressure drop of oldest windows beyond 2 pending with an info event, per-stage latency fields and timestamps in score events, call_summary at end, buffers freed. Acceptance: integration test starts the adapter, streams a fixture, receives ordered score events and one call_summary; mock mode passes the same schemas with mock=true on every event.
```

**M6. Stream simulator and contract tests**
```text
Write scripts/stream_wav.py that behaves like the Flutter app: reads a WAV, converts to 16 kHz mono PCM16, sends 1.75 s chunks with the 12-byte header from 6.2 at real-time pace (flag --fast for faster), prints every event and a latency table at the end, supports --telephony g711_ulaw and --contacts file. Add tests/integration using it. Acceptance: running it against the standalone adapter prints scores, alerts and a summary.
```

**M7. ASR and language ID**
```text
Implement asr/whisper_asr.py per 7.7: faster-whisper loaded once, language restricted to en or hi, initial_prompt built from session contacts, runs at 6 s and 12 s of accumulated speech in its own worker, emits transcript events and updates the session language used for thresholds. Check the installed faster-whisper API for detect_language. Acceptance: tests for language restriction, prompt building and the asr_unavailable info path; a script prints transcript, language and latency for a Hindi and an English fixture.
```

**M8. Keywords and contacts**
```text
Implement nlp/translit.py, nlp/keywords.py and nlp/contacts.py per 7.8 and 7.9 with configs/keywords.yaml (start from Appendix B). Phonetic key function, rapidfuzz ranking with ambiguity and no-match flags, never auto-select. Acceptance: tests for exact, nickname, Devanagari against Latin contacts, duplicate names, no match, empty transcript, and every keyword category in English, Hinglish and Devanagari.
```

**M9. Evaluation harness**
```text
Implement eval/metrics.py (EER, minDCF with Pspoof 0.05, FAR/FRR, confusion matrix), eval/run_eval.py (slices from 11.2 using the manifest, with codec and noise applied through audio/telephony.py and training/augment.py), eval/calibrate.py (11.4) and eval/report.py (tables, DET curve, score histograms). Write CSV, JSON and PNG into eval/results/. Acceptance: runs on a tiny fixture manifest; unit tests for EER on known inputs.
```

**M10. Training scripts**
```text
Implement training/prepare_data.py and training/augment.py per section 9, DeepFense config training/configs/xlsr_aasist_bilingual.yaml per 10.2, and a thin Colab notebook that installs requirements, pulls the manifest, trains Plan A, evaluates on dev by language, and saves the best checkpoint by macro EER over English and Hindi. Split by speaker and generator. Check the installed DeepFense version for exact CLI and config keys. Acceptance: a dry run on a 20-clip toy manifest completes end to end.
```

**M11. Scenarios and alerts**
```text
Implement scripts/make_scenarios.py (build WAVs and configs/scenarios.json from recorded and cloned clips listed in a CSV, 16 kHz mono) and scripts/make_alert_audio.py (English and Hindi alert clips from the strings in Appendix C using edge-tts, normalised, under 4 s). Acceptance: manifest validates; every alert key has en and hi audio.
```

**M12. Benchmark and hardening**
```text
Implement scripts/bench_latency.py (100 windows, p50/p95/p99 per stage, real-time factor) and add the failure tests from 15.3: reconnect with resume, faster-than-real-time frames, ASR disabled, injected detector exception, bad frame. Add a privacy test that fails if any file is created or any log line contains transcript text during a streamed call. Acceptance: all tests pass; benchmark output saved to docs/baseline-timings.md.
```

---

## 18. Risks and mitigations

| Risk | Impact | Mitigation |
| --- | --- | --- |
| Pretrained detectors fail on phone-mic and Hindi audio | Wrong bands in the demo | Bake-off first; fine-tune Plan A; wide abstain band; verification layer is the backstop |
| Fine-tuning overfits to its own generators or data | Looks good on dev, fails live | Held-out generator, speaker-disjoint splits, `test` touched once, `demo` never trained on |
| Hindi performance worse than English | Undermines the core claim | Report it honestly; add Hindi data; per-language thresholds; widen abstain for Hindi if needed |
| CPU or small GPU too slow | Scores fall behind audio | Benchmark early; smaller detector; backpressure drops with a visible `info` event |
| CUDA, cuDNN or CTranslate2 version clash | Whisper or PyTorch fails to start | Whisper on CPU int8 fallback; setup verification V3 and V8 before any coding |
| ASR misreads Hinglish names | Wrong or missing claim | Name-biased prompt, fuzzy and phonetic matching, manual picker is primary |
| Language ID flips on code-mixed speech | Threshold set changes mid-call | Confidence gate 0.7; fall back to default thresholds |
| Threshold chosen on a tiny dev set | Unstable bands | Report set sizes; keep hysteresis; do not over-tune |
| Contract drift between members | Integration failures late | Schema export, contract tests, written change process (6.9) |
| Licences of datasets, models or TTS tools | Legal or demo problem | Record licences in `model-card.md`; avoid non-commercial restrictions where you plan commercial claims; keep to demo and research use |
| Cloned-voice consent | Ethical and legal issue | Written consent for every cloned teammate, no public figures' voices |
| Overclaiming accuracy | Credibility loss with judges | "On our small test set" framing, show set sizes, show the failure slide, label vendor claims as vendor claims |

---

## Appendix A. Starter `configs/default.yaml`

```yaml
schema_version: "1.0"
env: dev                        # dev | demo (demo refuses debug dumps)

audio:
  sample_rate: 16000
  mode_default: chunks          # chunks | windows
  chunk_s: 1.75
  window_s: 3.5
  hop_s: 1.75
  ring_buffer_s: 8.0
  model_input_samples: 64600
  trim_silence_for_model: true
  pad_mode: repeat              # repeat | zeros (decide in bake-off)
  min_speech_s_for_scoring: 1.0
  max_frame_s: 10.0

vad:
  threshold: 0.5
  min_speech_ms: 250
  min_silence_ms: 100

detector:
  primary: xlsr300m_aasist_ft   # registry key; set after bake-off
  secondary: null
  device: auto                  # auto | cuda | cpu
  precision: fp16
  checkpoint_path: models/xlsr300m_aasist_ft.pth
  max_pending_windows: 2

scoring:
  alpha_base: 0.6
  escalate_consecutive: 2
  deescalate_consecutive: 3
  hysteresis_delta: 0.05
  immediate_high_margin: 0.15
  min_alert_spacing_s: 6.0
  evidence:
    w_speech: 0.45
    w_snr: 0.30
    w_agreement: 0.25
    good_min: 0.70
    fair_min: 0.45

asr:
  enabled: true
  model: small                  # choose by WER and latency (7.7)
  device: auto
  compute_type: auto            # float16 on GPU, int8 on CPU
  trigger_speech_s: [6, 12]
  max_speech_s: 12
  languages: [en, hi]
  language_confidence_min: 0.7
  beam_size: 1

telephony:
  default_profile: none
  profiles: [none, g711_ulaw, g711_alaw, amr_nb, gsm, opus_8k]

privacy:
  debug_dump_audio: false
  log_transcripts: false

session:
  resume_window_s: 60
```

`configs/thresholds.yaml` (**placeholders, replace after calibration**):

```yaml
# calibrated_on: dev   date: TBD   model: TBD   n_genuine: TBD   n_spoof: TBD
default: {low_max: 0.35, high_min: 0.65}
hi:      {low_max: 0.35, high_min: 0.65}
en:      {low_max: 0.35, high_min: 0.65}
```

---

## Appendix B. Starter keyword lexicon (`configs/keywords.yaml`)

Extend with your own scam scripts. Keep terms lowercase; the matcher normalises Devanagari to Latin keys.

```yaml
urgency:
  en: [urgent, urgently, immediately, right now, asap, hurry, quickly, emergency]
  hi_latin: [jaldi, turant, abhi, foran, jaldi karo, der mat karo, emergency]
  hi_deva: [जल्दी, तुरंत, अभी, फौरन, देर मत करो, इमरजेंसी]
secrecy:
  en: [don't tell anyone, do not tell, keep it secret, confidential, between us]
  hi_latin: [kisi ko mat batana, kisi ko mat bolna, raaz rakhna, gupt, confidential]
  hi_deva: [किसी को मत बताना, किसी को मत बोलना, राज़ रखना, गुप्त]
money:
  en: [transfer, send money, bank account, upi, gift card, payment, rupees, lakh]
  hi_latin: [paise, paisa, rupaye, transfer karo, paise bhejo, khata, upi, lakh]
  hi_deva: [पैसे, पैसा, रुपये, ट्रांसफर, पैसे भेजो, खाता, लाख, हज़ार]
otp_credentials:
  en: [otp, one time password, pin, password, cvv, card number, verification code]
  hi_latin: [otp, pin, password, cvv, card number, code batao, otp batao, otp bhejo]
  hi_deva: [ओटीपी, पिन, पासवर्ड, कोड बताओ, ओटीपी बताओ, ओटीपी भेजो]
authority:
  en: [police, cbi, customs, court, arrest, digital arrest, warrant, tax department, bank officer]
  hi_latin: [police, pulis, cbi, court, giraftari, arrest, warrant, income tax, bank officer]
  hi_deva: [पुलिस, सीबीआई, कोर्ट, गिरफ्तारी, अरेस्ट, वारंट, इनकम टैक्स]
family_emergency:
  en: [accident, hospital, in trouble, kidnapped, bail, surgery, injured]
  hi_latin: [accident, hospital, musibat, bail, operation, chot, zakhmi]
  hi_deva: [एक्सीडेंट, अस्पताल, हॉस्पिटल, मुसीबत, ज़मानत, ऑपरेशन, चोट]
```

---

## Appendix C. Alert texts (English and Hindi)

Short enough to read in under 4 seconds. Also shown on screen.

| Key | English | Hindi |
| --- | --- | --- |
| `low` | "No synthetic signs found so far. This is not proof of identity. Verify before sending money." | "अब तक नकली आवाज़ के संकेत नहीं मिले। यह पहचान का प्रमाण नहीं है। पैसे भेजने से पहले पुष्टि करें।" |
| `medium` | "This voice shows some warning signs. Be careful and consider verifying the caller." | "इस आवाज़ में कुछ चेतावनी के संकेत हैं। सावधान रहें और कॉलर की पुष्टि करने पर विचार करें।" |
| `high` | "Warning. This voice may be synthetic. Do not share money or codes. Verify the caller now." | "सावधान! यह आवाज़ नकली हो सकती है। पैसे या कोड न दें। अभी कॉलर की पुष्टि करें।" |
| `insufficient` | "Not enough clear audio to judge. Verify the caller before any sensitive action." | "आवाज़ का आकलन करने के लिए साफ़ ऑडियो पर्याप्त नहीं है। कोई भी संवेदनशील काम करने से पहले कॉलर की पुष्टि करें।" |
| `denied` | "Verification denied. This is likely an impersonation. Do not proceed." | "पुष्टि अस्वीकार हुई। यह नकली पहचान हो सकती है। आगे न बढ़ें।" |
| `confirmed` | "Verified through the linked account. Stay cautious with sensitive requests." | "लिंक किए गए खाते से पुष्टि हुई। संवेदनशील अनुरोधों में सावधानी रखें।" |

Have a Hindi speaker on the team read the Hindi text aloud and correct wording before recording.

---

## Appendix D. Reference decision function

Backend owns the production copy (decision D7). This module and its tests are provided so both sides share one definition.

**Inputs:** `voice_band` (`low|medium|high`), `voice_outcome` (`likely_genuine|suspicious|insufficient_evidence`), `verification` (`not_started|pending|confirmed|denied|expired|no_match`), `action_type` (`money|otp_credentials|confidential|other|none`).

```python
SENSITIVE = {"money", "otp_credentials", "confidential"}

def voice_class(band: str, outcome: str) -> str:
    if outcome == "insufficient_evidence":
        return "uncertain"
    if band == "high":
        return "high"
    if band == "medium":
        return "uncertain"
    return "low"

def decide(voice_band, voice_outcome, verification, action_type="none") -> str:
    v = voice_class(voice_band, voice_outcome)
    sensitive = action_type in SENSITIVE

    if verification == "denied":
        return "likely_impersonation"
    if verification == "no_match":
        return "cannot_verify_use_another_route"
    if verification == "confirmed":
        return "conflicting_signals_use_second_channel" if v == "high" else "verified_normal_caution"
    if v == "high":                                   # not_started, pending, expired
        return "hold_unverified_high_risk"
    if verification in ("pending", "expired"):        # low or uncertain
        return "unverified_hold" if sensitive else "unverified_caution"
    # verification == "not_started", low or uncertain
    if v == "uncertain":
        return "insufficient_evidence_verify_if_sensitive"
    return "no_indicators_verify_before_transfer" if sensitive else "no_indicators_not_proof"
```

Mapping to the solution document's table (section 8.3): the first five rules and the `uncertain / not_started` and `low / not_started` rows are implemented as written. **Gaps in the document's table that this reference closes with proposed defaults, which the team should confirm:**

| Gap | Proposed handling |
| --- | --- |
| High risk and verification `not_started` | Treated as `hold_unverified_high_risk` (same as pending or expired) |
| Low or uncertain with verification `pending` or `expired` | `unverified_hold` for sensitive actions, `unverified_caution` otherwise. Expiry never means safe |
| `medium` band | Treated as `uncertain` for the decision |
| Action type | Raises the message severity for money, OTP or credentials and confidential requests; does not change the verification logic |
| Message wording | Outcome codes are stable identifiers; the app maps them to English and Hindi text |

---

## Appendix E. Hand-over checklist and message template

**Before telling the others "ML is ready":**

- [ ] `pip install -e ml/` works on a clean machine from the README.
- [ ] `make mock` runs the stream simulator against mock mode.
- [ ] `make serve` starts the standalone adapter; `GET /ml/health` is green.
- [ ] `docs/contract.md`, `events.schema.json`, `openapi.json` are committed and current.
- [ ] Fixtures for every event type are in `assets/fixtures/events/`.
- [ ] Model checkpoint, thresholds and model card are versioned and recorded.
- [ ] Results table and "where it fails" slide are drafted from real result files.

**Message to Members 1 and 2 (adapt):**

```text
ML package ready for integration (schema_version 1.0).
Run mock mode: cd ml && make mock   (no GPU needed, all events carry mock=true).
Contract: ml/docs/contract.md, JSON Schema in ml/docs/events.schema.json.
Backend: create one AnalysisEngine at startup, await warmup(), start_session with contacts, forward binary frames to push_audio, fan out events, store call_summary as history, run the decision function in ml/src/satyaswar_ml/decision/decide.py.
App: send PCM16 16 kHz mono in 1.75 s chunks with the 12-byte header (seq, client_ts_ms); render insufficient_evidence as its own state; play alerts only from alert events; show a MOCK DATA banner when mock=true.
Languages: English and Hindi for detection, ASR, keywords and alerts.
Questions or contract changes: message me before merging; any change bumps schema_version.
```
