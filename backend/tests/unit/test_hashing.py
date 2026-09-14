"""Unit tests for Image Analysis and Hashing Service (Slice 2).

Tests:
- Deterministic SHA-256 fingerprinting
- 64-bit DCT perceptual hash (pHash)
- 64-bit gradient difference hash (dHash)
- Quality metrics computation (sharpness Laplacian, brightness, contrast, entropy)
- Robustness across small transformations
"""
from __future__ import annotations

import io
import pytest
from PIL import Image

from tests.fixtures.synthetic_corpus import generate_15_transform_corpus, get_image_bytes
from app.services.image_analysis_service import image_analysis_service


class TestImageHashing:
    @pytest.fixture
    def corpus(self):
        return generate_15_transform_corpus()

    def test_sha256_exact_match(self, corpus):
        base_bytes = get_image_bytes(corpus["00_base"], format="PNG")
        copy_bytes = get_image_bytes(corpus["01_exact_copy"], format="PNG")
        
        base_sha = image_analysis_service.compute_sha256(base_bytes)
        copy_sha = image_analysis_service.compute_sha256(copy_bytes)
        
        assert base_sha == copy_sha
        assert len(base_sha) == 64

    def test_phash_and_dhash_generation(self, corpus):
        base_bytes = get_image_bytes(corpus["00_base"], format="PNG")
        analysis = image_analysis_service.analyze_image(base_bytes)
        
        assert analysis.phash is not None
        assert len(analysis.phash) == 16  # 64-bit hex is 16 chars
        assert analysis.dhash is not None
        assert len(analysis.dhash) == 16

    def test_phash_hamming_distance_exact_copy(self, corpus):
        base_bytes = get_image_bytes(corpus["00_base"], format="PNG")
        copy_bytes = get_image_bytes(corpus["01_exact_copy"], format="PNG")
        
        base_analysis = image_analysis_service.analyze_image(base_bytes)
        copy_analysis = image_analysis_service.analyze_image(copy_bytes)
        
        dist_p = image_analysis_service.calculate_hamming_distance(base_analysis.phash, copy_analysis.phash)
        dist_d = image_analysis_service.calculate_hamming_distance(base_analysis.dhash, copy_analysis.dhash)
        
        assert dist_p == 0
        assert dist_d == 0

    def test_phash_robustness_on_transformations(self, corpus):
        base_bytes = get_image_bytes(corpus["00_base"], format="PNG")
        base_analysis = image_analysis_service.analyze_image(base_bytes)
        
        # JPEG recompressed should have low Hamming distance (< 12)
        jpeg_bytes = get_image_bytes(corpus["02_jpeg_recompressed_q20"], format="JPEG")
        jpeg_analysis = image_analysis_service.analyze_image(jpeg_bytes)
        dist_jpeg = image_analysis_service.calculate_hamming_distance(base_analysis.phash, jpeg_analysis.phash)
        assert dist_jpeg <= 12

        # Resized should have low Hamming distance (< 10)
        resized_bytes = get_image_bytes(corpus["03_resized_down_up"], format="PNG")
        resized_analysis = image_analysis_service.analyze_image(resized_bytes)
        dist_resized = image_analysis_service.calculate_hamming_distance(base_analysis.phash, resized_analysis.phash)
        assert dist_resized <= 10

    def test_phash_unrelated_image_high_distance(self, corpus):
        base_bytes = get_image_bytes(corpus["00_base"], format="PNG")
        base_analysis = image_analysis_service.analyze_image(base_bytes)
        
        unrelated_bytes = get_image_bytes(corpus["10_unrelated_scene"], format="PNG")
        unrelated_analysis = image_analysis_service.analyze_image(unrelated_bytes)
        
        dist_unrelated = image_analysis_service.calculate_hamming_distance(base_analysis.phash, unrelated_analysis.phash)
        assert dist_unrelated >= 15  # Unrelated images have high Hamming distance

    def test_quality_metrics(self, corpus):
        base_bytes = get_image_bytes(corpus["00_base"], format="PNG")
        analysis = image_analysis_service.analyze_image(base_bytes)
        quality = analysis.quality
        
        assert 0.0 <= quality.brightness <= 100.0
        assert 0.0 <= quality.contrast <= 100.0
        assert quality.sharpness >= 0.0
        assert quality.entropy >= 0.0
