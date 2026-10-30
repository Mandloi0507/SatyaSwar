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
| **Phase 3 (Stage 3)** | Audio Processing & Streaming Pipeline | **Completed** | WAV parser, window planner, audio playback engine, frame builder, and playback window synchronization implemented and verified |
| **Phase 4** | WebSocket & Real-Time Alert Service | Pending | Next stage: binary WebSocket client, mock fallback service, risk band parsing, audio ducking alerts |
| **Phase 5** | Authentication & State Providers | In Progress | Splash, Login, Register UI & Form Validation complete; preparing service abstractions |
| **Phase 6** | Dashboard & Contacts | In Progress | Home Dashboard, Bottom Navigation, Trusted Contacts & QR flows structured |
| **Phase 7** | Simulated Call Integration | In Progress | Scenarios definition, Scenario Picker, Incoming Call & Active Call screens connected to real WAV engine |
| **Phase 8** | Detection & Real-Time Risk UI | In Progress | Gauge, timeline chart, and evidence quality bar components integrated into active call screen |
| **Phase 9** | Independent Verification | In Progress | Verification bottom sheet & 3-step challenge code workflow implemented |
| **Phase 10** | Call History & Integration | In Progress | Scores-only history list and detail audit screen implemented |
| **Phase 11** | Testing & Stabilisation | **Active** | 29/29 tests passing (5 widget tests + 24 audio pipeline unit tests) |
| **Phase 12** | Demo Readiness & Release Packaging | Pending | Awaiting full integration before final release APK packaging |

---

## 2. Environment & Project Inspection Summary

- **Flutter SDK:** 3.47.5 (Channel stable)
- **Dart SDK:** 3.13.4
- **Physical Device:** Vivo T2 5G (Model V2240, Android 15, API 35) — Connected via ADB
- **Android SDK:** `C:\Android\Sdk`
- **Android NDK:** `28.2.13676358`
- **Static Analysis (`flutter analyze`):** Clean (0 issues found)
- **Automated Tests (`flutter test`):** 29/29 passing (100% pass rate)

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
- **Backend Protocol Status:** **Pending confirmation from Member 2 (Backend Team)**.
- **Design Pattern:** Strategy Pattern via `AudioFrameHeaderStrategy` abstract interface.
- **Default Strategy:** `Proposed20ByteHeaderStrategy`:
  - `[0..1]`: Magic bytes `0x5357` ('SW')
  - `[2]`: Protocol Version `0x01`
  - `[3]`: Flags (`bit 0` = `isLast`)
  - `[4..11]`: Timestamp ms (uint64 Big-Endian)
  - `[12..15]`: Window Index (uint32 Big-Endian)
  - `[16..19]`: Sample Count (uint32 Big-Endian, always 56,000)
  - `[20..112019]`: PCM16 little-endian audio payload (112,000 bytes)
  - **Total Frame Length:** 112,020 bytes.
- **Modularity:** Any change to the 20-byte header layout confirmed by Member 2 will be isolated entirely to `AudioFrameHeaderStrategy` without touching audio extraction or window synchronization.

### 3.4 Playback Window Synchronization (`WindowSender`)
- Listens to `AudioPlayerService.positionStream`.
- Window $k$ is emitted only when playback position reaches `endMsOf(k)`.
- Prevents premature transmission and guarantees time-aligned detection scores during simulated calls.
- On playback completion, any remaining trailing windows are flushed sequentially.

---

## 4. Test Verification Report

### Test Suites Executed:
1. `test/unit/audio_frame_builder_test.dart` (4 tests) — PASSED
   - Frame length equals 112,020 bytes.
   - `isLast` flag properly set in header.
   - Sample round-trip lossless extraction.
   - Modular strategy swapping.
2. `test/unit/wav_parser_test.dart` (7 tests) — PASSED
   - Valid 16 kHz mono PCM16 parsing.
   - Format validation errors (container, sample rate, channels, bit depth, format code).
3. `test/unit/window_planner_test.dart` (7 tests) — PASSED
   - Sample & byte constants validation.
   - Window count calculation (17.5s $\rightarrow$ 9 windows, 21.0s $\rightarrow$ 11 windows).
   - Minimum sample requirement (< 3.5s $\rightarrow$ 0 windows).
   - Window millisecond start/end bounds matching $0 \dots 17500$ ms.
   - Exact slice extraction and out-of-bounds guards.
4. `test/unit/window_sender_test.dart` (6 tests) — PASSED
   - Position gating: window 0 not emitted before 3,500 ms.
   - Window 0 emitted at 3,500 ms.
   - Step-by-step emission with playback advancement.
   - Multi-window catch-up on playback seek/jump.
   - Flushes remaining windows on completion.
   - Emitted frame byte lengths verified.
5. `test/widget/risk_band_badge_test.dart` (4 tests) — PASSED
6. `test/widget_test.dart` (1 test) — PASSED

**Total Tests:** 29 passed, 0 failed.

---

## 5. Files Created / Modified Log (Stage 3 Additions)

### Audio Pipeline Services (`lib/services/`)
- `lib/services/wav_parser.dart`: Zero-copy RIFF/WAVE chunk parsing and format validation.
- `lib/services/window_planner.dart`: 3.5s window / 1.75s hop calculation and slicing.
- `lib/services/audio_frame_builder.dart`: Modular binary frame header strategy and payload packer.
- `lib/services/audio_player_service.dart`: High-performance playback engine wrapping `just_audio` with volume ducking (0.2).
- `lib/services/window_sender.dart`: Playback position synchronized frame dispatcher.

### Unit Tests (`test/unit/`)
- `test/unit/wav_parser_test.dart`
- `test/unit/window_planner_test.dart`
- `test/unit/audio_frame_builder_test.dart`
- `test/unit/window_sender_test.dart`

### Audio Assets (`assets/audio/calls/`)
- `genuine_01.wav`: 17.5-second 16 kHz mono PCM16 audio asset (280,000 samples).
- `clone_ceo_01.wav`: 21.0-second 16 kHz mono PCM16 audio asset (336,000 samples).
- `noisy_01.wav`: 17.5-second 16 kHz mono PCM16 audio asset.
- `short_insufficient_01.wav`: 17.5-second 16 kHz mono PCM16 audio asset.

### UI Integration (`lib/screens/call/active_call_screen.dart`)
- Integrated `AudioPlayerService`, `WavParser`, `WindowPlanner`, and `WindowSender` into the simulated call experience.
- Plays asset audio from `rootBundle` while synchronizing window emissions with real playback position.
