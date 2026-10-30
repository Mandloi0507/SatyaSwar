# SatyaSwar Security Review & Audit Checklist
**Standard:** OWASP API Security Top 10 + Zero Trust Voice Security Architecture  
**Author:** Member 2 (Backend, Infrastructure, Database & Security)  
**Status:** AUDITED & VERIFIED

---

## 1. Authentication & Authorization Controls

- [x] **Firebase ID Token Verification:** All REST endpoints (except public `/health` and root `/`) enforce cryptographic signature verification via Firebase Admin SDK with `check_revoked=True`.
- [x] **Dual-Strategy WebSocket Authentication:** Supports standard HTTP `Authorization: Bearer <token>` handshake header with fallback to first-message JSON authentication within a strict 5.0-second timeout window. Tokens are never exposed in URL query parameters.
- [x] **Strict Object-Level Authorization (BOLA/IDOR Prevention):** Every database operation validates that the requesting user's UID owns the target resource (sessions, contacts, verifications).
- [x] **Anti-Enumeration Protection:** Access attempts to foreign or non-existent sessions/verifications consistently return `HTTP 404 Not Found` rather than `403 Forbidden` to prevent resource discovery.
- [x] **Client-Side Firestore Lockdown:** Native `firestore.rules` are set to `allow read, write: if false;`, eliminating mobile client-side tampering.

---

## 2. Audio Processing & Privacy-by-Design

- [x] **Zero Audio Retention Guarantee:** Audio window frames are ingested into memory, decoded, forwarded to the ML service via private in-transit HTTP, and discarded immediately. No raw PCM, WAV files, or transcripts are ever written to disk or database.
- [x] **Logging Sanitization:** All logging statements exclude raw audio bytes, speech transcripts, authorization tokens, invite codes, and match codes. Only session IDs, UIDs, and error types are logged.
- [x] **Automated Data Lifecycle Retention (TTL):** Call summaries in `call_history` carry an `expires_at` timestamp enforcing a strict 30-day retention window.

---

## 3. WebSocket Streaming & Backpressure Hardening

- [x] **Bounded Worker Queues:** Audio frame queues are bounded (`maxsize=4`). If downstream ML inference slows down, stale audio frames are discarded to prevent out-of-memory (OOM) crashes.
- [x] **Strict Sequence Monotonicity:** Frame sequence numbers must strictly increment (`seq > last_seq`). Duplicate or out-of-order frames are rejected cleanly with application error events.
- [x] **Inactivity Watchdog:** Connections exceeding 30.0 seconds of silence without audio or ping/pong are closed with custom close code `4408`.

---

## 4. Cryptographic Integrity & Anti-Tampering

- [x] **Single-Use Contact Invite Codes:** Generated with cryptographically secure randomness (`secrets.token_hex`) and stored strictly as SHA-256 hashes. Codes are single-use with a 48-hour expiration.
- [x] **Out-of-Band Match Codes:** Generated as 2-digit challenges and verified using HMAC-SHA256 with application secret key. Plaintext codes are never stored in the database.
- [x] **Attempt Rate-Limiting:** Verification match codes allow at most 3 failed attempts before automatically transitioning the request to `DENIED`.

---

## 5. Decision & Risk Engine Calibration

- [x] **Calibrated Risk Terminology:** The decision engine avoids absolute claims such as "guaranteed real voice", using calibrated phrasing ("lower spoof risk", "likely impersonation").
- [x] **Zero-Trust Verification Coupling:** High voice risk is never automatically cleared by contact verification; instead, conflicting signals trigger a hold on financial/credential actions.
- [x] **Fail-Safe Default:** When ML services fail or time out, the system emits `analysis_unavailable`, never defaulting to a safe score.
