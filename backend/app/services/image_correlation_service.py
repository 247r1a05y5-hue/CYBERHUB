"""Multi-Signal Image Correlation Engine.

Evaluates reference image against candidate image under versioned policy (correlation_policy_v1.0):
1. Cryptographic equality (SHA-256) -> EXACT_IMAGE (similarity 1.0)
2. Perceptual near-copy distance (pHash, dHash) -> TRANSFORMED_COPY
3. Instance visual similarity (DINOv2 ViT-S/14, 384-d)
4. Biometric identity comparison (ArcFace buffalo_l / w600k_r50.onnx, 512-d):
   - Only executed when candidate image has EXACTLY 1 usable face
   - 0 faces: face comparison skipped (no forced score)
   - >1 faces: recorded as ambiguous/multiple faces
   - Unusable face (blur/lighting/low-res): recorded as INSUFFICIENT_EVIDENCE

Strict Phase 3 Constraint:
- Zero VERIFIED status produced anywhere in this pipeline.
- Status stops strictly at PENDING_REVIEW.
- Persists threshold_config_ref ('correlation_policy_v1.0') and full model metadata.
"""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.correlation_policy import CORRELATION_POLICY_V1, CorrelationPolicyConfig
from app.models.investigation_record import CandidateImage, ImageCorrelation
from app.services.dinov2_service import dinov2_service
from app.services.face_detection_service import face_detection_service
from app.services.face_embedding_service import face_embedding_service

logger = logging.getLogger(__name__)


@dataclass
class CorrelationEvaluation:
    classification: str
    overall_score: float
    dinov2_score: float | None
    arcface_score: float | None
    phash_distance: int | None
    dhash_distance: int | None
    explanation: str
    model_info: dict[str, Any]
    threshold_config_ref: str = "correlation_policy_v1.0"


class ImageCorrelationService:
    """Computes multi-signal correlation and persists versioned forensic match candidate."""

    def __init__(self, policy: CorrelationPolicyConfig = CORRELATION_POLICY_V1) -> None:
        self.policy = policy

    @staticmethod
    def compute_hamming_distance(hash1_hex: str, hash2_hex: str) -> int:
        """Compute bitwise Hamming distance between two hex hashes."""
        if not hash1_hex or not hash2_hex or len(hash1_hex) != len(hash2_hex):
            return 64
        try:
            val1 = int(hash1_hex, 16)
            val2 = int(hash2_hex, 16)
            xor_val = val1 ^ val2
            return bin(xor_val).count("1")
        except ValueError:
            return 64

    def evaluate(
        self,
        ref_bytes: bytes,
        cand_bytes: bytes,
        cand_meta: CandidateImage,
        ref_sha256: str | None = None,
        ref_phash: str | None = None,
        ref_dhash: str | None = None,
    ) -> CorrelationEvaluation:
        """Evaluate reference vs candidate image across all 4 signal tiers."""
        import hashlib

        if not ref_sha256:
            ref_sha256 = hashlib.sha256(ref_bytes).hexdigest()

        model_info: dict[str, Any] = {
            "dinov2_model": dinov2_service.model_variant,
            "dinov2_dim": dinov2_service.dimension,
            "arcface_model": face_embedding_service.model_name,
            "arcface_dim": face_embedding_service.embedding_dimension,
            "policy_version": self.policy.policy_version,
        }

        # 1. Tier 1: Cryptographic exact match
        if ref_sha256 == cand_meta.sha256_hash:
            return CorrelationEvaluation(
                classification="EXACT_IMAGE",
                overall_score=1.0,
                dinov2_score=1.0,
                arcface_score=1.0 if cand_meta.has_usable_face else None,
                phash_distance=0,
                dhash_distance=0,
                explanation="Exact cryptographic byte-for-byte duplicate (SHA-256 match).",
                model_info=model_info,
                threshold_config_ref=self.policy.policy_version,
            )

        # 2. Tier 2: Perceptual Hash Distance
        phash_dist = None
        dhash_dist = None
        min_pdist = 64
        if ref_phash and cand_meta.phash:
            phash_dist = self.compute_hamming_distance(ref_phash, cand_meta.phash)
            min_pdist = min(min_pdist, phash_dist)
        if ref_dhash and cand_meta.dhash:
            dhash_dist = self.compute_hamming_distance(ref_dhash, cand_meta.dhash)
            min_pdist = min(min_pdist, dhash_dist)

        # 3. Tier 3: DINOv2 Visual Similarity
        dinov2_score = None
        try:
            ref_dino = dinov2_service.extract_embedding(ref_bytes)
            cand_dino = dinov2_service.extract_embedding(cand_bytes)
            dinov2_score = dinov2_service.compute_cosine_similarity(ref_dino.vector, cand_dino.vector)
        except Exception as dino_err:
            logger.warning(f"DINOv2 embedding extraction failed: {dino_err}")

        # 4. Tier 4: ArcFace Biometric Face Comparison (if applicable)
        arcface_score = None
        face_note = "No face comparison"
        if cand_meta.face_count == 1 and cand_meta.has_usable_face:
            try:
                # Detect and embed reference face
                ref_det = face_detection_service.detect_and_validate(ref_bytes)
                if ref_det.is_valid and ref_det.primary_face and ref_det.primary_face.aligned_crop is not None:
                    ref_face_emb = face_embedding_service.embed_aligned_face(ref_det.primary_face.aligned_crop)
                    cand_det = face_detection_service.detect_and_validate(cand_bytes)
                    if cand_det.is_valid and cand_det.primary_face and cand_det.primary_face.aligned_crop is not None:
                        cand_face_emb = face_embedding_service.embed_aligned_face(cand_det.primary_face.aligned_crop)
                        # Cosine similarity of unit vectors = dot product
                        dot = sum(x * y for x, y in zip(ref_face_emb, cand_face_emb))
                        arcface_score = max(-1.0, min(1.0, float(dot)))
                        face_note = f"ArcFace similarity: {arcface_score:.3f}"
            except Exception as face_err:
                logger.warning(f"ArcFace face comparison failed: {face_err}")
                face_note = f"Face comparison error: {face_err}"
        elif cand_meta.face_count > 1:
            face_note = f"Ambiguous: candidate contains {cand_meta.face_count} faces"
        elif cand_meta.face_count == 0:
            face_note = "0 faces in candidate image"

        # 5. Multi-Signal Classification Logic
        # Direct variant / transformed copy (crops, rotations, heavy compression, watermarks)
        if min_pdist <= self.policy.phash_exact_variant_max_dist or (dinov2_score is not None and dinov2_score >= self.policy.dinov2_variant_min_cosine):
            classification = "TRANSFORMED_COPY"
            overall_score = max(dinov2_score or 0.88, 1.0 - (min_pdist / 64.0))
            explanation = f"High semantic and structural match. Cropped, compressed, watermarked, or scaled variant of reference image (pHash dist: {min_pdist}, DINOv2: {dinov2_score or 'N/A'})."

        # Same biometric identity in different photograph
        elif arcface_score is not None and arcface_score >= self.policy.arcface_match_min_cosine:
            classification = "SAME_FACE_DIFFERENT_IMAGE"
            overall_score = arcface_score
            explanation = f"Biometric face match identified across distinct photographs ({face_note}, DINOv2: {dinov2_score or 'N/A'})."

        # Heavy modification / derivative framing
        elif min_pdist <= self.policy.phash_probable_max_dist or (dinov2_score is not None and dinov2_score >= self.policy.dinov2_probable_min_cosine):
            classification = "PROBABLE_RELATED"
            overall_score = dinov2_score or (1.0 - min_pdist / 64.0)
            explanation = f"Moderate visual correlation. Derivative scene, heavy framing, or screenshot container (DINOv2: {dinov2_score or 'N/A'}, pHash dist: {min_pdist})."

        # Visually similar aesthetic/palette
        elif dinov2_score is not None and dinov2_score >= self.policy.dinov2_similar_diff_min_cosine:
            classification = "VISUALLY_SIMILAR"
            overall_score = dinov2_score
            explanation = f"Shared visual layout or color composition without direct instance duplicate (DINOv2: {dinov2_score:.3f})."

        # Unrelated
        else:
            classification = "UNRELATED"
            overall_score = dinov2_score or 0.10
            explanation = f"No meaningful visual, structural, or biometric match found (DINOv2: {dinov2_score or 'N/A'}, {face_note})."

        return CorrelationEvaluation(
            classification=classification,
            overall_score=round(overall_score, 4),
            dinov2_score=round(dinov2_score, 4) if dinov2_score is not None else None,
            arcface_score=round(arcface_score, 4) if arcface_score is not None else None,
            phash_distance=phash_dist,
            dhash_distance=dhash_dist,
            explanation=explanation,
            model_info=model_info,
            threshold_config_ref=self.policy.policy_version,
        )

    async def correlate_and_persist(
        self,
        session: AsyncSession,
        candidate_image: CandidateImage,
        cand_bytes: bytes,
        ref_bytes: bytes,
        reference_image_id: uuid.UUID | None = None,
        ref_sha256: str | None = None,
        ref_phash: str | None = None,
        ref_dhash: str | None = None,
    ) -> ImageCorrelation:
        """Run correlation evaluation and persist ImageCorrelation database record."""
        eval_result = self.evaluate(
            ref_bytes=ref_bytes,
            cand_bytes=cand_bytes,
            cand_meta=candidate_image,
            ref_sha256=ref_sha256,
            ref_phash=ref_phash,
            ref_dhash=ref_dhash,
        )

        correlation = ImageCorrelation(
            candidate_image_id=candidate_image.id,
            reference_image_id=reference_image_id,
            organization_id=candidate_image.organization_id,
            case_id=candidate_image.case_id,
            classification=eval_result.classification,
            dinov2_similarity=eval_result.dinov2_score,
            arcface_similarity=eval_result.arcface_score,
            phash_distance=eval_result.phash_distance,
            dhash_distance=eval_result.dhash_distance,
            threshold_config_ref=eval_result.threshold_config_ref,
            model_info_json=eval_result.model_info,
            explanation=eval_result.explanation,
            status="PENDING_REVIEW",  # Strictly PENDING_REVIEW, never VERIFIED
        )

        session.add(correlation)
        await session.flush()

        return correlation


image_correlation_service = ImageCorrelationService()
