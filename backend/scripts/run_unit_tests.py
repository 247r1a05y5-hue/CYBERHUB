"""Fast Phase 3 Unit Test Runner Script."""
from __future__ import annotations

import asyncio
import sys
import traceback

from tests.unit.test_phase3_investigation import (
    TestCrawlCourtesy,
    TestHtmlAndImageExtraction,
    TestImageCorrelationEngine,
    TestOcrAndHistoricalSnapshots,
    TestRenderingFallback,
    TestSsrfAndSecurity,
    TestTenantIsolationAndIdempotency,
)


def run_all_tests():
    print("=" * 75)
    print("RUNNING PHASE 3 UNIT & SECURITY TEST SUITE")
    print("=" * 75)

    passed = 0
    failed = 0

    test_classes = [
        ("SSRF & Network Security", TestSsrfAndSecurity()),
        ("Crawl Courtesy & Robots.txt", TestCrawlCourtesy()),
        ("HTML & Image Extraction", TestHtmlAndImageExtraction()),
        ("Rendering Fallback Chain", TestRenderingFallback()),
        ("Image Correlation Engine", TestImageCorrelationEngine()),
        ("OCR & Historical Snapshots", TestOcrAndHistoricalSnapshots()),
        ("Tenant Isolation & Idempotency", TestTenantIsolationAndIdempotency()),
    ]

    for suite_name, instance in test_classes:
        print(f"\n--- {suite_name} ---")
        methods = [m for m in dir(instance) if m.startswith("test_")]
        for m_name in methods:
            func = getattr(instance, m_name)
            try:
                if asyncio.iscoroutinefunction(func):
                    asyncio.run(func())
                else:
                    func()
                print(f"  ✓ {m_name}")
                passed += 1
            except Exception as e:
                print(f"  ✗ {m_name}: {e}")
                traceback.print_exc()
                failed += 1

    print("\n" + "=" * 75)
    print(f"TEST RESULTS: {passed} PASSED, {failed} FAILED (TOTAL: {passed + failed})")
    print("=" * 75)
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
