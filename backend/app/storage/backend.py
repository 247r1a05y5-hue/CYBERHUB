"""Storage abstraction for local filesystem or cloud object stores."""
from __future__ import annotations

from abc import ABC, abstractmethod
import hashlib
import mimetypes
import os
from pathlib import Path
from typing import Optional, Tuple
import uuid

from app.core.config import get_settings

settings = get_settings()


class StorageBackend(ABC):
    @abstractmethod
    async def save(
        self,
        content: bytes,
        filename: Optional[str] = None,
        subfolder: str = "uploads",
    ) -> Tuple[str, str, int, Optional[str]]:
        """Save bytes and return (storage_ref, sha256, file_size_bytes, mime_type)."""
        pass

    @abstractmethod
    async def read(self, storage_ref: str) -> bytes:
        """Read content by storage_ref."""
        pass

    @abstractmethod
    async def delete(self, storage_ref: str) -> bool:
        """Delete file by storage_ref."""
        pass


class LocalFilesystemStorage(StorageBackend):
    def __init__(self, base_dir: Optional[str] = None) -> None:
        self.base_dir = Path(base_dir or settings.STORAGE_DIR or "./data/storage").resolve()
        self.base_dir.mkdir(parents=True, exist_ok=True)

    async def save(
        self,
        content: bytes,
        filename: Optional[str] = None,
        subfolder: str = "uploads",
    ) -> Tuple[str, str, int, Optional[str]]:
        sha256 = hashlib.sha256(content).hexdigest()
        size_bytes = len(content)
        
        ext = Path(filename).suffix if filename else ".bin"
        mime_type, _ = mimetypes.guess_type(filename or "data.bin")

        folder = self.base_dir / subfolder
        folder.mkdir(parents=True, exist_ok=True)

        storage_filename = f"{uuid.uuid4().hex}{ext}"
        target_path = folder / storage_filename
        
        target_path.write_bytes(content)
        storage_ref = f"{subfolder}/{storage_filename}"
        return storage_ref, sha256, size_bytes, mime_type

    async def read(self, storage_ref: str) -> bytes:
        file_path = (self.base_dir / storage_ref).resolve()
        # Security: ensure file_path is within base_dir (directory traversal protection)
        if not str(file_path).startswith(str(self.base_dir)):
            raise PermissionError("Path traversal attempt detected")
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {storage_ref}")
        return file_path.read_bytes()

    async def delete(self, storage_ref: str) -> bool:
        file_path = (self.base_dir / storage_ref).resolve()
        if not str(file_path).startswith(str(self.base_dir)):
            raise PermissionError("Path traversal attempt detected")
        if file_path.exists():
            file_path.unlink()
            return True
        return False


_storage_instance: Optional[StorageBackend] = None


def get_storage() -> StorageBackend:
    global _storage_instance
    if _storage_instance is None:
        _storage_instance = LocalFilesystemStorage()
    return _storage_instance
