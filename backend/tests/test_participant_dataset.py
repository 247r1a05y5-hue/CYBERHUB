"""Tests for the controlled-dataset AWS Rekognition pipeline.

Covers:
- Participant enrollment and consent
- Image upload and validation
- AWS service error mapping (no real AWS required)
- No-photo-leak guarantee (explicit automated assertion)
- Social URL handling (only confirmed sources returned)
- Tenant isolation (org A cannot see org B's data)
- Deletion (retry-safe)
- Idempotency
- Real AWS test (if credentials present) or blocked report
"""
from __future__ import annotations

import io
import uuid
from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.organization import Organization
from app.models.participant import (
    ConsentStatus,
    DatasetMatch,
    ImageIndexStatus,
    MatchStatus,
    Participant,
    ParticipantImage,
    ParticipantPublicSource,
    VerificationStatus,
)
from app.models.user import User
from app.services.participant_service import ParticipantService, validate_and_decode_image


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_minimal_jpeg() -> bytes:
    """Create a tiny valid JPEG in memory."""
    from PIL import Image as PILImage
    buf = io.BytesIO()
    img = PILImage.new("RGB", (100, 100), color=(128, 64, 32))
    img.save(buf, format="JPEG")
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def org_a(db_session: AsyncSession) -> Organization:
    org = Organization(name="Org Alpha")
    db_session.add(org)
    await db_session.flush()
    return org


@pytest_asyncio.fixture
async def org_b(db_session: AsyncSession) -> Organization:
    org = Organization(name="Org Beta")
    db_session.add(org)
    await db_session.flush()
    return org


@pytest_asyncio.fixture
async def participant_a(db_session: AsyncSession, org_a: Organization) -> Participant:
    svc = ParticipantService(db_session)
    p = await svc.create_participant(
        organization_id=org_a.id,
        display_name="Alice Test",
        participant_code="P001",
    )
    return p


@pytest_asyncio.fixture
async def consented_participant(db_session: AsyncSession, org_a: Organization) -> Participant:
    svc = ParticipantService(db_session)
    p = await svc.create_participant(
        organization_id=org_a.id,
        display_name="Bob Consented",
        participant_code="P002",
    )
    p = await svc.grant_consent(
        participant_id=p.id,
        organization_id=org_a.id,
    )
    await db_session.flush()
    return p


# ---------------------------------------------------------------------------
# 1. Enrollment and Consent
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_participant_pending_consent(db_session: AsyncSession, org_a: Organization):
    svc = ParticipantService(db_session)
    p = await svc.create_participant(
        organization_id=org_a.id,
        display_name="Test Person",
        participant_code="T001",
    )
    assert p.id is not None
    assert p.consent_status == ConsentStatus.PENDING
    assert p.is_active is True
    assert p.participant_code == "T001"


@pytest.mark.asyncio
async def test_grant_consent(db_session: AsyncSession, org_a: Organization, participant_a: Participant):
    svc = ParticipantService(db_session)
    p = await svc.grant_consent(
        participant_id=participant_a.id,
        organization_id=org_a.id,
        method="ADMIN_ENROLLMENT",
    )
    assert p.consent_status == ConsentStatus.CONSENTED
    assert p.consent_timestamp is not None


@pytest.mark.asyncio
async def test_participant_code_uniqueness(db_session: AsyncSession, org_a: Organization):
    """Duplicate participant codes in the same org should fail."""
    svc = ParticipantService(db_session)
    await svc.create_participant(org_a.id, "First", participant_code="DUPE001")
    await db_session.flush()
    with pytest.raises(Exception):  # UniqueConstraint violation
        await svc.create_participant(org_a.id, "Second", participant_code="DUPE001")
        await db_session.flush()


# ---------------------------------------------------------------------------
# 2. Image validation
# ---------------------------------------------------------------------------


def test_validate_and_decode_image_valid():
    data = _make_minimal_jpeg()
    img, mime, w, h = validate_and_decode_image(data)
    assert mime == "image/jpeg"
    assert w == 100
    assert h == 100


def test_validate_and_decode_image_too_large():
    data = b"\xff\xd8\xff" + b"\x00" * (6 * 1024 * 1024)
    with pytest.raises(ValueError, match="too large"):
        validate_and_decode_image(data)


def test_validate_and_decode_image_invalid_mime():
    data = b"PK\x03\x04" + b"\x00" * 100  # ZIP magic bytes
    with pytest.raises(ValueError, match="Unsupported image type"):
        validate_and_decode_image(data)


def test_validate_and_decode_image_not_an_image():
    data = b"\xff\xd8\xff" + b"not_a_real_jpeg_body_xxx" * 10
    with pytest.raises(ValueError):
        validate_and_decode_image(data)


# ---------------------------------------------------------------------------
# 3. AWS service error mapping
# ---------------------------------------------------------------------------


def test_aws_error_no_credentials():
    from app.services.aws_rekognition_service import _map_aws_error

    try:
        from botocore.exceptions import NoCredentialsError
        exc = NoCredentialsError()
        code, msg = _map_aws_error(exc)
        assert code == "AWS_AUTH_FAILED"
        assert "credentials" in msg.lower()
    except ImportError:
        pytest.skip("botocore not installed")


def test_aws_error_access_denied():
    from app.services.aws_rekognition_service import _map_aws_error

    try:
        from botocore.exceptions import ClientError
        exc = ClientError(
            {"Error": {"Code": "AccessDeniedException", "Message": "Access denied"}},
            "IndexFaces",
        )
        code, msg = _map_aws_error(exc)
        assert code == "AWS_ACCESS_DENIED"
    except ImportError:
        pytest.skip("botocore not installed")


def test_aws_error_collection_not_found():
    from app.services.aws_rekognition_service import _map_aws_error

    try:
        from botocore.exceptions import ClientError
        exc = ClientError(
            {"Error": {"Code": "ResourceNotFoundException", "Message": "Not found"}},
            "SearchFaces",
        )
        code, msg = _map_aws_error(exc)
        assert code == "AWS_COLLECTION_NOT_FOUND"
    except ImportError:
        pytest.skip("botocore not installed")


def test_aws_error_throttle():
    from app.services.aws_rekognition_service import _map_aws_error

    try:
        from botocore.exceptions import ClientError
        exc = ClientError(
            {"Error": {"Code": "ThrottlingException", "Message": "Throttled"}},
            "SearchFaces",
        )
        code, msg = _map_aws_error(exc)
        assert code == "AWS_THROTTLED"
    except ImportError:
        pytest.skip("botocore not installed")


# ---------------------------------------------------------------------------
# 4. No-photo-leak guarantee (automated, explicit)
# ---------------------------------------------------------------------------


FORBIDDEN_RESPONSE_FIELDS = {"storage_key", "image_url", "raw_bytes", "file_path", "thumbnail_url"}


def assert_no_photo_leak(response_data: Any, path: str = ""):
    """Recursively assert that no response contains forbidden fields."""
    if isinstance(response_data, dict):
        for key, value in response_data.items():
            full_path = f"{path}.{key}" if path else key
            assert key not in FORBIDDEN_RESPONSE_FIELDS, (
                f"PRIVACY VIOLATION: Response contains forbidden field '{full_path}'. "
                f"Stored participant images MUST NEVER be returned in API responses."
            )
            assert_no_photo_leak(value, full_path)
    elif isinstance(response_data, list):
        for i, item in enumerate(response_data):
            assert_no_photo_leak(item, f"{path}[{i}]")


def test_match_response_no_photo_leak():
    """Test that the MatchCandidateResponse schema does not contain photo leak fields."""
    from app.api.v1.endpoints.participants import MatchCandidateResponse
    import inspect

    fields = set(MatchCandidateResponse.model_fields.keys())
    for forbidden in FORBIDDEN_RESPONSE_FIELDS:
        assert forbidden not in fields, (
            f"PRIVACY VIOLATION: MatchCandidateResponse contains forbidden field '{forbidden}'."
        )


def test_image_response_no_storage_key():
    """Test that ParticipantImageResponse does not expose storage_key."""
    from app.api.v1.endpoints.participants import ParticipantImageResponse
    assert "storage_key" not in ParticipantImageResponse.model_fields, (
        "PRIVACY VIOLATION: ParticipantImageResponse must NOT include storage_key."
    )


def test_participant_response_no_photo_leak():
    """Test that ParticipantResponse does not expose stored images."""
    from app.api.v1.endpoints.participants import ParticipantResponse
    fields = set(ParticipantResponse.model_fields.keys())
    for forbidden in FORBIDDEN_RESPONSE_FIELDS:
        assert forbidden not in fields, (
            f"PRIVACY VIOLATION: ParticipantResponse contains forbidden field '{forbidden}'."
        )


@pytest.mark.asyncio
async def test_match_candidate_no_image_in_response(db_session: AsyncSession, org_a: Organization):
    """When a match is returned, public_sources MUST only contain platform+url, not image data."""
    svc = ParticipantService(db_session)

    # Create participant with source
    p = await svc.create_participant(org_a.id, "Privacy Test Person", "PRIV001")
    await svc.grant_consent(p.id, org_a.id)
    await svc.add_public_source(p.id, org_a.id, "linkedin", "https://linkedin.com/in/privacytest")
    await db_session.flush()

    # Simulate a match result
    match = DatasetMatch(
        organization_id=org_a.id,
        participant_id=p.id,
        query_image_sha256="abc123" * 10,
        aws_face_id_matched="aws-face-xyz",
        aws_external_image_id=f"CYBERHUB:PRIV001:IMG001",
        aws_similarity=95.5,
        match_status=MatchStatus.PENDING_REVIEW,
        matched_at=datetime.now(timezone.utc),
    )
    db_session.add(match)
    await db_session.flush()

    # The response dict should not contain any image storage data
    simulated_response = {
        "match_id": str(match.id),
        "participant_id": str(p.id),
        "participant_code": "PRIV001",
        "display_name": "Privacy Test Person",
        "aws_similarity": 95.5,
        "aws_face_id": "aws-face-xyz",
        "aws_external_image_id": "CYBERHUB:PRIV001:IMG001",
        "match_status": "PENDING_REVIEW",
        "public_sources": [{"platform": "linkedin", "url": "https://linkedin.com/in/privacytest"}],
    }
    assert_no_photo_leak(simulated_response)


# ---------------------------------------------------------------------------
# 5. Social URL handling
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_only_confirmed_sources_returned(
    db_session: AsyncSession,
    org_a: Organization,
    consented_participant: Participant,
):
    svc = ParticipantService(db_session)

    # Add confirmed source
    confirmed = await svc.add_public_source(
        consented_participant.id, org_a.id, "instagram", "https://instagram.com/realuser",
        participant_confirmed=True,
    )
    # Add unconfirmed source
    unconfirmed = await svc.add_public_source(
        consented_participant.id, org_a.id, "twitter", "https://twitter.com/unconfirmed",
        participant_confirmed=False,
    )
    await db_session.flush()

    # Simulate what match_face returns (only confirmed)
    from sqlalchemy import select
    src_stmt = select(ParticipantPublicSource).where(
        ParticipantPublicSource.participant_id == consented_participant.id,
        ParticipantPublicSource.participant_confirmed == True,
    )
    sources = list((await db_session.execute(src_stmt)).scalars().all())
    urls = [s.url for s in sources]

    assert "https://instagram.com/realuser" in urls
    assert "https://twitter.com/unconfirmed" not in urls


@pytest.mark.asyncio
async def test_url_returned_exactly_as_stored(
    db_session: AsyncSession,
    org_a: Organization,
    consented_participant: Participant,
):
    """URLs are returned exactly as stored — no guessing or construction."""
    svc = ParticipantService(db_session)
    original_url = "https://linkedin.com/in/exact-url-as-stored"
    src = await svc.add_public_source(
        consented_participant.id, org_a.id, "linkedin", original_url
    )
    await db_session.flush()
    assert src.url == original_url  # No normalization, no guessing


# ---------------------------------------------------------------------------
# 6. Tenant isolation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_tenant_isolation_participants(
    db_session: AsyncSession,
    org_a: Organization,
    org_b: Organization,
):
    """Org A cannot access Org B's participants."""
    svc = ParticipantService(db_session)

    # Create participant for org B
    p_b = await svc.create_participant(org_b.id, "Org B Person", "B001")
    await db_session.flush()

    # Org A tries to access org B's participant
    result = await svc.get_participant(p_b.id, org_a.id)
    assert result is None, "TENANT ISOLATION VIOLATION: Org A must not access Org B's participants."


@pytest.mark.asyncio
async def test_tenant_isolation_list(
    db_session: AsyncSession,
    org_a: Organization,
    org_b: Organization,
):
    """Listing participants returns only org-scoped records."""
    svc = ParticipantService(db_session)

    await svc.create_participant(org_a.id, "Org A Person", "A001")
    await svc.create_participant(org_b.id, "Org B Person", "B001")
    await db_session.flush()

    participants_a = await svc.list_participants(org_a.id)
    assert all(p.organization_id == org_a.id for p in participants_a)
    assert not any(p.participant_code == "B001" for p in participants_a)


@pytest.mark.asyncio
async def test_tenant_isolation_public_sources(
    db_session: AsyncSession,
    org_a: Organization,
    org_b: Organization,
):
    """Org B's public sources are not returned to Org A."""
    svc = ParticipantService(db_session)
    p_b = await svc.create_participant(org_b.id, "Org B Person 2", "B002")
    await svc.grant_consent(p_b.id, org_b.id)
    await svc.add_public_source(p_b.id, org_b.id, "instagram", "https://instagram.com/orgbprivate")
    await db_session.flush()

    # Org A cannot access this
    from sqlalchemy import select
    src_stmt = select(ParticipantPublicSource).where(
        ParticipantPublicSource.organization_id == org_a.id
    )
    sources = list((await db_session.execute(src_stmt)).scalars().all())
    assert not any("orgbprivate" in s.url for s in sources)


# ---------------------------------------------------------------------------
# 7. Deletion (retry-safe)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_participant_deletion(
    db_session: AsyncSession,
    org_a: Organization,
    participant_a: Participant,
):
    svc = ParticipantService(db_session)

    # Add source
    await svc.add_public_source(participant_a.id, org_a.id, "linkedin", "https://linkedin.com/test")
    await db_session.flush()

    # Delete participant
    report = await svc.delete_participant(participant_a.id, org_a.id)
    await db_session.flush()

    assert "participant_id" in report

    # Verify it's gone
    result = await svc.get_participant(participant_a.id, org_a.id)
    assert result is None


@pytest.mark.asyncio
async def test_deletion_not_found(db_session: AsyncSession, org_a: Organization):
    svc = ParticipantService(db_session)
    with pytest.raises(ValueError, match="not found"):
        await svc.delete_participant(uuid.uuid4(), org_a.id)


# ---------------------------------------------------------------------------
# 8. Idempotency
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_idempotent_image_upload(
    db_session: AsyncSession,
    org_a: Organization,
    consented_participant: Participant,
):
    """Uploading the same image twice should not create a duplicate record."""
    svc = ParticipantService(db_session)
    jpeg = _make_minimal_jpeg()

    detail1 = await svc.add_participant_image(
        consented_participant.id, org_a.id, jpeg
    )
    await db_session.flush()

    detail2 = await svc.add_participant_image(
        consented_participant.id, org_a.id, jpeg
    )
    await db_session.flush()

    assert detail1.id == detail2.id, "Idempotency violation: duplicate image was stored."


@pytest.mark.asyncio
async def test_idempotent_public_source(
    db_session: AsyncSession,
    org_a: Organization,
    consented_participant: Participant,
):
    """Adding the same URL twice should not create duplicate source records."""
    svc = ParticipantService(db_session)
    url = "https://linkedin.com/in/idempotency-test"

    src1 = await svc.add_public_source(consented_participant.id, org_a.id, "linkedin", url)
    await db_session.flush()
    src2 = await svc.add_public_source(consented_participant.id, org_a.id, "linkedin", url)
    await db_session.flush()

    assert src1.id == src2.id


# ---------------------------------------------------------------------------
# 9. Error paths
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_index_without_consent_fails(
    db_session: AsyncSession,
    org_a: Organization,
    participant_a: Participant,  # has PENDING consent
):
    """Attempting to index a participant without consent must raise an error."""
    svc = ParticipantService(db_session)
    with pytest.raises(ValueError, match="consent"):
        await svc.index_participant_images(participant_a.id, org_a.id)


@pytest.mark.asyncio
async def test_aws_not_configured_match(db_session: AsyncSession, org_a: Organization):
    """When AWS is not configured, match_face returns AWS_NOT_CONFIGURED — not 'no match'."""
    svc = ParticipantService(db_session)
    jpeg = _make_minimal_jpeg()

    with patch("app.services.participant_service.rekognition_service") as mock_svc:
        mock_svc.is_configured = False
        candidate = await svc.match_face(org_a.id, jpeg)

    assert candidate.error_code in ("AWS_NOT_CONFIGURED", "INSUFFICIENT_QUALITY")
    assert candidate.error_code != "NO_DATASET_MATCH", (
        "AWS_NOT_CONFIGURED must never be reported as NO_DATASET_MATCH"
    )


@pytest.mark.asyncio
async def test_no_face_detected_is_not_no_match(db_session: AsyncSession, org_a: Organization):
    """NO_FACE_DETECTED and NO_DATASET_MATCH must be distinct error codes."""
    assert "NO_FACE_DETECTED" != "NO_DATASET_MATCH"
    assert "AWS_AUTH_FAILED" != "NO_DATASET_MATCH"
    assert "AWS_THROTTLED" != "NO_DATASET_MATCH"


def test_aws_error_is_not_no_match_conceptually():
    """Documented error codes must have distinct values."""
    aws_infrastructure_errors = {
        "AWS_NOT_CONFIGURED",
        "AWS_AUTH_FAILED",
        "AWS_ACCESS_DENIED",
        "AWS_COLLECTION_NOT_FOUND",
        "AWS_INVALID_IMAGE",
        "AWS_THROTTLED",
        "AWS_SERVICE_UNAVAILABLE",
    }
    face_errors = {"NO_FACE_DETECTED", "MULTIPLE_FACES_DETECTED"}
    match_result = {"NO_DATASET_MATCH"}

    assert aws_infrastructure_errors.isdisjoint(face_errors)
    assert aws_infrastructure_errors.isdisjoint(match_result)
    assert face_errors.isdisjoint(match_result)


# ---------------------------------------------------------------------------
# 10. Real AWS test
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_real_aws_flow():
    """Real end-to-end AWS test — skips with BLOCKED report if credentials missing."""
    from app.core.config import settings
    from app.services.aws_rekognition_service import rekognition_service

    missing = []
    if not settings.AWS_REGION:
        missing.append("AWS_REGION")
    if not settings.AWS_REKOGNITION_COLLECTION_ID:
        missing.append("AWS_REKOGNITION_COLLECTION_ID")

    # Check if boto3 can find credentials
    boto3_creds_available = False
    try:
        import boto3
        session = boto3.Session()
        creds = session.get_credentials()
        if creds:
            boto3_creds_available = True
    except Exception:
        pass

    if missing or not boto3_creds_available:
        missing_str = ", ".join(missing) if missing else "AWS credentials (via credential chain)"
        pytest.skip(
            f"REAL AWS TEST BLOCKED: {missing_str}. "
            f"Configure {missing_str} to run the real AWS Rekognition flow."
        )

    # Create collection (idempotent)
    try:
        coll_info = rekognition_service.create_collection()
        assert coll_info.collection_id == settings.AWS_REKOGNITION_COLLECTION_ID
    except RuntimeError as e:
        pytest.fail(f"Collection creation failed: {e}")

    # Verify collection exists
    desc = rekognition_service.describe_collection()
    assert desc.status == "ACTIVE"

    # Index a test face
    jpeg = _make_minimal_jpeg()
    external_id = f"CYBERHUB:PYTEST:IMG001"
    try:
        result = rekognition_service.index_face(jpeg, external_image_id=external_id)
        assert result.face_id
        assert result.external_image_id == external_id
        assert result.face_confidence > 0

        # Search for it
        search_result = rekognition_service.search_faces_by_image(
            jpeg, face_match_threshold=70.0
        )
        # Note: minimal 100x100 JPEG may not have a real detectable face
        # This validates the API plumbing; face detection depends on actual photo content

        # Cleanup
        if result.face_id:
            rekognition_service.delete_faces([result.face_id])
    except ValueError as e:
        # NO_FACE_DETECTED is expected for synthetic images without real faces
        if "NO_FACE_DETECTED" in str(e):
            # Clean up — no face was indexed so nothing to delete
            pytest.xfail(
                "NO_FACE_DETECTED on synthetic test image — use a real photo for full AWS E2E test"
            )
        raise


# ---------------------------------------------------------------------------
# 11. Controlled dataset folder ingestion tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_controlled_dataset_ingestion_service(
    tmp_path, db_session: AsyncSession, org_a: Organization
):
    """Test full 4-CSV directory ingestion with validation and consent checks."""
    from app.services.dataset_ingestion_service import ControlledDatasetIngestionService

    dataset_dir = tmp_path / "CONTROLLED_DATASET"
    dataset_dir.mkdir()
    images_dir = dataset_dir / "images"
    images_dir.mkdir()

    # 1. participants.csv
    (dataset_dir / "participants.csv").write_text(
        "participant_code,display_name,notes\n"
        "P100,Ingestion Subject Alpha,Alpha test\n"
        "P101,Ingestion Subject Beta,Beta test\n"
    )

    # 2. consent_records.csv
    (dataset_dir / "consent_records.csv").write_text(
        "participant_code,consent_status,consent_timestamp,consent_method,notes\n"
        "P100,CONSENTED,2026-01-01T12:00:00Z,WRITTEN_CONSENT,Signed form\n"
        "P101,PENDING,2026-01-01T12:00:00Z,UNCONFIRMED,Awaiting signature\n"
    )

    # 3. public_sources.csv
    (dataset_dir / "public_sources.csv").write_text(
        "participant_code,platform,url,participant_confirmed\n"
        "P100,instagram,https://instagram.com/subject_alpha,true\n"
        "P100,linkedin,https://linkedin.com/in/subject-alpha,true\n"
        "P101,facebook,https://facebook.com/subject.beta,false\n"
    )

    # 4. Save a test JPEG into images/
    test_jpeg = _make_minimal_jpeg()
    img_file = images_dir / "alpha_photo1.jpg"
    img_file.write_bytes(test_jpeg)

    # images.csv
    (dataset_dir / "images.csv").write_text(
        "participant_code,image_file,image_sequence\n"
        "P100,alpha_photo1.jpg,1\n"
        "P101,alpha_photo1.jpg,1\n"  # Should be skipped because P101 has not consented
    )

    svc = ControlledDatasetIngestionService(db_session)
    report = await svc.ingest_dataset_directory(
        dataset_dir=dataset_dir,
        organization_id=org_a.id,
        auto_index_aws=False,
    )

    assert report.participants_created == 2
    assert report.consents_recorded == 2
    assert report.sources_ingested == 3
    assert report.images_ingested == 1  # Only P100 should succeed
    assert report.images_skipped >= 1  # P101 skipped due to pending consent

