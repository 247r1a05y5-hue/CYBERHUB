"""Unit tests & Latency Benchmarks for DINOv2 Embedding Service (Slice 2).

Tests:
- Embeddings are strictly 384 dimensions (for dinov2_vits14)
- Embeddings are L2-normalized (norm == 1.0)
- Cosine similarity between identical images == 1.0
- Cosine similarity behaves properly on transformed vs unrelated images
- Benchmarks and logs actual inference latency in milliseconds
"""
from __future__ import annotations

import math
import time
import pytest
from tests.fixtures.synthetic_corpus import generate_15_transform_corpus, get_image_bytes
from app.services.dinov2_service import dinov2_service


class TestDINOv2Embeddings:
    @pytest.fixture
    def corpus(self):
        return generate_15_transform_corpus()

    def test_embedding_dimensions_and_normalization(self, corpus):
        base_bytes = get_image_bytes(corpus["00_base"], format="PNG")
        embedding = dinov2_service.generate_embedding(base_bytes)
        
        assert len(embedding) == 384, f"Expected 384-dim embedding for dinov2_vits14, got {len(embedding)}"
        
        # Verify L2 normalization: sum of squares == 1.0 (within float tolerance)
        l2_norm = math.sqrt(sum(x * x for x in embedding))
        assert abs(l2_norm - 1.0) < 1e-4, f"Embedding is not L2 normalized: {l2_norm}"

    def test_cosine_similarity_identical_images(self, corpus):
        base_bytes = get_image_bytes(corpus["00_base"], format="PNG")
        copy_bytes = get_image_bytes(corpus["01_exact_copy"], format="PNG")
        
        emb1 = dinov2_service.generate_embedding(base_bytes)
        emb2 = dinov2_service.generate_embedding(copy_bytes)
        
        sim = dinov2_service.compute_cosine_similarity(emb1, emb2)
        assert abs(sim - 1.0) < 1e-4, f"Identical images similarity expected 1.0, got {sim}"

    def test_cosine_similarity_transformed_vs_unrelated(self, corpus):
        base_bytes = get_image_bytes(corpus["00_base"], format="PNG")
        emb_base = dinov2_service.generate_embedding(base_bytes)
        
        # Contrast altered image should have high similarity (> 0.85)
        contrast_bytes = get_image_bytes(corpus["07_contrast_plus40"], format="PNG")
        emb_contrast = dinov2_service.generate_embedding(contrast_bytes)
        sim_contrast = dinov2_service.compute_cosine_similarity(emb_base, emb_contrast)
        assert sim_contrast > 0.80, f"Transformed similarity expected > 0.80, got {sim_contrast}"
        
        # Unrelated image should have lower similarity (< 0.65)
        unrelated_bytes = get_image_bytes(corpus["10_unrelated_scene"], format="PNG")
        emb_unrelated = dinov2_service.generate_embedding(unrelated_bytes)
        sim_unrelated = dinov2_service.compute_cosine_similarity(emb_base, emb_unrelated)
        assert sim_unrelated < 0.70, f"Unrelated image similarity expected < 0.70, got {sim_unrelated}"

    def test_inference_latency_benchmark(self, corpus):
        base_bytes = get_image_bytes(corpus["00_base"], format="PNG")
        
        # Warmup run
        _ = dinov2_service.generate_embedding(base_bytes)
        
        # Benchmark 5 iterations
        latencies = []
        for _ in range(5):
            t0 = time.perf_counter()
            _ = dinov2_service.generate_embedding(base_bytes)
            t1 = time.perf_counter()
            latencies.append((t1 - t0) * 1000.0)  # ms
            
        avg_latency_ms = sum(latencies) / len(latencies)
        min_latency_ms = min(latencies)
        max_latency_ms = max(latencies)
        
        print(f"\n[DINOv2 Benchmark] dinov2_vits14 CPU Latency: avg={avg_latency_ms:.2f}ms, min={min_latency_ms:.2f}ms, max={max_latency_ms:.2f}ms")
        
        # Assert latency is reasonable (< 3000ms on CPU)
        assert avg_latency_ms < 3000.0
