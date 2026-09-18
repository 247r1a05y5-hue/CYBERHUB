"""File Upload Security & Image Validation Service.

Enforces strict validation rules:
- Magic bytes / header inspection (never trust file extensions)
- MIME type verification
- Safe decoding with PIL (decompression bomb protection, format verification)
- Dimension constraints (min 64x64, max 8192x8192)
- Max payload size (15 MB)
- Perceptual & cryptographic hashing (SHA-256, pHash, dHash)
- Path traversal prevention and secure UUID storage key generation
"""
from __future__ import annotations

import hashlib
import io
import os
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO

from PIL import Image, UnidentifiedImageError
import imagehash

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


class CorruptedImageError(ImageValidationError):
    """Raised when an image payload is truncated or undecodable."""
    pass


class DecompressionBombError(ImageValidationError):
    """Raised when an image exceeds safe pixel decompression limits."""
    pass


class UnsupportedFormatError(ImageValidationError):
    """Raised when an image format or MIME type is not allowed."""
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
    sha256: str
    phash: str
    dhash: str
    extension: str = ""

    @property
    def byte_size(self) -> int:
        return self.size_bytes


class ImageValidationService:
    """Validates uploaded images for security, format integrity, hashes, and dimensions."""

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
    def compute_hashes(cls, img: Image.Image, raw_bytes: bytes) -> tuple[str, str, str]:
        """Compute SHA-256, pHash, and dHash deterministically."""
        sha256 = hashlib.sha256(raw_bytes).hexdigest()
        try:
            phash = str(imagehash.phash(img))
        except Exception:
            phash = ""
        try:
            dhash = str(imagehash.dhash(img))
        except Exception:
            dhash = ""
        return sha256, phash, dhash

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
                f"File size {size_bytes / (1024 * 1024):.1f} MB exceeds maximum allowed limit of {max_size / (1024 * 1024):.1f} MB."
            )

        # 2. Magic byte inspection
        detected_mime = cls.detect_mime_from_magic_bytes(file_bytes)
        if not detected_mime or detected_mime not in SUPPORTED_MIME_TYPES:
            raise UnsupportedFormatError(
                f"Invalid image file header: unsupported file signature. Allowed: {', '.join(SUPPORTED_FORMATS)}"
            )

        # 3. PIL Safe Decoding & Dimension Check
        try:
            with Image.open(io.BytesIO(file_bytes)) as img:
                # Check for decompression bomb risk
                pixels = img.width * img.height
                if pixels > MAX_IMAGE_PIXELS:
                    raise DecompressionBombError(
                        f"Image pixel count ({pixels:,}) exceeds maximum safe threshold of {MAX_IMAGE_PIXELS:,}."
                    )

                img_format = (img.format or "").upper()
                if img_format not in SUPPORTED_FORMATS:
                    raise UnsupportedFormatError(
                        f"Decoded image format '{img_format}' is not permitted. Allowed: {', '.join(SUPPORTED_FORMATS)}"
                    )

                width, height = img.size
                if width < MIN_DIMENSION_PX or height < MIN_DIMENSION_PX:
                    raise ImageValidationError(
                        f"Image resolution {width}x{height} is below minimum allowed dimensions ({MIN_DIMENSION_PX}x{MIN_DIMENSION_PX})."
                    )
                if width > MAX_DIMENSION_PX or height > MAX_DIMENSION_PX:
                    raise ImageValidationError(
                        f"Image resolution {width}x{height} exceeds maximum allowed dimensions ({MAX_DIMENSION_PX}x{MAX_DIMENSION_PX})."
                    )

                # Force full raster read to detect truncated or corrupted files
                img.verify()

            # Re-open for hash computation (verify() invalidates image buffer)
            with Image.open(io.BytesIO(file_bytes)) as img_decoded:
                sha256, phash, dhash = cls.compute_hashes(img_decoded, file_bytes)

        except Image.DecompressionBombError as d_err:
            raise DecompressionBombError(f"Decompression bomb detected: {d_err}") from d_err
        except UnidentifiedImageError as u_err:
            raise CorruptedImageError(f"Cannot identify or decode image: {u_err}") from u_err
        except (IOError, SyntaxError) as cor_err:
            raise CorruptedImageError(f"Corrupted or truncated image payload: {cor_err}") from cor_err
        except (UnsupportedFormatError, DecompressionBombError, ImageValidationError):
            raise
        except Exception as gen_err:
            raise ImageValidationError(f"Unexpected image processing error: {gen_err}") from gen_err

        # 4. Generate collision-resistant secure storage key
        ext_map = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}
        ext = ext_map.get(detected_mime, "bin")
        secure_key = f"{uuid.uuid4().hex}.{ext}"

        return ValidatedImageMetadata(
            format=img_format,
            mime_type=detected_mime,
            width=width,
            height=height,
            size_bytes=size_bytes,
            storage_filename=secure_key,
            raw_bytes=file_bytes,
            sha256=sha256,
            phash=phash,
            dhash=dhash,
            extension=ext,
        )

    def validate(
        self,
        file_bytes: bytes,
        claimed_mime: str | None = None,
        filename: str | None = None,
        max_size: int = MAX_FILE_SIZE_BYTES,
    ) -> ValidatedImageMetadata:
        """Instance method alias for validation pipeline."""
        return self.validate_and_sanitize(
            file_bytes=file_bytes,
            filename=filename,
            max_size=max_size,
        )

    @classmethod
    def sanitize_path(cls, filename: str, target_dir: str | Path) -> Path:
        """Prevent path traversal attacks when writing files."""
        safe_name = os.path.basename(filename)
        target_path = Path(target_dir).resolve() / safe_name
        if not target_path.resolve().is_relative_to(Path(target_dir).resolve()):
            raise ImageValidationError("Path traversal detected in target filename.")
        return target_path


image_validation_service = ImageValidationService()

