# SatyaSwar Firestore Database Architecture & Schema
**Version:** 1.0.0  
**Author:** Member 2 (Backend, Infrastructure, Database & Security)

---

## 1. Security Philosophy: Complete Client Lockdown

All client writes and direct reads from mobile SDKs are locked down:
```javascript
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    match /{document=**} {
      allow read, write: if false;
    }
  }
}
```
All read/write operations occur through the authenticated FastAPI backend using the Firebase Admin SDK, ensuring complete authorization, auditability, anti-enumeration, and data integrity.

---

## 2. Collections Overview

```
firestore/
├── users/                     # User account profiles
├── trusted_contacts/          # Directional paired relationships & private aliases
├── call_sessions/             # Real-time ephemeral call session tracking
├── call_history/              # Compact, scores-only permanent summaries (TTL 30d)
├── verification_requests/     # Out-of-band contact verification requests (TTL 120s)
└── device_tokens/             # FCM push notification tokens
```

---

## 3. Detailed Document Schemas

### 3.1 `users`
Keyed by Firebase Auth UID (`doc_id = uid`).
```json
{
  "uid": "firebase_uid_123",
  "name": "Priyanka Sharma",
  "email": "priyanka@example.com",
  "phone": "+919876543210",
  "account_status": "active",
  "created_at": "TIMESTAMP",
  "updated_at": "TIMESTAMP"
}
```

### 3.2 `trusted_contacts`
Keyed by random auto-generated document ID.  
**Directional Isolation:** Each paired link creates two symmetric entries so personal aliases (e.g. "Priti" for "Priyanka Sharma") remain completely private to their respective owner.
```json
{
  "owner_uid": "user_alice",
  "contact_uid": "user_bob",
  "registered_name": "Bob Builder",
  "alias": "Bobby",
  "label": "office",
  "status": "accepted",
  "invite_code_hash": null,
  "invite_expires_at": null,
  "created_at": "TIMESTAMP",
  "updated_at": "TIMESTAMP"
}
```

### 3.3 `call_sessions`
Keyed by `session_id`. Represents active call state.
```json
{
  "session_id": "call_8f21a",
  "user_id": "user_alice",
  "status": "ACTIVE",
  "start_time": "TIMESTAMP",
  "end_time": null,
  "latest_risk_score": 0.85,
  "risk_level": "HIGH",
  "evidence_quality": "good",
  "verification_status": "NOT_REQUESTED",
  "window_count": 6,
  "created_at": "TIMESTAMP",
  "updated_at": "TIMESTAMP"
}
```

### 3.4 `call_history`
Keyed by auto-generated document ID.  
**Privacy Guarantee:** Retains only metadata and numeric scores. Contains ZERO audio bytes, waveforms, or transcripts.
```json
{
  "user_id": "user_alice",
  "session_id": "call_8f21a",
  "claimed_contact": "Bob Builder",
  "risk_score": 0.85,
  "risk_level": "HIGH",
  "evidence_quality": "good",
  "verification_status": "APPROVED",
  "final_outcome": "conflicting_signals",
  "created_at": "TIMESTAMP",
  "expires_at": "TIMESTAMP (+30 days)"
}
```

### 3.5 `verification_requests`
Keyed by auto-generated document ID.  
**Challenge Match Codes:** Generated as 2-digit numeric challenges, stored strictly as HMAC-SHA256 hashes.
```json
{
  "session_id": "call_8f21a",
  "requester_id": "user_alice",
  "contact_user_id": "user_bob",
  "claimed_identity": "Bob",
  "action_type": "money_transfer",
  "amount": 25000.0,
  "status": "PENDING",
  "code_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
  "attempts": 0,
  "max_attempts": 3,
  "created_at": "TIMESTAMP",
  "expires_at": "TIMESTAMP (+120s)",
  "responded_at": null
}
```

---

## 4. Automated Data Retention & TTL Policies

1. **`call_history`:** Each document includes an `expires_at` timestamp set to 30 days post-completion. Cloud Firestore's native TTL policy automatically deletes expired history documents without background compute costs.
2. **`verification_requests`:** Checked lazily on read and marked `EXPIRED` once `expires_at` is surpassed.

