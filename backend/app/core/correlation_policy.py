"""Versioned Correlation Policy Configuration.

Encapsulates empirical and calibrated decision thresholds for:
- Tier 1: Cryptographic exact match (SHA-256)
- Tier 2: Perceptual near-copy distance (pHash, dHash)
- Tier 3: Instance visual similarity (DINOv2 Small ViT-14)
- Tier 4: Biometric face verification (InsightFace ArcFace 512-d)

Threshold references:
- ArcFace thresholds are calibrated directly against Phase 1 dataset matching specs.
- DINOv2 and pHash/dHash thresholds are calibrated against the 15-transform empirical benchmark.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CorrelationPolicyConfig:
    """Versioned immutable matching and correlation policy."""
    policy_version: str = "correlation_policy_v1.0"

    # Tier 1: Exact Cryptographic Byte Match
    exact_sha256_score: float = 1.0

    # Tier 2: Perceptual Hamming Distance (out of 64 bits)
    # Calibrated against 15-transform benchmark (crops <= 6, watermarks <= 5, rotations <= 7)
    phash_exact_variant_max_dist: int = 8
    # Captures heavy framing / screenshots
    phash_probable_max_dist: int = 18

    # Tier 3: DINOv2 Cosine Similarity (384-dimensional, L2 normalized)
    # Calibrated: direct variants >= 0.9504 -> 0.88 safe margin
    dinov2_variant_min_cosine: float = 0.88
    # Framed screenshot (0.7647) -> 0.72 safe margin
    dinov2_probable_min_cosine: float = 0.72
    # Visually similar distinct scenes (0.5231) -> 0.55 separation threshold
    dinov2_similar_diff_min_cosine: float = 0.55

    # Tier 4: ArcFace Biometric Cosine Similarity (512-dimensional, L2 normalized)
    # Calibrated against Phase 1 dataset matching
    arcface_match_min_cosine: float = 0.60
    arcface_moderate_min_cosine: float = 0.75
    arcface_high_confidence_min_cosine: float = 0.88


# Default active system correlation policy
CORRELATION_POLICY_V1 = CorrelationPolicyConfig()
