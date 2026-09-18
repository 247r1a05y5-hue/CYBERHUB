"""Comprehensive Dataset Ingestion & Face Intelligence Pipeline.

Supports:
- LFW-style identity folder datasets (<root>/<identity_name>/<image>.jpg)
- Controlled participant dataset folders (participants.csv, images.csv, consent_records.csv, public_sources.csv)
- ZIP archive datasets
- CSV manifest datasets
- Deterministic Gallery / Probe splitting for identity evaluation
- End-to-end pipeline: Validation -> Face Detection -> Quality Check -> Alignment -> ArcFace Embedding -> Qdrant Indexing
- Comprehensive Dataset Health Reporting
"""
from __future__ import annotations

import csv
import hashlib
import io
import logging
import os
import random
import uuid
import zipfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditAction
from app.models.biometrics import FaceValidationStatus
from app.models.dataset import Dataset, DatasetIdentity, DatasetStatus
from app.models.participant import (
    ConsentStatus,
    ImageIndexStatus,
    Participant,
    ParticipantConsent,
    ParticipantImage,
    ParticipantPublicSource,
)
from app.services.audit_service import AuditService
from app.services.face_detection_service import face_detection_service
from app.services.face_embedding_service import face_embedding_service
from app.services.image_validation_service import ImageValidationError, ImageValidationService
from app.services.participant_service import ParticipantService
from app.services.qdrant_service import qdrant_service

logger = logging.getLogger(__name__)


@dataclass
class DatasetHealthReport:
    """Detailed health and quality audit report for an ingested dataset."""
    organization_id: uuid.UUID
    dataset_name: str
    total_images: int = 0
    total_identities: int = 0
    accepted_images: int = 0
    rejected_images: int = 0
    zero_face_count: int = 0
    multi_face_count: int = 0
    quality_rejection_count: int = 0
    corrupted_image_count: int = 0
    duplicate_count: int = 0
    embedding_success_count: int = 0
    embedding_failure_count: int = 0
    indexed_vectors: int = 0
    identities_with_insufficient_gallery: int = 0
    gallery_image_count: int = 0
    probe_image_count: int = 0
    errors: list[str] = field(default_factory=list)

    @property
    def is_healthy(self) -> bool:
        return self.accepted_images > 0 and len(self.errors) == 0


@dataclass
class ControlledDatasetIngestionReport:
    """Report for 4-CSV directory dataset ingestion."""
    participants_created: int = 0
    consents_recorded: int = 0
    sources_ingested: int = 0
    images_ingested: int = 0
    images_skipped: int = 0


class DatasetIngestionService:
    """Production service for ingesting, validating, embedding, and indexing image datasets."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.participant_service = ParticipantService(session)
        self.audit_service = AuditService(session)

    # ── 1. LFW-Style Directory Ingestion ─────────────────────────────────────

    async def ingest_lfw_directory(
        self,
        dataset_dir: str | Path,
        organization_id: uuid.UUID,
        dataset_name: str = "LFW Dataset",
        user_id: uuid.UUID | None = None,
        gallery_size_per_identity: int = 3,
        random_seed: int = 42,
    ) -> DatasetHealthReport:
        """Ingest LFW-style folder structure (<dataset_dir>/<identity_name>/<image_file>).

        Applies deterministic Gallery/Probe split:
        - Default 3 images per identity assigned to 'gallery' partition
        - Remaining images assigned to 'probe' partition
        - Reproducible splitting via deterministic random seed
        """
        dir_path = Path(dataset_dir).resolve()
        if not dir_path.exists() or not dir_path.is_dir():
            raise FileNotFoundError(f"Dataset directory not found: {dir_path}")

        report = DatasetHealthReport(
            organization_id=organization_id,
            dataset_name=dataset_name,
        )

        seen_sha256: set[str] = set()
        rng = random.Random(random_seed)

        # 1. Discover all identity directories
        identity_root = dir_path / "identities"
        if identity_root.is_dir():
            dir_path = identity_root

        identity_dirs = [d for d in dir_path.iterdir() if d.is_dir() and not d.name.startswith(".")]
        report.total_identities = len(identity_dirs)

        logger.info(f"Ingesting LFW dataset from '{dir_path}' ({len(identity_dirs)} identities found)...")

        for id_dir in sorted(identity_dirs, key=lambda x: x.name):
            identity_name = id_dir.name.replace("_", " ").strip()
            image_files = [
                f for f in id_dir.iterdir()
                if f.is_file() and f.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}
            ]

            if not image_files:
                continue

            # Deterministic shuffle for gallery/probe partition assignment
            shuffled_files = list(image_files)
            rng.shuffle(shuffled_files)

            if len(shuffled_files) < gallery_size_per_identity:
                report.identities_with_insufficient_gallery += 1

            # 2. Get or create participant in DB
            participant = await self._get_or_create_participant(
                organization_id=organization_id,
                full_name=identity_name,
                custom_id=f"id-{id_dir.name}",
            )

            # 3. Process identity images
            for idx, img_path in enumerate(shuffled_files):
                report.total_images += 1
                partition = "gallery" if idx < gallery_size_per_identity else "probe"

                try:
                    raw_bytes = img_path.read_bytes()
                except Exception as e:
                    report.corrupted_image_count += 1
                    report.rejected_images += 1
                    report.errors.append(f"Cannot read {img_path.name}: {e}")
                    continue

                # Validate image
                try:
                    meta = ImageValidationService.validate_and_sanitize(raw_bytes, filename=img_path.name)
                except ImageValidationError as val_err:
                    report.corrupted_image_count += 1
                    report.rejected_images += 1
                    report.errors.append(f"Validation failed for {img_path.name}: {val_err}")
                    continue

                # Check duplicates
                if meta.sha256 in seen_sha256:
                    report.duplicate_count += 1
                    report.rejected_images += 1
                    continue
                seen_sha256.add(meta.sha256)

                # Face Detection & Quality Validation
                det = face_detection_service.detect_and_validate(raw_bytes)
                if not det.is_valid:
                    report.rejected_images += 1
                    if det.status == FaceValidationStatus.NO_FACE:
                        report.zero_face_count += 1
                    elif det.status == FaceValidationStatus.MULTIPLE_FACES:
                        report.multi_face_count += 1
                    elif det.status == FaceValidationStatus.POOR_QUALITY:
                        report.quality_rejection_count += 1
                    continue

                report.accepted_images += 1
                if partition == "gallery":
                    report.gallery_image_count += 1
                else:
                    report.probe_image_count += 1

                # Generate Local ArcFace 512-d Embedding
                try:
                    aligned_arr = det.primary_face.aligned_crop if det.primary_face else None
                    if aligned_arr is not None:
                        embedding_vec = face_embedding_service.embed_aligned_face(aligned_arr)
                    else:
                        embedding_vec = face_embedding_service.embed(raw_bytes)
                    report.embedding_success_count += 1
                except Exception as emb_err:
                    report.embedding_failure_count += 1
                    logger.error(f"Embedding failed for {img_path.name}: {emb_err}")
                    embedding_vec = None

                # Save ParticipantImage record
                image_id = uuid.uuid4()
                p_img = ParticipantImage(
                    id=image_id,
                    participant_id=participant.id,
                    organization_id=organization_id,
                    storage_key=meta.storage_filename,
                    mime_type=meta.mime_type,
                    file_size_bytes=meta.size_bytes,
                    sha256=meta.sha256,
                    phash=meta.phash,
                    dhash=meta.dhash,
                    width=meta.width,
                    height=meta.height,
                    index_status=ImageIndexStatus.INDEXED if embedding_vec else ImageIndexStatus.PENDING,
                )
                self.session.add(p_img)

                # Index in Qdrant vector database
                if embedding_vec:
                    try:
                        await qdrant_service.upsert_face_embedding(
                            vector=embedding_vec,
                            organization_id=organization_id,
                            participant_id=participant.id,
                            image_id=image_id,
                            model_name=face_embedding_service.model_name,
                            model_version=face_embedding_service.model_version,
                            metadata={
                                "partition": partition,
                                "original_filename": img_path.name,
                                "identity_name": identity_name,
                            },
                        )
                        report.indexed_vectors += 1
                    except Exception as q_err:
                        logger.error(f"Qdrant indexing failed for {img_path.name}: {q_err}")

        await self.session.commit()

        logger.info(
            f"LFW Ingestion complete for '{dataset_name}': {report.accepted_images}/{report.total_images} accepted, "
            f"{report.indexed_vectors} vectors indexed in Qdrant."
        )
        return report

    # ── 2. ZIP Archive Ingestion ─────────────────────────────────────────────

    async def ingest_zip_dataset(
        self,
        zip_path: str | Path,
        organization_id: uuid.UUID,
        dataset_name: str = "ZIP Dataset",
        user_id: uuid.UUID | None = None,
        extract_to_dir: str | Path | None = None,
    ) -> DatasetHealthReport:
        """Extract and ingest a ZIP archive containing LFW or identity folders."""
        z_path = Path(zip_path).resolve()
        if not z_path.exists() or not z_path.is_file():
            raise FileNotFoundError(f"ZIP archive not found: {z_path}")

        target_dir = Path(extract_to_dir or f"/tmp/cyberhub_extract_{uuid.uuid4().hex[:8]}")
        target_dir.mkdir(parents=True, exist_ok=True)

        with zipfile.ZipFile(z_path, "r") as z:
            z.extractall(target_dir)

        # Check if extracted dir has a subfolder or directly identity folders
        subdirs = [d for d in target_dir.iterdir() if d.is_dir() and not d.name.startswith("__")]
        search_root = target_dir
        if len(subdirs) == 1 and not any((target_dir / f).is_file() for f in target_dir.iterdir()):
            search_root = subdirs[0]

        return await self.ingest_lfw_directory(
            dataset_dir=search_root,
            organization_id=organization_id,
            dataset_name=dataset_name,
            user_id=user_id,
        )

    # ── 3. Controlled 4-CSV Directory Ingestion ──────────────────────────────

    async def ingest_dataset_directory(
        self,
        dataset_dir: str | Path,
        organization_id: uuid.UUID,
        auto_index_aws: bool = False,
    ) -> ControlledDatasetIngestionReport:
        """Ingest a controlled dataset folder with participants.csv, consent_records.csv, public_sources.csv, images.csv."""
        d_path = Path(dataset_dir).resolve()
        report = ControlledDatasetIngestionReport()

        # 1. participants.csv
        p_file = d_path / "participants.csv"
        code_to_participant: dict[str, Participant] = {}
        if p_file.exists():
            with open(p_file, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    code = row.get("participant_code") or row.get("code")
                    name = row.get("display_name") or row.get("name") or code
                    notes = row.get("notes")
                    if code:
                        p = await self.participant_service.create_participant(
                            organization_id=organization_id,
                            display_name=name,
                            participant_code=code,
                            notes=notes,
                        )
                        code_to_participant[code] = p
                        report.participants_created += 1

        # 2. consent_records.csv
        c_file = d_path / "consent_records.csv"
        if c_file.exists():
            with open(c_file, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    code = row.get("participant_code")
                    status = (row.get("consent_status") or "").upper()
                    method = row.get("consent_method") or "CSV_INGESTION"
                    notes = row.get("notes")
                    p = code_to_participant.get(code)
                    if p:
                        if status == "CONSENTED":
                            await self.participant_service.grant_consent(
                                participant_id=p.id,
                                organization_id=organization_id,
                                method=method,
                            )
                        report.consents_recorded += 1

        # 3. public_sources.csv
        s_file = d_path / "public_sources.csv"
        if s_file.exists():
            with open(s_file, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    code = row.get("participant_code")
                    platform = row.get("platform") or "web"
                    url = row.get("url")
                    confirmed = str(row.get("participant_confirmed", "false")).lower() in ("true", "1", "yes")
                    p = code_to_participant.get(code)
                    if p and url:
                        await self.participant_service.add_public_source(
                            participant_id=p.id,
                            organization_id=organization_id,
                            platform=platform,
                            url=url,
                            participant_confirmed=confirmed,
                        )
                        report.sources_ingested += 1

        # 4. images.csv
        i_file = d_path / "images.csv"
        images_dir = d_path / "images"
        if i_file.exists():
            with open(i_file, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    code = row.get("participant_code")
                    img_name = row.get("image_file") or row.get("filename")
                    p = code_to_participant.get(code)
                    if not p:
                        report.images_skipped += 1
                        continue

                    # Consent check
                    stmt = select(Participant).where(Participant.id == p.id)
                    cur_p = (await self.session.execute(stmt)).scalar_one_or_none()
                    if not cur_p or cur_p.consent_status != ConsentStatus.CONSENTED:
                        report.images_skipped += 1
                        continue

                    img_path = images_dir / img_name if img_name else None
                    if img_path and img_path.exists():
                        try:
                            await self.participant_service.add_participant_image(
                                participant_id=p.id,
                                organization_id=organization_id,
                                image_data=img_path.read_bytes(),
                                original_filename=img_name,
                            )
                            report.images_ingested += 1
                        except Exception as e:
                            logger.error(f"Image upload failed for {img_name}: {e}")
                            report.images_skipped += 1
                    else:
                        report.images_skipped += 1

        return report

    # ── Helper Methods ───────────────────────────────────────────────────────

    async def _get_or_create_participant(
        self,
        organization_id: uuid.UUID,
        full_name: str,
        custom_id: str,
    ) -> Participant:
        """Find existing participant or create a new consented identity."""
        stmt = select(Participant).where(
            Participant.organization_id == organization_id,
            Participant.participant_code == custom_id,
        )
        result = await self.session.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            return existing

        now = datetime.now(timezone.utc)
        new_participant = Participant(
            id=uuid.uuid4(),
            organization_id=organization_id,
            participant_code=custom_id,
            display_name=full_name,
            is_active=True,
            consent_status=ConsentStatus.CONSENTED,
            consent_timestamp=now,
        )
        self.session.add(new_participant)
        await self.session.flush()

        # Add active consent record
        consent = ParticipantConsent(
            id=uuid.uuid4(),
            participant_id=new_participant.id,
            organization_id=organization_id,
            consent_status=ConsentStatus.CONSENTED,
            consent_timestamp=now,
            consent_method="DATASET_INGESTION",
        )
        self.session.add(consent)
        await self.session.flush()

        return new_participant


ControlledDatasetIngestionService = DatasetIngestionService
