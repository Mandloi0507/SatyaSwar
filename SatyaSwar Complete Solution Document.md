# SatyaSwar: Complete Solution Document

Detect. Score. Decide. Verify. | SIH 2026, Problem Statement 26104 | AICTE Cyber Security Cell | Theme: Blockchain & Cybersecurity

Status: draft for team review before implementation. Statistics come from secondary sources and vendor surveys; cite them with their source and treat them as ranges.

## 1. Executive Summary

Voice cloning lets an attacker impersonate a CEO, an official or a family member from about three seconds of recorded audio. People cannot reliably tell a clone from a real voice, and current call-verification habits (caller ID, call-back, voice familiarity) fail under pressure.

SatyaSwar is a real-time voice integrity layer. It does not stop at a real-or-fake label. It runs four stages:

1. **Detect:** analyse live audio windows with a fine-tuned anti-spoofing model.
2. **Score:** produce a rolling risk band with an honest evidence-quality measure.
3. **Decide:** combine the voice result with context (claimed identity, requested action) in one decision function.
4. **Verify:** confirm the caller through an independent channel, a push request to the claimed person's own registered account, so protection still works when the detector is wrong.

The 24-hour prototype is a Flutter Android app on the phone and a FastAPI analysis server plus live dashboard on a laptop. The call is simulated inside the app. The analysis, verification and decision logic are real.

## 2. Problem Statement

**Official statement (PS 26104):** Current telephony and communication ecosystems lack a robust, AI-driven mechanism to detect and flag voice cloning or synthetic speech impersonation during live calls. Existing solutions rarely analyse acoustic artifacts, prosody and speech generation patterns in a granular way, and typically cannot provide an actionable risk score while the conversation is ongoing. An end-to-end framework is needed that analyses incoming voice streams in near real time, estimates the likelihood of a cloned or AI-generated voice, and gives timely alerts and recommendations before sensitive actions are taken. It must be privacy-preserving, scalable across telecom and enterprise environments, and support multilingual contexts with diverse Indian accents and dialects.

**Our refined problem statement:** Attackers can convincingly impersonate trusted people on live calls, and neither humans nor today's systems can reliably tell cloned voices from real ones in the moment. We need a system that scores voice authenticity continuously during a call, understands who the caller claims to be, verifies that claim through an independent channel, and advises the user before money or confidential information changes hands, while keeping audio private and working across Indian languages and real phone-line conditions.

**Who is affected:** bank customers and frontline staff, enterprise finance and approval teams, government offices, telecom operators, and elderly or non-technical users who are targeted most often.

## 3. Problem Analysis

### 3.1 Metrics

| Type | Metric | Why it matters |
| --- | --- | --- |
| Detection | EER (Equal Error Rate), minDCF | Standard in ASVspoof challenges |
| Detection | FAR / FRR at a fixed threshold | Banks care about false alarms on genuine customers |
| Detection | Calibration quality | The PS asks for a usable risk score |
| Real-time | Time-to-first-score, per-window latency | The 'real-time' requirement |
| Robustness | Per-codec, per-language, per-noise breakdown | Lab results rarely hold on phone lines |
| Impact | Loss per incident, incidents per year, share of people who cannot tell | Sizes the problem |

### 3.2 How big is the problem

- **Ease of attack:** one tool in a McAfee study produced an 85% match from three seconds of audio. Cloning tools are reported at prices as low as 20 US dollars. Leading synthesis models run at 40 to 150 ms latency, so real-time impersonation is feasible.
- **Human limits:** a 2023 McAfee survey found 69% of Indian adults could not tell an AI voice from a real one, and 47% had experienced or knew someone who had experienced an AI voice scam, almost double the 25% global average (vendor survey).
- **India overall:** reported cyber fraud losses were about 22,846 crore rupees in 2024, up from about 2,290 crore in 2022. I4C (MHA) has projected up to 1.2 lakh crore rupees for 2025, about 0.7% of GDP. Voice cloning is one part of this, but it is the trust-breaker that makes digital-arrest, CEO-fraud and family-emergency scams work.

### 3.3 Money burning

- Per corporate incident: roughly 280,000 to 680,000 US dollars on average depending on the source.
- Headline cases: a reported 35 million dollar corporate theft through executive impersonation; an Italian defence minister's cloned voice used to extract nearly 1 million euros.
- Global totals range from about 200 million to 4.2 billion US dollars annually depending on definitions. FBI-reported AI-related scam losses were about 893 million dollars across 22,364 complaints in 2025 (secondary source citing FBI IC3).
- Takeaway for judges: totals are uncertain, but loss per incident is large enough that one prevented attack justifies the system.

### 3.4 How frequent

- Reported surges: enterprise voice fraud up about 1,300%, AI-enabled scams up about 1,210% during 2025, and a 450% rise in voice-cloning cases recorded by Haryana's cyber cell in late 2025.
- Among Indian victims in the McAfee survey, 83% lost money and 48% lost more than 50,000 rupees.
- Most cases go unreported, so every figure is a floor.

### 3.5 Existing solutions

- **Research:** ASVspoof 5 adds codec-encoded audio and adversarial attacks. Self-supervised front-ends (wav2vec2, WavLM, XLS-R) with AASIST-style heads are the strongest practical family.
- **Commercial:** Pindrop Pulse claims 99% accuracy with under 1% false positives, 90% on unseen deepfakes, detection from about 2 s of audio and 150 ms response (vendor claims). Its focus is contact centres. Reality Defender's own ASVspoof 5 paper reports 5.5% EER on ASVspoof 5 and 10.8% on In-the-Wild data.
- **Real-world gap evidence:** an independent study found models degrade by up to 1000% EER on in-the-wild audio compared with benchmarks, and the IndicSynth authors (ACL 2025) found existing detectors perform poorly on Indian-language test sets.

## 4. Gap Analysis

| # | Gap | Evidence | How SatyaSwar fills it |
| --- | --- | --- | --- |
| G1 | Lab-to-real-world drop | Up to 1000% EER degradation on in-the-wild audio | Held-out-generator evaluation, codec and noise augmentation, own phone-recorded test clips |
| G2 | Telephony conditions hide artifacts | Narrowband, compressed audio; reliability depends on duration and quality | 8 kHz codec simulation toggle, evidence-quality measure, rolling windows |
| G3 | Indian languages and accents | Detectors underperform on Indian-language sets | XLS-R multilingual front-end, fine-tuning on IndicSynth subset and own Hindi/Kannada recordings, per-language reporting |
| G4 | A score without a decision | Existing tools rarely act on the result | Decision function plus verification gate tied to the requested action |
| G5 | Single point of failure | Replay and voice conversion bypass TTS-only detectors | Out-of-band verification works even when the detector is fooled |
| G6 | Privacy and centralisation | Streaming raw audio conflicts with data-protection needs | Audio analysed in memory and discarded; scores and metadata only; edge deployment as roadmap |
| G7 | Contact-centre focus | Products target call centres, not consumers | Mobile-first client, API and widget for other channels |
| G8 | Alerts people cannot act on | Staff and users cannot judge a bare percentage | Plain-language voice and screen alerts, an abstain state, a guided next step |

## 5. Proposed Solution: SatyaSwar

### 5.1 Principles

1. **Strict against fraud, flexible with genuine users.** Friction scales with risk and with what is being asked.
2. **High risk is not proof of fraud, and low risk is not proof of identity.** 'No synthetic indicators detected' never means 'verified'.
3. **Verification is always available**, not only when the score is high. It is required before sensitive actions.
4. **Be honest about uncertainty.** Poor audio gives 'insufficient evidence', not a forced guess.
5. **A confirmation is evidence, not a guarantee** that the responder's device is uncompromised.

### 5.2 Mapping to the PS key components

| PS component | SatyaSwar implementation (prototype) | Roadmap |
| --- | --- | --- |
| Multi-layer authenticity analysis | SSL-based anti-spoofing model on 3.5 s windows; VAD and evidence quality; optional F0 and pause statistics as supporting heuristics | Prosody branch, phase features, speaker-consistency embeddings against enrolled voiceprints |
| Real-time risk scoring engine | Rolling score, risk bands, configurable thresholds, context from claimed identity, keyword flags and requested action | Call-origin and fraud-history enrichment |
| Alerting and user interaction | On-screen risk meter, spoken alert, verification prompt, outcome screen | SMS and email channels, supervisor escalation, configurable policy workflows |
| Privacy and compliance | In-memory analysis, no stored audio or transcripts | On-device or edge inference, federated updates, DPDP Act 2023 review |
| Platform and integration APIs | REST and WebSocket API, Flutter client, dashboard | gRPC, SDKs, SIP/telecom connectors |

## 6. System Architecture

### 6.1 Components

1. **Flutter Android app (victim's phone):** auth, trusted contacts, simulated call screen, audio playback and slicing, risk meter, voice alerts, verification UI, history.
2. **FastAPI analysis server (laptop):** WebSocket audio ingest, preprocessing, detection model, ASR, contact matching, decision engine, dashboard feed.
3. **Firebase:** Authentication, Firestore (users, links, verification requests, history), optional push.
4. **Live dashboard (laptop, shown to judges):** waveform, per-window score timeline, transcript, evidence quality, codec toggle, 'why flagged' panel, latency.
5. **Responder client:** a second phone, or a laptop responder page logged in as the trusted contact.

### 6.2 End-to-end data flow

1. Operator (dashboard) or user (app) triggers a scenario; the phone rings with the claimed caller name.
2. User accepts; the app plays the clip and slices it into 3.5 s windows with a 1.75 s hop.
3. Each window streams over WebSocket as PCM16, 16 kHz, mono, with sequence number and timestamp.
4. Server runs VAD, then the detector; in parallel, Whisper transcribes the early speech and the keyword rules run.
5. Server smooths window scores, computes evidence quality and the risk band, and pushes results to both the phone and the dashboard.
6. Phone updates the meter; on a band change it lowers call audio and plays a short spoken alert.
7. User selects what is being asked (money, OTP or credentials, confidential information, other) and the claimed contact.
8. App calls the verification endpoint; the server validates the link and creates the request.
9. Responder passes re-authentication, picks the matching code and confirms or denies; the server records the result once.
10. Server computes the final outcome with the decision function; the app shows the outcome, plays the voice message and stores a scores-only history entry.

### 6.3 API design

| Endpoint | Purpose |
| --- | --- |
| WS /ws/call/{callId} | Audio frames up; scores, alerts and events down |
| WS /ws/dashboard | Live feed to the dashboard |
| POST /calls/start | Create call session and scenario |
| POST /invites, POST /invites/{code}/accept | Create and accept trusted-contact link |
| POST /verifications | Create verification request (requester token, target UID) |
| POST /verifications/{id}/respond | Responder confirms or denies, once |
| GET /history | Scores-only call history |

All REST calls carry a Firebase ID token verified server-side.

### 6.4 Firestore structure

- users/{uid}: profile, device and token info, short display code. Owner read and write only.
- users/{uid}/contacts/{otherUid}: owner's alias, label, linked-at time, snapshot of the other person's registered name.
- links/{linkId}: members, status, expiry. Readable by members only.
- invites/{code}: creator, expiry, single-use flag.
- verificationRequests/{id}: requesterUid, targetUid, claimedName, actionType, amount (optional), matchCode, status (pending, confirmed, denied, expired), createdAt, expiresAt, respondedAt. **All client writes denied; the server writes with the Admin SDK.** Reads allowed only for the two parties.
- users/{uid}/history/{id}: timestamp, scenario, band, peak score, evidence quality, claimed contact, verification result, final outcome. No audio, no transcript.

## 7. Call Simulation Design

Android does not let third-party apps capture cellular call audio, so the prototype simulates the call inside the app. It is labelled as a simulation everywhere.

### 7.1 Tiers

| Tier | What it is | Priority |
| --- | --- | --- |
| 1 | Simulated call screen (ring, accept, timer) with a bundled clip (genuine, clone, noisy) or live mic | Must build |
| 2 | Telephony-condition filter on the server: 8 kHz narrowband with phone codecs via ffmpeg, toggled from the dashboard | Must build |
| 3 | WebRTC call between two devices; the receiver analyses the incoming remote track | Stretch |

In production the tap point would be SIPREC or a telecom or VoIP integration. The analysis path is identical for any 16 kHz stream.

### 7.2 Demo flow

| Step | Where | What happens |
| --- | --- | --- |
| 0 | Both | Phone and laptop on the phone hotspot; app shows a connected indicator |
| 1 | Laptop to phone | Operator picks a scenario; phone rings with the claimed caller name |
| 2 | Phone | User accepts; clip plays through the speaker; timer runs |
| 3 | Phone to laptop | App streams 3.5 s windows (1.75 s hop) |
| 4 | Laptop | VAD, model score, evidence quality; Whisper and keyword rules; dashboard updates |
| 5 | Laptop to phone | Score, band and evidence quality sent back |
| 6 | Phone | Risk meter moves; on a band change the call audio is lowered and a short spoken alert plays; 'Verify caller' button appears |
| 7 | Phone and responder | Contact selection, verification request, responder reply, final outcome and voice message |
| 8 | Phone | Call ends; scores-only history saved |

### 7.3 Key decisions

- **Digital slicing, not re-recording.** The app slices the bundled WAV in step with playback. It is clean, deterministic and immune to venue noise. Live-mic mode is secondary, and mic capture pauses while an alert plays.
- **Window and hop:** 3.5 s window, 1.75 s hop, both configurable. The first score arrives after about 3.5 s of speech plus processing time; say this number honestly. Detectors expect about 4 s, so the server pads windows to the model's input length.
- **Alerts:** a small fixed set of pre-recorded clips (low, medium, high, insufficient evidence, denied, confirmed), with on-device text-to-speech as a fallback. Alerts fire on band changes only, with hysteresis. Each is one or two sentences and also appears on screen. Call audio is lowered while an alert plays.
- **Connection:** Android blocks cleartext ws:// by default, so enable cleartext to the laptop's local address in the demo build, open the firewall port, provide a server-address field or QR on the dashboard, and auto-reconnect. Never fake results if the link drops.
- **Wire protocol:** one bidirectional WebSocket per call. Binary frames carry PCM16 with sequence number and timestamp; JSON carries control events and scores. Timestamps give per-window end-to-end latency on the dashboard.

## 8. Detection, Scoring and Decision

### 8.1 Pipeline

1. Voice activity detection (Silero VAD) removes silence and measures usable speech.
2. Window audio (3.5 s, padded to model length) goes to the detector, which returns a spoof score.
3. Scores are smoothed over windows (exponential moving average).
4. Evidence quality combines usable speech seconds, estimated SNR and agreement across windows (and across two models, if both run).
5. Output is one of three outcomes: **likely genuine**, **suspicious / likely synthetic**, **insufficient evidence**. Risk bands are thresholds tuned on the team's own test clips and are not calibrated probabilities.

### 8.2 Context signals

Rule-based keyword detection in English and Hinglish (urgency, secrecy, money, OTP phrases) feeds the dashboard and decision function as supporting context, separate from the voice score.

### 8.3 Decision function

One pure function maps voice outcome, verification state and action type to the final outcome. It is unit tested and runs on the server; the app only renders the result.

| Voice result | Verification | Outcome |
| --- | --- | --- |
| Any | Denied | Likely impersonation. Do not proceed. |
| High risk | Confirmed | Conflicting signals. Use a second channel before any sensitive action. |
| Low or uncertain | Confirmed | Verified through the linked account. Normal caution. |
| High risk | Pending or expired | Unverified, high risk. Hold the sensitive action. |
| Any | No contact match | Cannot verify through SatyaSwar. Use another route (call back on a known number). |
| Uncertain | Not started | Insufficient evidence. Verify if the request is sensitive. |
| Low | Not started | No synthetic indicators found. This is not proof of identity; verify before transfers. |

### 8.4 'Why flagged' must be real

Show only computed items: the per-window score timeline and highest-scoring segments, usable speech duration and SNR, model agreement, keyword flags, and optional F0 and pause statistics labelled as supporting heuristics. Do not show prose such as 'unnatural pitch' unless a measurement produced it.

### 8.5 Emergency Review

When a genuine person calls from an unfamiliar phone with a stressed voice and an unreachable account, the call is marked **Unverified**, not fraudulent. There is no bypass. The sensitive action stays held, and the screen offers alternatives: call back on a known number, ask a pre-agreed safe phrase set at link time (an extra factor, not proof), or ask a mutual trusted contact to confirm through SatyaSwar.

## 9. Identity and Verification

### 9.1 Claimed identity

- faster-whisper (small or medium) transcribes the early speech, with trusted-contact names passed in the initial prompt to bias decoding.
- The transcript is matched against the user's own contact names and aliases using fuzzy matching and Devanagari-to-Latin transliteration. This is more robust than open-ended name extraction because the candidate set is small.
- The result is a ranked candidate list, always shown to the user; the claim is never treated as proof. A manual contact picker is always available and is the primary path.

### 9.2 Aliases and duplicate names

- Aliases belong to the owner (Abhishek's 'Priti' for Priyanka Sharma is stored on his side).
- Each contact has a registered-name snapshot, owner aliases, a required unique label when names collide, and normalised tokens in both scripts.
- Duplicates are all shown with their labels and masked identifiers; the best guess is highlighted, never pre-selected. The User ID, not a phone number or display name, is the identity key.
- Zero matches is a valid outcome: SatyaSwar cannot verify this person and says so.

### 9.3 Linking

Trusted contacts link through a single-use, expiring **invite code or QR**, not phone-number lookup, which avoids exposing who is registered. The invitee sees the request and accepts.

### 9.4 Verification state machine

1. The requester's app calls POST /verifications with its ID token and the target UID.
2. The server verifies the token, confirms an active link, and creates the request with Admin credentials.
3. The responder (Firebase Auth identity on the target account) receives it by real-time listener, with push as a bonus.
4. The responder passes biometric or PIN re-authentication and picks the matching 2-digit code shown on the requester's screen.
5. The server checks in a transaction that the responder UID equals the target, status is pending and the request has not expired, then sets confirmed or denied exactly once.
6. The requester's app updates in real time. Requests expire after 90 to 120 seconds; expiry means **unverified**, never safe.

The question is precise: 'Are you on a call with Abhishek right now, asking for the amount shown?' Lock-screen notifications show minimal detail; specifics appear only after unlock. Requests are rate-limited and limited to linked contacts.

**Threat model:** the responder's account and device are assumed uncompromised. Production hardening would use a signed challenge with a device-bound key.

## 10. Technology Stack

| Layer | Choice | Notes |
| --- | --- | --- |
| Phone client | Flutter (Android) | One codebase, fast iteration; local\_auth for biometrics |
| Audio on phone | just\_audio or audioplayers, record, wakelock\_plus | Playback and volume control, live-mic mode, keep screen on |
| Networking | web\_socket\_channel | Binary frames up, JSON down |
| Backend | Python, FastAPI, Uvicorn | Models loaded once at startup |
| Audio processing | ffmpeg, torchaudio, Silero VAD | Resampling, codec simulation, VAD |
| Detector | PyTorch, DeepFense framework, XLS-R 300M front-end with AASIST or SLS style head | See section 11 |
| ASR | faster-whisper (small or medium) | Contact names in the prompt |
| Matching | rapidfuzz, transliteration library | Both scripts |
| Identity and data | Firebase Auth, Firestore, firebase-admin | Email or Google sign-in for the MVP; OTP only with Firebase test numbers |
| Push (optional) | Firebase Cloud Messaging | Firestore listener is the primary path |
| Dashboard | Web page (React or plain JS) with a waveform and charts | Connected by WebSocket |
| Networking setup | Phone hotspot, laptop on it | Firebase needs internet |
| Voice alerts | Bundled pre-recorded clips, flutter\_tts fallback | Check the installed voice on the demo phone |

Verify current package versions before pinning them, and confirm licences for models and datasets.

## 11. Model and Fine-Tuning Plan

### 11.1 Choice

XLS-R 300M front-end (multilingual, suited to Indian speech) with an AASIST or SLS style classifier head, built with DeepFense (YAML-configured training, Hugging Face front-ends, pretrained checkpoints). This avoids installing fairseq. If the laptop has no GPU, use a smaller WavLM-base or wav2vec2-base detector for speed, accepting weaker generalisation

### 11.2 Steps

1. **Baseline test (hours 0 to 2):** score the team's own clips with two off-the-shelf detectors: a DeepFense pretrained checkpoint and the XLS-R-SLS v1 checkpoint. This is the go/no-go gate.
2. **Fine-tune only if the baseline fails on the team's clips.** Train the head and last layers (or LoRA), not the whole network.
3. **Data:** a small subset of IndicSynth (about 4,000 hours of synthetic speech from 989 speakers across 12 Indian languages, including Hindi, Kannada, Tamil and Telugu), genuine speech from IndicSuperb (the bona fide source, CC0 per the authors), optional ASVspoof or MLAAD subsets, and the team's own phone-recorded genuine clips and consented clones.
4. **Augmentation:** 8 kHz codec chains (G.711 and AMR style via ffmpeg), background noise, and speaker-to-mic re-recording.
5. **Compute:** a free Colab or Kaggle GPU on a small subset, time-boxed to 2 to 3 hours, run by the ML owner in parallel with other work.
6. **Evaluate before and after** on a held-out set: own phone clips, Hindi and Kannada versus English, clean versus codec audio. Report EER and the confusion matrix.
7. **Fallback:** keep the baseline checkpoint. If fine-tuning overfits or does not beat the baseline on held-out data, do not use it.

Cloning of any teammate's voice requires their consent. Check dataset and tool licences (some synthesis tools are non-commercial).

### 11.3 Honest framing

Results are reported as 'on our small test set', never as general accuracy. The README of one candidate checkpoint itself warns about cross-domain overfitting, which is a reason the verification layer exists.

## 12. Real versus Simulated

| Real in the prototype | Simulated in the prototype |
| --- | --- |
| Voice analysis on actual audio windows | The phone call itself |
| Model inference, scoring and decision logic on the server | Cellular call audio capture |
| Firebase accounts, invite-code linking and contact matching | Caller number (supplied by the scenario) |
| Verification round trip between two accounts, with re-authentication and expiry | Some ASR lines (scripted for reliability) |
| Dashboard metrics: latency, per-window scores, evidence quality | Scenario audio clips (pre-recorded or consented clones) |
| Scores-only history, no stored audio or transcripts | Telecom or VoIP tap point (roadmap) |

## 13. Privacy, Security and Compliance

- Audio is analysed in memory and discarded. Only scores and metadata are stored.
- **No transcripts are stored.** They appear live on the dashboard only. Do not claim 'only scores are kept' if anything else is retained.
- Invite-code linking avoids number discovery, and Firestore rules restrict reads to the parties involved.
- Tokens are verified server-side on every call; verification state is server-owned.
- Voice samples of real people are used only with their consent.
- Alignment with India's DPDP Act 2023 (consent, minimisation, retention limits) needs a compliance review before any real deployment.
- Out of scope: compromised responder devices, SIM-swap defence, video deepfakes.

## 14. Test Plan

### 14.1 Unit tests

- Decision function: every row of the decision table, plus action-type variations.
- Contact matching: exact, nickname, Devanagari, duplicate names, zero matches.
- Verification state machine: wrong UID, double response, expiry, replay, unlinked users.
- Windowing: correct length, hop, padding and sequence numbers.

### 14.2 Model evaluation

| Test set | Purpose | Report |
| --- | --- | --- |
| Own genuine phone recordings | Domain realism | Score distribution, false-alarm rate |
| Own consented clones (2+ generators) | Core detection | Detection rate, EER |
| Held-out generator | Generalisation | EER versus seen generators |
| Hindi, Kannada, English | Language gap | Per-language EER |
| Clean versus 8 kHz codec | Telephony gap | Delta in EER |
| Phone speaker to mic | Channel realism | Delta in EER |
| Very short and noisy clips | Abstain behaviour | Share correctly marked insufficient evidence |

Report all of this before and after fine-tuning. Include one honest slide on where the system fails.

### 14.3 Integration and end-to-end

- Full path: ring, accept, stream, score, alert, contact selection, verification, outcome, history.
- Scenario matrix: genuine plus confirmed, clone plus denied, clone plus confirmed, clone plus expired, no contact match, insufficient evidence, emergency review.
- Latency: time-to-first-score and per-window latency measured on the demo laptop with GPU and CPU.

### 14.4 Failure and resilience tests

- Hotspot drop and reconnect; wrong server address; blocked cleartext traffic.
- ASR miss (manual picker works); ASR wrong name (user catches it).
- Alert and call audio overlap; alert played while mic is live.
- Responder offline; request expiry; double tap on confirm.
- Model server restart mid-call.

### 14.5 Acceptance criteria for the demo

1. The core path works end to end three times in a row on the demo phone.
2. A genuine clip and a clone clip are visibly separated on the dashboard.
3. The verification round trip completes in under 10 seconds on the hotspot.
4. Every claim on the slides is backed by a test result or labelled as roadmap.
5. A release APK and a pre-recorded backup video exist.

## 15. Risks and Mitigations

| Risk | Mitigation |
| --- | --- |
| Pretrained detector fails on phone-mic audio | Hour-2 go/no-go, fine-tune on own clips, report limits honestly, rely on verification layer |
| CPU inference too slow | GPU laptop, or smaller model fallback |
| Hotspot instability | Auto-reconnect, local address field, rehearsal on the real network |
| ASR misreads Hinglish names | Contact-name prompt biasing, manual picker, scripted demo lines |
| First-time Flutter and Firebase setup delays | Hello-world on the demo phone in hour 1, release APK backup |
| FCM unreliable | Firestore listener as primary path |
| Overclaiming accuracy | Small-test-set framing, vendor figures labelled as vendor claims |

## 16. Team Split and 24-Hour Plan

| Owner | Responsibilities |
| --- | --- |
| A: Mobile | Flutter app: call screens, audio playback and slicing, risk meter, alerts, verification UI, dashboard layout |
| B: Backend and Firebase | Auth, invite linking, verification state machine, Firestore rules, WebSocket server, decision function |
| C: ML and demo audio | Model baseline and fine-tuning, VAD, windowing, Whisper, evaluation, scenario clips and alert recordings |

| Hours | Work | Gate |
| --- | --- | --- |
| 0 to 2 | Contracts, Firebase project, Flutter hello-world on demo phone, **model go/no-go** | Model decision |
| 2 to 6 | App records or plays, uploads windows, shows score; dashboard receives feed | First end-to-end result |
| 6 to 10 | Auth, invite linking, contact matching, action selector |  |
| 10 to 14 | Verification state machine, responder flow, re-authentication | Full verification round trip |
| 14 to 17 | Decision function, outcome screen, voice alerts, history | **Core demo path works** |
| 17 to 19 | Whisper assist, codec toggle, polish |  |
| 19 to 21 | Optional: push, emergency review, WebRTC tier |  |
| 21 to 24 | Freeze features, test plan run, rehearsal, backups |  |

**Cut list if behind:** real OTP, outgoing-call polish, history charts, WebRTC tier, push, live-mic mode, in that order.

## 17. Assumptions and Open Items

These defaults apply until the team changes them:

1. The demo laptop has a GPU; the smaller model is the fallback.
2. The verification responder is a laptop page (switch to a second phone if available).
3. Voice alerts are English first, Hindi if time allows.
4. Sign-in uses email or Google; OTP is shown only with Firebase test numbers.
5. Dataset subset sizes and licences are confirmed from the IndicSynth repository before download.

## 18. Pitch Notes and Likely Questions

- **What is new?** A decision and verification layer, not just a detector: it works even when detection fails.
- **What about new generators?** Held-out evaluation, continual retraining, and out-of-band verification as the backstop.
- **False positives?** Calibrated bands, an abstain state, and a human-in-the-loop verification step before any hard block.
- **How real-time is it?** First score after about 3.5 s of speech plus processing, then a new score every 1.75 s; measured latency on the dashboard.
- **Privacy?** In-memory analysis; no audio or transcripts stored; edge inference is the production path.
- **Is the call real?** No. It is a labelled simulation; the tap point in production is a telecom or VoIP integration.
- **Business model?** Per-call API pricing for banks and contact centres, with an operator integration tier.
