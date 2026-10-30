# SatyaSwar: Member 2 Detailed Build Guide

**Role:** Backend, Infrastructure, Database & Security Engineer
**Stack:** Python 3.11+ · FastAPI · Firebase Auth · Cloud Firestore · WebSockets · HTTPX · Pytest

This guide turns the solution document into an ordered build plan. Each module has: goal, steps, code skeleton, and a "done when" checklist. Code is a **starting skeleton**, not final production code. Items marked **[CONFIRM]** need agreement with Member 1 or Member 3 before you finalize them.

---

## 0. How to Work Through This Guide

1. Do modules in order (M1 → M8). Each builds on the previous one.
2. After every module: run tests, commit, open a PR into `develop`.
3. Update `docs/api-contract.md` **whenever** an endpoint, schema or event changes. Members 1 and 3 depend on it.
4. Never commit secrets (`.env`, service-account JSON).

### What you own vs. do not own

| You own | You do NOT own |
|---|---|
| FastAPI server, REST APIs, WebSocket server | Flutter UI, audio capture/playback |
| Firebase Admin integration, token verification | ML model training / inference internals |
| Firestore schema, authorization, retention | Dashboard visuals |
| ML adapter (calling Member 3's service) | |
| Risk engine, verification workflow | |
| Tests, deployment, API contract doc | |

### Decisions to settle early

| # | Decision | Owner(s) | Default if undecided |
|---|---|---|---|
| 1 | OS + IDE | You | Windows + VS Code |
| 2 | Auth methods (email/password, Google, phone OTP) | You + M1 | Email/password + Google |
| 3 | Firestore region + retention period | You | Region nearest to users (e.g. `asia-south1`); 30-day call history |
| 4 | Audio encoding / sample rate / channels | You + M1 + M3 | PCM 16-bit LE, 16 kHz, mono |
| 5 | How ML runs (separate HTTP service vs in-process) | You + M3 | Separate HTTP service |
| 6 | Risk thresholds and smoothing α | You + M3 | See M6 (placeholders only) |
| 7 | Verification delivery (push, in-app, SMS) and codes | You + M1 | In-app + FCM push, no codes at first |
| 8 | Deployment platform | You | Google Cloud Run |

---

## M1: Backend Project Setup (2-3 h)

### Goal
A running FastAPI server with config management, health check, Swagger docs, and a Git repo.

### Step 1: Environment

```bash
python --version            # must be 3.11+
mkdir -p satyaswar/backend && cd satyaswar/backend
python -m venv .venv
```

Activate: PowerShell `.\.venv\Scripts\Activate.ps1` · CMD `.venv\Scripts\activate` · Linux/macOS `source .venv/bin/activate`

```bash
pip install fastapi "uvicorn[standard]" firebase-admin python-dotenv \
            pydantic pydantic-settings httpx pytest pytest-asyncio
pip freeze > requirements.txt
```

### Step 2: Folder structure

```text
backend/
├── app/
│   ├── main.py
│   ├── config.py
│   ├── routes/        auth.py users.py contacts.py calls.py verification.py
│   ├── services/      firebase.py ml_service.py notification_service.py
│   ├── repositories/  users.py contacts.py calls.py verification.py   (Firestore access)
│   ├── websocket/     connection.py call_stream.py
│   ├── decision/      risk_engine.py
│   ├── models/        schemas.py enums.py
│   └── dependencies/  auth.py
├── tests/
├── requirements.txt
├── .env.example
├── .gitignore
└── Dockerfile
```

(`repositories/` is a suggested addition so routes never touch Firestore directly.)

### Step 3: `.gitignore` (create before first commit)

```gitignore
.venv/
__pycache__/
.env
*.json.key
serviceAccount*.json
firebase-credentials*.json
*.wav
*.pcm
datasets/
.pytest_cache/
```

### Step 4: `app/config.py`

```python
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"            # development | production
    firebase_project_id: str = ""
    google_application_credentials: str = ""  # path to service account JSON (local only)
    cors_origins: list[str] = ["http://localhost:3000"]

    # ML integration
    ml_service_url: str = "http://localhost:9000"
    ml_timeout_seconds: float = 3.0

    # Audio contract [CONFIRM with M1/M3]
    audio_sample_rate: int = 16000
    audio_channels: int = 1
    audio_window_seconds: float = 3.5
    audio_hop_seconds: float = 1.75
    audio_sample_width_bytes: int = 2       # PCM16

    # Risk engine [CONFIRM with M3]
    risk_alpha: float = 0.4
    risk_high_threshold: float = 0.7
    risk_low_threshold: float = 0.3
    min_evidence_quality: float = 0.5

    # Verification
    verification_ttl_seconds: int = 120
    verification_max_attempts: int = 3
    verification_hmac_secret: str = ""      # used only if codes are adopted

@lru_cache
def get_settings() -> Settings:
    return Settings()
```

`.env.example`:

```env
APP_ENV=development
FIREBASE_PROJECT_ID=your-project-id
GOOGLE_APPLICATION_CREDENTIALS=./secrets/serviceAccount.json
ML_SERVICE_URL=http://localhost:9000
VERIFICATION_HMAC_SECRET=change-me
```

### Step 5: `app/main.py`

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.config import get_settings
from app.services.firebase import init_firebase

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_firebase()
    yield

settings = get_settings()
app = FastAPI(title="SatyaSwar API", version="0.1.0",
              description="Backend infrastructure for SatyaSwar", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"project": "SatyaSwar", "message": "Backend is running"}

@app.get("/health")
async def health():
    return {"status": "healthy"}

# Routers are added as each module is built:
# app.include_router(users.router, prefix="/api/v1/users", tags=["users"])
```

> For the very first milestone, comment out `init_firebase()` until M2.

### Step 6: Run and verify

```bash
uvicorn app.main:app --reload --port 8000
```

Check `http://127.0.0.1:8000/health` and `/docs`.

### Step 7: Git

```bash
git init && git add . && git commit -m "chore: initial FastAPI backend"
git branch -M main && git checkout -b develop && git checkout -b feature/backend-security
git remote add origin <repo-url> && git push -u origin feature/backend-security
```

### Done when
- [ ] Server runs, `/health` returns `{"status":"healthy"}`, `/docs` loads
- [ ] `.env` and credential files are git-ignored
- [ ] Code pushed to `feature/backend-security`

---

## M2: Firebase and Authentication (3-4 h)

### Goal
Verify Firebase ID tokens on every protected REST endpoint and WebSocket.

### Step 1: Firebase Console
1. Create project → enable **Authentication** (chosen providers) → create **Firestore** (production mode, chosen region).
2. Project Settings → Service accounts → **Generate new private key** → save as `backend/secrets/serviceAccount.json` (git-ignored).
3. Register the Flutter app (Android/iOS) and share `google-services.json` / `GoogleService-Info.plist` with Member 1.
4. In production, do **not** ship the JSON file; use the platform's default credentials / secret manager.

### Step 2: `app/services/firebase.py`

```python
import firebase_admin
from firebase_admin import credentials, firestore, auth
from app.config import get_settings

def init_firebase():
    if firebase_admin._apps:
        return
    s = get_settings()
    if s.google_application_credentials:
        cred = credentials.Certificate(s.google_application_credentials)
    else:
        cred = credentials.ApplicationDefault()   # Cloud Run / GCE
    firebase_admin.initialize_app(cred, {"projectId": s.firebase_project_id or None})

def db():
    return firestore.client()

def verify_id_token(token: str) -> dict:
    # check_revoked=True makes disabled/revoked users fail immediately
    return auth.verify_id_token(token, check_revoked=True)
```

### Step 3: `app/dependencies/auth.py`

```python
from fastapi import Depends, HTTPException, status, WebSocket
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from firebase_admin import auth as fb_auth
from pydantic import BaseModel
from app.services.firebase import verify_id_token

bearer = HTTPBearer(auto_error=False)

class AuthUser(BaseModel):
    uid: str
    email: str | None = None

def _verify(token: str) -> AuthUser:
    try:
        decoded = verify_id_token(token)
    except (fb_auth.InvalidIdTokenError, fb_auth.ExpiredIdTokenError,
            fb_auth.RevokedIdTokenError, fb_auth.UserDisabledError, ValueError):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token",
                            headers={"WWW-Authenticate": "Bearer"})
    return AuthUser(uid=decoded["uid"], email=decoded.get("email"))

def get_current_user(cred: HTTPAuthorizationCredentials = Depends(bearer)) -> AuthUser:
    if cred is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing bearer token")
    return _verify(cred.credentials)

def authenticate_ws_token(token: str | None) -> AuthUser | None:
    """Return user or None; caller closes the socket with code 4401 on None."""
    if not token:
        return None
    try:
        return _verify(token)
    except HTTPException:
        return None
```

### Step 4: WebSocket authentication design
Browsers/Flutter cannot always set headers on WebSockets. Two safe options:

- **Preferred:** connect, then client sends the **first message** `{"type":"auth","token":"<id_token>"}` within 5 s; server verifies and then sends `connection_ready`. Tokens stay out of URLs and logs.
- Fallback: `Authorization` header (Flutter's `IOWebSocketChannel` supports it).

Avoid `?token=` in query strings because URLs end up in logs.

### Step 5: Auth test endpoint (temporary)

```python
@router.get("/me-check")
def me_check(user: AuthUser = Depends(get_current_user)):
    return {"uid": user.uid}
```

Test: get an ID token from a Flutter test login (or Firebase Auth REST sign-in), call it from Swagger "Authorize".

### Done when
- [ ] Valid token → 200 with UID; missing/invalid/expired token → 401
- [ ] Revoked/disabled user rejected
- [ ] Token verification works for WebSocket first-message auth
- [ ] Tell Member 1: "Send `Authorization: Bearer <ID token>`; refresh tokens via `getIdToken()`"

---

## M3: Firestore Database Architecture (3-4 h)

### Goal
Implement collections, repositories, indexes, transactions, ownership checks and retention.

> **Critical:** the Admin SDK bypasses Firestore security rules. **Every** repository function must check ownership in code. Also set Firestore client rules to **deny all** (`allow read, write: if false;`) so the mobile app can only use your API.

### Collections and fields

| Collection | Doc ID | Fields |
|---|---|---|
| `users` | `uid` | uid, name, email, phone?, created_at, updated_at, account_status (`active`/`pending_deletion`/`deleted`) |
| `trusted_contacts` | auto | owner_uid, contact_uid (null until accepted), invitee_email?, display_name, status (`pending`/`accepted`/`rejected`/`removed`), invite_code_hash?, invite_expires_at?, created_at, updated_at |
| `call_sessions` | auto | session_id, user_id, status, start_time, end_time, latest_risk_score, risk_level, evidence_quality, verification_status, window_count, created_at |
| `verification_requests` | auto | session_id, requester_id, contact_user_id, claimed_identity, status, code_hash?, attempts, created_at, expires_at, responded_at |
| `call_history` | auto | user_id, session_id, risk_score, risk_level, evidence_quality, verification_status, created_at, expires_at |
| `device_tokens` | auto | user_id, token, platform, updated_at |

Notes:
- Use `firestore.SERVER_TIMESTAMP` for all timestamps.
- A trusted relationship is **directional per document** but should be treated as mutual once accepted. Simplest: one doc per pair, queried with `owner_uid == X` OR `contact_uid == X`. Decide and document this.
- `call_history` is a compact summary written on session completion; `call_sessions` may hold live state.

### Step 1: Pydantic enums (`models/enums.py`)

```python
from enum import StrEnum

class SessionStatus(StrEnum):
    CREATED="CREATED"; ACTIVE="ACTIVE"; PROCESSING="PROCESSING"
    COMPLETED="COMPLETED"; FAILED="FAILED"; CANCELLED="CANCELLED"

class RiskLevel(StrEnum):
    LOW="LOW"; MEDIUM="MEDIUM"; HIGH="HIGH"
    INCONCLUSIVE="INCONCLUSIVE"; UNAVAILABLE="UNAVAILABLE"

class VerificationStatus(StrEnum):
    NOT_REQUESTED="NOT_REQUESTED"; PENDING="PENDING"; APPROVED="APPROVED"
    DENIED="DENIED"; EXPIRED="EXPIRED"; CANCELLED="CANCELLED"

class ContactStatus(StrEnum):
    PENDING="pending"; ACCEPTED="accepted"; REJECTED="rejected"; REMOVED="removed"
```

### Step 2: Repository pattern (example)

```python
# repositories/calls.py
from firebase_admin import firestore
from app.services.firebase import db
from fastapi import HTTPException

COL = "call_sessions"

def get_owned_session(session_id: str, uid: str) -> dict:
    snap = db().collection(COL).document(session_id).get()
    if not snap.exists:
        raise HTTPException(404, "Session not found")
    data = snap.to_dict()
    if data["user_id"] != uid:
        raise HTTPException(404, "Session not found")   # 404, not 403: don't leak existence
    return data
```

### Step 3: Transactions
Use for: accepting an invite, verification responses, session state changes.

```python
from google.cloud import firestore as gcf

@gcf.transactional
def _transition(tx, ref, allowed_from: set[str], new_status: str):
    snap = ref.get(transaction=tx)
    if snap.get("status") not in allowed_from:
        raise HTTPException(409, "Invalid state transition")
    tx.update(ref, {"status": new_status, "updated_at": gcf.SERVER_TIMESTAMP})
```

### Step 4: Pagination
Cursor-based: order by `created_at desc`, `limit(n)`, return `next_cursor` = last doc's `created_at` + id; next call uses `start_after`.

### Step 5: Indexes
Create composite indexes as Firestore error links suggest, e.g.:
- `call_history`: `user_id ASC, created_at DESC`
- `trusted_contacts`: `owner_uid ASC, status ASC`; `contact_uid ASC, status ASC`
- `verification_requests`: `contact_user_id ASC, status ASC, created_at DESC`

Keep them in `firestore.indexes.json` in the repo.

### Step 6: Retention and account deletion
- Set `expires_at` on `call_history` and enable a Firestore **TTL policy** on that field.
- `DELETE /users/me`: set `account_status=pending_deletion`, then a background job deletes: user doc, contacts (both directions), sessions, history, verification requests, device tokens, and finally the Firebase Auth user (`auth.delete_user(uid)`).

### Step 7: Privacy rules (enforce in code and review)
- Never persist raw audio, frames, or transcripts, anywhere (DB, logs, temp files).
- Store only scores, levels and metadata.
- Logs must not contain tokens, emails, or payloads.

### Done when
- [ ] CRUD works for each collection through repositories
- [ ] Ownership checks exist in every repository read/write
- [ ] Firestore client rules deny all direct access
- [ ] Indexes file and TTL policy configured
- [ ] Account deletion flow works end to end on a test user

---

## M4: REST APIs and Call Session Management (4-5 h)

### Goal
All endpoints under `/api/v1/`, authenticated, authorized, validated, and usable from Swagger.

### Conventions
- Every route depends on `get_current_user` (except `/health`).
- Request/response bodies are Pydantic models; never return raw Firestore dicts.
- Standard error body: `{"error": {"code": "SESSION_NOT_FOUND", "message": "..."}}`. Add an exception handler and list codes in the contract.
- **Route order:** declare `GET /calls/history` **before** `GET /calls/{id}`, or `history` is parsed as an id.
- Use plain `def` routes with the sync Firestore client (FastAPI runs them in a threadpool), or wrap calls with `run_in_threadpool` inside `async def`.

### 4.1 User APIs

| Method | Path | Behavior |
|---|---|---|
| GET | `/users/me` | Return profile; create the doc on first call if missing (upsert from token claims) |
| PATCH | `/users/me` | Update `name`, `phone` only (whitelist fields; ignore anything else) |
| DELETE | `/users/me` | Mark `pending_deletion`, enqueue deletion job, return 202 |

```python
class UserUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=80)
    phone: str | None = Field(None, pattern=r"^\+?[0-9]{7,15}$")
```

### 4.2 Trusted-contact APIs

| Method | Path | Behavior |
|---|---|---|
| POST | `/contacts/invite` | Create `pending` relationship for an email (or generate an invite code); expiry 48 h; rate-limit |
| GET | `/contacts` | List relationships where caller is owner or contact; filter by `status` |
| POST | `/contacts/accept` | Invitee authenticates, presents invite id/code; transaction: validate not expired, not self, status pending, set `contact_uid`, `accepted` |
| POST | `/contacts/reject` | Same checks; set `rejected` |
| DELETE | `/contacts/{id}` | Either party may remove; set `removed` (or delete) |

Rules: cannot invite yourself; no duplicate active relationship; invite codes (if used) are random 128-bit, **stored hashed**, single use; do not reveal whether an email has an account.

### 4.3 Call APIs

| Method | Path | Behavior |
|---|---|---|
| POST | `/calls` | Create session `CREATED`; return `session_id` and WebSocket URL |
| GET | `/calls/history` | Paginated list from `call_history` for caller |
| GET | `/calls/{id}` | Session details (owner only) |
| POST | `/calls/{id}/end` | Move to `PROCESSING` → finalize → `COMPLETED`; write `call_history` |
| GET | `/calls/{id}/result` | Final structured outcome; 409 if not yet completed |

### 4.4 Session state machine

```text
CREATED ──► ACTIVE ──► PROCESSING ──► COMPLETED
   │           │            │
   └───────────┴────────────┴──► FAILED / CANCELLED
```

```python
ALLOWED = {
    "CREATED":    {"ACTIVE", "CANCELLED", "FAILED"},
    "ACTIVE":     {"PROCESSING", "CANCELLED", "FAILED"},
    "PROCESSING": {"COMPLETED", "FAILED"},
    "COMPLETED": set(), "FAILED": set(), "CANCELLED": set(),
}
```

- `CREATED → ACTIVE` happens when the WebSocket connects and passes auth.
- Terminal states are immutable. Use a transaction for every change.
- Auto-expire sessions stuck in `CREATED`/`ACTIVE` beyond a max duration (e.g. 2 h) to `FAILED`.

### 4.5 Result schema (agree with M1)

```json
{
  "session_id": "abc",
  "status": "COMPLETED",
  "risk_level": "HIGH",
  "latest_risk_score": 0.82,
  "evidence_quality": 0.9,
  "analysis_available": true,
  "verification_status": "NOT_REQUESTED",
  "message_code": "SUSPICIOUS_EVIDENCE",
  "ended_at": "2026-10-30T10:15:00Z"
}
```

### 4.6 Verification APIs
Built in M7; stub them here so Swagger shows the full surface.

### 4.7 Device token API (for push)
`POST /devices` (upsert `{token, platform}`), `DELETE /devices/{token}`. Required for notifying trusted contacts.

### Done when
- [ ] Every endpoint works from Swagger with an authorized token
- [ ] User B cannot read/modify User A's sessions, contacts or history (tested)
- [ ] Invalid state transitions return 409
- [ ] Pagination works on history
- [ ] `docs/api-contract.md` v1 published to Members 1 and 3

---

## M5: WebSocket and ML Integration (5-7 h)

### Goal
Receive audio windows from Flutter, get spoof scores from Member 3's service, run the risk engine, and push results back, reliably.

### Endpoint
`/ws/v1/calls/{session_id}` (use `wss://` in production)

### Step 1: Agree the audio contract **[CONFIRM]**

| Parameter | Proposed value |
|---|---|
| Encoding | PCM signed 16-bit little-endian |
| Sample rate | 16 000 Hz |
| Channels | mono |
| Window / hop | 3.5 s / 1.75 s |
| Window bytes | 3.5 × 16000 × 2 = **112 000** |

Proposed binary frame (one window per message):

```text
bytes 0-3   : uint32 BE  sequence number (starts at 0, +1 each window)
bytes 4-11  : uint64 BE  client capture timestamp (ms)
bytes 12-end: PCM16 audio payload
```

Validate: payload length == expected window bytes (allow a configured tolerance only if M3 agrees), sequence strictly increasing, no duplicates, within max rate.

### Step 2: Message protocol

Client → server (text JSON):
- `{"type":"auth","token":"..."}`: first message
- `{"type":"ping"}`
- `{"type":"request_verification", ...}` (optional)

Server → client events (all include `type`, `session_id`, `server_time`):

| Event | When |
|---|---|
| `connection_ready` | Auth + ownership verified; includes audio spec |
| `analysis_started` | First window accepted |
| `risk_update` | After each scored window: `risk_score`, `risk_level`, `window_id` |
| `evidence_update` | Evidence quality/speech duration changes |
| `verification_update` | Verification state changes |
| `analysis_unavailable` | ML failing/timeouts |
| `call_completed` | Session finalized |
| `error` | `code` + `message`, then optionally close |

Close codes: `4401` unauthenticated, `4403` not session owner, `4404` unknown session, `4409` invalid state, `4413` frame too large, `4429` rate exceeded.

### Step 3: `ml_service.py` adapter

```python
import httpx
from app.config import get_settings

class MLUnavailable(Exception): ...

class MLClient:
    def __init__(self):
        s = get_settings()
        self.client = httpx.AsyncClient(base_url=s.ml_service_url,
                                        timeout=s.ml_timeout_seconds)

    async def score_window(self, session_id: str, window_id: int, pcm: bytes) -> dict:
        try:
            r = await self.client.post(
                "/predict", content=pcm,
                headers={"Content-Type": "application/octet-stream",
                         "X-Session-Id": session_id, "X-Window-Id": str(window_id),
                         "X-Sample-Rate": "16000"})
            r.raise_for_status()
            data = r.json()
        except (httpx.HTTPError, ValueError) as e:
            raise MLUnavailable(str(e)) from e
        return validate_ml_output(data)

def validate_ml_output(d: dict) -> dict:
    for k in ("spoof_score", "evidence_quality"):
        v = d.get(k)
        if not isinstance(v, (int, float)) or not 0.0 <= v <= 1.0:
            raise MLUnavailable(f"invalid {k}")
    return d
```

Never log the audio bytes. Never treat an ML error as "safe".

### Step 3b: ML response contract **[CONFIRM with M3]**

```json
{ "session_id": "call_123", "window_id": 4, "spoof_score": 0.87,
  "evidence_quality": 0.91, "speech_duration": 3.2, "processing_time_ms": 120 }
```

Pin down: does a higher `spoof_score` mean more likely fake? Range 0-1? Is it calibrated? What does `evidence_quality` mean, and what does the service return for silence/no-speech?

### Step 4: Connection manager (`websocket/connection.py`)

```python
from collections import defaultdict
from fastapi import WebSocket

class ConnectionManager:
    def __init__(self):
        self.by_session: dict[str, set[WebSocket]] = defaultdict(set)

    def add(self, session_id, ws): self.by_session[session_id].add(ws)
    def remove(self, session_id, ws):
        self.by_session[session_id].discard(ws)
        if not self.by_session[session_id]:
            self.by_session.pop(session_id, None)

    async def broadcast(self, session_id, message: dict):
        for ws in list(self.by_session.get(session_id, ())):
            try: await ws.send_json(message)
            except Exception: self.remove(session_id, ws)
```

Broadcast only to sockets that passed auth **and** are authorized for that session (owner; later optionally the verified trusted contact).

### Step 5: Stream handler (`websocket/call_stream.py`), outline

```python
@router.websocket("/ws/v1/calls/{session_id}")
async def call_stream(ws: WebSocket, session_id: str):
    await ws.accept()
    # 1. auth: wait up to 5 s for first message {"type":"auth","token":...}
    # 2. load session; owner check; state must be CREATED or ACTIVE
    # 3. transition CREATED -> ACTIVE (transaction); send connection_ready
    # 4. create per-session state: RiskState, last_seq, bounded asyncio.Queue(maxsize=4)
    # 5. run 3 tasks: receiver, ml_worker, heartbeat; cancel all on first exit
    # 6. on disconnect: stop tasks, mark session per policy, remove from manager
```

**Receiver:** read `receive()`; binary → validate and `queue.put_nowait`; if full, **drop oldest** and emit a `window_dropped` counter (backpressure); text → handle `ping`/other commands.

**ML worker:** pull from queue → `await ml.score_window(...)` → on success `risk_engine.update(...)` → broadcast `risk_update`/`evidence_update`; on `MLUnavailable` increment failure count, send `analysis_unavailable` (after N consecutive failures), never a safe score.

**Heartbeat:** if no message or ping for e.g. 30 s, close with timeout code.

**Session isolation:** all state lives in a per-session object; no module-level mutable globals shared across sessions.

### Step 6: Reconnection
If the client drops mid-call, keep session `ACTIVE` for a grace period (e.g. 30 s). A reconnect with a valid token resumes with the stored `last_seq`/risk state; otherwise move to `PROCESSING → COMPLETED` using what exists.

### Step 7: Scaling note
In-memory per-session state and the connection manager mean one session's socket must stay on one instance. On Cloud Run: configure session affinity, set a long request timeout (WebSockets are still bound by the platform request timeout, up to 60 min), and expect reconnects. If you scale beyond one instance, add Redis or Firestore-backed state/pub-sub.

### Done when
- [ ] Unauthenticated/foreign-session sockets are rejected with the right close code
- [ ] Wrong-size, duplicate, out-of-order frames rejected cleanly
- [ ] ML timeout produces `analysis_unavailable`, never a "safe" result
- [ ] Queue is bounded; slow ML doesn't grow memory
- [ ] Two concurrent sessions never mix data
- [ ] Heartbeat timeout and graceful disconnect work
- [ ] A mock ML server lets you test without Member 3's model

**Tip:** build `tests/mock_ml_server.py` (a tiny FastAPI app returning random scores, with switches for delay/failure) on day one of M5.

---

## M6: Risk Aggregation and Decision Engine (3-4 h)

### Goal
A pure, well-tested module that turns per-window ML output + verification state into a structured outcome.

### Rolling score
R_t = α·S_t + (1 − α)·R_{t−1}, with R_0 = S_0.

Only update with windows whose evidence quality is acceptable; otherwise keep the last score and count the window as low-evidence. α and thresholds are **placeholders**; **[CONFIRM with M3]**, ideally from validation data.

### `decision/risk_engine.py` (skeleton)

```python
from dataclasses import dataclass, field
from app.config import get_settings

@dataclass
class RiskState:
    rolling: float | None = None
    windows_total: int = 0
    windows_good: int = 0
    latest_evidence: float = 0.0
    ml_failures_in_row: int = 0

def update(state: RiskState, spoof: float, evidence: float) -> RiskState:
    s = get_settings()
    state.windows_total += 1
    state.latest_evidence = evidence
    state.ml_failures_in_row = 0
    if evidence >= s.min_evidence_quality:
        state.windows_good += 1
        state.rolling = spoof if state.rolling is None else \
            s.risk_alpha * spoof + (1 - s.risk_alpha) * state.rolling
    return state

def classify(state: RiskState, ml_available: bool = True) -> dict:
    s = get_settings()
    if not ml_available or state.windows_total == 0:
        level, code = "UNAVAILABLE", "ANALYSIS_UNAVAILABLE"
    elif state.rolling is None or state.latest_evidence < s.min_evidence_quality:
        level, code = "INCONCLUSIVE", "INSUFFICIENT_EVIDENCE"
    elif state.rolling >= s.risk_high_threshold:
        level, code = "HIGH", "SUSPICIOUS_EVIDENCE"
    elif state.rolling <= s.risk_low_threshold:
        level, code = "LOW", "LOWER_SPOOF_RISK"
    else:
        level, code = "MEDIUM", "UNCERTAIN"
    return {"risk_level": level, "message_code": code,
            "risk_score": state.rolling, "evidence_quality": state.latest_evidence}
```

### Decision table to implement and test

| Condition | Level / message |
|---|---|
| High score + good evidence | `HIGH` / suspicious evidence |
| High score + poor evidence | `INCONCLUSIVE` |
| Low score + good evidence | `LOW` / lower spoof risk (never "guaranteed real") |
| Low score + poor evidence | `INCONCLUSIVE` |
| ML unavailable | `UNAVAILABLE` |
| Contact verified | Reported in a **separate** `verification_status` field |

**Rules:**
- A verified identity must **not** upgrade or downgrade the voice analysis automatically.
- Use wording like "lower spoof risk", never "this voice is real".
- Never default to a safe state on missing data.

### Persistence
At session end, build the final result from `RiskState`, write to `call_sessions` and a compact `call_history` doc (scores + metadata only).

### Unit tests (write first)
- Rolling formula with known inputs
- Each row of the decision table
- Poor-evidence windows don't move the score
- Zero windows → `UNAVAILABLE`
- Boundary values at thresholds

### Done when
- [ ] All decision-table cases pass tests
- [ ] Thresholds/α loaded from config, flagged as "to validate with M3"
- [ ] Result persisted without any audio or transcript

---

## M7: Trusted-Contact Verification (4-6 h)

### Goal
A secure, independent channel: the user asks a registered contact "did you call me?", and only that authenticated contact can answer.

### 7.1 Contact linking (from M4)
Invite → invitee authenticates → accepts → transaction validates both users → relationship `accepted`.

### 7.2 Verification workflow
1. User POSTs `/verification` with `session_id`, `contact_id` (relationship id), `claimed_identity`.
2. Backend checks: session owned by caller; relationship `accepted`; caller is a party; no other `PENDING` request for the same session+contact; rate limit not exceeded.
3. Create request `PENDING`, `expires_at = now + TTL` (default 120 s **[CONFIRM]**).
4. Notify contact: FCM push to their `device_tokens` (+ in-app polling `GET /verification?role=contact&status=PENDING`).
5. Contact authenticates and calls `POST /verification/{id}/respond {"approve": true|false}`.
6. Backend validates, in a **transaction**: caller UID == `contact_user_id`; status == `PENDING`; not expired; attempts not exceeded → set `APPROVED`/`DENIED`.
7. Update `call_sessions.verification_status`, push a `verification_update` WebSocket event to the requester.

### 7.3 State machine

```text
PENDING ──► APPROVED
   ├──────► DENIED
   ├──────► EXPIRED     (by timeout; lazy check on read + scheduled sweep)
   └──────► CANCELLED   (by requester)
```
Terminal states are final. Any transition from a non-`PENDING` state returns 409.

### 7.4 API

| Method | Path | Who | Notes |
|---|---|---|---|
| POST | `/verification` | requester | Creates request |
| GET | `/verification/{id}` | requester or contact | Status; mark `EXPIRED` if past `expires_at` |
| POST | `/verification/{id}/respond` | designated contact only | Approve / deny |
| POST | `/verification/{id}/cancel` | requester only | Only while `PENDING` |

### 7.5 Optional verification code
Only if the team adopts codes (decision #7):

```python
import hmac, hashlib, secrets

def new_code() -> str:             # 6 digits, cryptographically random
    return f"{secrets.randbelow(10**6):06d}"

def hash_code(code: str, request_id: str) -> str:
    key = get_settings().verification_hmac_secret.encode()
    return hmac.new(key, f"{request_id}:{code}".encode(), hashlib.sha256).hexdigest()

def check_code(code: str, request_id: str, stored: str) -> bool:
    return hmac.compare_digest(hash_code(code, request_id), stored)
```
Store only the hash; one-time use; max 3 attempts (increment inside the transaction); short expiry; never log the code.

### 7.6 Security requirements checklist
- [ ] Only the designated, authenticated contact can respond (UID check), never the caller or an arbitrary client
- [ ] Relationship must be `accepted` at request time and response time
- [ ] Atomic transitions, so double-approve or approve-after-cancel is impossible
- [ ] Replay prevention (terminal states + one-time codes)
- [ ] Rate limits on creating requests and on responses
- [ ] Requests are not enumerable (random IDs, 404 for non-parties)
- [ ] Verification result is reported **separately** from voice analysis

### Done when
- [ ] Full flow works with two test accounts
- [ ] Expiry, cancel, deny, double-respond and wrong-user cases all tested
- [ ] `verification_update` events reach the requester over WebSocket

---

## M8: Security, Testing and Deployment (4-6 h)

### 8.1 Security checklist

| Area | Implementation |
|---|---|
| AuthN | Firebase ID-token verification (`check_revoked=True`) |
| AuthZ | Ownership check in every repository call; 404 for non-owners |
| Validation | Pydantic everywhere; max lengths; enum fields |
| Rate limiting | `slowapi` or a gateway rule on invite, verification, auth-sensitive routes; per-UID limits |
| WebSocket | Auth timeout, ownership check, frame size/rate limits |
| Transport | HTTPS/WSS only in production |
| Secrets | Env vars / Secret Manager; never in Git |
| Firestore | Client rules deny-all; only backend writes |
| Logging | No tokens, emails, codes, or audio; log UIDs/session ids only |
| Privacy | No audio/transcripts persisted; TTL on history |
| CORS | Explicit origins in production, not `*` |
| Dependencies | `pip-audit` before release |

### 8.2 Testing plan

```text
tests/
├── unit/        test_risk_engine.py  test_session_state.py  test_verification_logic.py
├── api/         test_users.py test_contacts.py test_calls.py test_verification.py
├── websocket/   test_ws_auth.py test_ws_frames.py test_ws_ml_failure.py
├── integration/ test_e2e_flow.py
├── conftest.py            # fake auth + Firestore emulator fixtures
└── mock_ml_server.py
```

- **Firestore Emulator** (`firebase emulators:start --only firestore`) for tests; no production data.
- Override `get_current_user` with a fixture to simulate users A and B.
- Use FastAPI `TestClient` (`client.websocket_connect(...)`) for WebSocket tests.

Must-have cases:
1. Auth: missing, malformed, expired, revoked token → 401
2. Cross-user access to sessions/contacts/verification → 404/403
3. Invalid state transitions → 409
4. Wrong-size / duplicate / out-of-order audio frames
5. ML timeout, ML 500, ML malformed JSON → `analysis_unavailable`, never "safe"
6. Two concurrent sessions isolated
7. Verification: expired, replayed, wrong responder, cancelled
8. Account deletion removes all user data
9. No audio bytes appear in logs or DB (grep test)

Run: `pytest -q --cov=app`

### 8.3 Deployment (Cloud Run suggested)

`Dockerfile`:
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app
ENV PORT=8080
CMD ["sh","-c","uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
```

Steps:
1. Create a dedicated runtime service account with only Firestore + FCM permissions (no key file needed on Cloud Run).
2. Store secrets (`VERIFICATION_HMAC_SECRET`, etc.) in Secret Manager.
3. `gcloud run deploy satyaswar-api --source . --region <region> --session-affinity --timeout 3600 --set-env-vars ...`
4. Set production `CORS_ORIGINS`, `APP_ENV=production`.
5. Health check on `/health`; enable Cloud Logging/monitoring and alerts on 5xx and ML-failure rate.
6. Point Flutter at the `https://` / `wss://` URLs.
7. Write `docs/deployment.md` (env vars, deploy commands, rollback).

Alternatives: Render (simple, supports WebSockets), Compute Engine (most control, most ops).

### Done when
- [ ] Test suite green in CI (GitHub Actions: install, `pytest`, `pip-audit`)
- [ ] Deployed URL passes health check; WSS works from a real phone
- [ ] Security checklist reviewed with the team
- [ ] Deployment doc written

---

## Integration Responsibilities

### With Member 1 (Flutter)
Give them, in `docs/api-contract.md`: auth header format, all REST schemas, WebSocket auth + events + close codes, audio frame format, session/verification states, error codes, base URLs (dev/prod).

### With Member 3 (ML)
Agree and document: audio encoding, sample rate, channels, window metadata, request/response format, meaning and range of `spoof_score` and `evidence_quality`, timeout (default 3 s), failure behavior, and how ML is hosted/called.

### `docs/api-contract.md` template

```markdown
# SatyaSwar API Contract (v1)
## 1. Base URLs / Versioning
## 2. Authentication (REST + WebSocket)
## 3. Error format and codes
## 4. REST endpoints (per endpoint: method, path, auth, request, response, errors)
## 5. Session states and transitions
## 6. WebSocket: URL, handshake, client messages, server events, close codes
## 7. Audio frame format
## 8. ML request/response contract
## 9. Verification states and flow
## 10. Changelog (date, change, who must update)
```

---

## Suggested Schedule

| Day | Work | Output |
|---|---|---|
| 1 | M1 + start M2 | Running server, repo, Firebase project |
| 2 | Finish M2 + M3 | Token auth, Firestore schema/repositories |
| 3 | M4 | All REST endpoints, contract v1 shared |
| 4 | M5 (mock ML first) | Authenticated WS, frame validation, mock ML loop |
| 5 | M5 with real ML + M6 | End-to-end scoring, risk engine tests |
| 6 | M7 | Contact linking and verification flow |
| 7 | M8 | Tests, security review, deployment, docs |

Estimated focused effort: **28-39 h**, excluding coordination.

---

## Git Workflow

- Branch: `feature/backend-security` → PR into `develop` → release to `main`.
- Small commits: `feat:`, `fix:`, `test:`, `docs:` prefixes.
- Never commit credentials, private keys, datasets, or generated audio.
- Merge only with passing tests; integrate daily; keep the contract in sync with every API change.

---

## Final Deliverables Checklist

**Foundation:** [ ] project structure [ ] config [ ] health [ ] Swagger [ ] GitHub
**Firebase/DB:** [ ] Firebase project [ ] Admin SDK [ ] auth dependency [ ] Firestore schema [ ] ownership checks [ ] indexes/TTL
**REST:** [ ] users [ ] contacts [ ] calls [ ] verification [ ] history [ ] devices
**Real time:** [ ] authenticated WS [ ] audio receiver/validator [ ] ML adapter [ ] broadcaster [ ] timeout/error handling
**Decision:** [ ] rolling risk [ ] evidence handling [ ] decision engine [ ] contact linking [ ] verification state machine
**Production:** [ ] unit tests [ ] API tests [ ] WS tests [ ] integration tests [ ] security review [ ] deployment [ ] docs (`api-contract.md`, `deployment.md`)

---

## Definition of Done

The backend can securely authenticate users, manage permitted data, create and close call sessions, receive audio windows, communicate with the ML component, publish validated risk updates, run trusted-contact verification, produce structured outcomes, and pass the agreed end-to-end, security and failure-mode tests, **with no raw audio or transcripts stored and no "safe" result ever shown when analysis fails.**

---

## Your Very Next Actions

1. Confirm OS + IDE, check `python --version`.
2. Do M1 Steps 1-7 and push.
3. Create the Firebase project and download the service-account key (keep it out of Git).
4. Message Members 1 and 3 with the **[CONFIRM]** items (audio format, ML contract, verification channel).
