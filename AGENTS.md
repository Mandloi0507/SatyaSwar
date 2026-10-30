# AGENTS.md — SatyaSwar ML Implementation Guardrails

This file contains mandatory project rules for any AI coding agent working in this repository. Read it before taking action. The user has confirmed that the environment setup is complete; the current phase is implementation and testing.

## Authority and scope

- `Implementation.md` is the source of truth for ML implementation and integration contracts.
- `SatyaSwar Complete Solution Document.md` is the source of truth for product behaviour, privacy promises, architecture, and system acceptance.
- `PS.txt` contains the problem statement.
- Inspect the actual repository and preserve existing working code and teammate changes.
- Your ownership is the ML subsystem under `ml/`, its adapters/contracts/tests/evaluation and the hand-over to the frontend/backend members. Do not take over their components.

## Mandatory workflow

1. Inspect the repository tree, `git status`, diffs, configuration and existing tests before editing.
2. Read the source documents completely; do not rely on summaries or assumptions.
3. Do not reinstall or rebuild the environment just because implementation is starting. Verify the existing environment and only change dependencies in response to a specific evidenced issue.
4. Create a short plan with milestones and tests. Then execute it in small increments; do not stop at planning.
5. Run focused tests after each change, contract tests after interface changes, and the full test suite before declaring completion.
6. Keep a factual changelog of files changed, commands actually run, results, and blockers.

## Anti-hallucination rules

- Never invent files, paths, function signatures, schemas, endpoints, model names, dependency versions, dataset contents, test results, performance numbers, or command output.
- Inspect the actual implementation and installed library/API version before relying on it.
- If a fact cannot be verified, label it `UNKNOWN`, `NOT VERIFIED`, or `NOT MEASURED`.
- Do not claim tests passed unless they were executed and their output observed.
- Do not generate fake checkpoints, fake evaluation tables, fake fixture outputs, or fake “successful” inference results.
- If documents conflict, quote the relevant section names, explain the conflict, and ask for a decision. Do not silently choose one.
- If a required model/dataset is inaccessible or incompatible, report the actual blocker and use only a documented fallback.
- Never hide, delete, or weaken a failing test to obtain a green result.

## Preserve the working environment

- Environment setup is already complete.
- Do not create a new virtual environment, reinstall the complete stack, upgrade packages, or pin new versions without a specific demonstrated need.
- Do not run destructive cleanup or reset commands.
- Do not overwrite uncommitted changes or work belonging to other team members.
- Never expose `.env`, tokens, keys, credentials, private recordings, or personal data in logs or commits.
- Keep secrets out of `.env.example`; keep environment files, raw data and model artefacts out of version control as specified.

## Integration contract: no unilateral changes

- Follow `Implementation.md`, Section 6, exactly for audio framing, sample format, headers, timestamps, sequence numbers, session lifecycle, event names, payload fields, endpoints, error handling, mock flags and schema version.
- Keep the Python engine as the single source of core analysis logic; REST/WebSocket adapters must not implement competing scoring logic.
- Do not change schemas or enums casually. A necessary change requires a documented reason, compatibility impact, coordinated updates to schemas/fixtures/docs, a schema-version change where required, and team approval.
- Keep the frontend/backend teammates unblocked with deterministic fixtures, mock mode, contract docs and a concise hand-over.
- Mock output must be explicitly marked `mock=true` and must never be presented as a real model result.
- Do not alter backend-owned authentication, Firebase, contact-linking persistence, or verification-state-machine behaviour.

## Model and evidence integrity

- This system provides risk signals, not definitive proof of identity or fraud.
- A low risk score does not verify identity; a high risk score does not prove fraud.
- Use `insufficient_evidence` for short, silent, noisy or poor-quality input where evidence is inadequate.
- Risk thresholds are placeholders until calibrated against the team’s own held-out evaluation data.
- Do not call scores calibrated probabilities without calibration evidence.
- “Why flagged” explanations must correspond to computed measurements/events. No fabricated natural-language explanations.
- ASR and contact-name matches are suggestions, never identity proof.
- Benchmark claims and local results must be clearly distinguished.
- Fine-tuning must follow a measured baseline comparison and must be justified by time, data, compute and licensing.
- Verify dataset/model terms and access requirements before depending on them.

## Privacy and safe handling

- Process audio in memory and discard it after analysis, consistent with the source documents.
- Do not persist raw audio or transcripts. Store only documented score/metadata fields.
- Use consented genuine recordings and consented synthetic/clone samples.
- Handle malformed audio, empty input, invalid sample rates, model exceptions, disconnected clients and backpressure without crashing the service.
- Do not claim production readiness, telecom integration, or legal compliance certification that has not been implemented and verified.

## Testing requirements

Use the exact test locations and commands documented by the repository and `Implementation.md`. Cover, as applicable:

- Unit tests for audio conversion/windowing, VAD/evidence, smoothing/hysteresis, outcomes and decision rules.
- Boundary cases: empty, short, silent, noisy, malformed and low-evidence audio.
- English and Hindi processing separately.
- Contact matching for exact names, aliases, duplicate/ambiguous names, Devanagari transliteration and zero matches.
- All decision-function rows and action types.
- Contract/schema tests for all event types, headers, sequence/timestamp behaviour and session lifecycle.
- Mock mode without GPU and without model downloads.
- Real model path only when the model is actually available; report environmental/access blockers honestly.
- Codec simulation only for codecs verified as available.
- WebSocket errors, disconnect/reconnect, backpressure and server restart where feasible.
- End-to-end scenarios from the solution document, subject to availability of the other team components.
- Actual latency and evaluation measurements, stored in the paths specified by the implementation plan.

Do not mark unrun tests as passed. Report skipped tests and why they were skipped.

## Special mid-challenge addition — clarification required

The user has stated that a further challenge requirement exists, that it must be handled during testing, and that its output is a priority. However, the exact feature/behaviour is not specified in the current instructions.

- Do not guess or invent this feature.
- Keep the implementation modular and add a visible TODO in the implementation notes/test plan: `ADDITIONAL_CHALLENGE_REQUIREMENT — awaiting exact specification`.
- Ask the user for the exact expected behaviour, input, output, acceptance condition and constraints before implementing it.
- Once clarified, write explicit acceptance tests first, implement the smallest appropriate change, and test/report the output independently.
- Do not declare the whole project complete while the requirement remains unspecified or its required output remains untested. Core work can proceed, with this item clearly marked blocked.

## Required reporting format after each milestone

- **Milestone:** name/number
- **Implemented:** factual summary
- **Files changed:** exact paths
- **Commands run:** exact commands
- **Tests:** pass/fail/skipped, with actual results
- **Integration impact:** any contract changes or `None`
- **Blockers/risks:** evidence-based
- **Next milestone:** specific next step

## Definition of done

Do not report the ML side as integration-ready until the applicable checklist in `Implementation.md` Appendix E and Section 15.5 is verified. At minimum:
- Package installation/run instructions are accurate.
- Mock stream simulation works without GPU and marks all output as mock.
- Standalone service health endpoint responds successfully.
- Contract docs, schemas, OpenAPI output and fixtures match the implementation.
- Real-model status is explicit and no mock result is misrepresented.
- Test and evaluation results are generated from actual runs.
- Known limitations and failures are documented.
- The special mid-challenge addition has either been clarified, implemented and tested, or is explicitly marked blocked pending user input.
