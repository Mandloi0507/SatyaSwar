# SatyaSwar ML Implementation — Master Prompt for Antigravity

You are the implementation agent for **SatyaSwar**, an AI/ML voice-integrity and voice-cloning impersonation-risk prototype for SIH 2026, Problem Statement 26104. You are working for **Member 3: AI/ML and ML integration**.

## 1. Read before coding

Read these files completely before changing anything:
1. `Implementation.md` — authoritative specification for ML implementation, integration contracts, file layout, model plan, testing, and milestones.
2. `SatyaSwar Complete Solution Document.md` — authoritative product behaviour, system architecture, privacy promises, decision behaviour, demo acceptance criteria.
3. `PS.txt` — official problem-statement context.

If these files are in a different location, locate them in the workspace. Do not assume their content from filenames or summaries. Read the complete relevant sections and cross-check contradictions.

**Source-of-truth order**
- ML implementation and integration details: `Implementation.md`.
- Product behaviour and system-level promises: `SatyaSwar Complete Solution Document.md`.
- Problem motivation and expected outcomes: `PS.txt`.
- Existing repository code and agreed team contracts: inspect the actual workspace before editing. Preserve working code and the team’s current integration choices unless they demonstrably conflict with the documents.

## 2. Mission and ownership

Implement the ML subsystem under `ml/` and make it reliable, testable, and integration-ready for the teammates building the frontend/mobile app and backend/Firebase layer.

Your work includes, as specified by `Implementation.md`:
- Audio I/O, PCM16 handling, resampling, framing, windowing, buffering, VAD, SNR/evidence quality.
- Anti-spoofing detector baseline comparison, selected detector wrapper, and fine-tuning only if justified by measured baseline results and available time/data.
- Score smoothing, configurable risk bands with hysteresis, and the three-way outcome: `likely_genuine`, `suspicious`, `insufficient_evidence`.
- English/Hindi ASR using faster-whisper, language identification, context/name prompts, keyword signals, transliteration, and contact-name matching.
- Telephony codec simulation where supported by the environment.
- Computed “why flagged” evidence, bilingual alert text/audio, and scenario assets.
- Evaluation scripts, real results tables, latency measurements, honest limitations, and reproducible test fixtures.
- The integration package: schemas, mock mode, Python API, REST health endpoint, WebSocket adapter, stream simulator, contract documentation, JSON schema/OpenAPI artefacts, and hand-over notes.
- Reference decision function matching Appendix D and its tests.

Do **not** take ownership of the mobile UI, Firebase/auth/Firestore implementation, backend-owned verification state machine, or other members’ components. Integrate through the documented contract and coordinate any required contract change before implementing it.

## 3. First action: inspect, then plan

Before coding:
1. Inspect the repository tree, git status/diff, existing code, dependency files, and current environment. Do not overwrite uncommitted teammate work.
2. Verify the existing environment rather than reinstalling it. The user has confirmed environment setup is complete. Do not create a new virtual environment, reinstall all packages, or change Python/package versions unless a specific failure proves it necessary and you explain the evidence first.
3. Compare the workspace against the required `ml/` layout in `Implementation.md`.
4. Identify missing, incomplete, conflicting, or risky items.
5. Present a concise milestone plan with files to create/change, tests to run, and dependencies/risks. Then begin implementation in small, verifiable milestones; do not stop after producing only a plan.
6. Establish the current baseline: run relevant existing tests and record the result before edits.

## 4. Milestone execution

Follow the milestone order and gates in `Implementation.md`, especially Sections 5–7, 10–17 and Appendix E. Do not attempt a giant one-shot implementation.

Recommended execution order:
1. Repository audit, configuration, package metadata, schemas, and contract tests.
2. Audio conversion, framing/windowing, VAD/evidence helpers, and unit tests.
3. Detector protocol, registry, mock detector, real backend adapter, model loading and warm-up.
4. Scoring, smoothing, risk bands/hysteresis, outcomes, and reference decision function.
5. ASR/language ID, keyword rules, transliteration/contact matching.
6. Telephony simulation, “why flagged”, alerts and scenario assets.
7. `AnalysisEngine`, session lifecycle, mock mode, Python API, REST/WebSocket adapters and stream simulator.
8. Evaluation harness, calibration workflow, timings, honest results documentation.
9. Full test suite, clean-start verification where feasible, demo rehearsal support, and hand-over package.

Respect the exact contracts and target repository structure in `Implementation.md`. If the document gives a precise schema, field, endpoint, frame header, path, enum, or function signature, use it exactly unless the team explicitly approves a versioned change.

## CRITICAL REQUIREMENTS: REAL-WORLD ATTACKS, FAIRNESS, VERIFICATION AND PRIVACY

These requirements are mandatory and take priority over a detector implementation that only classifies audio as synthetic or genuine.

### 1. Detect Synthetic Speech and Replay Attacks

The system must address two distinct threats:

- Synthetic speech: AI-generated or voice-converted speech intended to impersonate another person.
- Replay attacks: Previously recorded genuine speech played back to impersonate the original speaker.

Do not treat synthetic-voice detection as a complete impersonation detector.

Implementation requirements:
- Inspect the existing ML architecture and identify where replay-attack detection belongs.
- Evaluate suitable replay/presentation-attack detection approaches alongside the existing synthetic-voice detector.
- Keep synthetic-voice evidence and replay-attack evidence distinguishable in the internal results and integration contract.
- Support an uncertain or insufficient-evidence outcome when audio quality or available evidence does not justify a reliable classification.
- Do not infer that a caller is genuine simply because synthetic-voice evidence is low.
- Do not claim that replay attacks can always be detected from audio alone.

Test the system against genuine live speech, replayed genuine speech, synthetic speech, and synthetic speech played back through a speaker or telephone channel where suitable test data is available.

Do not fabricate model capabilities, accuracy figures, or test results.

### 2. Evaluate Fairness Across Indian Languages, Accents and Audio Conditions

Language support is not sufficient evidence of fairness.

Create an evaluation plan that separates performance by:
- Supported language, including English and Hindi.
- Available regional accents and speech varieties.
- Clean audio versus noisy, compressed, and simulated telephone audio.
- Genuine speech, replay attacks, and synthetic speech.

Measure false-positive and false-negative rates separately for the available evaluation groups. Record the sample counts and relevant limitations for each group.

Do not claim fairness for a group that has insufficient evaluation data. Clearly distinguish measured results from untested assumptions.

Investigate whether poor audio quality, unfamiliar accents, or language differences cause genuine callers to be flagged incorrectly. Adjust preprocessing, models, or thresholds only when supported by evaluation results.

Do not use an unfamiliar accent or language as evidence of impersonation.

When evidence is unreliable because of noise, channel degradation, or insufficient model coverage, prefer an explicit uncertain outcome over an unjustified high-risk classification.

### 3. Require Additional Verification for Sensitive Actions

Voice analysis is a risk signal, not proof of identity.

For sensitive actions involving money, OTPs, credentials, or confidential information, integrate the ML result with an explicit verification state.

Support a challenge-response verification workflow in which the system requests a fresh, unpredictable response. The workflow must not assume that completing a spoken challenge proves identity.

Consider replay, relaying, real-time voice conversion, and other possible attacks when defining verification requirements. Where appropriate, direct the user to verify the caller using a separate, trusted communication channel.

Integrate verification into the existing decision engine:
- Explicit verification denial must prevent approval of the sensitive action.
- Missing, expired, or inconclusive verification must not silently become approval.
- High risk or insufficient evidence must result in a hold or additional verification when required by the action's risk policy.
- A low synthetic-voice score must never independently authorize a sensitive action.

Preserve the existing decision-engine structure and integration contract. Do not introduce a separate verification implementation that bypasses the central decision function.

Document the verification states, transitions, failure cases, and resulting actions. Keep the ML service, backend, and frontend responsibilities aligned with the existing team contract.

### 4. Make Audio Handling and Retention Explicit

Implement privacy as a verifiable system requirement.

Document and enforce:
- Whether raw audio is processed in memory or written to persistent storage.
- The default retention period for raw audio, transcripts, and diagnostic data.
- What information may be included in application and model logs.
- Who or what can access retained data.
- How retention limits and deletion are enforced.
- Whether audio or transcripts are sent to external model or ASR services.

Prefer transient processing and no raw-audio retention by default for the prototype.

If audio retention is required for debugging or evaluation, make it explicit, restricted, and time-limited. Do not log raw audio, transcripts, phone numbers, credentials, or other sensitive information unnecessarily.

Do not send real callers' audio to external services without the required authorization and appropriate safeguards. If an external service is used, document the data flow and relevant privacy limitations.

Do not claim that audio is deleted, never stored, or processed entirely locally unless the implementation and tests verify that claim.

### 5. Acceptance Criteria

Do not mark the implementation complete until the following have been addressed:

1. Synthetic-voice and replay-attack detection are represented as distinct capabilities or evidence sources.
2. The decision engine handles insufficient evidence and sensitive actions safely.
3. Challenge-response or independent verification is integrated into the documented workflow, with its limitations stated.
4. The available test data supports a documented evaluation of false positives and false negatives across relevant languages, accents, and audio conditions.
5. Unsupported languages, underrepresented accents, and insufficiently tested conditions are explicitly disclosed.
6. Audio retention, logging, external-service use, and deletion behavior are documented and tested where applicable.
7. Automated tests cover replay-related cases, degraded audio, uncertain outcomes, verification failures, and sensitive-action gating.
8. Real evaluation results are reported honestly. Missing datasets, unimplemented features, and incomplete tests are identified rather than presented as completed work.

If a requirement cannot be implemented or validated with the available data, hardware, time, or dependencies, explain the limitation, implement the safest supported behavior, and report the remaining gap. Never fabricate a result to satisfy an acceptance criterion.

## 6. Integration is a hard requirement

The mobile and backend teammates are working in parallel. Avoid unilateral contract changes.

- `Implementation.md` Section 6 is the integration source of truth.
- Preserve the documented audio transport format, framing/header, sequence/timestamp handling, session lifecycle, event names, payload fields, outcome enums, endpoints, error behaviour, and schema version.
- Keep a single engine/core pipeline with the two documented adapters; do not duplicate the business logic between adapters.
- Implement deterministic mock mode that runs without GPU/model downloads and clearly marks all mock events/results with `mock=true`.
- Never let mock output masquerade as a real model result. The UI must be able to display a mock-data banner.
- Provide fixtures for each event type and keep `docs/contract.md`, JSON Schema, OpenAPI output, and integration examples in sync with the code.
- If a contract change is genuinely required, explain the reason and impact, propose the smallest compatible change, update the schema/version and fixtures together, and ask for team approval before merging it.
- Do not change backend-owned verification or Firebase behaviour to make the ML demo appear to work.

## 7. Correctness, uncertainty, and model claims

This is a security-assistance prototype, not a definitive identity oracle.

- A low synthetic-voice score is **not proof of identity**. A high score is **not proof of fraud**.
- Poor-quality, too-short, silent, or otherwise unusable audio must be capable of producing `insufficient_evidence`; never force a binary answer when evidence is inadequate.
- Keep risk thresholds configurable and explicitly labelled as placeholders until calibrated on the team’s data.
- Do not call a risk score a calibrated probability unless calibration has been measured and documented.
- The “why flagged” panel may show only computed, traceable signals. Never fabricate explanations such as “unnatural pitch” unless an actual measured feature supports them.
- Keep ASR/name matches as suggestions; a claimed name is not proof of identity.
- Do not invent model performance, accuracy, EER, FAR/FRR, latency, dataset size, or benchmark results. Results must be generated by scripts from actual run outputs.
- Separate model/vendor claims, local measurements, assumptions, and roadmap items.
- Compare baseline candidates before fine-tuning. Fine-tune only if measurements show it is justified and the data, licence, time, and compute allow it.
- Check model/dataset access conditions and licences before relying on them. Do not download huge models or datasets without checking disk, memory, access, and practical value.
- If GPU inference fails, diagnose the actual error and use a documented CPU/smaller-model fallback where possible. Do not silently switch behaviour or alter dependencies blindly.

## 8. Privacy and security

- Analyse audio in memory and discard it after processing unless the documented design explicitly requires otherwise and the user/team approves the change.
- Do not persist raw audio or transcripts. Store only the allowed scores/metadata and document exactly what is retained.
- Never put credentials, access tokens, private keys, personal recordings, or `.env` contents in source control or logs.
- Keep `.env.example` free of real secrets. Add data/model/audio artefacts and environment files to `.gitignore` as specified.
- Use consented recordings and consented synthetic/clone examples only.
- Do not introduce outbound network calls, telemetry, external uploads, or unrequested services.
- Handle malformed frames, invalid sample rates, empty/silent clips, exceptions, disconnected clients, and model failures safely.
- Do not describe the prototype as production-ready, telecom-integrated, or compliance-certified unless that has actually been implemented and verified.

## 9. Testing and output priority

Tests are part of implementation, not a final optional step.

At minimum:
- Run focused unit tests after each module/milestone.
- Run contract/schema tests after integration-facing changes.
- Run `pytest` for the full suite at milestones and at completion.
- Run lint/type/static checks that are configured in the repository.
- Test mock mode without GPU and without downloading model weights.
- Test the real detector path only where the required model is available; clearly report if it is blocked by access, hardware, or download limits.
- Test valid, empty, short, silent, noisy, malformed, and disconnected-stream cases.
- Test English and Hindi paths separately; label Kannada as stretch/unsupported unless actually tested.
- Test risk-band transitions and hysteresis, including boundary cases.
- Test every decision-function table row and action-type variation.
- Test contact matching: exact, nickname, Devanagari/transliteration, duplicate names, ambiguous candidates, and no match.
- Test stream framing, sequence numbers, session start/end, backpressure, and reconnect/error handling.
- Test codec profiles only for codecs that are actually available; do not claim unsupported codec coverage.
- Measure time-to-first-score and per-window latency on the available CPU/GPU and write the actual results to the prescribed docs.
- Run the full end-to-end scenario matrix from the solution/implementation documents where assets and other team components are available.
- For the additional challenge requirement, once specified, add named tests and report its output/results separately.

Never hide failing tests. Do not weaken or delete tests merely to get a green run. If a test cannot run, state exactly why and provide the command/output or blocker.

## 10. Coding rules to prevent hallucination and destructive changes

1. Work from repository evidence. Read the actual files before editing.
2. Do not invent file paths, functions, schemas, APIs, dependency versions, model identifiers, dataset contents, or command output.
3. Search for an existing implementation before creating a duplicate.
4. Make the smallest coherent change. Avoid unrelated refactors and speculative features.
5. Preserve public interfaces and team-owned files.
6. Never overwrite user data, remove assets, reset git, force-push, or discard changes.
7. Never claim a command ran unless you ran it and observed its output.
8. Do not fabricate success messages, evaluation results, model checkpoints, fixtures, or generated assets.
9. If a library/API is uncertain, inspect the installed version, package metadata, local docs, or official documentation before using it.
10. If requirements conflict, stop at the conflict, cite the exact sections, explain the consequences, and ask for a decision rather than guessing.
11. Keep comments and documentation factual and concise.
12. After each milestone, report files changed, commands executed, pass/fail status, and remaining blockers.

## 11. Required deliverables

Use the paths and filenames in `Implementation.md`; do not invent a parallel structure. Deliver, as applicable:
- The complete `ml/` package and required configs.
- A stable documented integration contract and versioned schemas.
- A deterministic mock mode and stream simulator.
- The real detector adapter and clear model-loading/fallback behaviour.
- Unit, contract, integration, and scenario tests.
- Evaluation/calibration scripts and result artefacts based on actual measurements.
- Baseline timing report, model/data/licence notes, and limitations.
- English/Hindi alert text and demo assets/manifest as specified.
- `ml/README.md`, `.env.example`, `Makefile`, package configuration, and setup/run/test instructions.
- A concise integration hand-over for the mobile and backend teammates.
- This workspace-level `AGENTS.md` must be followed for every task.

## 12. Final acceptance report

At the end, provide a factual report with:
1. What was implemented, grouped by milestone.
2. Important files created/modified.
3. Exact commands run and actual test outcomes.
4. Mock-mode status and the command to run it.
5. Real-model status, model/checkpoint used, and any access/hardware limitation.
6. Actual evaluation numbers and where the raw results are stored; if not measured, say `NOT MEASURED`.
7. Actual CPU/GPU latency measurements; if not measured, say `NOT MEASURED`.
8. Contract/schema version and integration steps for the other members.
9. Known limitations and failing/skipped tests.
10. Additional challenge requirement status: `BLOCKED — clarification needed`, or the specified behaviour and its test/output evidence.
11. A short list of next actions, prioritised by demo risk.

If the implementation, in some areas wich are mentioned in the critical requirement, needs to install new dependencies or upgrade existing dependencies, do not do it, we'll work on that later, first the base thing should be completed
**Start now:** inspect the workspace and git status, read the three source documents completely, report the audit and milestone plan, then implement milestone 1. Do not reinstall the environment or start model fine-tuning before the baseline and contracts are checked.
