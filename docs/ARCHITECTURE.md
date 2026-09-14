# CYBERHUB Architecture & Lifecycle Specification

## Overview

CYBERHUB is an enterprise image exposure intelligence, digital footprint attribution, and authorized exposure containment platform. It operates an end-to-end 13-stage deterministic investigation and response lifecycle.

---

## 13-Stage Investigation Lifecycle

```
[1. CAMERA / UPLOAD]
         │
         ▼
[2. SECURE VALIDATION & INTAKE]
         │
         ▼
[3. FORENSIC ATTESTATION & AUDIT GATE]
         │
         ▼
[4. IMAGE INTELLIGENCE & EMBEDDINGS (DINOv2 + pHash + dHash)]
         │
         ▼
[5. QDRANT VECTOR ENROLLMENT & TIERED MATCHING]
         │
         ▼
[6. MULTI-PROVIDER PUBLIC DISCOVERY ADAPTERS]
         │
         ▼
[7. CLUSTERING & CORRELATION ENGINE]
         │
         ▼
[8. HUMAN-IN-THE-LOOP ANALYST VERIFICATION]
         │
         ▼
[9. FORENSIC EVIDENCE VAULT (SSRF-Safe Capture & Cryptographic Hashing)]
         │
         ▼
[10. DETERMINISTIC RISK EVALUATION ENGINE (v1)]
         │
         ▼
[11. EXPOSURE GRAPH TOPOLOGY & TIMELINE AUDIT TRAIL]
         │
         ▼
[12. REPRODUCIBLE REPORT & RESPONSE PACKAGE DISPATCH]
         │
         ▼
[13. CONTINUOUS RESCANNING & DELTA MONITORING ENGINE]
```

---

## Component Architecture

### 1. Ingestion & Invariant Validation
- **MIME & Header Verification**: Verifies magic bytes (`image/jpeg`, `image/png`, `image/webp`).
- **EXIF Sanitization**: Strips GPS coordinates and embedded camera metadata prior to disk persistence.
- **Biometric Quality Scoring**: Computes sharpness (Laplacian variance), contrast, and brightness metrics.

### 2. Forensic Attestation Control
- **Explicit Authorization**: Requires human investigator attestation of lawful investigation scope.
- **SHA-256 Binding**: Attestation statement cryptographically references reference image SHA-256 fingerprint.
- **Immutable Log**: Attestation records cannot be deleted or modified once saved.

### 3. Multi-Tier Image Matching Engine
- **Tier 1 (Exact)**: SHA-256 bit-identical match.
- **Tier 2 (Perceptual)**: pHash / dHash Hamming distance ≤ 8.
- **Tier 3 (Semantic & Recompression)**: DINOv2 384-d / 768-d cosine similarity ≥ 0.85 with thresholded fallback.
- **Qdrant Vector DB**: Cosine vector indexing partitioned by tenant and case.

### 4. Provider Discovery & Circuit-Breaker Mesh
- **Adapter Layer**: Normalized unified response schema across Google Cloud Vision, TinEye, Bing Visual Search, and custom feeds.
- **Rate & Budget Guard**: Daily request quotas and cost guard rails per tenant.
- **Circuit Breaker**: Tracks consecutive provider errors and protects upstream APIs.

### 5. Human-in-the-Loop Verification
- **Verified vs. Candidate Separation**: Discovered findings remain `PENDING_REVIEW` candidates until an analyst signs off.
- **Confirmed Exposure**: ONLY `VERIFIED` findings transition to confirmed exposures and risk impact.

### 6. SSRF-Safe Forensic Evidence Preservation
- **DNS Pinning & Private IP Prohibition**: Rejects `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`, `127.0.0.0/8`, `169.254.0.0/16`, and cloud metadata endpoints (`169.254.169.254`).
- **Chain of Custody**: Cryptographic linking with sequence tracking and hash pointers (`previous_evidence_hash`).

### 7. Continuous Monitoring & Delta Model
- **Scheduled / Manual Re-scans**: Executes re-scans on daily or weekly schedules.
- **Delta Classification Engine**:
  - `NEW`: Newly observed candidate source.
  - `UNCHANGED`: Existing finding observed in latest scan.
  - `NOT_OBSERVED_IN_LATEST_SCAN`: Historical finding missing from latest scan (retained for audit integrity; NEVER deleted).
  - `REAPPEARED`: Previously unobserved finding seen again.
- **Idempotency**: Repeated scans with identical source inputs produce 0 duplicate findings or alerts.

---

## Production Readiness & Database Rules
- **PostgreSQL Requirement**: Production deployments (`APP_ENV=production`) strictly require PostgreSQL.
- **No Silent Fallback**: If PostgreSQL is unreachable in production, the application fails startup or reports `503 Service Unavailable` on `/health/ready`.
- **SQLite Permitted Only in Dev/Test**: Local testing flag `ALLOW_SQLITE_DEV_MODE=true` is rejected in production mode.
