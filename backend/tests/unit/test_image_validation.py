"""Unit tests for Image Validation Service (Slice 1).

Tests:
- MIME & Magic byte verification (JPEG, PNG, WebP)
- Extension spoofing detection
- Decompression bomb guard
- File size and dimension boundary checks
- Safe UUID generation & path traversal prevention
"""
from __future__ import annotations

import io
import pytest
from PIL import Image

from app.services.image_validation_service import (
    ImageValidationError,
    image_validation_service,
)
from app.services.secure_storage_service import secure_storage_service


def _create_image_bytes(format: str = "PNG", size: tuple[int, int] = (200, 200), color: str = "red") -> bytes:
    img = Image.new("RGB", size, color=color)
    buf = io.BytesIO()
    img.save(buf, format=format)
    return buf.getvalue()


class TestImageValidation:
    def test_valid_png_validation(self):
        content = _create_image_bytes(format="PNG", size=(300, 300))
        validated = image_validation_service.validate_and_sanitize(content, "test_image.png")
        assert validated.mime_type == "image/png"
        assert validated.extension == "png"
        assert validated.width == 300
        assert validated.height == 300
        assert validated.byte_size == len(content)

    def test_valid_jpeg_validation(self):
        content = _create_image_bytes(format="JPEG", size=(400, 300))
        validated = image_validation_service.validate_and_sanitize(content, "sample.jpg")
        assert validated.mime_type == "image/jpeg"
        assert validated.extension in ("jpg", "jpeg")
        assert validated.width == 400
        assert validated.height == 300

    def test_valid_webp_validation(self):
        content = _create_image_bytes(format="WEBP", size=(250, 250))
        validated = image_validation_service.validate_and_sanitize(content, "sample.webp")
        assert validated.mime_type == "image/webp"
        assert validated.extension == "webp"
        assert validated.width == 250
        assert validated.height == 250

    def test_extension_spoofing_rejected(self):
        # Plain text disguised as PNG
        fake_content = b"Not a real image file content, just text."
        with pytest.raises(ImageValidationError, match="Invalid image file header"):
            image_validation_service.validate_and_sanitize(fake_content, "attack.png")

    def test_executable_disguised_rejected(self):
        # Windows PE header disguised as JPG
        fake_pe = b"MZ" + b"\x00" * 200
        with pytest.raises(ImageValidationError, match="Invalid image file header"):
            image_validation_service.validate_and_sanitize(fake_pe, "malware.jpg")

    def test_oversized_file_rejected(self):
        # Pretend file is 16MB (exceeds 15MB limit)
        huge_bytes = b"\x00" * (16 * 1024 * 1024)
        with pytest.raises(ImageValidationError, match="exceeds maximum allowed"):
            image_validation_service.validate_and_sanitize(huge_bytes, "huge.png")

    def test_under_dimension_rejected(self):
        # Image smaller than 64x64
        tiny = _create_image_bytes(format="PNG", size=(32, 32))
        with pytest.raises(ImageValidationError, match="below minimum allowed dimensions"):
            image_validation_service.validate_and_sanitize(tiny, "tiny.png")

    def test_decompression_bomb_rejected(self):
        # Test extreme dimension that violates MAX_IMAGE_PIXELS
        # Pillow default MAX_IMAGE_PIXELS or service bound 16M
        with pytest.raises(ImageValidationError):
            # Attempt to allocate 10000x10000
            huge_img = Image.new("RGB", (10000, 10000))
            buf = io.BytesIO()
            huge_img.save(buf, format="PNG")
            image_validation_service.validate_and_sanitize(buf.getvalue(), "bomb.png")

    def test_safe_storage_key_generation(self):
        storage_key = secure_storage_service.generate_storage_key("org_123", "inv_456", "png")
        assert "org_123" in storage_key
        assert "inv_456" in storage_key
        assert storage_key.endswith(".png")
        assert ".." not in storage_key
        assert "/" not in storage_key or "\\" not in storage_key
