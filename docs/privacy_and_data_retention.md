# SatyaSwar: Privacy, Data Handling & Zero-Retention Architecture

| Attribute | Specification |
|---|---|
| **Authoritative Source** | Master Prompt Critical Requirement 4 & Implementation.md Section 14 |
| **Privacy Paradigm** | Strict Data Minimization & Transient In-Memory Processing |
| **Zero Raw-Audio Retention** | Default: Enforced. Zero raw PCM/WAV written to persistent disk |
| **Default Retention Period** | Raw Audio: **0 seconds** (instant discard post-window). Transcripts: **0 seconds** (transient socket stream only). Metadata: Session lifetime only. |
| **Third-Party / Cloud APIs** | **Zero External Transmission**. All models (Silero VAD, faster-whisper, XLS-R detector) execute 100% locally on-device / local laptop |

---

## 1. Data Lifecycle & Processing Boundaries

```
[ Incoming Audio Stream (PCM16) ]
               │
               ▼
   [ Transient RingBuffer (RAM only) ]
               │
      ┌────────┴────────┐
      ▼                 ▼
[ Silero VAD ]   [ Detector (XLS-R) ]
 (RAM analysis)    (RAM analysis)
      │                 │
      └────────┬────────┘
               ▼
[ Computed Feature Metrics: Scores & Bands ]
               │
               ▼
[ WebSocket Broadcast to App/Dashboard: JSON Events only ]
               │
               ▼
   [ Immediate RAM Discard / Garbage Collection ]
```

1. **Ingest:** Audio frames arrive via WebSocket as binary PCM16 buffers.
2. **Buffering:** Audio is held solely in a circular in-memory `RingBuffer` (max 8.0s sliding window).
3. **Execution:** Feature extraction, VAD, Whisper ASR, and neural classification run entirely in volatile memory (CPU/GPU RAM).
4. **Disposal:** Once a window is evaluated, audio slices are dereferenced and purged. Upon `session_end` or connection teardown, all ring buffers and contact caches are explicitly cleared.
5. **Disk Write Policy:** No raw audio, no spectral representations, and no transcripts are written to persistent storage (SSD/HDD) by default.

---

## 2. Retention Periods & Enforcement

| Data Class | Persistent Storage? | Retention Period | Deletion Mechanism | Access Control |
|---|---|---|---|---|
| **Raw Caller Audio** | **No** (Memory only) | **0 seconds** (purged after 3.5s window evaluation) | Python reference release & `RingBuffer.clear()` | Restricted to ephemeral ML worker thread |
| **Spoken Transcripts** | **No** (Memory only) | **0 seconds** (streamed to client, never logged or stored) | Discarded immediately after keyword extraction | In-memory session state only |
| **Contact Lists & Aliases**| **No** (Session memory) | **Call duration only** | Flushed at `session_end` / socket close | Scoped strictly to active `call_id` |
| **Call Risk Summary (`call_summary`)** | **Yes** (Backend Firestore) | Permanent (or user-configurable in app) | Backend user deletion API | Authenticated account owner only |

---

## 3. Logging & Data Sanitization Rules

Logs must never be used as a backdoor for audio or PII retention:
1. **Allowed in Logs:**
   - Session identifiers (`call_id`, `session_start`, `session_end`)
   - Sequence numbers and window indices
   - Durations (`speech_seconds`, window timestamps)
   - Risk scores, bands (`low`, `medium`, `high`), and outcome decisions
   - Latency measurements (`decode`, `telephony`, `vad`, `detector`, `total`)
   - System error and diagnostic warning codes
2. **Strictly Prohibited in Logs:**
   - Raw audio samples, PCM hex dumps, or binary payloads
   - Spoken transcript text or raw ASR output
   - Caller phone numbers or identity document numbers
   - Passwords, OTP codes, PINs, or financial account details
   - Biometric or voiceprint enrollment vectors

---

## 4. Local Execution & External Service Guarantee

- **No Cloud Inference:** Audio is never transmitted to OpenAI, Google Cloud Speech, ElevenLabs, or any external third-party API.
- **Local Neural Backends:**
  - `faster-whisper`: Executes on local CTranslate2 engine.
  - `silero-vad`: Executes on local PyTorch CPU runtime.
  - `deepfense` / `transformers` (XLS-R): Executes on local PyTorch GPU/CPU.
- **Zero Network Egress for Telephony Audio:** The only network boundary is the direct LAN/hotspot WebSocket between the user's mobile client and the local analysis server.

---

## 5. Security Gates & Anti-Tamper Controls

1. **`ML_ENV=demo` Production Safeguard:**
   - Setting `ML_ENV=demo` strictly prevents any debug audio dumping (`ML_DEBUG_DUMP_AUDIO=true` will refuse to start and terminate with `ValueError`).
2. **Backpressure & Queue Capping:**
   - If network or processing delays occur, the ring buffer caps pending queues to 2 windows, explicitly dropping oldest windows with a sanitized `InfoEvent("windows_dropped")` rather than spilling to disk.
3. **Automated Verification:**
   - Automated tests (`test_privacy_enforcement.py` and `test_stream_and_api.py`) inspect the file system during continuous streaming to guarantee zero `.wav`, `.pcm`, or temporary cache files are created.
