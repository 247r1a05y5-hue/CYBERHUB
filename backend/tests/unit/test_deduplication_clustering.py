"""Unit tests for Deduplication & Exposure Clustering (Slice 6).

Tests:
- Canonical URL normalization
- Multi-provider provenance merging (Google Vision + TinEye matches merge without data loss)
- Cluster grouping with transparent rationale reason strings
"""
from __future__ import annotations

import datetime
import pytest
from app.services.deduplication_clustering_service import (
    DeduplicatedCandidate,
    ExposureClusterGroup,
    deduplication_and_clustering_service,
)
from app.services.provider_orchestration_service import NormalizedDiscoveryResult


class TestDeduplicationAndClustering:
    def test_canonical_url_normalization(self):
        url1 = "https://EXAMPLE.com/path/image.jpg?utm_source=twitter#section"
        url2 = "http://example.com:80/path/image.jpg"
        
        canon1 = deduplication_and_clustering_service.canonicalize_url(url1)
        canon2 = deduplication_and_clustering_service.canonicalize_url(url2)
        
        assert canon1.startswith("https://example.com/path/image.jpg")
        assert canon2.startswith("http://example.com/path/image.jpg")

    def test_multi_provider_provenance_retention(self):
        now = datetime.datetime.now(datetime.timezone.utc)
        
        # Result discovered by Google Vision
        res1 = NormalizedDiscoveryResult(
            provider="google_vision",
            image_url="https://site-a.com/avatar.jpg",
            page_url="https://site-a.com/profile",
            domain="site-a.com",
            page_title="Profile Page",
            provider_raw_ref="gv_ref_1",
            provider_score=0.95,
            discovered_at=now,
            metadata={"gv_full_match": True},
        )
        
        # Exact same page discovered by TinEye
        res2 = NormalizedDiscoveryResult(
            provider="tineye",
            image_url="https://site-a.com/avatar.jpg",
            page_url="https://site-a.com/profile",
            domain="site-a.com",
            page_title="Profile Page",
            provider_raw_ref="tineye_ref_1",
            provider_score=0.92,
            discovered_at=now,
            metadata={"tineye_crawl_date": "2026-01-01"},
        )

        deduped = deduplication_and_clustering_service.deduplicate_results([res1, res2])
        assert len(deduped) == 1
        
        # Verify provenance has BOTH providers recorded
        merged = deduped[0]
        assert "google_vision" in merged.providers
        assert "tineye" in merged.providers
        assert len(merged.provenance_records) == 2

    def test_exposure_clustering_with_reasons(self):
        candidates = [
            DeduplicatedCandidate(
                id="cand_1",
                canonical_url="https://social.com/img1.png",
                image_url="https://social.com/img1.png",
                domain="social.com",
                page_title="User 1",
                providers=["google_vision"],
                provenance_records=[],
                similarity_score=0.95,
                classification="SAME_IMAGE_TRANSFORMED_VARIANT",
            ),
            DeduplicatedCandidate(
                id="cand_2",
                canonical_url="https://social.com/img2.png",
                image_url="https://social.com/img2.png",
                domain="social.com",
                page_title="User 2",
                providers=["google_vision"],
                provenance_records=[],
                similarity_score=0.90,
                classification="SAME_IMAGE_TRANSFORMED_VARIANT",
            ),
            DeduplicatedCandidate(
                id="cand_3",
                canonical_url="https://news.com/article_pic.jpg",
                image_url="https://news.com/article_pic.jpg",
                domain="news.com",
                page_title="News Article",
                providers=["tineye"],
                provenance_records=[],
                similarity_score=1.0,
                classification="EXACT_SAME_FILE",
            ),
        ]

        clusters = deduplication_and_clustering_service.cluster_candidates(candidates, reference_hash="ref_hash_123")
        assert len(clusters) == 2
        for cluster in clusters:
            assert cluster.reason_string != ""
            assert len(cluster.member_candidate_ids) > 0
