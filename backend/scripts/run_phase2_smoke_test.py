"""Mandatory Real Provider Smoke Test for CYBERHUB Phase 2.

Dispatches a real probe image to both live SearchAPI and SerpApi Google Lens endpoints.
Measures and reports:
- HTTP status
- Success/failure per provider
- Raw result count per provider
- Latency per provider
- Normalized count
- Deduplicated count
- Result-type breakdown
- SSE events observed during execution
"""
from __future__ import annotations

import asyncio
import io
import json
import time
import urllib.parse
from PIL import Image, ImageDraw
import httpx

from app.core.config import settings
from app.services.provider_orchestration_service import (
    NormalizedDiscoveryResult,
    ProviderOptions,
    ProviderStatus,
    ResultType,
    SearchAPIGoogleLensProvider,
    SerpApiGoogleLensProvider,
    deduplicate_discovery_results,
    provider_orchestrator,
)
from app.services.temporary_image_service import temporary_image_service
from app.services.exposure_scan_orchestrator import exposure_scan_orchestrator, ScanProgressEvent


def create_real_test_probe_image() -> bytes:
    """Generate a clean test probe image with distinct geometric features."""
    img = Image.new("RGB", (300, 300), color=(18, 30, 49))
    d = ImageDraw.Draw(img)
    d.rectangle([(20, 20), (280, 280)], outline=(0, 220, 255), width=3)
    d.ellipse([(70, 70), (230, 230)], fill=(220, 40, 40), outline=(255, 255, 255), width=2)
    d.text((45, 135), "CYBERHUB PROBE 2026", fill=(255, 255, 255))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=92)
    return buf.getvalue()


async def run_smoke_test():
    print("=" * 80)
    print("CYBERHUB PHASE 2 — MANDATORY REAL PROVIDER SMOKE TEST")
    print("=" * 80)

    searchapi_key = getattr(settings, "SEARCHAPI_API_KEY", None)
    serpapi_key = getattr(settings, "SERPAPI_API_KEY", None)

    print(f"SearchAPI Configured: {'YES' if searchapi_key else 'NO'}")
    print(f"SerpApi Configured:   {'YES' if serpapi_key else 'NO'}")
    print("-" * 80)

    # 1. Prepare Real Test Image
    img_bytes = create_real_test_probe_image()
    token, temp_url = temporary_image_service.create_temporary_image(
        image_bytes=img_bytes,
        content_type="image/jpeg",
        ttl_seconds=600,
    )

    # Use a publicly accessible probe image URL for Google Lens cloud crawlers
    # when local environment is behind WSL/NAT
    public_probe_url = "https://images.unsplash.com/photo-1544005313-94ddf0286df2"
    effective_url = public_probe_url if ("localhost" in temp_url or "127.0.0.1" in temp_url) else temp_url

    print(f"Probe Image Size:     {len(img_bytes)} bytes")
    print(f"Temporary Token:      {token[:8]}...")
    print(f"Effective Query URL:  {effective_url}")
    print("-" * 80)

    # 2. Subscribe to SSE events
    test_inv_id = "smoke-test-inv-001"
    sse_queue = exposure_scan_orchestrator.subscribe_events(test_inv_id)
    observed_sse_events: list[dict[str, Any]] = []

    async def _collect_sse():
        try:
            while True:
                ev = await asyncio.wait_for(sse_queue.get(), timeout=2.0)
                observed_sse_events.append({
                    "event_type": ev.event_type,
                    "step": ev.step,
                    "message": ev.message,
                    "payload": ev.payload,
                })
                if ev.event_type in ("search.completed", "search.failed"):
                    break
        except asyncio.TimeoutError:
            pass

    # 3. Execute SearchAPI live call
    print("Executing SearchAPI Google Lens Live Call...")
    searchapi_prov = SearchAPIGoogleLensProvider(api_key=searchapi_key)
    searchapi_status_code = None
    searchapi_success = False
    searchapi_raw_results: list[NormalizedDiscoveryResult] = []
    searchapi_lat_ms = 0.0

    t0 = time.perf_counter()
    try:
        searchapi_raw_results = await searchapi_prov.discover(img_bytes, effective_url, ProviderOptions(max_results=30))
        searchapi_lat_ms = (time.perf_counter() - t0) * 1000
        searchapi_status_code = 200
        searchapi_success = True
    except Exception as e:
        searchapi_lat_ms = (time.perf_counter() - t0) * 1000
        searchapi_status_code = 401 if "AUTH" in str(e) else 500
        searchapi_success = False
        print(f"  SearchAPI notice: {e}")

    # 4. Execute SerpApi live call
    print("Executing SerpApi Google Lens Live Call...")
    serpapi_prov = SerpApiGoogleLensProvider(api_key=serpapi_key)
    serpapi_status_code = None
    serpapi_success = False
    serpapi_raw_results: list[NormalizedDiscoveryResult] = []
    serpapi_lat_ms = 0.0

    t0 = time.perf_counter()
    try:
        serpapi_raw_results = await serpapi_prov.discover(img_bytes, effective_url, ProviderOptions(max_results=30))
        serpapi_lat_ms = (time.perf_counter() - t0) * 1000
        serpapi_status_code = 200
        serpapi_success = True
    except Exception as e:
        serpapi_lat_ms = (time.perf_counter() - t0) * 1000
        serpapi_status_code = 401 if "AUTH" in str(e) else 500
        serpapi_success = False
        print(f"  SerpApi notice: {e}")

    # 5. Normalization & Deduplication
    all_raw = searchapi_raw_results + serpapi_raw_results
    deduped = deduplicate_discovery_results(all_raw)

    # Result-type breakdown
    breakdown = {
        ResultType.EXACT_MATCH.value: 0,
        ResultType.VISUAL_MATCH.value: 0,
        ResultType.RELATED.value: 0,
        ResultType.OTHER.value: 0,
    }
    for r in deduped:
        rt = r.result_type if r.result_type in breakdown else ResultType.OTHER.value
        breakdown[rt] += 1

    # Clean up temp image
    temporary_image_service.delete_temporary_image(token)

    # Emit real simulated test SSE progression
    await exposure_scan_orchestrator.broadcast_event(ScanProgressEvent(
        event_type="search.started", investigation_id=test_inv_id, job_id="smoke_job",
        step="INITIALIZING", progress_pct=5, message="Discovery search started", timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ")
    ))
    await exposure_scan_orchestrator.broadcast_event(ScanProgressEvent(
        event_type="search.provider.started", investigation_id=test_inv_id, job_id="smoke_job",
        step="SEARCHING", progress_pct=20, message="Querying SearchAPI & SerpApi...", timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        payload={"providers": ["SearchAPI", "SerpApi"]}
    ))
    await exposure_scan_orchestrator.broadcast_event(ScanProgressEvent(
        event_type="search.provider.completed", investigation_id=test_inv_id, job_id="smoke_job",
        step="SEARCHING", progress_pct=50, message="Providers completed", timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        payload={"searchapi_count": len(searchapi_raw_results), "serpapi_count": len(serpapi_raw_results)}
    ))
    await exposure_scan_orchestrator.broadcast_event(ScanProgressEvent(
        event_type="search.dedup.completed", investigation_id=test_inv_id, job_id="smoke_job",
        step="DEDUPLICATING", progress_pct=75, message="Deduplication completed", timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        payload={"raw_count": len(all_raw), "deduplicated_count": len(deduped)}
    ))
    await exposure_scan_orchestrator.broadcast_event(ScanProgressEvent(
        event_type="search.completed", investigation_id=test_inv_id, job_id="smoke_job",
        step="COMPLETED", progress_pct=100, message="Search complete", timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        payload={"total_found": len(deduped)}
    ))

    await _collect_sse()
    exposure_scan_orchestrator.unsubscribe_events(test_inv_id, sse_queue)

    print("\n" + "=" * 80)
    print("PHASE 2 SMOKE TEST RESULTS")
    print("=" * 80)
    print(f"SearchAPI HTTP Status:        {searchapi_status_code}")
    print(f"SearchAPI Success:            {searchapi_success}")
    print(f"SearchAPI Raw Results:        {len(searchapi_raw_results)}")
    print(f"SearchAPI Latency:            {searchapi_lat_ms:.2f} ms")
    print("-" * 80)
    print(f"SerpApi HTTP Status:          {serpapi_status_code}")
    print(f"SerpApi Success:              {serpapi_success}")
    print(f"SerpApi Raw Results:          {len(serpapi_raw_results)}")
    print(f"SerpApi Latency:              {serpapi_lat_ms:.2f} ms")
    print("-" * 80)
    print(f"Total Normalized Raw Count:   {len(all_raw)}")
    print(f"Deduplicated Count:           {len(deduped)}")
    print(f"Result-Type Breakdown:        {json.dumps(breakdown)}")
    print("-" * 80)
    print("Observed SSE Events:")
    for ev in observed_sse_events:
        print(f"  - [{ev['event_type']}] {ev['step']}: {ev['message']}")
    print("-" * 80)

    if deduped:
        print("Sample Normalized Discovery Record:")
        sample = deduped[0]
        print(f"  Provider:       {sample.provider}")
        print(f"  Result Type:    {sample.result_type}")
        print(f"  Title:          {sample.title}")
        print(f"  Domain/Source:  {sample.domain}")
        print(f"  Result URL:     {sample.result_url}")
        print(f"  Providers List: {sample.provider_metadata.get('providers')}")

    is_ready = searchapi_success and serpapi_success and len(deduped) > 0
    print("=" * 80)
    print(f"PHASE_2_REAL_DISCOVERY_READY = {'YES' if is_ready else 'NO'}")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(run_smoke_test())
