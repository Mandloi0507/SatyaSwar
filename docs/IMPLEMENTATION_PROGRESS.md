# SatyaSwar Implementation Progress Tracker

**Project:** SatyaSwar — AI-Powered Voice Integrity & Independent Caller-Verification Mobile Application  
**Tagline:** Detect. Score. Decide. Verify.  
**Theme:** Blockchain & Cybersecurity (SIH 2026, PS 26104)  
**Target:** Flutter Android on Vivo T2 5G (Physical Test Device)  
**Last Updated:** 2026-10-30  

---

## 1. Execution Phase Status

| Phase | Description | Status | Notes |
|---|---|---|---|
| **Phase 1** | Project Inspection & Preparation | **Completed** | Baseline check passed, complete clean architecture folder scaffold created |
| **Phase 2** | Design System & UI Foundation | **Completed** | Full dark-first cybersecurity design system, colors, typography, reusable components, and declarative router with all 14 screens implemented |
| **Phase 3 (Stage 3)** | Audio Processing & Streaming Pipeline | **Verified & Closed** | WAV parser, window planner, audio playback engine, frame builder, window synchronization, and physical device test verified |
| **Phase 4** | WebSocket & Real-Time Alert Service | Pending | Next stage: binary WebSocket client, mock fallback service, risk band parsing, audio ducking alerts |
| **Phase 5** | Authentication & State Providers | In Progress | Splash, Login, Register UI & Form Validation complete; preparing service abstractions |
| **Phase 6** | Dashboard & Contacts | In Progress | Home Dashboard, Bottom Navigation, Trusted Contacts & QR flows structured |
| **Phase 7** | Simulated Call Integration | In Progress | Scenarios definition, Scenario Picker, Incoming Call & Active Call screens connected to real WAV engine |
| **Phase 8** | Detection & Real-Time Risk UI | In Progress | Gauge, timeline chart, and evidence quality bar components integrated into active call screen |
| **Phase 9** | Independent Verification | In Progress | Verification bottom sheet & 3-step challenge code workflow implemented |
| **Phase 10** | Call History & Integration | In Progress | Scores-only history list and detail audit screen implemented |
| **Phase 11** | Testing & Stabilisation | **Active** | 33/33 tests passing (5 widget tests + 24 unit tests + 4 E2E pipeline integration tests) |
| **Phase 12** | Demo Readiness & Release Packaging | Pending | Awaiting full integration before final release APK packaging |

---

## 2. Environment & Project Inspection Summary

- **Flutter SDK:** 3.47.5 (Channel stable)
- **Dart SDK:** 3.13.4
- **Physical Device:** Vivo T2 5G (Model V2240, Android 15, API 35) — Connected via ADB
- **Android SDK:** `C:\Android\Sdk`
- **Android NDK:** `28.2.13676358`
- **Static Analysis (`flutter analyze`):** Clean (0 issues found)
- **Automated Tests (`flutter test`):** 33/33 passing (100% pass rate)

---

## 3. Audio Pipeline Specifications & Validation

### 3.1 Audio Format
- **Encoding:** Uncompressed PCM16 (format code 1)
- **Sample Rate:** Exactly 16,000 Hz
- **Channels:** Exactly 1 (Mono)
- **Bit Depth:** 16-bit little-endian (2 bytes per sample)

### 3.2 Window Slicing Mathematics
- **Window Duration:** 3.5 seconds
- **Window Samples:** $3.5 \times 16,000 = 56,000$ samples
- **Window Bytes:** $56,000 \times 2 = 112,000$ bytes
- **Hop Duration:** 1.75 seconds (50% overlap)
- **Hop Samples:** $1.75 \times 16,000 = 28,000$ samples
- **Hop Bytes:** $28,000 \times 2 = 56,000$ bytes
- **Window Count Formula:** $\text{count} = 1 + \lfloor \frac{\text{totalSamples} - 56,000}{28,000} \rfloor$
- **Asset Validations:**
  - `genuine_01.wav` (17.5s, 280,000 samples) $\rightarrow$ exactly **9 windows** ($1 + \frac{280,000 - 56,000}{28,000} = 9$).
  - `clone_ceo_01.wav` (21.0s, 336,000 samples) $\rightarrow$ exactly **11 windows** ($1 + \frac{336,000 - 56,000}{28,000} = 11$).

### 3.3 Modular Binary Frame Header Strategy
- **Backend Protocol Status:** **PROVISIONAL — Pending confirmation from Member 2 (Backend Team)**.
- **Design Pattern:** Strategy Pattern via `AudioFrameHeaderStrategy` abstract interface.
- **Implemented Default Strategy:** `Proposed20ByteHeaderStrategy` (matches `Implementation.md` Section 8.5):
  - **Encoding:** Little-Endian (`Endian.little`)
  - `Byte 0`: Protocol Version (`0x01`, uint8)
  - `Byte 1`: Flags (`bit 0` = `isLast`, uint8)
  - `Bytes 2–3`: Reserved (`0x0000`, uint16)
  - `Bytes 4–7`: Window Index / Sequence Number `seq` (uint32 little-endian)
  - `Bytes 8–11`: Window Start Audio Offset `offsetMs` (uint32 little-endian)
  - `Bytes 12–19`: Client Send Unix Epoch Timestamp `sendEpochMs` (uint64 little-endian)
  - `Bytes 20–112019`: PCM16 little-endian audio payload (56,000 samples = 112,000 bytes)
  - **Total Frame Length:** 112,020 bytes.
- **Protocol Decoupling:** Any future backend adjustments from Member 2 are strictly confined to `AudioFrameHeaderStrategy` implementations without requiring modifications to WAV parsing, window planning, or playback synchronization.

### 3.4 Playback Window Synchronization (`WindowSender`)
- Listens to `AudioPlayerService.positionStream`.
- Window $k$ is emitted only when playback position reaches `endMsOf(k)`.
- Prevents premature transmission and guarantees time-aligned detection scores during simulated calls.
- On playback completion, any remaining trailing windows are flushed sequentially.

---

## 4. End-to-End Pipeline Verification Findings (Vivo T2 5G & E2E Tests)

### Detailed Verification Checklist:

1. **Does the bundled WAV file actually play on the Vivo T2 5G?**
   - **CONFIRMED (YES):** Audio is loaded from `rootBundle` (`assets/audio/calls/genuine_01.wav`) into `AudioPlayerService` wrapping `just_audio`. Android system audio engine initializes and streams audio natively to the device speaker.
   - Device logcat confirmed:
     `[DEBUG] [ActiveCallScreen] Initializing audio pipeline with assets/audio/calls/genuine_01.wav`
     `[DEBUG] [AudioPlayerService] Loading audio asset: assets/audio/calls/genuine_01.wav`

2. **Are audio windows emitted while playback is progressing, rather than only being generated in isolation?**
   - **CONFIRMED (YES):** `WindowSender` emits frames strictly as playback proceeds.
   - Device logcat captures exact emission timestamps:
     - `17:32:33.003`: Window 0 emitted (after 3.5s initial buffer reached)
     - `17:32:34.765`: Window 1 emitted (+1.762s elapsed)
     - `17:32:36.492`: Window 2 emitted (+1.727s elapsed)
     - `17:32:38.256`: Window 3 emitted (+1.764s elapsed)
     - `17:32:39.998`: Window 4 emitted (+1.742s elapsed)
     - `17:32:41.743`: Window 5 emitted (+1.745s elapsed)
     - `17:32:43.506`: Window 6 emitted (+1.763s elapsed)
     - `17:32:45.247`: Window 7 emitted (+1.741s elapsed)
     - `17:32:46.984`: Window 8 emitted (+1.737s elapsed)

3. **Are the windows exactly 3.5 seconds with a 1.75-second hop?**
   - **CONFIRMED (YES):** Window duration is 3,500 ms (56,000 samples / 112,000 bytes) and hop duration is 1,750 ms (28,000 samples / 56,000 bytes). Validated across all 9 boundary offsets ($0\dots3500$, $1750\dots5250$, $3500\dots7000$, $\dots$, $14000\dots17500$ ms) in both automated test suites and device logs.

4. **Are sequence numbers and timestamps generated correctly?**
   - **CONFIRMED (YES):** Sequence indices ($0 \dots 8$) are encoded sequentially at byte offset 12 (uint32). System send timestamp is encoded as uint64 epoch milliseconds. The `isLast` flag is set to `0` for windows $0 \dots 7$ and `1` for window $8$.

5. **Does WindowSender actually transmit frames to a receiver, or is it currently using a mock?**
   - **CLARIFIED:** In Stage 3, `WindowSender` dispatches binary frames (112,020 bytes each) through its decoupled callback `onFrame: (Uint8List frame, int seq, DateTime timestamp)`. In `ActiveCallScreen`, this callback receives the real binary frames and drives the local UI.
   - Transmission over a live WebSocket connection to the backend server is intentionally deferred to **Stage 4 (Phase 4: WebSocket & Alert Service)**.

6. **Is the binary frame header still provisional pending Member 2's confirmation?**
   - **CONFIRMED (YES):** The 20-byte header is provisional and decoupled via `AudioFrameHeaderStrategy`. When Member 2 confirms the backend protocol specification, updating the strategy class will adapt the header layout without requiring changes to any parser, planner, or sender logic.

---

## 5. Test Verification Report

### Test Suites Executed:
1. `test/integration/audio_pipeline_e2e_verification_test.dart` (4 tests) — PASSED
   - E2E WAV parsing (16 kHz mono PCM16).
   - E2E WindowPlanner math & boundaries (3.5s window / 1.75s hop).
   - E2E WindowSender playback position gating and frame structure.
   - Modular frame builder strategy swapping.
2. `test/unit/audio_frame_builder_test.dart` (4 tests) — PASSED
3. `test/unit/wav_parser_test.dart` (7 tests) — PASSED
4. `test/unit/window_planner_test.dart` (7 tests) — PASSED
5. `test/unit/window_sender_test.dart` (6 tests) — PASSED
6. `test/widget/risk_band_badge_test.dart` (4 tests) — PASSED
7. `test/widget_test.dart` (1 test) — PASSED

**Total Tests:** 33 passed, 0 failed (100% pass rate).

---

## 6. Pending Backend Integration Dependencies

1. **Protocol Layout Confirmation (Member 2):**
   - Confirmation of exact binary frame header byte length and field ordering (magic bytes, version, sequence number, timestamp, offset, flags, checksum).
2. **WebSocket Endpoint & Handshake:**
   - URL schema (`ws://` / `wss://`) and handshake query/header parameters (`token`, `call_id`, `caller_id`).
3. **Response JSON Schema:**
   - Confirmation of backend analysis payload format (e.g. `window_seq`, `risk_score`, `risk_band`, `evidence_quality`, `latency_ms`).
