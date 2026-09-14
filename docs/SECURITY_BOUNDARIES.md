# CYBERHUB Security Boundaries & Defensive Invariants

## 1. Multi-Tenant Cryptographic Isolation
- **Organization Scoping**: All database queries strictly join or filter by `organization_id`.
- **Worker Context Preservation**: Background workers (discovery, monitoring, embedding inference) pass and validate `organization_id`, `case_id`, and `reference_image_id` throughout the entire processing pipeline.
- **Cross-Tenant Test Verification**: Automated regression suites verify that Tenant A cannot access, scan, or modify Tenant B's investigations, findings, rules, or evidence vaults.

## 2. Server-Side Request Forgery (SSRF) Prevention
- **DNS Resolution Pinning**: Resolves hostnames before request dispatch and validates target IP addresses.
- **Prohibited Address Space**:
  - `127.0.0.0/8` (Loopback)
  - `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16` (RFC 1918 Private Subnets)
  - `169.254.0.0/16` (Link-Local & Cloud Metadata Services, e.g., AWS/GCP `169.254.169.254`)
  - `::1` and IPv6 site-local equivalents.
- **Redirect Validation**: Followed HTTP redirects are re-subjected to the same IP filtration rules.

## 3. Data Retention, Minimization & Custody
- **Forensic Hash Preservation**: Evidence items maintain immutable SHA-256 digests and custody sequence numbers (`custody_sequence`).
- **Cryptographic Purge Protocol**:
  - Relational database row deletion.
  - Disk / S3 object removal.
  - Qdrant vector embedding un-indexing.
  - Explicit reconciliation audit receipt (`reconciliation_status`).

## 4. Production Database Security Rules
- **No SQLite in Production**: `APP_ENV=production` immediately rejects SQLite URLs or dev fallback flags.
- **Fail-Closed Principle**: Failure of production PostgreSQL results in system unavailability (`503 Service Unavailable`), preventing insecure or un-audited state mutation.
- **Credential Hygiene**: Default test credentials (`analyst@cyberhub.security` / `Password123!`) are locked strictly to local development and rejected in production environments.
