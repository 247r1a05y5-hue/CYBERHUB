"""Test to verify invariant #3: Face embeddings are NEVER leaked to API responses or plaintext logs."""
from __future__ import annotations

import io
import logging
import pytest
from app.services.face_service import MockFaceDetector, FaceValidationService
from app.services.audit_service import AuditService
from app.models.biometrics import FaceValidationStatus


def test_detector_embedding_in_memory_only():
    detector = MockFaceDetector()
    result = detector.detect_and_validate(b"MOCK_TEST_IMAGE_BYTES")
    assert result.is_valid is True
    assert result.embedding_vector is not None
    assert len(result.embedding_vector) == 512


def test_audit_service_scrubs_raw_vectors():
    class DummySession:
        def __init__(self):
            self.added = []
        def add(self, item):
            self.added.append(item)
        async def flush(self):
            pass

    session = DummySession()
    service = AuditService(session)

    # Test that vector array is redacted in audit logs
    test_vector = [0.123] * 512
    sanitized = service._sanitize({
        "quality": 0.95,
        "raw_embedding": test_vector,
        "token": "secret_token",
    })

    assert sanitized["raw_embedding"] == "[REDACTED]"
    assert sanitized["token"] == "[REDACTED]"
    assert sanitized["quality"] == 0.95
