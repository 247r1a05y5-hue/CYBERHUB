"""CYBERHUB Phase 4: Live Search Provider Verification Runner.

Disciplined verification distinguishing:
- Live Google Cloud Vision Web Detection API
- Live TinEye MatchEngine API
- Unconfigured states (honest reporting with zero fabrication)
"""
from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.core.config import settings
from app.services.provider_orchestration_service import (
    GoogleVisionWebDetectionProvider,
    ProviderOptions,
    ProviderStatus,
    TinEyeMatchEngineProvider,
    provider_orchestrator,
)
from tests.fixtures.synthetic_corpus import generate_15_transform_corpus, get_image_bytes


async def run_live_provider_verification():
    print("=" * 80)
    print("CYBERHUB PHASE 4: LIVE DISCOVERY PROVIDER CREDENTIAL & ENDPOINT VERIFICATION")
    print("=" * 80)

    corpus = generate_15_transform_corpus()
    sample_img_bytes = get_image_bytes(corpus["00_base"], format="PNG")

    # -------------------------------------------------------------------------
    # 1. GOOGLE CLOUD VISION (WEB DETECTION)
    # -------------------------------------------------------------------------
    print("\n[1] Evaluating Google Cloud Vision Provider...")
    google_provider = GoogleVisionWebDetectionProvider()
    g_status = google_provider.get_status()

    if g_status == ProviderStatus.NOT_CONFIGURED:
        print("  -> Status: NOT_CONFIGURED")
        print("  -> LIVE GOOGLE PROVIDER: NOT CONFIGURED (No GOOGLE_VISION_API_KEY configured in environment)")
        print("  -> Notice: Real public-web discovery via Google Vision requires valid enterprise API credentials.")
    else:
        print(f"  -> Status: {g_status.value}")
        try:
            print("  -> Sending live test payload to Google Vision Web Detection endpoint...")
            results = await google_provider.discover(sample_img_bytes, None, ProviderOptions(max_results=5))
            print(f"  -> LIVE GOOGLE PROVIDER: VERIFIED (Received {len(results)} live signal(s) from vision.googleapis.com)")
            for r in results[:3]:
                print(f"     * Found: {r.domain} - {r.page_url} (Score: {r.provider_score})")
        except Exception as err:
            print(f"  -> LIVE GOOGLE PROVIDER: FAILED ({err})")

    # -------------------------------------------------------------------------
    # 2. TINEYE MATCHENGINE
    # -------------------------------------------------------------------------
    print("\n[2] Evaluating TinEye MatchEngine Provider...")
    tineye_provider = TinEyeMatchEngineProvider()
    t_status = tineye_provider.get_status()

    if t_status == ProviderStatus.NOT_CONFIGURED:
        print("  -> Status: NOT_CONFIGURED")
        print("  -> LIVE TINEYE PROVIDER: NOT CONFIGURED (No TINEYE_API_KEY configured in environment)")
        print("  -> Notice: Real reverse-image discovery via TinEye requires valid enterprise API credentials.")
    else:
        print(f"  -> Status: {t_status.value}")
        try:
            print("  -> Sending live test payload to TinEye API endpoint...")
            results = await tineye_provider.discover(sample_img_bytes, None, ProviderOptions(max_results=5))
            print(f"  -> LIVE TINEYE PROVIDER: VERIFIED (Received {len(results)} live signal(s) from api.tineye.com)")
            for r in results[:3]:
                print(f"     * Found: {r.domain} - {r.page_url} (Score: {r.provider_score})")
        except Exception as err:
            print(f"  -> LIVE TINEYE PROVIDER: FAILED ({err})")

    # -------------------------------------------------------------------------
    # SUMMARY
    # -------------------------------------------------------------------------
    print("\n" + "=" * 80)
    print("LIVE PROVIDER STATUS SUMMARY:")
    print(f"  • Google Cloud Vision : {google_provider.get_status().value}")
    print(f"  • TinEye MatchEngine  : {tineye_provider.get_status().value}")
    print("  • Fabrication Policy  : STRICT (Zero simulated findings are reported as live discovery)")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    asyncio.run(run_live_provider_verification())
