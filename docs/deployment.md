# SatyaSwar Backend Deployment Guide
**Target Platform:** Google Cloud Run (Fully Managed Serverless Container)  
**Author:** Member 2 (Backend, Infrastructure, Database & Security)  
**Date:** 2026-10-30

---

## 1. Architecture Overview

The SatyaSwar FastAPI backend runs as a containerized workload on **Google Cloud Run**, tightly coupled with **Firebase Authentication** and **Cloud Firestore**. Real-time WebSocket audio streaming runs over secure WebSockets (`wss://`) with Cloud Run **Session Affinity** enabled to maintain sticky routing for active calls.

```
                      ┌──────────────────────┐
                      │ Flutter Client App   │
                      │ (Android / Demo)     │
                      └──────────┬───────────┘
                                 │ HTTPS / WSS
                                 ▼
                      ┌──────────────────────┐
                      │ Google Cloud Run     │
                      │ satyaswar-api        │
                      └──────┬────────┬──────┘
                             │        │
             Firebase Tokens │        │ gRPC / Private HTTP
                             ▼        ▼
                   ┌──────────┐      ┌─────────────────────────┐
                   │ Firebase │      │ Member 3 ML Service     │
                   │ & DB     │      │ (Laptop / GPU Instance) │
                   └──────────┘      └─────────────────────────┘
```

---

## 2. Prerequisites

1. **Google Cloud SDK (`gcloud` CLI):**
   ```bash
   gcloud auth login
   gcloud config set project <YOUR_GCP_PROJECT_ID>
   ```
2. **Artifact Registry / Container Registry:**
   ```bash
   gcloud services enable run.googleapis.com \
                          artifactregistry.googleapis.com \
                          secretmanager.googleapis.com \
                          firestore.googleapis.com
   ```
3. **Dedicated Runtime Service Account:**
   ```bash
   gcloud iam service-accounts create satyaswar-backend-sa \
       --description="Runtime identity for SatyaSwar FastAPI backend" \
       --display-name="SatyaSwar Backend SA"

   # Grant Firestore User role
   gcloud projects add-iam-policy-binding <YOUR_GCP_PROJECT_ID> \
       --member="serviceAccount:satyaswar-backend-sa@<YOUR_GCP_PROJECT_ID>.iam.gserviceaccount.com" \
       --role="roles/datastore.user"

   # Grant Secret Accessor role
   gcloud projects add-iam-policy-binding <YOUR_GCP_PROJECT_ID> \
       --member="serviceAccount:satyaswar-backend-sa@<YOUR_GCP_PROJECT_ID>.iam.gserviceaccount.com" \
       --role="roles/secretmanager.secretAccessor"
   ```

---

## 3. Secret Management & Environment Variables

Store all sensitive secrets in **Google Secret Manager**:
```bash
echo -n "a_strong_random_secret_for_hmac_signing_at_least_64_chars" | \
gcloud secrets create satyaswar-verification-secret --data-file=-
```

### Environment Variables Matrix

| Variable | Description | Development Default | Production Recommended |
|---|---|---|---|
| `APP_ENV` | Runtime environment tier | `development` | `production` |
| `PORT` | Container listen port | `8000` | `8080` |
| `FIREBASE_PROJECT_ID` | GCP / Firebase project identifier | Auto-discovered | `<YOUR_GCP_PROJECT_ID>` |
| `CORS_ORIGINS` | Allowed web origins | `["http://localhost:3000"]` | `["https://dashboard.satyaswar.internal"]` |
| `ML_SERVICE_URL` | Member 3 audio analysis URL | `http://localhost:9000` | `http://10.128.0.5:9000` (Internal VPC IP) |
| `ML_TIMEOUT_SECONDS` | Timeout for inference | `3.0` | `3.0` |
| `VERIFICATION_TTL_SECONDS` | TTL for match-code requests | `120` | `120` |
| `VERIFICATION_HMAC_SECRET` | Secret for match code hashes | Loaded from env | Secret Manager reference |

---

## 4. Build & Deployment Commands

### 4.1 Build and Deploy to Cloud Run

```bash
gcloud run deploy satyaswar-api \
    --source . \
    --region us-central1 \
    --platform managed \
    --service-account satyaswar-backend-sa@<YOUR_GCP_PROJECT_ID>.iam.gserviceaccount.com \
    --session-affinity \
    --timeout 3600 \
    --concurrency 80 \
    --min-instances 1 \
    --max-instances 10 \
    --cpu 2 \
    --memory 2Gi \
    --allow-unauthenticated \
    --set-env-vars "APP_ENV=production,FIREBASE_PROJECT_ID=<YOUR_GCP_PROJECT_ID>,ML_SERVICE_URL=http://<ML_IP>:9000" \
    --set-secrets "VERIFICATION_HMAC_SECRET=satyaswar-verification-secret:latest"
```

### 4.2 Key Configuration Flags:
- `--session-affinity`: Guarantees that subsequent WebSocket packets and reconnect attempts from the same client stay routed to the exact same backend instance.
- `--timeout 3600`: Extends request timeout to 1 hour, allowing long call streaming sessions without premature HTTP termination.
- `--min-instances 1`: Eliminates cold-start latency during emergency verification requests and live demo presentations.

---

## 5. Deploying Firestore Rules & Indexes

Deploy database security rules and composite indexes:
```bash
firebase deploy --only firestore:rules,firestore:indexes
```

---

## 6. Verification & Health Monitoring

1. **Liveness Probe:**
   ```bash
   curl -i https://<CLOUD_RUN_URL>/health
   # Expected: HTTP 200 OK {"status": "healthy"}
   ```
2. **OpenAPI Documentation:**
   Open `https://<CLOUD_RUN_URL>/docs` in browser to verify route registrations.
3. **Cloud Logging Filter:**
   ```
   resource.type="cloud_run_revision"
   severity>=WARNING
   ```

---

## 7. Rollback Procedure

If a deployment experiences regression:
```bash
# List previous revisions
gcloud run revisions list --service satyaswar-api --region us-central1

# Instantly route 100% traffic back to known healthy revision
gcloud run services update-traffic satyaswar-api \
    --to-revisions satyaswar-api-00001-abc=100 \
    --region us-central1
```

