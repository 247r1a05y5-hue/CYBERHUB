"""Secure File Storage Service.

Provides isolated filesystem storage with:
- Non-predictable UUID storage identifiers
- Strict path traversal defense
- Cryptographic SHA-256 digest validation
- Safe deletion and cleanup
"""
from __future__ import annotations

import hashlib
import os
import shutil
import uuid
from pathlib import Path
from typing import BinaryIO

from app.core.config import settings


class StorageSecurityError(Exception):
    """Raised on security violation (e.g. path traversal attempt)."""
    pass


class SecureStorageService:
    """Manages secure file persistence on isolated storage."""

    def __init__(self, base_dir: str | Path | None = None) -> None:
        self.base_dir = Path(base_dir or settings.STORAGE_PATH).resolve()
        self.reference_dir = self.base_dir / "references"
        self.evidence_dir = self.base_dir / "evidence"
        self.reports_dir = self.base_dir / "reports"

        # Initialize storage directories
        for directory in (self.reference_dir, self.evidence_dir, self.reports_dir):
            directory.mkdir(parents=True, exist_ok=True)

    def _resolve_safe_path(self, target_dir: Path, filename: str) -> Path:
        """Resolve path and verify it stays strictly within the target directory."""
        # Clean filename: basename only
        clean_name = os.path.basename(filename)
        if clean_name != filename or ".." in filename:
            raise StorageSecurityError(f"Path traversal detected in filename: '{filename}'")

        resolved = (target_dir / clean_name).resolve()
        if not str(resolved).startswith(str(target_dir.resolve())):
            raise StorageSecurityError(f"Target path '{resolved}' escaped base directory '{target_dir}'")

        return resolved

    def save_reference_image(self, file_bytes: bytes, filename: str) -> tuple[str, str]:
        """Save reference image bytes. Returns (storage_path, sha256_hash)."""
        safe_path = self._resolve_safe_path(self.reference_dir, filename)
        sha256 = hashlib.sha256(file_bytes).hexdigest()

        with open(safe_path, "wb") as f:
            f.write(file_bytes)

        return str(safe_path), sha256

    def save_evidence_artifact(self, file_bytes: bytes, filename: str) -> tuple[str, str]:
        """Save captured evidence artifact bytes. Returns (storage_path, sha256_hash)."""
        safe_path = self._resolve_safe_path(self.evidence_dir, filename)
        sha256 = hashlib.sha256(file_bytes).hexdigest()

        with open(safe_path, "wb") as f:
            f.write(file_bytes)

        return str(safe_path), sha256

    def read_file(self, file_path: str) -> bytes:
        """Read bytes from storage path with safety boundary verification."""
        resolved = Path(file_path).resolve()
        if not str(resolved).startswith(str(self.base_dir)):
            raise StorageSecurityError(f"Cannot read file outside storage boundary: '{resolved}'")

        if not resolved.exists():
            raise FileNotFoundError(f"Storage file not found: {resolved}")

        with open(resolved, "rb") as f:
            return f.read()

    def load_evidence_artifact(self, file_path: str) -> bytes:
        """Alias for read_file to load evidence artifact bytes securely."""
        return self.read_file(file_path)

    def delete_file(self, file_path: str) -> bool:
        """Securely delete file. Returns True if deleted, False if did not exist."""
        try:
            resolved = Path(file_path).resolve()
            if not str(resolved).startswith(str(self.base_dir)):
                raise StorageSecurityError(f"Cannot delete file outside storage boundary: '{resolved}'")

            if resolved.exists():
                resolved.unlink()
                return True
            return False
        except StorageSecurityError:
            raise
        except Exception:
            return False


    def save_file(self, org_id: str | uuid.UUID, investigation_id: str | uuid.UUID, file_bytes: bytes, extension: str = "png") -> str:
        """Save file in secure storage and return storage key/path."""
        filename = self.generate_storage_key(str(org_id), str(investigation_id), extension)
        safe_path = self._resolve_safe_path(self.reference_dir, filename)
        with open(safe_path, "wb") as f:
            f.write(file_bytes)
        return str(safe_path)

    def file_exists(self, file_path: str) -> bool:
        """Check if file exists within storage boundary."""
        try:
            resolved = Path(file_path).resolve()
            return resolved.exists() and str(resolved).startswith(str(self.base_dir))
        except Exception:
            return False

    def generate_storage_key(self, org_id: str, investigation_id: str, extension: str) -> str:
        """Generate safe, non-predictable UUID storage key preventing directory traversal."""
        clean_org = "".join(c for c in str(org_id) if c.isalnum() or c in ("-", "_"))
        clean_inv = "".join(c for c in str(investigation_id) if c.isalnum() or c in ("-", "_"))
        clean_ext = extension.lstrip(".").lower()
        if not clean_ext:
            clean_ext = "bin"
        return f"{clean_org}_{clean_inv}_{uuid.uuid4().hex}.{clean_ext}"


secure_storage_service = SecureStorageService()
