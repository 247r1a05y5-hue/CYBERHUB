"""Integration tests for Cross-Store Deletion Consistency & Data Retention (Slice 11).

Tests:
- Scheduled purge deletes relational rows from PostgreSQL
- Purges raw files from secure isolated storage
- Purges associated vectors from Qdrant vector database
- Asserts zero orphaned vectors or filesystem artifacts survive
- Generates reproducible, auditable deletion receipt
"""
from __future__ import annotations

import io
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from PIL import Image

from app.models.attestation import InvestigationAttestation
from app.models.biometrics import ReferenceImage
from app.models.case import Case, CaseStatus
from app.models.discovery import SearchJob, SearchResult
from app.services.dinov2_service import dinov2_service
from app.services.qdrant_service import qdrant_service
from app.services.retention_service import retention_service
from app.services.secure_storage_service import secure_storage_service
from tests.fixtures.synthetic_corpus import create_base_synthetic_image, get_image_bytes


@pytest.mark.asyncio
class TestCrossStoreDeletionConsistency:
    async def test_atomic_purge_across_stores(self, db_session: AsyncSession, test_org, test_user):
        org_id = test_org.id
        user_id = test_user.id

        # 1. Create Case / Investigation
        case = Case(
            organization_id=org_id,
            title="Retention Purge Test Case",
            description="To be purged",
            status=CaseStatus.CLOSED,
            created_by_id=user_id,
        )
        db_session.add(case)
        await db_session.flush()
        await db_session.refresh(case)

        # 2. Store a physical test file in secure storage
        test_img = create_base_synthetic_image()
        img_bytes = get_image_bytes(test_img, format="PNG")
        storage_key = secure_storage_service.save_file(org_id, case.id, img_bytes, "png")
        assert secure_storage_service.file_exists(storage_key) is True

        # 3. Insert ReferenceImage and index vector into Qdrant
        emb = dinov2_service.generate_embedding(img_bytes)
        ref_image = ReferenceImage(
            organization_id=org_id,
            case_id=case.id,
            file_name="purge_target.png",
            storage_path=storage_key,
            sha256_hash="test_sha256_hash",
            phash="0123456789abcdef",
            dhash="0123456789abcdef",
            uploaded_by=user_id,
        )
        db_session.add(ref_image)
        await db_session.flush()
        await db_session.refresh(ref_image)

        # Index in Qdrant
        await qdrant_service.upsert_embedding(
            ref_image_id=ref_image.id,
            vector=emb,
            investigation_id=case.id,
            org_id=org_id,
            metadata={"file_name": "purge_target.png"},
        )
        # Verify vector exists
        found_vecs = await qdrant_service.search_similar(emb, org_id=org_id, limit=5)
        assert any(v.reference_image_id == ref_image.id for v in found_vecs)

        # 4. Perform Complete Cross-Store Purge
        receipt = await retention_service.purge_investigation(db_session, case.id, org_id)
        assert receipt is not None
        assert receipt.investigation_id == case.id
        assert receipt.purged_files_count >= 1
        assert receipt.purged_vectors_count >= 1
        assert receipt.deleted_at is not None

        # 5. Assert Cross-Store Consistency Assertions:
        # A. Relational DB row is deleted
        db_check = await db_session.execute(select(Case).where(Case.id == case.id))
        assert db_check.scalar_one_or_none() is None

        ref_check = await db_session.execute(select(ReferenceImage).where(ReferenceImage.case_id == case.id))
        assert ref_check.scalar_one_or_none() is None

        # B. Filesystem artifact is physically removed
        assert secure_storage_service.file_exists(storage_key) is False

        # C. Qdrant vector is purged (zero orphaned vectors)
        post_purge_vecs = await qdrant_service.search_similar(emb, org_id=org_id, limit=5)
        assert not any(v.reference_image_id == ref_image.id for v in post_purge_vecs)
