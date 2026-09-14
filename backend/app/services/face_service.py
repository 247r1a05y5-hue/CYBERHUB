"""Face detection, quality analysis, and biometric embedding abstraction."""
from __future__ import annotations

import abc
import hashlib
import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditAction
from app.models.biometrics import FaceEmbedding, FaceRecord, FaceValidationStatus, ReferenceImage
from app.services.audit_service import AuditService


@dataclass
class FaceDetectionResult:
    face_count: int
    bounding_box: dict[str, Any]
    landmarks: dict[str, Any]
    quality_score: float
    status: FaceValidationStatus
    is_valid: bool
    embedding_vector: list[float] | None = None  # Kept in memory, never returned to client


class FaceDetector(abc.ABC):
    @abc.abstractmethod
    def detect_and_validate(self, image_bytes: bytes) -> FaceDetectionResult:
        """Detect faces and compute quality."""


class MockFaceDetector(FaceDetector):
    """Clean mock face detector with deterministic states for tests and demo mode."""

    def detect_and_validate(self, image_bytes: bytes) -> FaceDetectionResult:
        # Check for simulated test triggers
        img_len = len(image_bytes)
        img_hash = hashlib.sha256(image_bytes).hexdigest()

        if b"TRIGGER_NO_FACE" in image_bytes or (img_len < 10 and b"MOCK" not in image_bytes):
            return FaceDetectionResult(
                face_count=0,
                bounding_box={},
                landmarks={},
                quality_score=0.0,
                status=FaceValidationStatus.NO_FACE,
                is_valid=False,
            )

        if b"TRIGGER_MULTIPLE_FACES" in image_bytes:
            return FaceDetectionResult(
                face_count=3,
                bounding_box={"x": 100, "y": 80, "w": 200, "h": 220},
                landmarks={"left_eye": [130, 120], "right_eye": [220, 120]},
                quality_score=0.78,
                status=FaceValidationStatus.MULTIPLE_FACES,
                is_valid=False,
            )

        if b"TRIGGER_POOR_QUALITY" in image_bytes:
            return FaceDetectionResult(
                face_count=1,
                bounding_box={"x": 120, "y": 90, "w": 180, "h": 190},
                landmarks={"left_eye": [140, 130], "right_eye": [210, 130]},
                quality_score=0.32,
                status=FaceValidationStatus.POOR_QUALITY,
                is_valid=False,
            )

        # Standard valid detection
        # Deterministic 512-d mock vector based on sha256
        seed_ints = [int(img_hash[i : i + 2], 16) / 255.0 for i in range(0, 64, 2)]
        mock_embedding = (seed_ints * 16)[:512]

        return FaceDetectionResult(
            face_count=1,
            bounding_box={"x": 150, "y": 100, "w": 240, "h": 260},
            landmarks={
                "left_eye": [190, 180],
                "right_eye": [290, 180],
                "nose": [240, 220],
                "mouth_left": [200, 280],
                "mouth_right": [280, 280],
            },
            quality_score=0.94,
            status=FaceValidationStatus.VALID,
            is_valid=True,
            embedding_vector=mock_embedding,
        )


class FaceValidationService:
    """Service to process camera capture uploads, detect faces, validate quality, and save biometrics."""

    def __init__(self, session: AsyncSession, detector: FaceDetector | None = None):
        self.session = session
        self.detector = detector or MockFaceDetector()
        self.audit_service = AuditService(session)

    async def process_capture(
        self,
        case_id: uuid.UUID,
        image_bytes: bytes,
        image_url: str,
        user_id: uuid.UUID | None = None,
        organization_id: uuid.UUID | None = None,
    ) -> tuple[ReferenceImage, FaceRecord]:
        """Validate face in captured image and record reference photo & biometrics."""
        sha256_hash = hashlib.sha256(image_bytes).hexdigest()

        # Run face detection & validation
        det_result = self.detector.detect_and_validate(image_bytes)

        # Save ReferenceImage
        ref_image = ReferenceImage(
            case_id=case_id,
            image_url=image_url,
            sha256_hash=sha256_hash,
            size_bytes=len(image_bytes),
            quality_score=det_result.quality_score,
            is_primary=True,
        )
        self.session.add(ref_image)
        await self.session.flush()

        # Save FaceRecord
        face_record = FaceRecord(
            case_id=case_id,
            reference_image_id=ref_image.id,
            bounding_box=det_result.bounding_box,
            landmarks=det_result.landmarks,
            quality_score=det_result.quality_score,
            face_count=det_result.face_count,
            is_valid=det_result.is_valid,
            validation_status=det_result.status,
        )
        self.session.add(face_record)
        await self.session.flush()

        # Store FaceEmbedding in dedicated table (Decoupled, never sent over wire)
        if det_result.is_valid and det_result.embedding_vector:
            vector_id = f"vec-{face_record.id}"
            face_embedding = FaceEmbedding(
                face_record_id=face_record.id,
                vector_id=vector_id,
                algorithm="ArcFace-r100",
                dimension=len(det_result.embedding_vector),
            )
            self.session.add(face_embedding)
            await self.session.flush()

        # Audit sensitive capture & validation
        await self.audit_service.log(
            action=AuditAction.face_validated,
            user_id=user_id,
            organization_id=organization_id,
            resource_type="case",
            resource_id=str(case_id),
            details={
                "quality_score": det_result.quality_score,
                "face_count": det_result.face_count,
                "is_valid": det_result.is_valid,
                "status": det_result.status.value,
                "reference_image_id": str(ref_image.id),
            },
        )

        return ref_image, face_record
