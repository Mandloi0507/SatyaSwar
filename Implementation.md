# SatyaSwar: Flutter Mobile Implementation Plan

**Project:** SatyaSwar. Detect. Score. Decide. Verify.
**Problem statement:** SIH 2026, PS 26104 (Blockchain & Cybersecurity theme)
**Owner of this document:** Member 1, Flutter Android application
**Source of truth:** "SatyaSwar: Complete Solution Document" (the team's finalized design)
**Status:** implementation handbook. Payloads marked **[PROPOSAL]** are not defined in the solution document and need teammate approval before they are frozen.

---

## 1. Project Overview

### 1.1 What the mobile app is responsible for

The Flutter app is the **victim's phone** in the demo. It:

1. Signs the user in (Firebase Authentication).
2. Manages trusted contacts through invite codes and QR codes.
3. Shows a **simulated** incoming call, plays a bundled WAV clip, and slices that clip into **3.5 s windows with a 1.75 s hop**.
4. Streams each window to the FastAPI server over a WebSocket as **PCM16, 16 kHz, mono** binary frames.
5. Displays live risk results the server returns (risk band, score, evidence quality) and plays short spoken alerts.
6. Starts caller verification, shows the pending/confirmed/denied state, and displays the final outcome.
7. Shows scores-only call history.

### 1.2 What the mobile app must never do

| Rule | Why |
|---|---|
| Never decide whether verification succeeded | The server owns the verification state machine and the final decision function |
| Never compute the final outcome | Same reason; the app only renders what the server sends |
| Never store raw audio or transcripts | Privacy line of the whole project |
| Never show "verified" because the voice looked genuine | Low risk means "no synthetic indicators found", not proof of identity |
| Never present the call as a real cellular call | The call is simulated; a visible banner must say so |
| Never hold service-account credentials | Only the server uses the Firebase Admin SDK |

### 1.3 The three voice outcomes the UI supports

1. **Likely genuine** (shown as "No synthetic indicators detected", never as "verified")
2. **Suspicious / likely synthetic**
3. **Insufficient evidence** (poor or short audio; the system refuses to guess)

The detector score is a **risk band driven by thresholds tuned on the team's own clips**. It is not a calibrated probability, so the UI never labels it "% chance of fake".

### 1.4 Scope tags used in this document

- **[MVP]** must work for the demo.
- **[OPT]** optional enhancement, built only if the MVP path is stable.

---

## 2. Flutter Architecture

### 2.1 Decision: simple layered architecture with Provider

For a student team learning Flutter, I recommend:

- **Layered folders** (screens, widgets, models, services, repositories, providers).
- **`provider` with `ChangeNotifier`** for state.
- **Plain Dart `Stream`s** inside services for audio position, WebSocket messages and Firestore snapshots.
- **Interfaces for every external dependency** (API, analysis socket, Firestore) so a mock can replace the real one. This is what lets you work while the backend and ML are unfinished.

Why not Riverpod or Bloc? They are good, but each adds concepts (providers-of-providers, events, states, code generation) you would have to learn in the same 24 hours. `provider` is smaller and its `ChangeNotifier` pattern is easy to follow. You can always migrate later.

### 2.2 Layer responsibilities

```
UI (screens/widgets)
   |  reads state, calls methods
Providers (ChangeNotifier controllers)       <- app state and lifecycle
   |  call
Repositories (AuthRepository, ContactsRepository, VerificationRepository, HistoryRepository)
   |  call
Services (ApiClient, CallAnalysisService, AudioPlayerService, AlertService, WavParser, WindowPlanner)
   |  talk to
External: Firebase Auth, Firestore, FastAPI REST, FastAPI WebSocket, device audio
```

Rules:

- Screens never call Firebase or HTTP directly. They call a provider.
- Services contain no UI code.
- Models are plain Dart classes with `fromJson` and `toJson`. Avoid code generation (`freezed`, `json_serializable`) to remove build-runner problems.

### 2.3 End-to-end data flow in the app

```
Scenario picker -> POST /calls/start -> callId + wsUrl + window config
Ringing screen -> Accept
   -> open WebSocket /ws/call/{callId}
   -> start just_audio playback of bundled WAV
   -> positionStream drives the window sender (digital slicing)
   -> each window = binary frame to server
Server -> JSON "score" messages -> RiskMonitorProvider -> risk UI + AlertController
User taps Verify -> choose contact + action -> POST /verifications
   -> Firestore listener on verificationRequests/{id}
Responder responds (second phone or laptop page) -> server updates doc
Server -> "outcome" message -> OutcomeScreen -> history entry (server-created)
```

---

## 3. Complete Technology Stack

| Area | Choice | Notes |
|---|---|---|
| Framework | Flutter (stable channel), Dart | Target Android only for the demo |
| State management | `provider` | ChangeNotifier controllers |
| Navigation | `go_router` | Auth redirect in one place |
| Auth | Firebase Authentication (email/password; Google sign-in optional) | Session persists automatically |
| Database | Cloud Firestore | Read-only listeners from the app; writes go through FastAPI |
| REST | `http` package + a small wrapper | Attaches the Firebase ID token |
| Real-time analysis | `web_socket_channel` (`IOWebSocketChannel`) | Binary up, JSON down |
| Playback | `just_audio` + `audio_session` | Volume control for ducking |
| Spoken alerts | Bundled clips (primary), `flutter_tts` (fallback) | |
| Biometrics | `local_auth` | Responder gate (client-side convenience only) |
| QR | `qr_flutter` (show), `mobile_scanner` (scan) | |
| Local settings | `shared_preferences` | Server address, demo toggles |
| Secrets | `flutter_secure_storage` | Only if you store a PIN hash; Firebase persists the session itself |
| Charts | `fl_chart` | Score timeline |
| Screen awake | `wakelock_plus` | During a call |
| Live-mic (optional) | `record`, `permission_handler` | Secondary mode only |

**Not introduced:** Bloc, Riverpod, Dio, GetX, Hive, `freezed`, Firebase Cloud Messaging (push is optional; the Firestore listener is the primary delivery path, as agreed).

---

## 4. Package Recommendations and Installation

### 4.1 How to add packages safely

Always add with `flutter pub add`, which resolves a compatible version for your Flutter SDK instead of you guessing a number:

```bash
flutter pub add provider go_router http web_socket_channel
flutter pub add firebase_core firebase_auth cloud_firestore
flutter pub add just_audio audio_session flutter_tts
flutter pub add local_auth qr_flutter mobile_scanner
flutter pub add shared_preferences flutter_secure_storage
flutter pub add fl_chart wakelock_plus uuid intl
# Optional live-mic mode only:
flutter pub add record permission_handler
# Dev dependencies:
flutter pub add --dev mocktail
```

Then **commit `pubspec.lock`** and do **not** run `flutter pub upgrade` during the hackathon. A mid-event upgrade is one of the easiest ways to break a working build.

### 4.2 Verification I did (and what to re-check yourself)

On pub.dev, as of my check: `just_audio` is on the 0.10.x line with `audio_session` 0.2.x (older packages that still pin `audio_session ^0.1.x` can conflict), `record` has moved to 7.x (its 6.x line is still widely depended on), and the Firebase packages are on `firebase_core` 4.x, `firebase_auth` 6.x and `cloud_firestore` 6.x. I did not find reason to avoid any package in the table above. Before adding anything, spend 30 seconds on its pub.dev page: check **last published date, Android platform support, and the "pub points" dependency check**.

### 4.3 Package details

| Package | Purpose | Why needed | Compatibility notes |
|---|---|---|---|
| `provider` | State management | Share call/risk/auth state across screens | Stable and tiny |
| `go_router` | Navigation | Declarative routes, redirect to login when signed out | Official Flutter-team package |
| `http` | REST calls | `/calls/start`, `/invites`, `/verifications`, `/history` | Wrap it so every request carries the ID token |
| `web_socket_channel` | WebSocket | Stream audio windows, receive scores | Use `IOWebSocketChannel` so you can send an `Authorization` header |
| `firebase_core` | Firebase init | Required by all Firebase packages | Run `flutterfire configure` |
| `firebase_auth` | Sign-in, ID tokens | `getIdToken()` for backend auth | May require `minSdkVersion` 23; follow the build error and FlutterFire docs |
| `cloud_firestore` | Real-time listeners | Contacts list, verification status | Firestore caches data on device; that is fine because no audio or transcripts are stored |
| `just_audio` | WAV playback | Position stream drives window slicing; `setVolume` for ducking | Prefer the latest compatible major |
| `audio_session` | Audio focus/ducking config | Two audio sources in one app | See the overlap risk in section 17 |
| `flutter_tts` | Fallback alerts | If a bundled clip fails | Check the demo phone has the voice/language installed |
| `local_auth` | Biometric/PIN gate | Responder confirmation UX | **`MainActivity` must extend `FlutterFragmentActivity`** or the prompt fails on Android |
| `qr_flutter` | Show invite QR | Creator side | Pure Dart, low risk |
| `mobile_scanner` | Scan invite QR | Accept side | Needs the camera permission only on the scan screen |
| `shared_preferences` | Local settings | Server address, mock toggle | Not for secrets |
| `flutter_secure_storage` | Secure storage | Only if you add a local PIN | Android Keystore backed |
| `fl_chart` | Score timeline | Window-by-window score graph | Keep charts simple to stay fast |
| `wakelock_plus` | Keep screen on | Prevents sleep mid-call | Works without extra permissions |
| `record` + `permission_handler` | Live-mic mode | **[OPT]** secondary mode | Request mic only when that mode is opened |

---

## 5. Project Folder Structure

```
satyaswar_app/
├── pubspec.yaml
├── analysis_options.yaml
├── README.md
├── android/
│   └── app/src/main/AndroidManifest.xml     # INTERNET, demo cleartext flag
├── assets/
│   ├── audio/
│   │   ├── calls/                           # 16 kHz mono PCM16 WAV clips
│   │   │   ├── genuine_01.wav
│   │   │   ├── clone_ceo_01.wav
│   │   │   ├── noisy_01.wav
│   │   │   └── short_insufficient_01.wav
│   │   └── alerts/                          # pre-recorded voice alerts
│   │       ├── low.wav
│   │       ├── medium.wav
│   │       ├── high.wav
│   │       ├── insufficient.wav
│   │       ├── verification_denied.wav
│   │       └── verification_confirmed.wav
│   ├── scenarios.json                       # demo scenario definitions
│   ├── fonts/                               # bundled font files (no runtime download)
│   └── images/
├── lib/
│   ├── main.dart                            # Firebase init, providers, runApp
│   ├── app.dart                             # MaterialApp.router + theme
│   ├── config/
│   │   ├── app_config.dart                  # useMocks, default server URL (dart-define)
│   │   └── constants.dart                   # window ms, hop ms, sample rate, timeouts
│   ├── routing/
│   │   └── app_router.dart                  # GoRouter + auth redirect
│   ├── theme/
│   │   ├── app_colors.dart
│   │   ├── app_text_styles.dart
│   │   ├── app_theme.dart
│   │   └── risk_style.dart                  # band -> color/icon/label
│   ├── models/
│   │   ├── app_user.dart
│   │   ├── trusted_contact.dart
│   │   ├── scenario.dart
│   │   ├── call_session.dart                # callId, wsUrl, window config
│   │   ├── risk_update.dart                 # one "score" message
│   │   ├── risk_band.dart                   # enum + parsing
│   │   ├── verification_request.dart
│   │   ├── verification_status.dart
│   │   ├── final_outcome.dart
│   │   └── history_entry.dart
│   ├── services/
│   │   ├── api_client.dart                  # REST wrapper, token attach, 401 retry
│   │   ├── call_analysis_service.dart       # interface + WebSocket implementation
│   │   ├── mock_call_analysis_service.dart  # scripted scores for offline dev
│   │   ├── audio_player_service.dart        # just_audio wrapper, duck/restore
│   │   ├── alert_service.dart               # bundled clip -> TTS fallback
│   │   ├── wav_parser.dart                  # RIFF/WAVE parsing, validation
│   │   ├── window_planner.dart              # window math and slicing
│   │   ├── audio_frame_builder.dart         # binary frame encoder
│   │   ├── window_sender.dart               # playback position -> send windows
│   │   └── biometric_service.dart           # local_auth wrapper
│   ├── repositories/
│   │   ├── auth_repository.dart
│   │   ├── contacts_repository.dart         # Firestore stream + invite REST
│   │   ├── verification_repository.dart     # REST + Firestore listener
│   │   ├── history_repository.dart
│   │   └── scenario_repository.dart         # loads assets/scenarios.json
│   ├── providers/
│   │   ├── auth_provider.dart
│   │   ├── settings_provider.dart           # server address, mock toggle
│   │   ├── contacts_provider.dart
│   │   ├── call_provider.dart               # call lifecycle state machine
│   │   ├── risk_monitor_provider.dart       # live scores and alert hysteresis
│   │   ├── verification_provider.dart
│   │   └── history_provider.dart
│   ├── screens/
│   │   ├── splash/splash_screen.dart
│   │   ├── auth/login_screen.dart
│   │   ├── auth/register_screen.dart
│   │   ├── home/home_screen.dart
│   │   ├── contacts/contacts_screen.dart
│   │   ├── contacts/add_contact_screen.dart       # create invite / accept invite
│   │   ├── contacts/scan_invite_screen.dart
│   │   ├── call/scenario_picker_screen.dart
│   │   ├── call/incoming_call_screen.dart
│   │   ├── call/active_call_screen.dart
│   │   ├── verification/verify_caller_sheet.dart
│   │   ├── verification/outcome_screen.dart
│   │   ├── verification/responder_screen.dart     # second-phone responder
│   │   ├── history/history_screen.dart
│   │   ├── history/history_detail_screen.dart
│   │   └── settings/settings_screen.dart
│   ├── widgets/
│   │   ├── common/                                # PrimaryButton, GlassCard, AppScaffold, StatusChip, EmptyState, ErrorState, LoadingOverlay
│   │   ├── risk/risk_meter.dart
│   │   ├── risk/risk_band_badge.dart
│   │   ├── risk/evidence_quality_bar.dart
│   │   ├── risk/score_timeline_chart.dart
│   │   ├── call/simulated_banner.dart
│   │   ├── call/call_timer.dart
│   │   └── contacts/contact_tile.dart
│   └── utils/
│       ├── result.dart                            # simple success/failure wrapper
│       ├── time_format.dart
│       └── logger.dart                            # never logs tokens or audio
└── test/
    ├── unit/
    │   ├── wav_parser_test.dart
    │   ├── window_planner_test.dart
    │   ├── audio_frame_builder_test.dart
    │   ├── band_hysteresis_test.dart
    │   └── risk_update_parsing_test.dart
    ├── widget/
    │   ├── risk_meter_test.dart
    │   └── verify_sheet_test.dart
    ├── providers/
    │   ├── call_provider_test.dart
    │   └── verification_provider_test.dart
    └── integration/
        └── full_call_flow_test.dart
```

Parallel-development benefit: `services/` interfaces plus `mock_call_analysis_service.dart` let you build every screen before the backend exists.

### 5.1 Demo scenario file (`assets/scenarios.json`)

```json
[
  {
    "id": "genuine_family",
    "title": "Genuine call from a known contact",
    "claimedName": "Priyanka",
    "callerNumber": "+91 98xxxxxx01",
    "audioAsset": "assets/audio/calls/genuine_01.wav",
    "durationMs": 17500
  },
  {
    "id": "clone_ceo",
    "title": "Cloned CEO requesting an urgent transfer",
    "claimedName": "Rakesh Sir",
    "callerNumber": "Unknown",
    "audioAsset": "assets/audio/calls/clone_ceo_01.wav",
    "durationMs": 21000
  }
]
```

**Authoring rule for clips:** make each clip `3.5 s + n x 1.75 s` long (for example 17.5 s or 21.0 s). Then the final window ends exactly at the clip end and no partial window exists.

---

## 6. UI/UX Specification

### 6.1 Design principles

Modern, minimal, dark-first, blue and white. Glassmorphism is used **only** on the call overlay and the verification sheet (blur is expensive; keep it to two or three widgets). Risk states must be readable without color alone (icon plus label plus color).

### 6.2 Color palette

| Token | HEX | Use |
|---|---|---|
| `background` | `#0A0F1C` | Screen background |
| `surface` | `#121A2B` | Cards |
| `surfaceHigh` | `#1A2438` | Elevated cards, sheets |
| `border` | `#26334D` | Dividers, outlines |
| `primary` | `#3B82F6` | Primary buttons, links |
| `primaryDeep` | `#1D4ED8` | Pressed state, gradients |
| `primaryGlow` | `#60A5FA` | Highlights |
| `textPrimary` | `#F8FAFC` | Main text (white) |
| `textSecondary` | `#94A3B8` | Secondary text |
| `riskLow` | `#22C55E` | Low risk |
| `riskMedium` | `#F59E0B` | Medium risk |
| `riskHigh` | `#EF4444` | High risk |
| `riskUnknown` | `#94A3B8` | Insufficient evidence |
| `success` | `#16A34A` | Confirmed |
| `warning` | `#F59E0B` | Pending/expiring |
| `danger` | `#DC2626` | Denied/errors |
| `glass` | `#FFFFFF` at 8% opacity | Glass card fill |

### 6.3 Typography

Bundle a font such as **Inter** (or Manrope) in `assets/fonts/` instead of using `google_fonts`, which downloads fonts at runtime and can fail on a hotspot.

| Style | Size / weight |
|---|---|
| Display (risk number) | 56 / 700 |
| Title | 22 / 600 |
| Section header | 16 / 600 |
| Body | 14 / 400 |
| Caption | 12 / 400, `textSecondary` |
| Monospace (codes) | 20 / 600, letter spacing 2 |

### 6.4 Component styles

- **Buttons:** primary = filled blue, radius 14, height 52, white label; secondary = outlined `border`; destructive = filled `danger`. Disabled = 40% opacity. Minimum touch target 48 dp.
- **Cards:** `surface` fill, 1 px `border`, radius 18, padding 16. Glass card: 8% white fill, 12 px blur, 1 px white 12% border.
- **Risk indicator:** a circular gauge (semi-circle arc) with the band label under the number, an icon (shield-check, shield-alert, shield-x, help-circle), and an evidence-quality bar below it. The number is labelled "Risk index", never "probability".
- **Chips:** connection status (Connected / Reconnecting / Offline), simulated-call banner.
- **Navigation:** bottom navigation with Home, Contacts, History, Settings. The call flow is full-screen and hides the bar.
- **Loading:** skeleton blocks on lists; a centered spinner for blocking actions with a text label.
- **Empty states:** icon, one-line explanation, one action button ("Add your first trusted contact").
- **Error states:** icon, plain explanation, "Try again" button, and a technical detail line in small text for the demo operator.
- **Success/warning states:** colored left border on cards plus an icon.
- **Animation:** 200 to 300 ms ease-out transitions; the gauge animates between values; no looping animations except the ringing pulse.

### 6.5 Screen-by-screen layouts

**Splash:** centered logo and tagline "Detect. Score. Decide. Verify.", checks the auth state, routes to Login or Home.

**Login:** logo, email field, password field, "Sign in" button, "Create account" link. Inline error text under fields.

**Register:** full name, email, password, confirm password, "Create account". Short note: "Your voice is analysed in memory and never stored."

**Home:**
1. Greeting card ("Welcome, <name>") with a security status chip ("Protection ready" if the server is reachable, otherwise "Server offline").
2. Large primary card **"Start simulated call"**.
3. Row of shortcuts: Trusted contacts (with count), History.
4. "Recent calls" list (last 3 entries).
5. Footer note: "Calls in this prototype are simulated."

**Trusted contacts:** list of tiles (alias, registered name, label, linked date). Floating button "Add contact". Empty state when none.

**Add contact:** two tabs. *Invite someone* generates a code and QR with an expiry countdown. *Accept an invite* has a code field and a "Scan QR" button. After accepting, a form asks for an optional alias and a required label if the registered name duplicates an existing contact.

**Scenario picker:** list of scenarios from `scenarios.json` with a short description, plus a "Direction" toggle (incoming, outgoing).

**Incoming call:** full-screen, pulsing avatar, claimed caller name, number, a **"SIMULATED CALL" banner at the top**, round Decline (red) and Accept (green) buttons.

**Active call:**
1. Simulated banner and connection chip at the top.
2. Caller name and call timer.
3. Risk gauge (center) with band badge and evidence-quality bar.
4. Row of small stats: usable speech seconds, windows analysed, last round-trip latency.
5. Score timeline chart (window-by-window).
6. Alert message strip (latest alert text).
7. Bottom bar: **Verify caller** (always visible), End call.

**Verify caller (bottom sheet):** step 1 pick the claimed contact (candidates highlighted, never pre-selected, with "Not in my contacts" option), step 2 pick what is being asked (Money transfer, OTP or credentials, Confidential information, Other; optional amount), step 3 pending view with the **match code** large, an expiry countdown ring, and a live status line.

**Outcome:** large outcome headline and icon, a plain-language recommendation, the voice result summary, the verification result, and buttons "Back to home" and "View in history".

**Responder (second phone):** list of pending requests; opening one asks the precise question "Are you on a call with <requester> right now?", shows three code options, requires the biometric gate, then Confirm or Deny.

**History:** list with date, claimed contact, peak band badge, verification status, outcome. Detail screen repeats the fields and the score timeline if the server provides it.

**Settings:** server address field (with a "Test connection" button and QR scan option), mock-mode toggle (demo build only), alert volume, account and logout.

---

## 7. Detailed Module Specifications

For each module: screens, logic, backend calls, states, tests, and done criteria.

### Module A: Authentication [MVP]

**Screens:** Splash, Login, Register, Profile (inside Settings).

**Flows:**
- *Register:* `createUserWithEmailAndPassword`, then update the display name, then call the backend to create the user profile if Member 2's design requires it **[PROPOSAL: a first authenticated request, or Firestore profile created server-side on first call]**.
- *Login:* `signInWithEmailAndPassword`.
- *Session:* Firebase persists the session. `authStateChanges()` drives routing through a `ChangeNotifier` that `GoRouter` listens to (`refreshListenable`).
- *Logout:* sign out, clear provider state, cancel any listeners.

**Token handling:** every REST call and the WebSocket handshake use `await user.getIdToken()`. The SDK refreshes automatically. On a `401`, call `getIdToken(true)` once and retry once; if it still fails, sign out.

**Secure communication:** HTTPS in production. For the demo, plain `http://` and `ws://` to the laptop on the hotspot (see section 12).

**Tests:** unit-test `AuthProvider` with a fake `AuthRepository`; widget-test form validation (empty email, short password).

**Done when:** a new user can register, close and reopen the app and stay signed in, and logout returns to Login.

### Module B: Home Dashboard [MVP]

Described in section 6.5. Data: user name, contact count (from `ContactsProvider`), last 3 history items (from `HistoryProvider`), server reachability (a `GET` health check or the settings "Test connection"; **[PROPOSAL: backend exposes `GET /health`]**).

**Done when:** all shortcuts navigate correctly and empty states render with no data.

### Module C: Trusted Contacts [MVP]

**Data source:** Firestore stream of `users/{uid}/contacts` (read-only for the client). Fields the app expects **[PROPOSAL]**:

```json
{
  "contactUid": "uid_abc",
  "registeredName": "Priyanka Sharma",
  "alias": "Priti",
  "label": "college",
  "displayCode": "U102",
  "linkedAt": "2026-10-30T10:12:00Z"
}
```

**Create invite:** `POST /invites` returns a code and expiry. Show the code in monospace and a QR containing `satyaswar:invite:<code>`.

**Accept invite:** typed code or scanned QR; strip the prefix, then `POST /invites/{code}/accept`. On success show the new contact and ask for the alias and label.

**Duplicate names:** if two contacts share a `registeredName`, the form forces a unique `label`. The list shows `alias` first, then `registeredName`, then `label` as a chip. Contacts are always keyed by `contactUid`, never by name or phone number.

**Alias editing and unlinking:** not in the agreed endpoint list. **[OPEN QUESTION]** Either a restricted Firestore write on `alias` and `label` only, or proposed endpoints `PATCH /contacts/{contactUid}` and `DELETE /links/{linkId}`. Build the UI behind a feature flag until Member 2 decides.

**Do not** use phone-number discovery anywhere.

**Tests:** parsing of the QR payload (valid, wrong prefix, expired), duplicate-name label rule, empty state.

**Done when:** two accounts (two phones, or one phone and the laptop responder) can link through an invite and both see each other.

### Module D: Simulated Call Interface [MVP]

**Lifecycle:**
1. User picks a scenario and direction.
2. App calls `POST /calls/start` **at ring time** so the dashboard can show "ringing".
3. Incoming screen shows the claimed name from the scenario. **Accept** opens the WebSocket and starts playback together. **Decline** ends the session (see open question on `POST /calls/{id}/end`).
4. Active screen runs the timer from the moment playback starts.
5. **End call** stops playback, sends a WebSocket `end` message, closes the socket after the server's outcome message (or a timeout), and shows the verification or outcome flow.

**Simulation honesty:** a permanent banner reads "SIMULATED CALL. This is not a cellular call." The same text appears on the incoming screen.

**Optional trigger from the dashboard** (operator makes the phone ring): needs a signal channel such as a Firestore document the app listens to. **[OPT] [OPEN QUESTION]**; the MVP trigger is the in-app button.

**Done when:** ring, accept, timer, playback and end work with the mock service even without the server.

### Module E: Audio Processing and Streaming [MVP]

Fully specified in section 8.

### Module F: Real-Time Risk Monitoring [MVP]

**Input:** `score` JSON messages (section 9.3).

**State held by `RiskMonitorProvider`:**

```dart
class RiskMonitorState {
  final RiskBand? currentBand;        // smoothed band from server
  final double? riskIndex;            // 0-100 display value
  final VoiceOutcome? outcome;        // likelyGenuine | suspicious | insufficientEvidence
  final EvidenceQuality? evidence;    // level + usableSpeechSec
  final List<WindowScore> timeline;   // for the chart
  final int windowsAnalysed;
  final int? lastRoundTripMs;         // measured client-side
  final bool analysisConnected;
}
```

**UI rules:**
- Show "Risk index" and band label. Never "probability of fake".
- Low band text: "No synthetic indicators detected. This is not proof of identity."
- Insufficient evidence shows a grey gauge and "Not enough clear speech yet".
- The first result needs about 3.5 s of speech plus processing time. Before it arrives, show "Analysing (first result in about 4 seconds)".
- Round-trip latency is measured **on the phone** (send time stored per `seq`, subtracted on receipt). This avoids clock-sync problems between phone and laptop.

**Validation:** reject messages missing `type`, with a band outside the known values, or a score outside 0 to 100 (log and ignore, never crash).

**Done when:** scripted mock scores move the gauge, change colors and fill the timeline correctly.

### Module G: Alert System [MVP]

**Alert events:** low, medium, high, insufficient evidence, verification denied, verification confirmed.

**Rules:**
1. Alerts trigger on **band changes** only.
2. A new band must be seen on **2 consecutive windows** before it becomes the stable band (configurable), except that the first stable band after the call starts is set at the first score.
3. A cooldown (default 8 s) blocks any spoken alert from firing right after another.
4. The same band never repeats.
5. A de-escalation (for example high to medium) is shown on screen but only spoken if it reaches low or insufficient evidence **and** the stable window count is met.
6. Verification result alerts are always spoken once.
7. Every spoken alert has the same text on screen.

**Ducking:** lower the call player volume to about 0.2, play the alert, restore volume when the alert finishes (also restore in a `finally`). See section 17 for the audio-focus risk and fallback.

**Hysteresis sketch:**

```dart
class BandHysteresis {
  BandHysteresis({this.confirmWindows = 2});
  final int confirmWindows;
  RiskBand? _stable, _candidate;
  int _count = 0;

  /// Returns the new stable band if it changed, otherwise null.
  RiskBand? update(RiskBand incoming) {
    if (_stable == null) { _stable = incoming; return incoming; }
    if (incoming == _stable) { _candidate = null; _count = 0; return null; }
    if (incoming == _candidate) { _count++; } else { _candidate = incoming; _count = 1; }
    if (_count >= confirmWindows) {
      _stable = incoming; _candidate = null; _count = 0;
      return incoming;
    }
    return null;
  }
}
```

**Done when:** a scripted score sequence produces exactly the expected alerts, with no repeats and no overlap with call audio.

### Module H: Caller Verification [MVP]

**Steps in the UI:**
1. **Claimed contact selection.** The server may send ranked `claimed_identity` candidates over the WebSocket **[PROPOSAL]**. The app highlights the best guess but never pre-selects it. A manual picker listing all trusted contacts is always available, plus "Not in my contacts".
2. **Requested action:** `money_transfer`, `otp_credentials`, `confidential_info`, `other`, with an optional amount.
3. **Create request:** `POST /verifications` with the selected `contactUid`.
4. **Pending:** display the **match code** returned by the server and an expiry countdown (from `expiresAt`). Listen to `verificationRequests/{id}` in Firestore.
5. **Result states:** confirmed, denied, expired (shown as **Unverified**, never as safe), no contact match, error.
6. **Final decision:** the server sends an `outcome` message; the app renders it.

**The client never decides.** It only reflects `status` from Firestore and `outcome` from the server.

**No-contact-match state:** if the user selects "Not in my contacts", show "SatyaSwar cannot verify this person. Do not proceed on this call. Contact them through a number you already know." and send the server an `unmatched` indication **[PROPOSAL: `POST /verifications` is not called; the WebSocket sends `verification_unavailable`]** so the decision function still receives that state.

**Responder side (same app on a second phone, [MVP if you have a second phone, otherwise the laptop page]):** a query on `verificationRequests` where `targetUid == myUid && status == "pending"`. The responder screen asks the precise question, requires the biometric/PIN gate (`local_auth`), shows three candidate codes, and calls `POST /verifications/{id}/respond`.

**Honest note on the biometric gate:** biometric success is checked **on the device**, so the server cannot verify it. It is a user-experience safeguard. The server-verifiable protections are the authenticated ID token, the number-matching code, single-use state and expiry. Say this plainly in the pitch.

**Done when:** all four paths work with the real backend: confirm, deny, expire, no match.

### Module I: Call History [MVP]

`GET /history` returns scores-only entries. The list and detail screens show date and time, claimed contact, peak risk index, band, evidence quality, verification status and final outcome. No audio, no transcript. Pull-to-refresh and a short loading skeleton.

**Done when:** a completed call appears in history after refresh with all fields populated.

---

## 8. Audio Processing and Streaming Design

This is the most technical module. The design goal is a **deterministic simulated tap**: the app plays a bundled clip and, in step with playback, sends exactly the audio the listener has "heard" so far to the analysis server.

### 8.1 Audio file requirements

Prepare every call clip **once, offline, on your laptop**, so the app never has to resample at runtime:

```bash
# Convert any source to 16 kHz, mono, 16-bit PCM WAV, trimmed to 17.5 s
ffmpeg -i source.mp3 -ac 1 -ar 16000 -sample_fmt s16 -c:a pcm_s16le -t 17.5 genuine_01.wav
# Check it
ffprobe -hide_banner genuine_01.wav
```

| Requirement | Value |
|---|---|
| Container | RIFF/WAVE |
| Encoding | PCM, 16-bit little-endian (`pcm_s16le`) |
| Sample rate | 16000 Hz |
| Channels | 1 (mono) |
| Duration | `3.5 s + n x 1.75 s` (for example 17.5 s, 21.0 s, 24.5 s) |

Why prepare offline instead of converting in the app: runtime resampling and stereo-to-mono code is extra bug surface and costs time. The app **validates** the format on load and shows a clear developer error if a clip is wrong. If you later need runtime conversion (for live-mic mode), handle it there: ask the recorder for 16 kHz mono PCM16 directly rather than converting afterwards.

### 8.2 Concepts, in beginner terms

- **PCM16:** each audio sample is one signed 16-bit integer (2 bytes). 16 kHz means 16,000 samples per second. One second is 32,000 bytes.
- **Window:** a chunk of audio the model scores. Window = 3.5 s = 56,000 samples = **112,000 bytes**.
- **Hop:** how far the next window starts after the previous one. Hop = 1.75 s = 28,000 samples. Windows overlap by 50%.
- **Window count** for a clip of `N` samples: `1 + (N - 56000) ~/ 28000`. A 17.5 s clip (280,000 samples) gives 9 windows.
- **Sequence number (`seq`):** 0, 1, 2, ... one per window, so the server can detect loss and reorder, and the app can match each score to its window.
- **Offset (`offsetMs`):** where the window starts inside the call audio. Window `i` starts at `i x 1750` ms.

### 8.3 WAV parsing (`lib/services/wav_parser.dart`)

WAV files can contain extra chunks (such as `LIST`) before `data`, so do not assume a fixed 44-byte header. Walk the chunks:

```dart
import 'dart:typed_data';

class WavData {
  WavData(this.sampleRate, this.channels, this.bitsPerSample, this.samples);
  final int sampleRate, channels, bitsPerSample;
  final Int16List samples; // mono PCM16
  int get durationMs => samples.length * 1000 ~/ sampleRate;
}

class WavParser {
  static WavData parse(Uint8List bytes) {
    final bd = ByteData.sublistView(bytes);
    if (bytes.length < 44 || _tag(bytes, 0) != 'RIFF' || _tag(bytes, 8) != 'WAVE') {
      throw const FormatException('Not a RIFF/WAVE file');
    }
    int? sr, ch, bits, fmt, dataStart, dataLen;
    var offset = 12;
    while (offset + 8 <= bytes.length) {
      final id = _tag(bytes, offset);
      final size = bd.getUint32(offset + 4, Endian.little);
      final body = offset + 8;
      if (id == 'fmt ') {
        fmt = bd.getUint16(body, Endian.little);
        ch = bd.getUint16(body + 2, Endian.little);
        sr = bd.getUint32(body + 4, Endian.little);
        bits = bd.getUint16(body + 14, Endian.little);
      } else if (id == 'data') {
        dataStart = body;
        dataLen = size.clamp(0, bytes.length - body);
        break;
      }
      offset = body + size + (size.isOdd ? 1 : 0); // chunks are word-aligned
    }
    if (fmt != 1) throw const FormatException('WAV must be PCM (format 1)');
    if (sr != 16000) throw FormatException('Expected 16000 Hz, got $sr');
    if (ch != 1) throw FormatException('Expected mono, got $ch channels');
    if (bits != 16) throw FormatException('Expected 16-bit, got $bits');
    if (dataStart == null || dataLen == null) throw const FormatException('No data chunk');

    final n = dataLen ~/ 2;
    final samples = Int16List(n);
    for (var i = 0; i < n; i++) {
      samples[i] = bd.getInt16(dataStart + i * 2, Endian.little);
    }
    return WavData(sr!, ch!, bits!, samples);
  }

  static String _tag(Uint8List b, int o) => String.fromCharCodes(b.sublist(o, o + 4));
}
```

Load the asset with `rootBundle.load(path)` and call `WavParser.parse(data.buffer.asUint8List())`.

### 8.4 Window planning (`lib/services/window_planner.dart`)

Read `windowMs` and `hopMs` from the `POST /calls/start` response (defaults 3500 and 1750) so the app and server can never disagree.

```dart
class WindowPlanner {
  WindowPlanner({required this.totalSamples, this.sampleRate = 16000,
                 this.windowMs = 3500, this.hopMs = 1750});
  final int totalSamples, sampleRate, windowMs, hopMs;

  int get windowSamples => sampleRate * windowMs ~/ 1000; // 56000
  int get hopSamples => sampleRate * hopMs ~/ 1000;       // 28000
  int get count => totalSamples < windowSamples
      ? 0 : 1 + (totalSamples - windowSamples) ~/ hopSamples;

  int startSampleOf(int i) => i * hopSamples;
  int startMsOf(int i) => startSampleOf(i) * 1000 ~/ sampleRate;
  int endMsOf(int i) => (startSampleOf(i) + windowSamples) * 1000 ~/ sampleRate;

  Int16List sliceOf(Int16List pcm, int i) {
    final s = startSampleOf(i);
    return Int16List.sublistView(pcm, s, s + windowSamples);
  }
}
```

Clips shorter than one window produce zero windows. Handle that case by showing "Clip too short for analysis" in development; for the "insufficient evidence" demo clip, make it a normal length with mostly silence or heavy noise instead, so the **server** decides it is insufficient.

### 8.5 Binary frame format **[PROPOSAL, needs Member 2's approval]**

All integers are **little-endian**. One WebSocket binary message = one window.

| Bytes | Field | Type | Meaning |
|---|---|---|---|
| 0 | `version` | uint8 | `1` |
| 1 | `flags` | uint8 | bit 0 = last window |
| 2-3 | `reserved` | uint16 | `0` |
| 4-7 | `seq` | uint32 | Window sequence number from 0 |
| 8-11 | `offsetMs` | uint32 | Window start inside the call audio |
| 12-19 | `sendEpochMs` | uint64 | Phone clock at send time (informational) |
| 20-... | `pcm` | int16[] | 56,000 samples (112,000 bytes) |

```dart
Uint8List buildAudioFrame({
  required int seq,
  required int offsetMs,
  required int sendEpochMs,
  required Int16List pcm,
  bool isLast = false,
}) {
  const headerLen = 20;
  final out = Uint8List(headerLen + pcm.length * 2);
  final bd = ByteData.sublistView(out);
  bd.setUint8(0, 1);
  bd.setUint8(1, isLast ? 1 : 0);
  bd.setUint16(2, 0, Endian.little);
  bd.setUint32(4, seq, Endian.little);
  bd.setUint32(8, offsetMs, Endian.little);
  bd.setUint64(12, sendEpochMs, Endian.little);
  for (var i = 0; i < pcm.length; i++) {
    bd.setInt16(headerLen + i * 2, pcm[i], Endian.little);
  }
  return out;
}
```

### 8.6 Synchronising slicing with playback (`lib/services/window_sender.dart`)

Window `i` is sent when playback position reaches the **end** of that window (`endMsOf(i)`), which simulates audio arriving live: the server never gets audio the "listener" has not yet heard.

```dart
class WindowSender {
  WindowSender({required this.player, required this.pcm, required this.planner,
                required this.onFrame});
  final AudioPlayer player;           // from just_audio
  final Int16List pcm;
  final WindowPlanner planner;
  final void Function(Uint8List frame, int seq, DateTime sentAt) onFrame;

  int _next = 0;
  StreamSubscription<Duration>? _posSub;
  StreamSubscription<PlayerState>? _stateSub;

  void start() {
    _posSub = player.positionStream.listen((pos) {
      while (_next < planner.count && pos.inMilliseconds >= planner.endMsOf(_next)) {
        _emit(_next++);
      }
    });
    _stateSub = player.playerStateStream.listen((s) {
      if (s.processingState == ProcessingState.completed) {
        while (_next < planner.count) { _emit(_next++); } // flush rounding leftovers
      }
    });
  }

  void _emit(int i) {
    final now = DateTime.now();
    final frame = buildAudioFrame(
      seq: i, offsetMs: planner.startMsOf(i),
      sendEpochMs: now.millisecondsSinceEpoch,
      pcm: planner.sliceOf(pcm, i),
      isLast: i == planner.count - 1,
    );
    onFrame(frame, i, now);
  }

  Future<void> dispose() async {
    await _posSub?.cancel();
    await _stateSub?.cancel();
  }
}
```

Behaviour notes:
- `positionStream` ticks roughly every 200 ms, so a window may be sent up to about 0.2 s late. That is acceptable.
- If playback is **paused**, position stops and nothing is sent. Seeking is disabled in the UI.
- Call `dispose()` when the call ends so no listener keeps running.

### 8.7 Sequence numbers, timestamps, latency

- `seq` starts at 0 for each call and increments by 1 per window. Never reuse a `seq`.
- Keep a `Map<int, DateTime> _sentAt`. When a `score` message with `seq` arrives, round-trip latency = `now - _sentAt[seq]`. Remove the entry afterwards.
- `sendEpochMs` is informational only; do not depend on phone and laptop clocks agreeing.

### 8.8 Buffer management and backpressure

Each window is about 112 KB and one is sent every 1.75 s, which is trivial for a local network. Still:

- Do not accumulate frames in memory. Build, send, drop.
- If the socket is not connected when a window is due, **do not queue more than 2 stale windows**; mark the gap in the timeline ("analysis interrupted") and continue with the next live window after reconnect. Stale audio is worthless for a real-time score.

### 8.9 Connection loss and reconnection

```
connected -> (error/close while call active) -> reconnecting
reconnecting: retry after 0.5 s, 1 s, 2 s, 4 s, 4 s (max 5 attempts)
   success  -> send hello with {resume: true, lastSeq} [PROPOSAL] -> connected
   failure  -> failed: show banner "Analysis unavailable", keep audio playing
```

On final failure the call can continue, but the UI must say "Analysis interrupted; results may be incomplete" and the outcome must be treated as **insufficient evidence**. Never fabricate scores.

### 8.10 Error handling summary

| Situation | App behaviour |
|---|---|
| Asset missing or invalid WAV | Developer error dialog naming the file and the expected format |
| `POST /calls/start` fails | Error state with retry; do not ring |
| WebSocket handshake rejected (401) | Refresh token once, retry once, then show "Please sign in again" |
| Server sends `error` message | Show message; if `fatal` is true end analysis |
| Malformed JSON | Log and ignore; never crash |
| Server silent for more than 8 s mid-call | Show "Waiting for analysis" and start reconnect logic |
| App goes to background | Pause playback, stop sending, show "Call paused" on return |

### 8.11 Live-microphone mode [OPT]

Secondary only. Use the `record` package with a PCM16 stream at 16 kHz mono (`AudioEncoder.pcm16bits`, `sampleRate: 16000`, `numChannels: 1`), accumulate into the same `WindowPlanner` logic using a rolling buffer, and request `RECORD_AUDIO` only when the user opens this mode. Pause capture while an alert plays so the alert is not analysed. Check the `record` changelog for the current API before coding; the major version changed recently.

---

## 9. Backend API Integration Contract

**Everything in this section is a [PROPOSAL] unless the solution document already defined it.** The solution document defines the endpoint names and the existence of the WebSocket, binary PCM windows, scores, and the verification state machine, but **not** the payloads. Freeze this with Member 2 in the first hour (checkpoint CP0).

### 9.1 Division of responsibility

| Mobile developer (you) | Backend developer (Member 2) | Must agree on together |
|---|---|---|
| UI, audio slicing, frame encoding, WebSocket client, reconnect, alert logic, Firestore listeners, REST client | Token verification, `/calls/start`, WebSocket server, verification state machine, invites, history, Firestore rules, decision function | JSON field names and enums, binary frame layout, auth handshake, error codes, `seq` and window config, who fires the "ring", unlink/alias endpoints, whether the WebSocket supports resume |
| | | ML team (Member 3): score range, band thresholds, evidence-quality definition, whether `claimed_identity` arrives over the WebSocket |

### 9.2 REST endpoints

All requests carry `Authorization: Bearer <Firebase ID token>`. All bodies are JSON. Timestamps are ISO 8601 UTC.

**POST /calls/start**

```json
// request
{
  "scenarioId": "clone_ceo",
  "claimedName": "Rakesh Sir",
  "callerNumber": "Unknown",
  "direction": "incoming",
  "audio": { "sampleRate": 16000, "channels": 1, "durationMs": 21000 }
}
// response 201
{
  "callId": "call_8f21a",
  "wsUrl": "ws://192.168.43.10:8000/ws/call/call_8f21a",
  "config": { "windowMs": 3500, "hopMs": 1750, "sampleRate": 16000 },
  "serverTime": "2026-10-31T06:12:09Z"
}
```

**POST /invites**

```json
// response 201
{ "code": "K7M2-9QX4", "expiresAt": "2026-10-31T06:22:00Z",
  "qrPayload": "satyaswar:invite:K7M2-9QX4" }
```

**POST /invites/{code}/accept**

```json
// request
{ "alias": "Priti", "label": "college" }
// response 200
{ "linkId": "link_91b", "contact": {
    "contactUid": "uid_abc", "registeredName": "Priyanka Sharma", "displayCode": "U102" } }
// errors: 404 invalid code, 410 expired/used, 409 already linked, 400 cannot link to self
```

**POST /verifications**

```json
// request
{
  "callId": "call_8f21a",
  "targetUid": "uid_abc",
  "claimedName": "Priyanka",
  "actionType": "money_transfer",          // money_transfer | otp_credentials | confidential_info | other
  "amount": 50000                          // optional
}
// response 201
{ "verificationId": "ver_77d", "matchCode": "47",
  "status": "pending", "expiresAt": "2026-10-31T06:14:10Z" }
// errors: 403 not linked, 429 rate limited, 409 an active request already exists
```

**POST /verifications/{id}/respond** (responder side)

```json
// request
{ "decision": "confirm", "selectedCode": "47" }     // decision: confirm | deny
// response 200
{ "status": "confirmed" }
// errors: 403 wrong user, 409 already answered, 410 expired, 400 code mismatch
```

**GET /history**

```json
{ "items": [ {
    "callId": "call_8f21a", "startedAt": "2026-10-31T06:12:09Z",
    "claimedContact": "Priyanka Sharma", "peakRiskIndex": 91, "peakBand": "high",
    "evidenceQuality": "good", "verificationStatus": "denied",
    "finalOutcome": "likely_impersonation" } ] }
```

**Optional additions to ask Member 2 for:** `GET /health`, `POST /calls/{callId}/end` (decline or abort before the WebSocket opens), `PATCH /contacts/{contactUid}` (alias and label), `DELETE /links/{linkId}` (unlink).

### 9.3 WebSocket: `/ws/call/{callId}`

**Connection and authentication**

- URL comes from `POST /calls/start`.
- Connect with `IOWebSocketChannel.connect(uri, headers: {'Authorization': 'Bearer $idToken'})`.
- The first JSON message from the client is a `hello`.
- Do not put the token in the URL (URLs get logged).

**Client to server**

```json
// text frame, once, right after connecting
{ "type": "hello", "callId": "call_8f21a", "client": "flutter", "version": 1,
  "resume": false, "lastSeq": null }

// text frame, when the call ends
{ "type": "end", "reason": "user_ended", "lastSeq": 8 }

// text frame, if the user says the caller is not a trusted contact
{ "type": "verification_unavailable", "reason": "no_contact_match" }
```

Binary frames: audio windows as defined in section 8.5.

**Server to client**

```json
{ "type": "hello_ack", "callId": "call_8f21a", "config": { "windowMs": 3500, "hopMs": 1750 } }

{
  "type": "score",
  "seq": 3,
  "windowStartMs": 5250,
  "windowRiskIndex": 78,
  "call": { "riskIndex": 71, "band": "high", "peakRiskIndex": 78 },
  "voiceOutcome": "suspicious",              // likely_genuine | suspicious | insufficient_evidence
  "evidence": { "level": "good", "usableSpeechSec": 9.8 },   // level: good | limited | poor
  "serverProcessingMs": 420
}

{ "type": "claimed_identity",
  "candidates": [ { "contactUid": "uid_abc", "label": "Priyanka Sharma (Priti)", "confidence": "medium" } ],
  "heardName": "Priyanka" }

{ "type": "outcome", "finalOutcome": "likely_impersonation",
  "headline": "Likely impersonation. Do not proceed.",
  "recommendation": "Contact the person through a number you already know." }

{ "type": "error", "code": "model_unavailable", "message": "Analysis is temporarily unavailable.", "fatal": false }
```

**Termination:** the client sends `end`, waits up to about 5 s for `outcome`, then closes with code 1000. The server may close first after sending `outcome`.

**Reconnection:** see section 8.9. Needs a decision from Member 2 on whether `resume` is supported. If not, the call fails gracefully into "insufficient evidence".

**Server to client: note on the transcript.** The solution document says transcripts are never stored. If Member 2/3 want to show the transcript on the **dashboard** only, the phone does not receive or display it.

### 9.4 Mock strategy summary

The app depends on two interfaces so it can run without a server:

```dart
abstract class CallAnalysisService {
  Stream<ServerMessage> get messages;
  Stream<ConnectionStatus> get status;
  Future<void> connect(CallSession session, String idToken);
  void sendFrame(Uint8List frame);
  void sendControl(Map<String, dynamic> json);
  Future<void> close();
}
```

`WebSocketCallAnalysisService` is the real one; `MockCallAnalysisService` emits scripted `score` messages (timed to the received windows) per scenario. See section 14.

---

## 10. Firebase Integration

### 10.1 Setup steps (do these exactly, once)

1. Member 2 creates the Firebase project and adds you as an editor, **or** you create it and share it. Decide in hour 0.
2. Enable **Authentication, Email/Password** in the console.
3. Install tools:
   ```bash
   npm install -g firebase-tools
   dart pub global activate flutterfire_cli
   firebase login
   ```
4. In the project root run:
   ```bash
   flutterfire configure
   ```
   Choose the project and the Android platform. This generates `lib/firebase_options.dart` and registers the Android app. Follow the CLI output for any Gradle changes it asks for.
5. Initialise in `main.dart`:
   ```dart
   void main() async {
     WidgetsFlutterBinding.ensureInitialized();
     await Firebase.initializeApp(options: DefaultFirebaseOptions.currentPlatform);
     runApp(const SatyaSwarApp());
   }
   ```
6. If the build complains about `minSdkVersion`, set it in `android/app/build.gradle` (or `.kts`) as the error message suggests (often 23).
7. For `local_auth`, change `android/app/src/main/kotlin/.../MainActivity.kt` so it extends `FlutterFragmentActivity`.
8. Add `android:allowBackup="false"` to the `<application>` tag.
9. Add the **SHA-1 and SHA-256** of your debug keystore in the Firebase console if you later enable Google sign-in:
   ```bash
   cd android && ./gradlew signingReport
   ```

### 10.2 What the app reads from Firestore (read-only)

| Path | Used by | Purpose |
|---|---|---|
| `users/{uid}/contacts/*` | ContactsProvider | Trusted contacts list |
| `verificationRequests/{id}` | VerificationProvider | Live status of my request |
| `verificationRequests` where `targetUid == me` and `status == "pending"` | Responder screen | Incoming requests |

**Never write** to `verificationRequests`; the server owns it. Ask Member 2 for Firestore rules that allow exactly these reads and nothing else.

### 10.3 Pattern for a safe Firestore listener

```dart
StreamSubscription? _sub;

void watch(String verificationId) {
  _sub?.cancel();                                   // never two listeners
  _sub = FirebaseFirestore.instance
      .collection('verificationRequests').doc(verificationId)
      .snapshots()
      .listen(_onSnapshot, onError: _onError);
}

@override
void dispose() {
  _sub?.cancel();
  super.dispose();
}
```

### 10.4 Local caching note

Firestore keeps a local cache on the device. That is acceptable: it holds contact and verification metadata only, never audio or transcripts.

---

## 11. State Management

### 11.1 Providers

| Provider | Holds | Lifetime |
|---|---|---|
| `AuthProvider` | Current user, auth status | App |
| `SettingsProvider` | Server address, mock toggle, alert volume | App |
| `ContactsProvider` | Contacts stream, invite state | App (after login) |
| `CallProvider` | **Call lifecycle state machine**, session, timer, playback state | Per call |
| `RiskMonitorProvider` | Live scores, evidence, timeline, alert hysteresis | Per call |
| `VerificationProvider` | Selected contact, action, request state, countdown | Per call |
| `HistoryProvider` | History list, loading and error | App |

`CallProvider`, `RiskMonitorProvider` and `VerificationProvider` are **created when a call starts and disposed when the call screen closes** (use `ChangeNotifierProvider` scoped at the call route, or a `CallScope` widget). This is the single biggest protection against stale state and leaks.

### 11.2 Call lifecycle and transitions

```
idle
  -> starting          (POST /calls/start in flight)
  -> ringing           (session created)        | failed
ringing
  -> connecting        (user accepted: open WebSocket)   | declined -> ended
connecting
  -> active            (hello_ack received and playback started) | failed
active
  -> reconnecting      (socket dropped)  -> active | analysisLost
  -> ending            (user ended or audio completed)
ending
  -> awaitingOutcome   (end sent, waiting for outcome)
awaitingOutcome
  -> ended             (outcome received or timeout)
ended -> idle
```

Verification sub-states (independent of the call phase, but only meaningful while `active` or after `ended`):

```
none -> selecting -> creating -> pending -> confirmed | denied | expired | error
none -> noMatch   (user chose "Not in my contacts")
```

Model both as Dart `enum`s and change them only through methods on the provider. Never set them from widgets.

### 11.3 Avoiding leaks and duplicate listeners

1. **One owner per resource.** `CallProvider` owns the `AudioPlayer`, the `WindowSender` and the WebSocket service. When the call ends it disposes all of them in one method.
2. **Always keep and cancel your `StreamSubscription`s**, including in `dispose()`.
3. **Guard late events:**
   ```dart
   bool _disposed = false;
   @override void dispose() { _disposed = true; /* cancel everything */ super.dispose(); }
   void _safeNotify() { if (!_disposed) notifyListeners(); }
   ```
4. **Never open a second socket** while one is active; check the status first.
5. **Use `context.read` (not `watch`) in callbacks**, and `mounted` checks after any `await` in a widget.
6. **Lifecycle:** implement `WidgetsBindingObserver` in the call screen. On `paused`, pause playback and stop sending; on `resumed`, show "Call paused" and let the user resume or end. On `detached`, end the call.
7. **Audio:** dispose the `AudioPlayer`s when the call ends; keep the alert player separate from the call player so you can stop one without the other.
8. **Wakelock:** enable at call start, disable in `dispose()` (wrap in try/finally).

### 11.4 Wiring example (`lib/main.dart`, simplified)

```dart
runApp(MultiProvider(
  providers: [
    ChangeNotifierProvider(create: (_) => SettingsProvider()..load()),
    ChangeNotifierProvider(create: (_) => AuthProvider(AuthRepository())),
    ProxyProvider<SettingsProvider, ApiClient>(
      update: (_, s, __) => ApiClient(baseUrl: s.serverUrl, tokenProvider: AuthRepository.idToken)),
    ChangeNotifierProxyProvider<AuthProvider, ContactsProvider>(
      create: (_) => ContactsProvider(),
      update: (_, auth, c) => c!..bind(auth.user)),
    ChangeNotifierProvider(create: (_) => HistoryProvider()),
  ],
  child: const SatyaSwarApp(),
));
```

---

## 12. Security and Privacy

### 12.1 Principles and how the app enforces them

| Principle | Implementation |
|---|---|
| No permanent audio | The WAV is a bundled asset; windows exist only in memory while being sent. Never write audio to disk, never log it. In live-mic mode, stream to memory only (no file path in the recorder). |
| No stored transcripts | The phone does not receive transcripts. If a transcript ever reaches the app, display only and never persist. |
| No service-account credentials | Only `firebase_options.dart` (public client config) is in the app. Never commit a service-account JSON anywhere. |
| Never trust client verification status | The app has no code path that writes `status` or the final decision. |
| ID tokens for backend auth | `ApiClient` and the WebSocket handshake attach `getIdToken()`. |
| Secure storage | Firebase persists the session itself. `flutter_secure_storage` is only for a local PIN hash if you add one. `shared_preferences` is for non-secret settings. |
| Validate server responses | Parse defensively; unknown enum values map to a safe default (`insufficient_evidence` for voice outcome, "unverified" for verification). |
| Minimal permissions | `INTERNET` always. Camera only on the QR scan screen. Microphone only in live-mic mode. No notification, contacts or location permission. |
| Session expiry | One token refresh retry, then sign out. |
| Simulation clarity | A banner on incoming and active screens: "SIMULATED CALL". |
| Logging | `logger.dart` redacts tokens and never prints payload bytes. Disable verbose logging in release. |
| Backups | `android:allowBackup="false"`. |

### 12.2 Android networking for the local laptop server

Android 9 and later block plain (cleartext) `http://` and `ws://` traffic by default. Your demo server on the laptop is on a local IP without HTTPS, so the demo build needs an explicit exception.

Two things to do:

1. **Release builds do not include the INTERNET permission by default.** Add to `android/app/src/main/AndroidManifest.xml`:
   ```xml
   <uses-permission android:name="android.permission.INTERNET"/>
   ```
2. **Demo-only cleartext** on the `<application>` tag:
   ```xml
   <application
       android:usesCleartextTraffic="true"
       android:allowBackup="false"
       ... >
   ```
   Add a visible comment: `<!-- DEMO ONLY: remove before any real deployment -->`. A tighter alternative is a `network_security_config.xml` that permits cleartext only for hosts you list; check that IP-address entries behave as expected on your test phone before relying on it.

Other demo networking tasks:
- Put the phone and the laptop on the **same hotspot**.
- Open the laptop firewall for the backend port (for example 8000).
- Use the Settings screen's **server address field** (and optional QR from the dashboard) because the laptop's IP can change.
- Add a "Test connection" button.

### 12.3 Demo-only settings versus production requirements

| Demo (acceptable now) | Production (required later) |
|---|---|
| Cleartext `http://` and `ws://` on a local network | TLS everywhere (`https://`, `wss://`) with proper certificates |
| Email/password sign-in | Phone-number verification, device attestation, hardened account recovery |
| Biometric gate as a client-side convenience | Device-bound signed challenge (Android Keystore) verified by the server |
| Bundled clips simulate the call | Telecom or VoIP integration at the tap point |
| Mock toggle in Settings | Removed from release builds |
| Server address typed by hand | Fixed, pinned production endpoint |

### 12.4 Threat model reminder (say it in the pitch)

The responder's device and account are assumed uncompromised. A confirmation is evidence, not a guarantee.

---

## 13. Implementation Roadmap

Time estimates assume you are new to Flutter and working in parallel with Members 2 and 3. Total is about 20 hours of your own work, leaving slack inside a 24-hour window. Stages marked **[MVP]** must be finished; **[OPT]** stages are cut first.

### Stage 1: Environment and project setup [MVP] (about 1.5 h)

- **Objective:** a "hello world" running on the actual demo phone.
- **Tasks:**
  1. Install Flutter and the Android SDK; run `flutter doctor` until clean.
  2. Enable developer options and USB debugging on the phone; confirm with `adb devices`.
  3. `flutter create --org com.satyaswar --platforms android satyaswar_app`
  4. Create the folder structure from section 5 (empty files are fine).
  5. Create a Git repository and a `.gitignore` check (never commit keys).
  6. `flutter run` on the phone.
- **Files:** `pubspec.yaml`, folder skeleton.
- **Packages:** none yet.
- **Dependencies:** none.
- **Expected output:** the default counter app on your phone.
- **Testing:** hot reload a text change; build a debug APK with `flutter build apk --debug`.
- **Complete when:** the app runs on the demo phone and a teammate can clone and run it.

### Stage 2: Theme and UI foundation [MVP] (about 1.5 h)

- **Objective:** the design system and reusable widgets.
- **Tasks:** colors, text styles, `ThemeData` (dark), `AppScaffold`, `PrimaryButton`, `GlassCard`, `StatusChip`, `EmptyState`, `ErrorState`, `LoadingOverlay`, `RiskBandBadge` (static), bundled font, `go_router` skeleton with placeholder screens.
- **Files:** `lib/theme/*`, `lib/widgets/common/*`, `lib/routing/app_router.dart`, `lib/app.dart`.
- **Packages:** `go_router`, `provider`.
- **Dependencies:** Stage 1.
- **Expected output:** a style-guide screen that shows every component in every state.
- **Testing:** widget test that `RiskBandBadge` shows the right label and color per band.
- **Complete when:** all placeholder routes navigate and the theme looks consistent.

### Stage 3: Authentication [MVP] (about 2 h)

- **Objective:** register, log in, persist the session, log out.
- **Tasks:** `flutterfire configure`; `AuthRepository`, `AuthProvider`; Splash, Login, Register; router redirect on auth state; token helper `AuthRepository.idToken()`.
- **Files:** `lib/main.dart`, `lib/firebase_options.dart` (generated), `lib/repositories/auth_repository.dart`, `lib/providers/auth_provider.dart`, `lib/screens/splash/*`, `lib/screens/auth/*`.
- **Packages:** `firebase_core`, `firebase_auth`.
- **Dependencies:** Firebase project and Email/Password enabled (Member 2 or you).
- **Expected output:** a user can register, close and reopen the app, and stay signed in.
- **Testing:** manual register/login/logout; unit test `AuthProvider` with a fake repository; test wrong-password error message.
- **Complete when:** the session persists and logout returns to Login.

### Stage 4: Home dashboard [MVP] (about 1 h)

- **Objective:** the main hub and navigation.
- **Tasks:** `HomeScreen` with the cards from section 6.5; bottom navigation; `SettingsProvider` with server address and the mock toggle (load/save with `shared_preferences`); Settings screen with "Test connection".
- **Files:** `lib/screens/home/*`, `lib/screens/settings/*`, `lib/providers/settings_provider.dart`, `lib/config/*`.
- **Packages:** `shared_preferences`.
- **Dependencies:** Stages 2 and 3.
- **Expected output:** Home with welcome, "Start simulated call", shortcuts, empty recent calls.
- **Testing:** widget test for empty states; verify the server address persists after restart.
- **Complete when:** every shortcut navigates and settings survive a restart.

### Stage 5: Trusted contacts [MVP] (about 2 h)

- **Objective:** link two accounts through an invite.
- **Tasks:** `ContactsRepository` (Firestore stream plus invite REST calls), `ContactsProvider`, list screen, add-contact screen (create and accept tabs), QR show/scan, alias and label form with duplicate-name rule. Start against mocks if the backend is not ready.
- **Files:** `lib/repositories/contacts_repository.dart`, `lib/providers/contacts_provider.dart`, `lib/services/api_client.dart`, `lib/models/trusted_contact.dart`, `lib/screens/contacts/*`, `lib/widgets/contacts/contact_tile.dart`.
- **Packages:** `cloud_firestore`, `http`, `qr_flutter`, `mobile_scanner`.
- **Dependencies:** invite endpoints and contacts structure from Member 2 (or mocks).
- **Expected output:** create an invite on one phone, accept it on another, both lists update.
- **Testing:** unit-test QR payload parsing; widget-test the duplicate-label rule; manual two-account test.
- **Complete when:** a real link between two accounts works and the contact appears in the list.

### Stage 6: Simulated call interface [MVP] (about 1.5 h)

- **Objective:** the call experience without audio yet.
- **Tasks:** `ScenarioRepository` (loads `scenarios.json`), scenario picker, incoming screen, active screen shell, `CallProvider` state machine, timer, simulated banner, `wakelock_plus`.
- **Files:** `lib/models/scenario.dart`, `lib/repositories/scenario_repository.dart`, `lib/providers/call_provider.dart`, `lib/screens/call/*`, `lib/widgets/call/*`, `assets/scenarios.json`.
- **Packages:** `wakelock_plus`.
- **Dependencies:** Stage 4.
- **Expected output:** ring, accept, timer runs, end call returns Home.
- **Testing:** unit-test every legal and illegal state transition in `CallProvider`.
- **Complete when:** the full ring-to-end flow works with the mock service and the banner is always visible.

### Stage 7: WAV playback and digital audio slicing [MVP] (about 2.5 h) **critical**

- **Objective:** play the clip and produce correct windows in step with playback.
- **Tasks:** prepare clips with ffmpeg (section 8.1); `WavParser`, `WindowPlanner`, `AudioFrameBuilder`, `AudioPlayerService` (just_audio, volume control), `WindowSender`; log window index, byte length and timing (no payload) to verify.
- **Files:** `lib/services/wav_parser.dart`, `window_planner.dart`, `audio_frame_builder.dart`, `window_sender.dart`, `audio_player_service.dart`, `assets/audio/calls/*`, `test/unit/*`.
- **Packages:** `just_audio`, `audio_session`.
- **Dependencies:** Stage 6; clips from Member 3 (or placeholders, same format).
- **Expected output:** during playback of a 17.5 s clip, exactly 9 frames of 112,020 bytes each (112,000 plus the 20-byte header) are produced, at the expected times.
- **Testing:** unit tests (parser rejects wrong format; planner count and boundaries; frame header bytes); on-device check of window timing against the playback position.
- **Complete when:** the sender produces the right count, sizes and seq numbers, and stops cleanly on end call.

### Stage 8: WebSocket integration [MVP] (about 2 h)

- **Objective:** send frames to a real or mock server and receive JSON.
- **Tasks:** `CallAnalysisService` interface; `WebSocketCallAnalysisService` (connect with token header, hello, binary send, JSON parse, status stream, reconnect with backoff); `MockCallAnalysisService`; `AppConfig.useMocks` toggle.
- **Files:** `lib/services/call_analysis_service.dart`, `mock_call_analysis_service.dart`, `lib/models/risk_update.dart`, `lib/models/call_session.dart`, `lib/services/api_client.dart` (for `/calls/start`).
- **Packages:** `web_socket_channel`.
- **Dependencies:** Stage 7; cleartext and INTERNET manifest edits (section 12.2); a running server or the mock.
- **Expected output:** against the mock, scripted scores arrive after each window; against Member 2's echo server, frames arrive intact (they should confirm size and `seq`).
- **Testing:** unit tests with a fake channel; kill the server mid-call and confirm the reconnect states; wrong-token test.
- **Complete when:** a real round trip works end to end on the hotspot, measured latency is displayed.

### Stage 9: Real-time risk monitoring [MVP] (about 2 h)

- **Objective:** live gauge, band, evidence quality, timeline.
- **Tasks:** `RiskMonitorProvider`, `RiskMeter`, `EvidenceQualityBar`, `ScoreTimelineChart`, stats row, "analysing" and "insufficient" states, defensive parsing.
- **Files:** `lib/providers/risk_monitor_provider.dart`, `lib/widgets/risk/*`, `lib/models/risk_band.dart`, `lib/theme/risk_style.dart`.
- **Packages:** `fl_chart`.
- **Dependencies:** Stage 8.
- **Expected output:** gauge animates through low, medium, high and insufficient states from mock data; the real server changes it later.
- **Testing:** widget tests for each state; unit test malformed messages are ignored.
- **Complete when:** the UI matches the spec for all three outcomes and never shows "verified" or "probability".

### Stage 10: Alerts [MVP] (about 1.5 h)

- **Objective:** spoken and visual alerts without overlap or repetition.
- **Tasks:** record or generate the six alert clips (Member 3 can help); `AlertService` (just_audio clip first, `flutter_tts` fallback), `BandHysteresis`, cooldown, duck and restore, alert text strip.
- **Files:** `lib/services/alert_service.dart`, hysteresis class (in `risk_monitor_provider.dart` or its own file), `assets/audio/alerts/*`, `test/unit/band_hysteresis_test.dart`.
- **Packages:** `flutter_tts`.
- **Dependencies:** Stage 9; audio focus test on the real phone.
- **Expected output:** a scripted low-to-high sequence produces exactly one spoken high alert, with call audio ducked and restored.
- **Testing:** unit tests for hysteresis and cooldown; on-device overlap test; test with the phone volume low and high.
- **Complete when:** alerts are audible, never loop, and the call audio resumes at normal volume.

### Stage 11: Verification workflow [MVP] (about 2.5 h)

- **Objective:** the differentiating feature, end to end.
- **Tasks:** `VerificationRepository` (REST plus Firestore listener), `VerificationProvider`, verify sheet (contact picker, action picker, pending with code and countdown), results (confirmed, denied, expired, no match), outcome screen, responder screen with `local_auth`.
- **Files:** `lib/repositories/verification_repository.dart`, `lib/providers/verification_provider.dart`, `lib/screens/verification/*`, `lib/models/verification_*.dart`, `lib/models/final_outcome.dart`, `lib/services/biometric_service.dart`.
- **Packages:** `local_auth`.
- **Dependencies:** Stages 5 and 9; Member 2's endpoints and rules (or mocks); `MainActivity` change (section 10.1).
- **Expected output:** request created, code displayed, responder confirms or denies, the requester's screen updates in real time, and the outcome screen shows the server's decision.
- **Testing:** four-path scenario test (confirm, deny, expire, no match); double-tap on Confirm; countdown accuracy; responder cannot respond for someone else.
- **Complete when:** all four paths work against the real backend.

### Stage 12: Call history [MVP] (about 1 h)

- **Objective:** scores-only history.
- **Tasks:** `HistoryRepository` (`GET /history`), `HistoryProvider`, list and detail screens, pull to refresh, recent calls on Home.
- **Files:** `lib/repositories/history_repository.dart`, `lib/providers/history_provider.dart`, `lib/screens/history/*`, `lib/models/history_entry.dart`.
- **Packages:** `intl`.
- **Dependencies:** Member 2's `/history`.
- **Expected output:** a completed demo call appears in history with all fields.
- **Testing:** empty, loading and error states; date formatting; confirm no audio or transcript fields exist.
- **Complete when:** history matches what the dashboard recorded.

### Stage 13: Backend integration [MVP] (about 2 h, overlapping)

- **Objective:** replace every mock with the real service.
- **Tasks:** switch `useMocks` off per feature, run the full path against the real server, fix field-name mismatches, tune timeouts, rehearse on the hotspot.
- **Files:** configuration only, plus fixes.
- **Packages:** none.
- **Dependencies:** checkpoints CP1 to CP5 (section 14).
- **Expected output:** the complete demo path runs with real scores.
- **Testing:** the full scenario matrix (section 15.4).
- **Complete when:** the full path works three times in a row.

### Stage 14: Testing and APK generation [MVP] (about 1.5 h)

- **Objective:** a demo-ready build and backups.
- **Tasks:** `flutter test`; failure-mode tests; remove debug noise; set the app name and icon; build the release APK; install on the demo phone and a spare device; record a backup video of a successful run.
- **Commands:**
  ```bash
  flutter test
  flutter build apk --release
  adb install -r build/app/outputs/flutter-apk/app-release.apk
  ```
  (A release build needs the INTERNET permission in the main manifest; see section 12.2. If you use a custom signing config, follow Flutter's Android release documentation.)
- **Expected output:** `app-release.apk` that works offline from your laptop's IDE.
- **Testing:** fresh-install test: install on a phone that has never run the app and complete a full demo.
- **Complete when:** the release APK passes the acceptance checklist in section 16.

**Cut order if you fall behind:** live-mic mode, alias editing and unlinking, history detail chart, dashboard-triggered ring, QR scanning (keep typed codes), responder biometric (keep password re-entry or a PIN).

---

## 14. Parallel Team Development

### 14.1 Working while others are still building

You must be able to build almost everything with **no backend and no model**. Use these seams:

| Dependency | Interface in the app | Temporary mock | Replace when |
|---|---|---|---|
| Analysis socket | `CallAnalysisService` | `MockCallAnalysisService` emits a scripted `score` after each sent window (scenario-specific sequences, with realistic 300 to 800 ms delays, including an "insufficient evidence" script) | CP2 (echo server) then CP3 (real model) |
| REST client | `ApiClient` | Fake that returns canned `POST /calls/start`, invites, verifications and history | CP1 |
| Contacts | `ContactsRepository` | In-memory list | CP1 |
| Verification | `VerificationRepository` | Fake that moves `pending` to `confirmed` or `denied` after a delay, with a button on a debug panel | CP4 |
| Auth | `AuthRepository` | Use real Firebase Auth from the start (cheap) | n/a |
| Alert audio | `AlertService` | Placeholder beeps or TTS | When Member 3 delivers clips |

Switch with `--dart-define=USE_MOCKS=true` for development, and a Settings toggle for demo day. **Add a visible "MOCK" chip** whenever mocks are active so no one accidentally demos fake results.

### 14.2 Integration checkpoints

| Checkpoint | Time | What must be true | Owners |
|---|---|---|---|
| **CP0** Contract freeze | Hour 0 to 1 | Section 9 payloads agreed; Firebase project shared; server IP and port convention set; demo clip format set | All |
| **CP1** REST skeleton | About hour 4 | `/calls/start`, invites, verifications and history return the agreed JSON (even with fake data) | You and Member 2 |
| **CP2** WebSocket echo | About hour 6 | Server accepts the handshake and acknowledges each binary frame, logging `seq` and byte size | You and Member 2 |
| **CP3** Real scores | About hour 10 | Frames reach the model; `score` messages use real detector output | Member 3 and Member 2, you verify the UI |
| **CP4** Verification real | About hour 14 | State machine live; two accounts confirm and deny | You and Member 2 |
| **CP5** Full dry run | About hour 18 | Complete demo flow with the dashboard | All |
| **CP6** Freeze | About hour 21 | Only bug fixes; release APK built | All |

### 14.3 What to hand each teammate

- **To Member 2:** this document's section 9 as the proposed contract; the binary frame spec with a test vector (a hex dump of one header plus a few samples); the list of Firestore reads the app performs; the requirement that the final outcome and history come from the server.
- **To Member 3:** the clip format and the `3.5 + n x 1.75 s` duration rule; the six alert messages to record; the `evidence.level` and `voiceOutcome` enums you expect; confirmation that the model receives 56,000-sample windows (or pads to the model's input).
- **From Member 2:** the server URL, test accounts, Firestore rules, an echo endpoint early.
- **From Member 3:** demo clips, alert recordings, and the band thresholds so the UI labels match.

---

## 15. Testing Strategy

### 15.1 Commands

```bash
flutter test                        # unit and widget tests
flutter test test/unit              # one folder
flutter test integration_test       # on a connected device (add integration_test to dev dependencies when you reach it)
flutter analyze                     # static checks
```

### 15.2 Unit tests

| Test file | What it proves |
|---|---|
| `wav_parser_test.dart` | Accepts a valid 16 kHz mono PCM16 WAV; rejects stereo, 44.1 kHz, 8-bit, non-PCM; skips a `LIST` chunk before `data` |
| `window_planner_test.dart` | 280,000 samples gives 9 windows; start and end ms are exact (0/3500, 1750/5250 ...); clip shorter than a window gives 0 windows |
| `audio_frame_builder_test.dart` | Header bytes are exact (version, flags, little-endian seq, offset, timestamp); payload length is 112,000 bytes; last flag set |
| `band_hysteresis_test.dart` | A single outlier window does not change the band; two consecutive do; no repeat on the same band; cooldown blocks rapid alerts |
| `risk_update_parsing_test.dart` | Valid message parses; unknown band maps to safe default; missing fields are rejected without throwing |

Example:

```dart
test('17.5 s clip gives 9 windows of 56000 samples', () {
  final p = WindowPlanner(totalSamples: 280000);
  expect(p.count, 9);
  expect(p.sliceOf(Int16List(280000), 8).length, 56000);
  expect(p.endMsOf(8), 17500);
});
```

### 15.3 Widget and provider tests

- `RiskMeter` renders the correct label, icon and color for each band; never contains the text "verified" or "probability".
- Verify sheet: contact list never pre-selects; "Not in my contacts" leads to the no-match state.
- `CallProvider` legal and illegal transitions (cannot go from `ended` to `active`).
- `VerificationProvider`: `expired` is displayed as unverified, never as safe; the provider has no method that sets `confirmed` locally.
- Authentication: invalid email, short password, wrong credentials, session restored after restart (use a fake repository).

### 15.4 Scenario matrix (manual, on the real phone)

| # | Scenario | Expected |
|---|---|---|
| 1 | Genuine clip, no verification | Low band, "No synthetic indicators detected" message, not labelled verified |
| 2 | Clone clip, verification denied | High band, spoken alert, outcome "likely impersonation" |
| 3 | Clone clip, verification confirmed | Conflicting-signals outcome (not auto-cleared) |
| 4 | Clone clip, no response | Request expires, shown as **Unverified**, sensitive action still held |
| 5 | User selects "Not in my contacts" | No-match state with the guidance text |
| 6 | Noisy or short clip | Insufficient-evidence state; no forced classification |
| 7 | Duplicate contact names | Both listed with labels; none pre-selected |

### 15.5 WebSocket and network tests

- Handshake with an expired or wrong token (expect 401 then one refresh retry).
- Stop the server mid-call (expect the reconnecting state, backoff, then failure banner).
- Turn the phone's Wi-Fi off and on during a call.
- Server sends malformed JSON (app ignores it).
- Server sends an `error` with `fatal: true` (analysis ends, call audio can continue, outcome shows insufficient evidence).
- Wrong server address in Settings (clear error, "Test connection" fails clearly).

### 15.6 Audio tests

- Window sender emits exactly the expected frames for each demo clip, and stops on end call.
- Alert plays while the call audio is ducked, then volume returns.
- Alert fired twice in quick succession (cooldown holds).
- App backgrounded mid-call (playback pauses, sending stops, no crash on return).
- Headset and speaker output both work.

### 15.7 End-to-end test

One integration test using the mock service drives: login, start a scenario, accept, feed scripted scores, verify, outcome, history. The same flow is then run manually against the real backend (Stage 13).

### 15.8 Acceptance criteria (testing)

1. All unit and widget tests pass.
2. The scenario matrix passes on the demo phone three times in a row.
3. The first score appears within about 6 seconds of accepting a call on the hotspot (3.5 s of audio plus processing); later scores every 1.75 s plus processing.
4. No crash when the server is killed mid-call.
5. No audio or transcript data found in app storage (check with `adb shell run-as <package> ls files cache` on a debug build).

---

## 16. Final Demo Acceptance Checklist

| # | Demonstration requirement | How to prove it | Done |
|---|---|---|---|
| 1 | User authentication | Register, restart the app, still signed in | ☐ |
| 2 | Trusted-contact linking | Invite code or QR accepted on a second account; both lists show the contact | ☐ |
| 3 | Simulated incoming call | Ring screen with the **simulated** banner | ☐ |
| 4 | Audio playback | Clip plays through the phone speaker | ☐ |
| 5 | Actual audio-window transmission | Dashboard shows windows arriving with increasing `seq` | ☐ |
| 6 | Actual ML-generated detection results | Scores differ between genuine and clone clips; mock chip is **off** | ☐ |
| 7 | Live risk updates | Gauge, band, evidence and timeline update about every 1.75 s | ☐ |
| 8 | Voice and visual alerts | Spoken alert on band change, call audio ducked, text strip shown | ☐ |
| 9 | Verification request | Match code and countdown visible | ☐ |
| 10 | Responder confirmation or denial | Second phone or laptop page responds; requester updates live | ☐ |
| 11 | Final decision | Outcome screen shows the **server's** decision | ☐ |
| 12 | Scores-only history | History entry with no audio or transcript fields | ☐ |
| 13 | Honesty | Banner says simulated; slides list real vs simulated | ☐ |
| 14 | Resilience | Release APK installed; backup video recorded; spare phone ready | ☐ |

**Pre-demo ritual (10 minutes before):** phone on hotspot and charged, laptop on the same hotspot, server running, "Test connection" green, volume set, Do Not Disturb on, scenario clips verified, second phone or responder page signed in, mock toggle **off**.

---

## 17. Technical Risks and Mitigation

| Risk | Impact | Mitigation |
|---|---|---|
| **Audio focus conflict:** the alert clip steals focus and pauses call playback (two players in one app) | Demo glitch at the key moment | Test on day one. Options in order: configure one shared `audio_session`; construct the players with interruption handling disabled and verify on the phone; play alerts through `flutter_tts` or a different audio plugin that does not request exclusive focus; as a last resort pause the call, speak, and resume |
| Hotspot instability or changing laptop IP | Connection fails during the demo | Settings server field, QR for the address, "Test connection", reconnect with backoff, a rehearsal on the real network, local hotspot not venue Wi-Fi |
| Cleartext traffic blocked | Silent connection failure | Manifest flag and INTERNET permission (section 12.2), test with a **release** APK, not just debug |
| First-time Flutter, Firebase and Gradle setup delays | Lost hours | Stage 1 first; `flutterfire configure` early; build a release APK early to catch Gradle problems |
| `local_auth` crash | Responder screen fails | `FlutterFragmentActivity`, test on the demo phone; fallback is password re-entry or a PIN |
| Backend contract drift | Mismatched JSON | CP0 freeze, shared sample JSON files, tolerant parsing, contract tests against the mock |
| ML latency too high on the laptop | Laggy demo | Measure at CP3; show processing time in the UI; Member 3 uses the GPU or the smaller-model fallback |
| Model gives poor results on the phone-recorded demo audio | Weak demo | Demo uses bundled clips prepared with the same pipeline Member 3 tested; report limits honestly |
| Package update breaks the build | Lost time | Commit `pubspec.lock`; no upgrades mid-hackathon |
| Memory leaks or duplicate listeners | Crashes after a few calls | Section 11.3 rules; run three consecutive calls in testing |
| Overclaiming | Credibility loss | "Simulated call" banner; never "verified" from voice alone; scores called "risk index" |
| TTS voice missing on the demo phone | Silent fallback | Bundled alert clips are primary; test TTS availability on the phone |
| Clip duration not matching the window rule | Partial window or misaligned results | Author clips as `3.5 + n x 1.75 s`; planner unit tests |

---

## 18. Open Questions Requiring Confirmation from Teammates

**For Member 2 (backend and Firebase):**

1. Do you approve the REST and WebSocket payloads in section 9, or what changes do you want?
2. How does the WebSocket authenticate: the `Authorization` header (preferred) or something else?
3. Does the server support `resume` after a dropped socket, or should a drop end analysis?
4. Where does the final outcome travel: a WebSocket `outcome` message, a Firestore field, or both? What happens if the socket is already closed?
5. Are alias and label edits done by a restricted Firestore write, or via `PATCH /contacts/{contactUid}`? Will you provide `DELETE /links/{linkId}` for unlinking?
6. Will you add `GET /health` and `POST /calls/{callId}/end`?
7. Who creates the user profile document on first sign-in, and what fields?
8. Which Firestore reads are permitted by the rules (contacts, my verification requests, pending requests for me)?
9. Does the server send ranked `claimed_identity` candidates over the WebSocket, and in what shape?
10. Should the dashboard be able to make the phone ring? If yes, through which channel?
11. Second device for the responder: a second phone with this app, or the laptop responder page?

**For Member 3 (AI/ML):**

12. What are the risk-index range and the band thresholds, and how is `evidence.level` defined (usable speech seconds, SNR, window agreement)?
13. Does the model take exactly 56,000 samples, or does the server pad to its expected length?
14. Can you provide the demo clips (format rules in section 8.1) and the six alert recordings, in which language(s)?
15. How should "insufficient evidence" be triggered, and will the demo include a clip that reliably triggers it?
16. What is the realistic per-window processing time on the demo laptop (GPU and CPU)?

**For the whole team:**

17. Which exact scenarios will the demo show, in which order?
18. Is the app display name "SatyaSwar", and who provides the logo and icon?
19. Who owns the pitch slide that lists real versus simulated components?

---

## Appendix A: Quick Command Reference

```bash
# Project
flutter create --org com.satyaswar --platforms android satyaswar_app
flutter doctor
flutter devices
flutter run
flutter run --dart-define=USE_MOCKS=true

# Packages
flutter pub get
flutter pub outdated          # information only; do not upgrade mid-hackathon

# Firebase
dart pub global activate flutterfire_cli
flutterfire configure

# Android
adb devices
adb logcat | grep -i satyaswar
cd android && ./gradlew signingReport

# Audio prep
ffmpeg -i in.mp3 -ac 1 -ar 16000 -sample_fmt s16 -c:a pcm_s16le -t 17.5 out.wav

# Builds
flutter build apk --debug
flutter build apk --release
adb install -r build/app/outputs/flutter-apk/app-release.apk
```

## Appendix B: Build-Order Summary (one screen)

1. Environment and hello world on the demo phone.
2. Theme and shared widgets.
3. Auth.
4. Home and settings.
5. Contacts and invites.
6. Simulated call screens and state machine.
7. WAV parsing, windowing, frame encoding, playback sync (**critical**).
8. WebSocket client and mock service.
9. Risk monitor UI.
10. Alerts and ducking.
11. Verification and responder.
12. History.
13. Real backend integration.
14. Tests, release APK, backup video.