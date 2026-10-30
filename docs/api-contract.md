# SatyaSwar API Integration Contract
**Version:** 0.1.0  
**Last Updated:** 2026-10-30  
**Author:** Member 2 (Backend, Infrastructure, Database and Security)  
**Target Audience:** Member 1 (Flutter Client) & Member 3 (ML/Audio Analysis)

---

## 1. Overview & Base URLs

| Environment | Base URL | WebSocket URL |
|---|---|---|
| Local Development (Emulator / Hotspot) | `http://<laptop-ip>:8000` | `ws://<laptop-ip>:8000` |
| Cloud Run Production | `https://api.satyaswar.internal` | `wss://api.satyaswar.internal` |

All business REST endpoints are versioned under `/api/v1/`.

---

## 2. Authentication

### REST Endpoints
Every protected REST endpoint requires a valid Firebase ID token in the standard HTTP header:
```http
Authorization: Bearer <Firebase ID token>
```
- The Flutter client acquires this via `await FirebaseAuth.instance.currentUser?.getIdToken()`.
- On receiving HTTP `401 Unauthorized`, the client should call `getIdToken(true)` once to force-refresh and retry the request once before redirecting to login.

### WebSocket Endpoints
Supported via dual-strategy authentication:
1. **Primary (Preferred for Flutter):** Attach the `Authorization: Bearer <Firebase ID token>` header during the WebSocket handshake (`IOWebSocketChannel.connect(uri, headers: {'Authorization': 'Bearer $token'})`).
2. **Fallback:** If headers cannot be passed, connect and send a first JSON text frame within **5.0 seconds**:
   ```json
   {
     "type": "auth",
     "token": "<Firebase ID token>"
   }
   ```
- Tokens must **NEVER** be placed in query strings (`?token=...`) to avoid logging and exposure.
- Invalid or timed-out WebSocket authentication closes the connection with application close code **`4401`**.

---

## 3. Standard Error Envelope

All API errors return a uniform JSON error envelope:
```json
{
  "error": {
    "code": "SESSION_NOT_FOUND",
    "message": "Call session not found",
    "details": null
  }
}
```

### Documented Error Codes
| HTTP Status | Error Code | Meaning / Scenario |
|---|---|---|
| `400` | `BAD_REQUEST` | Malformed parameters, self-invite attempt, code mismatch |
| `401` | `UNAUTHORIZED` | Missing, expired, invalid, or revoked Firebase token |
| `403` | `FORBIDDEN` | Caller not authorized to perform action (e.g. non-responder attempting verification) |
| `404` | `NOT_FOUND` | Resource not found OR not owned by caller (prevents existence enumeration) |
| `409` | `CONFLICT` | State machine violation (e.g. re-answering a closed request, duplicate pairing) |
| `410` | `GONE` | Expired invite code or verification request |
| `422` | `VALIDATION_ERROR` | Schema validation failure (details array provided) |
| `429` | `TOO_MANY_REQUESTS` | Rate limit exceeded |
| `500` | `INTERNAL_SERVER_ERROR` | Unhandled server error |
| `503` | `SERVICE_UNAVAILABLE` | External service (ML / Firebase) unavailable |

---

## 4. REST Endpoints Specification

### 4.1 System & General
- `GET /` — Root health and service info (`{"project": "SatyaSwar", "message": "Backend is running"}`).
- `GET /health` — Container probe check (`{"status": "healthy"}`). No auth required.

---

### 4.2 User Profile (`/api/v1/users`)

#### `GET /api/v1/users/me`
Retrieves the authenticated user's profile. Provisions a Firestore user document on first call.
- **Headers:** `Authorization: Bearer <token>`
- **Response `200 OK`:**
  ```json
  {
    "uid": "firebase_uid_123",
    "name": "Priyanka Sharma",
    "email": "priyanka@example.com",
    "phone": "+919876543210",
    "account_status": "active",
    "created_at": "2026-10-30T10:00:00Z",
    "updated_at": "2026-10-30T10:00:00Z"
  }
  ```

#### `PATCH /api/v1/users/me`
Updates profile display name or phone number.
- **Request Body:**
  ```json
  {
    "name": "Priyanka S.",
    "phone": "+919876543210"
  }
  ```
- **Response `200 OK`:** Updated `UserProfile` object.

#### `DELETE /api/v1/users/me`
Initiates cascading account deletion.
- **Response `202 Accepted`:**
  ```json
  {
    "status": "pending_deletion",
    "message": "Account and all associated records have been marked and scheduled for deletion"
  }
  ```

---

### 4.3 Trusted Contacts (`/api/v1/contacts`)

#### `POST /api/v1/contacts/invite`
Generates a random single-use invitation code and QR payload.
- **Request Body:** `{}` or `{"invitee_email": "friend@example.com"}`
- **Response `201 Created`:**
  ```json
  {
    "code": "K7M2-9QX4",
    "expires_at": "2026-10-30T10:15:00Z",
    "qr_payload": "satyaswar:invite:K7M2-9QX4"
  }
  ```

#### `GET /api/v1/contacts`
Lists all accepted trusted contacts for the caller, including caller-private aliases.
- **Response `200 OK`:**
  ```json
  [
    {
      "id": "doc_xyz",
      "owner_uid": "my_uid",
      "contact_uid": "friend_uid",
      "registered_name": "Priyanka Sharma",
      "alias": "Priti",
      "label": "college",
      "status": "accepted",
      "created_at": "2026-10-30T10:05:00Z"
    }
  ]
  ```

#### `POST /api/v1/contacts/accept`
Accepts an invitation code and creates reciprocal contact links.
- **Request Body:**
  ```json
  {
    "code": "K7M2-9QX4",
    "alias": "Priti",
    "label": "college"
  }
  ```
- **Response `200 OK`:** Created `TrustedContact` record for caller.

#### `PATCH /api/v1/contacts/{contact_uid}`
Updates caller's personal alias and disambiguation label.
- **Request Body:**
  ```json
  {
    "alias": "Priti Sister",
    "label": "family"
  }
  ```
- **Response `200 OK`:** Updated `TrustedContact` record.

#### `DELETE /api/v1/contacts/{contact_uid}`
Unlinks the relationship in both directions.
- **Response `200 OK`:** `{"status": "removed", "contact_uid": "..."}`.

---

### 4.4 Call Sessions (`/api/v1/calls`)

#### `POST /api/v1/calls` (or `POST /api/v1/calls/start`)
Initializes a new call session.
- **Request Body:**
  ```json
  {
    "scenario_id": "clone_ceo",
    "claimed_name": "Rakesh Sir",
    "caller_number": "Unknown",
    "direction": "incoming"
  }
  ```
- **Response `201 Created`:**
  ```json
  {
    "session_id": "call_a1b2c3d4e5f6",
    "status": "CREATED",
    "ws_url": "/ws/call/call_a1b2c3d4e5f6",
    "config": {
      "window_seconds": 3.5,
      "hop_seconds": 1.75,
      "sample_rate": 16000,
      "channels": 1,
      "sample_width_bytes": 2
    },
    "server_time": "2026-10-30T10:00:00Z"
  }
  ```

#### `GET /api/v1/calls/history`
Returns caller's paginated call history.
- **Query Params:** `limit=20` (max 100)
- **Response `200 OK`:** Array of `CallHistoryItem`.

#### `GET /api/v1/calls/{session_id}`
Returns live status and metrics for an active or completed session.
- **Response `200 OK`:** `CallSession` object.
- **Errors:** `404` if session does not exist or caller is not owner.

#### `POST /api/v1/calls/{session_id}/end`
Terminates a call session and triggers finalization.
- **Response `200 OK`:** `CallSession` object with `status: "COMPLETED"`.

#### `GET /api/v1/calls/{session_id}/result`
Returns the final structured evaluation.
- **Response `200 OK`:**
  ```json
  {
    "session_id": "call_a1b2c3d4e5f6",
    "status": "COMPLETED",
    "risk_level": "HIGH",
    "latest_risk_score": 0.85,
    "evidence_quality": "good",
    "verification_status": "DENIED",
    "windows_processed": 6,
    "start_time": "2026-10-30T10:00:05Z",
    "end_time": "2026-10-30T10:00:25Z"
  }
  ```

---

## 5. Lifecycle State Machines

### 5.1 Call Session Status
```
CREATED  ──►  ACTIVE  ──►  PROCESSING  ──►  COMPLETED
   │             │              │
   ▼             ▼              ▼
CANCELLED     FAILED         FAILED
```
- **Terminal States:** `COMPLETED`, `CANCELLED`, `FAILED` (immutable once entered).

### 5.2 Verification Request Status
```
PENDING  ──►  APPROVED
   │     ──►  DENIED
   │     ──►  EXPIRED
   ▼
CANCELLED
```
- **Terminal States:** `APPROVED`, `DENIED`, `EXPIRED`, `CANCELLED`.

---

## 6. Privacy & Data Handling Guarantees
1. **Zero Audio Persistence:** Raw audio, binary frames, audio recordings, and voice transcripts are processed in memory and discarded immediately. They are never written to Firestore, cloud storage, logs, or local disk.
2. **Metadata Only:** The database retains strictly session IDs, numerical risk scores, categorical risk bands, evidence quality levels, verification outcomes, and automated 30-day TTL expiration timestamps.

---

## 7. WebSocket Audio Streaming Protocol (M5)

### 7.1 Endpoints
- **Primary:** `/ws/v1/calls/{session_id}`
- **Flutter Compatibility Alias:** `/ws/call/{session_id}`

### 7.2 Connection Lifecycle
1. Client establishes connection with `Authorization: Bearer <Firebase ID token>` (or sends `{"type": "auth", "token": "<token>"}` within 5s).
2. Server validates token and verifies that the caller owns the specified `session_id`.
3. Server transitions session state from `CREATED` $\to$ `ACTIVE`.
4. Server transmits `connection_ready` acknowledgement:
   ```json
   {
     "type": "connection_ready",
     "session_id": "call_123",
     "server_time": "2026-10-30T10:00:00Z",
     "config": {
       "windowMs": 3500,
       "hopMs": 1750,
       "sampleRate": 16000
     }
   }
   ```
5. Client optionally sends `{"type": "hello", "callId": "call_123"}` and receives `hello_ack`.
6. Client streams binary audio window frames.
7. Server responds with live `score` updates per scored window.
8. When call finishes, client sends `{"type": "end"}` and receives final `outcome` message before disconnect.

### 7.3 Binary Audio Frame Formats
Backend automatically supports both formats without client configuration:

**Format A — Member 1 Proposed Header (20 bytes LE + 112,000 bytes PCM = 112,020 bytes):**
- Bytes 0: `version` (uint8, `1`)
- Byte 1: `flags` (uint8, bit 0 = `is_last`)
- Bytes 2-3: `reserved` (uint16 LE, `0`)
- Bytes 4-7: `seq` (uint32 LE, starting at 0)
- Bytes 8-11: `offset_ms` (uint32 LE)
- Bytes 12-19: `send_epoch_ms` (uint64 LE)
- Bytes 20-end: PCM signed 16-bit little-endian mono (56,000 samples = 112,000 bytes)

**Format B — Member 2 Proposed Header (12 bytes BE + 112,000 bytes PCM = 112,012 bytes):**
- Bytes 0-3: `seq` (uint32 BE)
- Bytes 4-11: `capture_epoch_ms` (uint64 BE)
- Bytes 12-end: PCM signed 16-bit little-endian mono (112,000 bytes)

### 7.4 Live Score Message (`score`)
```json
{
  "type": "score",
  "seq": 0,
  "windowStartMs": 0,
  "windowRiskIndex": 88,
  "call": {
    "riskIndex": 88,
    "band": "high",
    "peakRiskIndex": 88
  },
  "voiceOutcome": "suspicious",
  "evidence": {
    "level": "good",
    "usableSpeechSec": 1.75
  },
  "serverProcessingMs": 110
}
```

### 7.5 WebSocket Application Close Codes
| Code | Meaning |
|---|---|
| `4401` | Unauthorized (invalid, expired, or missing token) |
| `4403` | Forbidden (caller is not session owner) |
| `4404` | Session not found |
| `4408` | Heartbeat timeout (30s inactivity) |
| `4409` | Conflict (session already in terminal state) |
| `4413` | Invalid audio frame (wrong size or out of order) |
| `4429` | Rate limit exceeded |

---

## 8. ML Service Interface Contract (Member 3)

### 8.1 Overview

The backend communicates with Member 3's ML audio analysis inference service via async HTTP.
The ML service endpoint is configurable via the environment variable `ML_SERVICE_URL` (default: `http://localhost:9000`).
Request timeout is configurable via `ML_TIMEOUT_SECONDS` (default: `3.0` seconds).

### 8.2 Request Specification

```
POST /predict
Content-Type: application/octet-stream
```

**Request Body:** Raw PCM audio bytes for a single analysis window.  
The body contains exactly `sample_rate × window_seconds × sample_width_bytes × channels` bytes of raw audio (e.g., 16000 × 3.5 × 2 × 1 = 112,000 bytes at default settings).

**Request Headers:**

| Header | Type | Example | Description |
|---|---|---|---|
| `Content-Type` | string | `application/octet-stream` | Always `application/octet-stream` |
| `X-Session-Id` | string | `call_a1b2c3d4e5f6` | Unique call session identifier |
| `X-Window-Id` | string | `0` | Zero-based sequence index of the audio window |
| `X-Sample-Rate` | string | `16000` | Audio sample rate in Hz |
| `X-Sample-Width` | string | `2` | Bytes per sample (2 = PCM signed 16-bit little-endian) |
| `X-Channels` | string | `1` | Channel count (1 = mono) |

### 8.3 Audio Format Assumptions (PROVISIONAL)

The backend assumes the following fixed PCM format, configurable via environment variables:

| Parameter | Default | Env Variable | Description |
|---|---|---|---|
| Sample Rate | 16000 Hz | `AUDIO_SAMPLE_RATE` | Sampling frequency |
| Sample Width | 2 bytes | `AUDIO_SAMPLE_WIDTH_BYTES` | Bytes per sample (PCM signed 16-bit LE) |
| Channels | 1 (mono) | `AUDIO_CHANNELS` | Number of audio channels |
| Window Duration | 3.5 s | `AUDIO_WINDOW_SECONDS` | Duration of each analysis window |
| Hop Interval | 1.75 s | `AUDIO_HOP_SECONDS` | Overlap between consecutive windows (50%) |
| Byte Order | Little-endian | — | Fixed: PCM signed 16-bit little-endian |

**Expected PCM payload size per window:** `16000 × 3.5 × 2 × 1 = 112,000 bytes`

### 8.4 Response Specification

**Response `200 OK` — JSON:**

```json
{
  "spoof_score": 0.88,
  "evidence_quality": 0.92
}
```

**Required fields (validated by backend):**

| Field | Type | Range | Description |
|---|---|---|---|
| `spoof_score` | float | [0.0, 1.0] | Probability that the audio is synthetically generated or replayed. Higher = more likely spoofed. |
| `evidence_quality` | float | [0.0, 1.0] | Confidence/quality of the analysis. Higher = more reliable evidence. Below `min_evidence_quality` (default 0.5), the score is ignored. |

**Optional fields (passthrough, not validated):**

| Field | Type | Description |
|---|---|---|
| `session_id` | string | Echo of request session ID |
| `window_id` | int | Echo of request window ID |
| `speech_duration` | float | Detected speech duration in seconds |
| `processing_time_ms` | int | Server-side inference time in milliseconds |

**Validation rules applied by the backend:**
1. Response must be valid JSON (`Content-Type: application/json`).
2. `spoof_score` and `evidence_quality` must be present, numeric, and finite.
3. `NaN`, `Infinity`, and `-Infinity` are explicitly **rejected**.
4. Values must satisfy `0.0 ≤ value ≤ 1.0`.
5. Any validation failure produces an `MLUnavailable` error and the window is treated as an analysis failure (never as safe).

### 8.5 Error Handling

The backend handles ML service failures defensively:

| Scenario | Backend Behavior |
|---|---|
| HTTP timeout (`ML_TIMEOUT_SECONDS` exceeded) | `MLUnavailable` raised. Window treated as analysis failure. |
| Non-200 HTTP status (e.g., 500, 503, 403) | `MLUnavailable` raised with HTTP status code. |
| Connection refused / network error | `MLUnavailable` raised. |
| Malformed or non-JSON response | `MLUnavailable` raised. |
| Invalid, out-of-range, NaN, or Infinity scores | `MLUnavailable` raised. |
| 3 consecutive failures in a session | `analysis_unavailable` event broadcast to client via WebSocket. |

**Critical safety guarantee:** ML failures are **NEVER** treated as genuine/safe. An unavailable analysis produces `FinalOutcome.ANALYSIS_UNAVAILABLE` or `FinalOutcome.INSUFFICIENT_EVIDENCE`, never `LIKELY_GENUINE`.

### 8.6 Privacy & Security

1. **Zero audio logging:** Raw PCM bytes are never written to logs at any log level (`DEBUG`, `INFO`, `WARNING`, `ERROR`).
2. **Zero audio persistence:** Raw audio is held in memory only for the duration of the HTTP request to the ML service, then discarded.
3. **No disk storage:** Audio bytes are never written to Firestore, cloud storage, local filesystem, or any persistent medium.
4. **Transport only:** Audio is transmitted over HTTP to the ML service endpoint. TLS (`https://`) is strongly recommended for production.

### 8.7 Information Required from Member 3

> **ACTION REQUIRED:** The following details must be confirmed by Member 3 before real ML integration can proceed.

| # | Item | Current Assumption | Status |
|---|---|---|---|
| 1 | **ML Service Base URL** | `http://localhost:9000` (dev default) | ⚠️ Needs production URL |
| 2 | **Authentication** | None (no auth headers sent beyond `X-*` metadata) | ⚠️ Confirm if API key, bearer token, or mTLS is required |
| 3 | **Endpoint Path** | `POST /predict` | ⚠️ Confirm exact path |
| 4 | **Input Format** | Raw PCM bytes (`application/octet-stream`) | ⚠️ Confirm acceptance of raw PCM or if a different encoding (WAV, FLAC, base64) is needed |
| 5 | **Sample Rate** | 16000 Hz, mono, PCM signed 16-bit LE | ⚠️ Confirm supported sample rates and formats |
| 6 | **Output Schema** | `{"spoof_score": float, "evidence_quality": float}` both in [0.0, 1.0] | ⚠️ Confirm exact response schema and field names |
| 7 | **Additional Output Fields** | `speech_duration`, `processing_time_ms` (optional) | ⚠️ Confirm if additional fields are returned |
| 8 | **Score Semantics** | `spoof_score` ∈ [0,1] where 1.0 = definitely spoofed | ⚠️ Confirm score polarity and calibration |
| 9 | **Error Response Format** | Generic HTTP error codes | ⚠️ Confirm error response body format |
| 10 | **Rate Limits** | None assumed | ⚠️ Confirm if rate limits or concurrency limits exist |
| 11 | **Model Versioning** | Not tracked | ⚠️ Confirm if model version is returned in response headers or body |
| 12 | **Health Check Endpoint** | `GET /health` assumed | ⚠️ Confirm health/readiness probe endpoint |

**Note:** Until Member 3 provides their actual service, all integration tests use `httpx.MockTransport` or the in-process `tests/mock_ml_server.py` stub. The backend adapter (`app/services/ml_service.py`) is ready to connect to the real service with zero code changes once the above items are confirmed.

