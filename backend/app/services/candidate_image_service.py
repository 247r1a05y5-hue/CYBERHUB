"""Candidate Image Download, Validation, and Hashing Service.

Pipeline per candidate image:
1. SSRF-safe bounded fetch (rejecting internal/loopback IPs & redirect-to-private attacks)
2. HTTP status, Content-Type, and magic-byte signature validation (rejects HTML disguised as JPEG)
3. PIL safe decoding: min/max dimensions & decompression bomb limits
4. Cryptographic SHA-256 and perceptual pHash / dHash generation
5. Face detection and quality inspection (recording face_count & has_usable_face)
6. Secure storage preservation and CandidateImage DB persistence
"""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.investigation_record import CandidateImage
from app.services.face_detection_service import face_detection_service
from app.services.image_validation_service import ImageValidationError, ImageValidationService, image_validation_service
from app.services.secure_storage_service import secure_storage_service
from app.services.ssrf_safe_fetcher import EvidenceCaptureSecurityError, SafeFetchResult, secure_url_fetcher

logger = logging.getLogger(__name__)


@dataclass
class ProcessedCandidateImage:
    candidate_image: CandidateImage
    raw_bytes: bytes
    is_valid: bool
    rejection_reason: str | None = None


class CandidateImageService:
    """Safely downloads, decodes, hashes, and indexes candidate images."""

    async def download_and_process(
        self,
        session: AsyncSession,
        page_investigation_id: uuid.UUID,
        case_id: uuid.UUID,
        organization_id: uuid.UUID,
        image_url: str,
    ) -> ProcessedCandidateImage:
        """Download candidate image, validate headers/pixels, compute hashes, and persist DB record."""
        # 1. SSRF-safe download
        try:
            fetch_res: SafeFetchResult = await secure_url_fetcher.fetch(
                image_url,
                max_size=settings.MAX_IMAGE_BYTES,
                check_robots=False,
            )
        except Exception as fetch_err:
            logger.debug(f"Failed to fetch candidate image '{image_url}': {fetch_err}")
            return ProcessedCandidateImage(
                candidate_image=None,  # type: ignore
                raw_bytes=b"",
                is_valid=False,
                rejection_reason=f"DOWNLOAD_FAILED: {fetch_err}",
            )

        # 2. Strict validation & sanitization (magic bytes, dimensions, decompression limit)
        try:
            val_meta = image_validation_service.validate_and_sanitize(
                file_bytes=fetch_res.raw_bytes,
                max_size=settings.MAX_IMAGE_BYTES,
            )
        except Exception as val_err:
            logger.debug(f"Image validation failed for '{image_url}': {val_err}")
            return ProcessedCandidateImage(
                candidate_image=None,  # type: ignore
                raw_bytes=b"",
                is_valid=False,
                rejection_reason=f"VALIDATION_FAILED: {val_err}",
            )

        # 3. Face detection and quality inspection
        det_result = face_detection_service.detect_and_validate(fetch_res.raw_bytes)
        face_count = det_result.face_count
        has_usable_face = det_result.is_valid and det_result.primary_face is not None

        # 4. Save image payload securely
        storage_key = None
        try:
            storage_key = await secure_storage_service.save_file(
                file_bytes=fetch_res.raw_bytes,
                filename=val_meta.storage_filename,
            )
        except Exception as st_err:
            logger.warning(f"Failed to store candidate image to disk: {st_err}")

        # 5. Persist CandidateImage record
        cand_img = CandidateImage(
            page_investigation_id=page_investigation_id,
            organization_id=organization_id,
            case_id=case_id,
            original_image_url=image_url,
            final_image_url=fetch_res.final_url,
            storage_key=storage_key or val_meta.storage_filename,
            sha256_hash=val_meta.sha256,
            phash=val_meta.phash,
            dhash=val_meta.dhash,
            mime_type=val_meta.mime_type,
            width=val_meta.width,
            height=val_meta.height,
            size_bytes=val_meta.size_bytes,
            face_count=face_count,
            has_usable_face=has_usable_face,
        )

        session.add(cand_img)
        await session.flush()

        return ProcessedCandidateImage(
            candidate_image=cand_img,
            raw_bytes=fetch_res.raw_bytes,
            is_valid=True,
        )


candidate_image_service = CandidateImageService()
