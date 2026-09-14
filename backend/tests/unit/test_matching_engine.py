"""Unit & Calibration tests for Tiered Image Matching Engine (Phase 3).

Evaluates the 15-transform matrix across:
- Tier 1: SHA-256 (Exact file equality)
- Tier 2: pHash/dHash Hamming distance
- Tier 3: DINOv2 cosine similarity
"""
from __future__ import annotations

import pytest
from tests.fixtures.synthetic_corpus import generate_15_transform_corpus, get_image_bytes
from app.services.image_analysis_service import image_analysis_service
from app.services.dinov2_service import dinov2_service
from app.services.image_matching_service import (
    MatchClassification,
    MatchEvaluationResult,
    image_matching_service,
)


class TestMatchingEngineCalibration:
    @pytest.fixture
    def corpus(self):
        return generate_15_transform_corpus()

    @pytest.fixture
    def reference_analysis(self, corpus):
        base_bytes = get_image_bytes(corpus["00_base"], format="PNG")
        analysis = image_analysis_service.analyze(base_bytes)
        emb = dinov2_service.extract_embedding(base_bytes)
        return {"bytes": base_bytes, "analysis": analysis, "embedding": emb}

    def test_tier1_exact_copy(self, corpus, reference_analysis):
        copy_bytes = get_image_bytes(corpus["01_exact_copy"], format="PNG")
        copy_analysis = image_analysis_service.analyze(copy_bytes)
        copy_emb = dinov2_service.extract_embedding(copy_bytes)

        result: MatchEvaluationResult = image_matching_service.evaluate_match(
            reference_sha256=reference_analysis["analysis"].sha256_hash,
            candidate_sha256=copy_analysis.sha256_hash,
            reference_phash=reference_analysis["analysis"].phash,
            candidate_phash=copy_analysis.phash,
            reference_dhash=reference_analysis["analysis"].dhash,
            candidate_dhash=copy_analysis.dhash,
            reference_vector=reference_analysis["embedding"].vector,
            candidate_vector=copy_emb.vector,
        )

        assert result.classification == MatchClassification.EXACT
        assert result.tier_applied == 1
        assert result.phash_distance == 0
        assert result.dhash_distance == 0

    def test_tier2_and_3_transformations(self, corpus, reference_analysis):
        # 1. JPEG recompressed (quality 20)
        jpeg_bytes = get_image_bytes(corpus["02_jpeg_recompressed_q20"], format="JPEG")
        jpeg_analysis = image_analysis_service.analyze(jpeg_bytes)
        jpeg_emb = dinov2_service.extract_embedding(jpeg_bytes)
        res_jpeg = image_matching_service.evaluate_match(
            reference_sha256=reference_analysis["analysis"].sha256_hash,
            candidate_sha256=jpeg_analysis.sha256_hash,
            reference_phash=reference_analysis["analysis"].phash,
            candidate_phash=jpeg_analysis.phash,
            reference_dhash=reference_analysis["analysis"].dhash,
            candidate_dhash=jpeg_analysis.dhash,
            reference_vector=reference_analysis["embedding"].vector,
            candidate_vector=jpeg_emb.vector,
        )
        assert res_jpeg.classification in (
            MatchClassification.SAME_TRANSFORMED_IMAGE,
            MatchClassification.PROBABLE_RELATED,
        )

        # 2. Resized
        res_bytes = get_image_bytes(corpus["03_resized_down_up"], format="PNG")
        res_analysis = image_analysis_service.analyze(res_bytes)
        res_emb = dinov2_service.extract_embedding(res_bytes)
        res_resized = image_matching_service.evaluate_match(
            reference_sha256=reference_analysis["analysis"].sha256_hash,
            candidate_sha256=res_analysis.sha256_hash,
            reference_phash=reference_analysis["analysis"].phash,
            candidate_phash=res_analysis.phash,
            reference_dhash=reference_analysis["analysis"].dhash,
            candidate_dhash=res_analysis.dhash,
            reference_vector=reference_analysis["embedding"].vector,
            candidate_vector=res_emb.vector,
        )
        assert res_resized.classification in (
            MatchClassification.SAME_TRANSFORMED_IMAGE,
            MatchClassification.PROBABLE_RELATED,
        )

    def test_unrelated_image_classified_unrelated(self, corpus, reference_analysis):
        unrel_bytes = get_image_bytes(corpus["10_unrelated_scene"], format="PNG")
        unrel_analysis = image_analysis_service.analyze(unrel_bytes)
        unrel_emb = dinov2_service.extract_embedding(unrel_bytes)

        res = image_matching_service.evaluate_match(
            reference_sha256=reference_analysis["analysis"].sha256_hash,
            candidate_sha256=unrel_analysis.sha256_hash,
            reference_phash=reference_analysis["analysis"].phash,
            candidate_phash=unrel_analysis.phash,
            reference_dhash=reference_analysis["analysis"].dhash,
            candidate_dhash=unrel_analysis.dhash,
            reference_vector=reference_analysis["embedding"].vector,
            candidate_vector=unrel_emb.vector,
        )
        assert res.classification in (
            MatchClassification.UNRELATED,
            MatchClassification.VISUALLY_SIMILAR,
        )

    def test_calibrated_15_matrix_sweep(self, corpus, reference_analysis):
        """Runs through all 15 transforms and asserts classifications."""
        results = {}
        for name, img in corpus.items():
            if name == "00_base":
                continue
            img_format = "JPEG" if "jpeg" in name or "compression" in name else "PNG"
            b = get_image_bytes(img, format=img_format)
            analysis = image_analysis_service.analyze(b)
            emb = dinov2_service.extract_embedding(b)
            score = image_matching_service.evaluate_match(
                reference_sha256=reference_analysis["analysis"].sha256_hash,
                candidate_sha256=analysis.sha256_hash,
                reference_phash=reference_analysis["analysis"].phash,
                candidate_phash=analysis.phash,
                reference_dhash=reference_analysis["analysis"].dhash,
                candidate_dhash=analysis.dhash,
                reference_vector=reference_analysis["embedding"].vector,
                candidate_vector=emb.vector,
            )
            results[name] = score

        assert results["01_exact_copy"].classification == MatchClassification.EXACT
        assert results["02_jpeg_recompressed_q20"].classification == MatchClassification.SAME_TRANSFORMED_IMAGE
        assert results["08_screenshot_frame"].classification == MatchClassification.PROBABLE_RELATED
        assert results["10_unrelated_scene"].classification == MatchClassification.UNRELATED
