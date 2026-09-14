"""Tiered Image Matching Engine & Candidate Classifier (Phase 3 Calibrated).

Evaluation Hierarchy:
- Tier 1: SHA-256 Exact Byte Comparison
- Tier 2: pHash / dHash Perceptual Hamming Distance
- Tier 3: DINOv2 Embedding Cosine Similarity (dinov2_vits14)

Candidate Classifications (Locked to 5 Categories):
- EXACT
- SAME_TRANSFORMED_IMAGE
- PROBABLE_RELATED
- VISUALLY_SIMILAR
- UNRELATED

All thresholds are calibrated directly against the 15-transform synthetic benchmark corpus.
"""
from __future__ import annotations

import enum
from dataclasses import dataclass
from typing import Any

from app.services.dinov2_service import dinov2_service
from app.services.image_analysis_service import image_analysis_service


class MatchClassification(str, enum.Enum):
    """Categorical classification of candidate similarity (5 locked categories)."""
    EXACT = "EXACT"
    SAME_TRANSFORMED_IMAGE = "SAME_TRANSFORMED_IMAGE"
    PROBABLE_RELATED = "PROBABLE_RELATED"
    VISUALLY_SIMILAR = "VISUALLY_SIMILAR"
    UNRELATED = "UNRELATED"

    # Backwards compatibility aliases for older unit references
    EXACT_SAME_FILE = "EXACT"
    SAME_IMAGE_TRANSFORMED_VARIANT = "SAME_TRANSFORMED_IMAGE"
    PROBABLE_RELATED_IMAGE = "PROBABLE_RELATED"
    VISUALLY_SIMILAR_BUT_DIFFERENT = "VISUALLY_SIMILAR"


@dataclass(frozen=True)
class MatchingThresholds:
    """Threshold parameters calibrated against the 15-transform benchmark corpus."""
    # Tier 2: Perceptual Hamming Distance (out of 64 bits)
    phash_exact_variant_max_dist: int = 8
    phash_probable_max_dist: int = 18

    # Tier 3: DINOv2 Cosine Similarity
    dinov2_variant_min_cosine: float = 0.88
    dinov2_probable_min_cosine: float = 0.72
    dinov2_similar_diff_min_cosine: float = 0.55


@dataclass(frozen=True)
class MatchEvaluationResult:
    """Detailed multi-tier match evaluation output."""
    classification: MatchClassification
    overall_similarity_score: float
    tier_applied: int  # 1, 2, or 3
    is_byte_exact: bool
    phash_distance: int | None
    dhash_distance: int | None
    dinov2_cosine_similarity: float | None
    explanation: str
    signals: dict[str, Any]


class ImageMatchingService:
    """Evaluates candidates against reference images using 3-tier calibrated pipeline."""

    def __init__(self, thresholds: MatchingThresholds | None = None) -> None:
        self.thresholds = thresholds or MatchingThresholds()

    def evaluate_match(
        self,
        reference_sha256: str,
        candidate_sha256: str | None = None,
        reference_phash: str | None = None,
        candidate_phash: str | None = None,
        reference_dhash: str | None = None,
        candidate_dhash: str | None = None,
        reference_vector: list[float] | None = None,
        candidate_vector: list[float] | None = None,
    ) -> MatchEvaluationResult:
        """Run tiered evaluation on reference vs candidate image features."""

        # -------------------------------------------------------------
        # TIER 1: SHA-256 Exact Byte Comparison
        # -------------------------------------------------------------
        if candidate_sha256 and reference_sha256.lower() == candidate_sha256.lower():
            return MatchEvaluationResult(
                classification=MatchClassification.EXACT,
                overall_similarity_score=1.0,
                tier_applied=1,
                is_byte_exact=True,
                phash_distance=0,
                dhash_distance=0,
                dinov2_cosine_similarity=1.0,
                explanation="Exact cryptographic byte-for-byte duplicate.",
                signals={"tier": "TIER_1_SHA256", "sha256": candidate_sha256},
            )

        # Calculate perceptual hash distances if available
        phash_dist = None
        dhash_dist = None
        if reference_phash and candidate_phash:
            phash_dist = image_analysis_service.calculate_hamming_distance(reference_phash, candidate_phash)
        if reference_dhash and candidate_dhash:
            dhash_dist = image_analysis_service.calculate_hamming_distance(reference_dhash, candidate_dhash)

        # Calculate DINOv2 cosine similarity if vectors available
        dinov2_sim = None
        if reference_vector and candidate_vector:
            dinov2_sim = dinov2_service.compute_cosine_similarity(reference_vector, candidate_vector)

        # -------------------------------------------------------------
        # TIER 2: Perceptual Hashes (pHash & dHash)
        # -------------------------------------------------------------
        min_pdist = phash_dist if phash_dist is not None else dhash_dist
        if phash_dist is not None and dhash_dist is not None:
            min_pdist = min(phash_dist, dhash_dist)

        # -------------------------------------------------------------
        # TIER 3: DINOv2 Embedding Similarity & Combined Scoring
        # -------------------------------------------------------------
        if dinov2_sim is not None:
            # Check for high instance match (Same Transformed Image)
            if dinov2_sim >= self.thresholds.dinov2_variant_min_cosine or (
                min_pdist is not None and min_pdist <= self.thresholds.phash_exact_variant_max_dist
            ):
                score = round(max(dinov2_sim, 1.0 - (min_pdist / 64.0) if min_pdist is not None else dinov2_sim), 4)
                return MatchEvaluationResult(
                    classification=MatchClassification.SAME_TRANSFORMED_IMAGE,
                    overall_similarity_score=score,
                    tier_applied=3 if dinov2_sim >= self.thresholds.dinov2_variant_min_cosine else 2,
                    is_byte_exact=False,
                    phash_distance=phash_dist,
                    dhash_distance=dhash_dist,
                    dinov2_cosine_similarity=dinov2_sim,
                    explanation="Transformed variant of the reference image (crop, compression, watermark, or rotation).",
                    signals={"dinov2_cosine": dinov2_sim, "phash_distance": phash_dist, "dhash_distance": dhash_dist},
                )
            elif dinov2_sim >= self.thresholds.dinov2_probable_min_cosine or (
                min_pdist is not None and min_pdist <= self.thresholds.phash_probable_max_dist
            ):
                score = round(dinov2_sim, 4)
                return MatchEvaluationResult(
                    classification=MatchClassification.PROBABLE_RELATED,
                    overall_similarity_score=score,
                    tier_applied=3,
                    is_byte_exact=False,
                    phash_distance=phash_dist,
                    dhash_distance=dhash_dist,
                    dinov2_cosine_similarity=dinov2_sim,
                    explanation="Probable related image with structural or contextual similarity.",
                    signals={"dinov2_cosine": dinov2_sim, "phash_distance": phash_dist, "dhash_distance": dhash_dist},
                )
            elif dinov2_sim >= self.thresholds.dinov2_similar_diff_min_cosine:
                return MatchEvaluationResult(
                    classification=MatchClassification.VISUALLY_SIMILAR,
                    overall_similarity_score=round(dinov2_sim, 4),
                    tier_applied=3,
                    is_byte_exact=False,
                    phash_distance=phash_dist,
                    dhash_distance=dhash_dist,
                    dinov2_cosine_similarity=dinov2_sim,
                    explanation="Visually similar composition or palette without shared instance identity.",
                    signals={"dinov2_cosine": dinov2_sim, "phash_distance": phash_dist, "dhash_distance": dhash_dist},
                )
            else:
                return MatchEvaluationResult(
                    classification=MatchClassification.UNRELATED,
                    overall_similarity_score=round(dinov2_sim, 4),
                    tier_applied=3,
                    is_byte_exact=False,
                    phash_distance=phash_dist,
                    dhash_distance=dhash_dist,
                    dinov2_cosine_similarity=dinov2_sim,
                    explanation="Unrelated image with no meaningful structural match.",
                    signals={"dinov2_cosine": dinov2_sim},
                )

        # Fallback when only perceptual hashes are present (e.g. Qdrant degradation mode)
        if min_pdist is not None:
            if min_pdist <= self.thresholds.phash_exact_variant_max_dist:
                sim = round(1.0 - (min_pdist / 64.0), 4)
                return MatchEvaluationResult(
                    classification=MatchClassification.SAME_TRANSFORMED_IMAGE,
                    overall_similarity_score=sim,
                    tier_applied=2,
                    is_byte_exact=False,
                    phash_distance=phash_dist,
                    dhash_distance=dhash_dist,
                    dinov2_cosine_similarity=None,
                    explanation="Perceptual hash match (distance within exact transformation bounds).",
                    signals={"phash_distance": phash_dist, "dhash_distance": dhash_dist},
                )
            elif min_pdist <= self.thresholds.phash_probable_max_dist:
                sim = round(1.0 - (min_pdist / 64.0), 4)
                return MatchEvaluationResult(
                    classification=MatchClassification.PROBABLE_RELATED,
                    overall_similarity_score=sim,
                    tier_applied=2,
                    is_byte_exact=False,
                    phash_distance=phash_dist,
                    dhash_distance=dhash_dist,
                    dinov2_cosine_similarity=None,
                    explanation="Moderate perceptual correlation.",
                    signals={"phash_distance": phash_dist, "dhash_distance": dhash_dist},
                )

        return MatchEvaluationResult(
            classification=MatchClassification.UNRELATED,
            overall_similarity_score=0.0,
            tier_applied=0,
            is_byte_exact=False,
            phash_distance=phash_dist,
            dhash_distance=dhash_dist,
            dinov2_cosine_similarity=None,
            explanation="Insufficient matching signals.",
            signals={},
        )


image_matching_service = ImageMatchingService()
