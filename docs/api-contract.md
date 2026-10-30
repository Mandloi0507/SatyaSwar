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

The backend interacts with the audio analysis ML service via async HTTP:
- **Target URL:** `settings.ml_service_url` (`POST /predict`)
- **Request Body:** Raw PCM audio bytes (`Content-Type: application/octet-stream`)
- **Request Headers:**
  - `X-Session-Id`: Unique call session ID
  - `X-Window-Id`: Sequence index of the window
  - `X-Sample-Rate`: `16000`
- **Response `200 OK` JSON:**
  ```json
  {
    "session_id": "call_123",
    "window_id": 0,
    "spoof_score": 0.88,
    "evidence_quality": 0.92,
    "speech_duration": 3.5,
    "processing_time_ms": 110
  }
  ```
- **Error Behavior:** Timeouts or non-200 responses trigger fallback `analysis_unavailable` events to the client. Failures are NEVER treated as safe.

