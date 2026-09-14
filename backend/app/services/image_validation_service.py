"""File Upload Security & Image Validation Service.

Enforces strict validation rules:
- Magic bytes / header inspection (never trust file extensions)
- MIME type verification
- Safe decoding with PIL (decompression bomb protection, format verification)
- Dimension constraints (min 64x64, max 8192x8192)
- Max payload size (15 MB)
- Path traversal prevention and secure UUID storage key generation
"""
from __future__ import annotations

import io
import os
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO

from PIL import Image, UnidentifiedImageError

# Security constants
MAX_FILE_SIZE_BYTES = 15 * 1024 * 1024  # 15 MB
MIN_DIMENSION_PX = 64
MAX_DIMENSION_PX = 8192
MAX_IMAGE_PIXELS = 16_000_000  # Guard against decompression bombs (16 MP)

# Set PIL safety limit
Image.MAX_IMAGE_PIXELS = MAX_IMAGE_PIXELS

SUPPORTED_FORMATS = {"JPEG", "PNG", "WEBP"}
SUPPORTED_MIME_TYPES = {"image/jpeg", "image/png", "image/webp"}

# Magic byte signatures
MAGIC_SIGNATURES = {
    b"\xff\xd8\xff": "image/jpeg",
    b"\x89PNG\r\n\x1a\n": "image/png",
    b"RIFF": "image/webp",  # WebP files start with 'RIFF....WEBP'
}


class ImageValidationError(ValueError):
    """Raised when an uploaded file fails security or structural validation."""
    pass


@dataclass(frozen=True)
class ValidatedImageMetadata:
    """Validated image attributes."""
    format: str
    mime_type: str
    width: int
    height: int
    size_bytes: int
    storage_filename: str
    raw_bytes: bytes
    extension: str = ""

    @property
    def byte_size(self) -> int:
        return self.size_bytes


class ImageValidationService:
    """Validates uploaded images for security, format integrity, and dimensions."""

    @staticmethod
    def detect_mime_from_magic_bytes(data: bytes) -> str | None:
        """Inspect magic bytes to determine true format."""
        if len(data) < 4:
            return None

        # Check JPEG (\xff\xd8\xff)
        if data.startswith(b"\xff\xd8\xff"):
            return "image/jpeg"

        # Check PNG (\x89PNG\r\n\x1a\n)
        if data.startswith(b"\x89PNG\r\n\x1a\n"):
            return "image/png"

        # Check WebP (RIFF + WEBP at offset 8)
        if len(data) >= 12 and data.startswith(b"RIFF") and data[8:12] == b"WEBP":
            return "image/webp"

        return None

    @classmethod
    def validate_and_sanitize(
        cls,
        file_bytes: bytes,
        filename: str | None = None,
        max_size: int = MAX_FILE_SIZE_BYTES,
    ) -> ValidatedImageMetadata:
        """Thoroughly inspect and decode image bytes with strict security controls."""
        size_bytes = len(file_bytes)

        # 1. Size check
        if size_bytes == 0:
            raise ImageValidationError("Uploaded image file is empty.")
        if size_bytes > max_size:
            raise ImageValidationError(
                f"File size ({size_bytes / (1024 * 1024):.2f} MB) exceeds maximum allowed {max_size / (1024 * 1024):.0f} MB."
            )

        # 2. Magic bytes check
        detected_mime = cls.detect_mime_from_magic_bytes(file_bytes)
        if not detected_mime or detected_mime not in SUPPORTED_MIME_TYPES:
            raise ImageValidationError(
                "Invalid image file header. Only genuine JPEG, PNG, and WebP files are permitted."
            )

        # 3. Decode verification with PIL (catches polyglots, truncated payloads, decompression bombs)
        try:
            with Image.open(io.BytesIO(file_bytes)) as img:
                # Check for decompression bomb before verify
                width, height = img.size
                if width * height > MAX_IMAGE_PIXELS:
                    raise ImageValidationError(
                        f"Decompression bomb detected: image resolution ({width}x{height} = {width*height} px) exceeds safety threshold of {MAX_IMAGE_PIXELS} px."
                    )
                img.verify()
        except ImageValidationError:
            raise
        except (UnidentifiedImageError, SyntaxError, ValueError) as err:
            raise ImageValidationError(f"Corrupted or invalid image data: {err}") from err
        except Image.DecompressionBombError as err:
            raise ImageValidationError(f"Decompression bomb detected: {err}") from err

        # 4. Re-open to read dimensions and verified format
        try:
            with Image.open(io.BytesIO(file_bytes)) as img:
                width, height = img.size
                img_format = (img.format or "").upper()

                if img_format not in SUPPORTED_FORMATS:
                    raise ImageValidationError(
                        f"Image format '{img_format}' is not in supported list: {', '.join(SUPPORTED_FORMATS)}."
                    )

                if width < MIN_DIMENSION_PX or height < MIN_DIMENSION_PX:
                    raise ImageValidationError(
                        f"Image dimensions ({width}x{height}) are below minimum allowed dimensions of {MIN_DIMENSION_PX}x{MIN_DIMENSION_PX}."
                    )

                if width > MAX_DIMENSION_PX or height > MAX_DIMENSION_PX:
                    raise ImageValidationError(
                        f"Image dimensions ({width}x{height}) exceed maximum allowed dimensions of {MAX_DIMENSION_PX}x{MAX_DIMENSION_PX}."
                    )
        except Exception as err:
            if isinstance(err, ImageValidationError):
                raise
            raise ImageValidationError(f"Failed to inspect image dimensions: {err}") from err

        # 5. Generate secure UUID storage key (prevents path traversal and name collisions)
        ext_map = {"JPEG": "jpg", "PNG": "png", "WEBP": "webp"}
        extension = ext_map.get(img_format, "bin")
        secure_filename = f"{uuid.uuid4().hex}.{extension}"

        return ValidatedImageMetadata(
            format=img_format,
            mime_type=detected_mime,
            width=width,
            height=height,
            size_bytes=size_bytes,
            storage_filename=secure_filename,
            raw_bytes=file_bytes,
            extension=extension,
        )

    @classmethod
    def validate(
        cls,
        file_bytes: bytes,
        claimed_mime: str | None = None,
        max_size: int = MAX_FILE_SIZE_BYTES,
    ) -> ValidatedImageMetadata:
        """Alias for validate_and_sanitize with optional claimed_mime check."""
        meta = cls.validate_and_sanitize(file_bytes, max_size=max_size)
        if claimed_mime:
            clean_claimed = claimed_mime.split(";")[0].strip().lower()
            if clean_claimed != meta.mime_type:
                if not (
                    (clean_claimed in ("image/pjpeg", "image/jpg") and meta.mime_type == "image/jpeg")
                    or clean_claimed == "application/octet-stream"
                ):
                    raise ImageValidationError(
                        f"MIME type mismatch: claimed '{claimed_mime}' but file contents identify as '{meta.mime_type}'."
                    )
        return meta


image_validation_service = ImageValidationService()

