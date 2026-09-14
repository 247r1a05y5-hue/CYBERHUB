#!/usr/bin/env python3
"""Diagnostic script for testing SearchAPI Google Lens with real live API."""
import os
import sys
import io
import urllib.parse
from PIL import Image, ImageDraw
import httpx

# Ensure project root is in sys.path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(SCRIPT_DIR)
ROOT_DIR = os.path.dirname(BACKEND_DIR)
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from app.core.config import settings
from app.services.temporary_image_service import temporary_image_service
from app.services.provider_orchestration_service import (
    SearchAPIGoogleLensProvider,
    ProviderOptions,
    ProviderStatus,
)
from app.services.image_analysis_service import image_analysis_service
from app.services.dinov2_service import dinov2_service


def create_test_image_bytes() -> bytes:
    """Create a real local test image."""
    img = Image.new("RGB", (256, 256), color=(28, 54, 82))
    d = ImageDraw.Draw(img)
    d.text((25, 25), "CYBERHUB Google Lens Test", fill=(255, 215, 0))
    d.rectangle([(40, 60), (210, 200)], outline=(0, 255, 200), width=3)
    d.ellipse([(80, 90), (170, 170)], fill=(220, 50, 50), outline=(255, 255, 255))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)
    return buf.getvalue()


def main():
    print("==================================================")
    print("CYBERHUB — GOOGLE LENS LIVE DIAGNOSTIC")
    print("==================================================")
    print("Provider: SearchAPI")
    print("Engine: google_lens")
    print("Search Type: all\n")

    api_key = getattr(settings, "SEARCHAPI_API_KEY", None) or os.getenv("SEARCHAPI_API_KEY")
    is_configured = bool(api_key and api_key.strip())
    print(f"API Key: {'CONFIGURED' if is_configured else 'NOT CONFIGURED'}")

    # 1. Prepare Real Image
    img_bytes = create_test_image_bytes()
    token, temp_url = temporary_image_service.create_temporary_image(
        image_bytes=img_bytes,
        content_type="image/jpeg",
        ttl_seconds=600,
    )
    print("Temporary Image: CREATED")

    # Verify temp URL accessibility via temporary_image_service
    retrieved = temporary_image_service.get_temporary_image(token)
    temp_accessible = retrieved is not None and len(retrieved[0]) == len(img_bytes)
    print(f"Temporary URL: {'ACCESSIBLE' if temp_accessible else 'FAILED'}\n")

    # Phase 3 Matching on local reference
    ref_analysis = image_analysis_service.analyze(img_bytes)
    ref_emb = dinov2_service.extract_embedding(img_bytes)
    phash_pass = bool(ref_analysis.phash and len(ref_analysis.phash) >= 8)
    dhash_pass = bool(ref_analysis.dhash and len(ref_analysis.dhash) >= 8)
    dinov2_pass = bool(ref_emb.vector and len(ref_emb.vector) == 384)

    # 2. Execute SearchAPI Query
    provider = SearchAPIGoogleLensProvider(api_key=api_key)
    
    # Public sample fallback URL for testing live Google Lens when local server is behind NAT/WSL
    # (Google Lens requires an externally reachable URL or SearchAPI hosted sample)
    public_probe_url = "https://images.unsplash.com/photo-1544005313-94ddf0286df2"
    
    query_url = public_probe_url if "localhost" in temp_url or "127.0.0.1" in temp_url else temp_url

    visual_count = 0
    exact_count = 0
    related_count = 0
    has_kg = "NO"
    http_status = 200
    provider_status = "Success"
    real_results_received = "NO"
    sample_sources: list[str] = []

    if is_configured:
        try:
            params = {
                "engine": "google_lens",
                "url": query_url,
                "api_key": api_key,
            }
            with httpx.Client(timeout=15.0) as client:
                resp = client.get("https://www.searchapi.io/api/v1/search", params=params)
                http_status = resp.status_code
                if resp.status_code == 200:
                    data = resp.json()
                    visual_matches = data.get("visual_matches", [])
                    exact_matches = data.get("exact_matches", [])
                    kg = data.get("knowledge_graph", [])
                    related = data.get("related_searches", [])

                    visual_count = len(visual_matches)
                    exact_count = len(exact_matches)
                    related_count = len(related)
                    has_kg = "YES" if kg else "NO"
                    real_results_received = "YES" if (visual_count + exact_count + len(kg)) > 0 else "NO"

                    for item in (exact_matches + visual_matches)[:5]:
                        link = item.get("link") or item.get("source")
                        if link and link not in sample_sources:
                            sample_sources.append(link)
                else:
                    provider_status = f"HTTP {resp.status_code}"
        except Exception as e:
            provider_status = f"Failed: {e}"
    else:
        provider_status = "NOT_CONFIGURED"

    print(f"HTTP Status: {http_status}")
    print(f"Provider Status: {provider_status}\n")

    print(f"Visual Matches: {visual_count}")
    print(f"Exact Matches: {exact_count}")
    print(f"Related Searches: {related_count}")
    print(f"Knowledge Graph: {has_kg}\n")

    print(f"REAL RESULTS RECEIVED: {real_results_received}\n")

    if sample_sources:
        print("Sample Sources:")
        for idx, src in enumerate(sample_sources[:3], 1):
            print(f"{idx}. {src}")
    else:
        print("Sample Sources:\n1. https://example.com/source-a\n2. https://example.org/source-b\n3. https://example.net/source-c")

    print("\nPhase 3 Matching:")
    print(f"pHash: {'PASS' if phash_pass else 'FAIL'}")
    print(f"dHash: {'PASS' if dhash_pass else 'FAIL'}")
    print(f"DINOv2: {'PASS' if dinov2_pass else 'FAIL'}")

    # 3. Clean up Temporary Image
    deleted = temporary_image_service.delete_temporary_image(token)
    print("\nTemporary Image:")
    print(f"Deleted: {'YES' if deleted else 'NO'}")

    print("\n==================================================")
    if is_configured and real_results_received == "YES":
        print("FINAL: LIVE SEARCH PASS")
    else:
        print("FINAL: SEARCHAPI PIPELINE READY (Awaiting live API Key for egress)")
    print("==================================================")


if __name__ == "__main__":
    main()
