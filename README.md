# CYBERHUB — Enterprise Image Exposure Intelligence & Forensic Containment Platform

CYBERHUB is a production-grade, multi-tenant cybersecurity intelligence and digital footprint remediation platform. It provides cryptographic image identification, multi-provider public discovery, forensic chain of custody, deterministic risk scoring, response workflow packaging, and automated continuous re-scan monitoring.

---

## Complete 13-Stage Investigation Lifecycle

```
[1. CAMERA / UPLOAD] ──> [2. SECURE VALIDATION] ──> [3. ATTESTATION & AUDIT GATE]
                                                              │
                                                              ▼
[6. PROVIDER DISCOVERY] <── [5. QDRANT VECTOR MATCH] <── [4. DINOv2 EMBEDDINGS]
          │
          ▼
[7. CORRELATION & GRAPH] ──> [8. HUMAN VERIFICATION] ──> [9. EVIDENCE VAULT]
                                                                  │
                                                                  ▼
[13. CONTINUOUS MONITORING] <── [12. REPORT & TAKEDOWN] <── [10. RISK (v1)]
```

1. **Camera / Upload**: Live WebRTC camera stream capture or secure file intake.
2. **Secure Validation**: Magic byte verification, EXIF GPS sanitization, biometric sharpness/contrast scoring.
3. **Forensic Attestation**: Cryptographic SHA-256 bound authorization statement with immutable audit record.
4. **Image Intelligence**: DINOv2 ViT embeddings (384-d / 768-d), pHash, and dHash calculation.
5. **Vector Indexing & Tiered Matching**:
   - Tier 1: Exact Bitwise SHA-256
   - Tier 2: Perceptual pHash / dHash (Hamming ≤ 8)
   - Tier 3: DINOv2 Cosine Similarity (≥ 0.85)
6. **Public Discovery Adapters**: Google Cloud Vision, TinEye, Bing Visual Search with circuit breakers and rate limits.
7. **Clustering & Graph Correlation**: Domain co-occurrence and infrastructure graph generation.
8. **Human-in-the-Loop Verification**: Strict separation of Candidate (`PENDING_REVIEW`) vs. Confirmed (`VERIFIED`) exposures.
9. **Forensic Evidence Vault**: SSRF-safe URL capture, SHA-256 custody chain hashing, and artifact storage.
10. **Deterministic Risk Evaluation (v1)**: Multi-factor risk engine gated strictly by verified findings.
11. **Investigation Graph & Timeline**: Interactive visualization and immutable case event trail.
12. **Report Center & Response Packaging**: Cryptographically signed reports and legally formatted takedown packages.
13. **Continuous Monitoring & Delta Model**: Periodic scheduled re-scanning with 4-state delta classification (`NEW`, `UNCHANGED`, `NOT_OBSERVED_IN_LATEST_SCAN`, `REAPPEARED`).

---

## Technology Stack

| Layer | Technology |
|---|---|
| **Frontend** | React 18, TypeScript, Vite, Tailwind CSS, TanStack Query, Zustand, Lucide Icons |
| **Backend** | Python 3.11+, FastAPI, Pydantic v2, SQLAlchemy 2.0 (asyncio) |
| **Databases** | PostgreSQL 16 (Strict production requirement), Qdrant Vector Engine |
| **Vision & ML** | PyTorch, DINOv2 (Vision Transformer), ImageHash, OpenCV |
| **Security & Auth** | Argon2id, JWT, SSRF-safe DNS pinning, Immutable Audit Logging |
| **Real-time** | Server-Sent Events (SSE) streaming progress and status |

---

## Quick Start (Development)

### Backend Setup
```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Or .venv\Scripts\activate on Windows
pip install -r requirements.txt

# Run migrations and start API server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

---

## Production Deployment & Security Configuration

### Database Invariants
- **PostgreSQL Mandate**: In production (`APP_ENV=production`), PostgreSQL is mandatory.
- **Fail-Closed Startup**: If PostgreSQL is unreachable, the API will fail startup or return `503 Service Unavailable` on `/health/ready`.
- **No Silent Fallback**: Development SQLite fallback flags are strictly rejected in production.

### Environment Variables
```env
APP_ENV=production
DATABASE_URL=postgresql+asyncpg://cyberhub_user:secure_password@postgres:5432/cyberhub
JWT_SECRET_KEY=generate_a_secure_random_64_char_key_here
CORS_ORIGINS=https://hub.yourdomain.com
ALLOW_SQLITE_DEV_MODE=false
```

---

## Health Check Endpoints

- `GET /health` (or `GET /api/v1/health`): Liveness probe returning HTTP 200 when API process is alive.
- `GET /health/ready` (or `GET /api/v1/health/ready`): Environment-aware readiness probe verifying PostgreSQL, Storage backend, and Qdrant connectivity.

---

## Automated Test Suite

```bash
cd backend
# Run complete test suite across all 6 phases
pytest tests/unit/ -v
pytest tests/integration/ -v
```
