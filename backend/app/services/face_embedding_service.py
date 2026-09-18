"""Local ArcFace / InsightFace Biometric Embedding Service.

Features:
- Official InsightFace buffalo_l pack / w600k_r50.onnx recognition model (ResNet-50)
- 512-dimensional normalized biometric embeddings
- ONNX Runtime local execution with CPU / CUDA execution provider
- Canonical 112x112 input tensor preprocessing
- Strict L2 normalization: ||v||_2 = 1.0
- In-process session caching
- Strict failure when model weights are missing (never silent random/mock embeddings)
"""
from __future__ import annotations

import hashlib
import io
import logging
import os
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

from app.core.config import settings

logger = logging.getLogger(__name__)


class ModelWeightsNotFoundError(FileNotFoundError):
    """Raised when the specified InsightFace/ArcFace ONNX model weights file is missing."""
    pass


class FaceEmbeddingService:
    """Production local InsightFace recognition service (buffalo_l / w600k_r50.onnx)."""

    def __init__(self, model_path: str | Path | None = None) -> None:
        self.model_family = "InsightFace"
        self.model_pack = "buffalo_l"
        self.model_name = "w600k_r50.onnx"
        self.model_version = "v1.0"
        self.embedding_dimension = 512
        self._custom_model_path = Path(model_path) if model_path else None
        self._session = None
        self._active_model_path: Path | None = None
        self._model_sha256: str | None = None
        self._initialized = False

    @property
    def model_path(self) -> Path:
        """Resolve the active model weights path."""
        if self._custom_model_path is not None:
            return self._custom_model_path

        if self._active_model_path and self._active_model_path.exists():
            return self._active_model_path

        candidates = []
        cfg_path = getattr(settings, "INSIGHTFACE_MODEL_PATH", None) or getattr(settings, "ARCFACE_MODEL_PATH", None)
        if cfg_path:
            candidates.append(Path(cfg_path))

        candidates.extend([
            Path("models/insightface/buffalo_l/w600k_r50.onnx"),
            Path("backend/models/insightface/buffalo_l/w600k_r50.onnx"),
            Path.home() / ".insightface/models/buffalo_l/w600k_r50.onnx",
            Path.home() / ".cache/insightface/models/buffalo_l/w600k_r50.onnx",
        ])

        for cand in candidates:
            if cand.exists() and cand.is_file() and cand.stat().st_size > 0:
                self._active_model_path = cand
                return cand

        # Fallback to primary expected path
        return candidates[0] if candidates else Path("models/insightface/buffalo_l/w600k_r50.onnx")

    @property
    def is_model_available(self) -> bool:
        """Check if InsightFace ONNX weights are present on disk."""
        p = self.model_path
        return p.exists() and p.is_file() and p.stat().st_size > 0

    @property
    def model_sha256(self) -> str:
        """Compute and return SHA-256 hash of the active ONNX model weights."""
        if self._model_sha256:
            return self._model_sha256
        if not self.is_model_available:
            return ""
        
        h = hashlib.sha256()
        with open(self.model_path, "rb") as f:
            while chunk := f.read(1024 * 1024):
                h.update(chunk)
        self._model_sha256 = h.hexdigest()
        return self._model_sha256

    def _ensure_session(self) -> Any:
        """Initialize and cache ONNX runtime session."""
        if self._session is not None:
            return self._session

        if not self.is_model_available:
            raise ModelWeightsNotFoundError(
                f"InsightFace recognition model weights not found at '{self.model_path}'. "
                f"Ensure the buffalo_l / w600k_r50.onnx model is present to enable real biometric inference."
            )

        try:
            import onnxruntime as ort

            providers = ["CUDAExecutionProvider", "CPUExecutionProvider"]
            available = ort.get_available_providers()
            active_providers = [p for p in providers if p in available]

            self._session = ort.InferenceSession(
                str(self.model_path),
                providers=active_providers,
            )
            self._initialized = True
            logger.info(
                f"InsightFace {self.model_name} ONNX session initialized from {self.model_path} "
                f"with providers: {active_providers} (SHA-256: {self.model_sha256[:16]}...)"
            )
            return self._session
        except Exception as e:
            logger.error(f"Failed to load ONNX InsightFace session: {e}")
            raise

    def preprocess_aligned_face(self, face_arr: np.ndarray) -> np.ndarray:
        """Preprocess (112, 112, 3) normalized float array into NCHW InsightFace input tensor."""
        # Convert range [0, 1] to [-1, 1] standard InsightFace normalization: (x - 127.5) / 127.5
        norm = (face_arr * 255.0 - 127.5) / 127.5
        # Transpose from (H, W, C) to (C, H, W)
        chw = np.transpose(norm, (2, 0, 1))
        # Add batch dimension: (1, 3, 112, 112)
        nchw = np.expand_dims(chw, axis=0).astype(np.float32)
        return nchw

    def embed_aligned_face(self, aligned_face_arr: np.ndarray) -> list[float]:
        """Generate 512-d L2-normalized embedding from aligned (112, 112, 3) face array."""
        if aligned_face_arr.shape[:2] != (112, 112):
            # Resize if necessary
            pil_face = Image.fromarray((aligned_face_arr * 255).astype(np.uint8))
            resized = pil_face.resize((112, 112), Image.Resampling.BILINEAR)
            aligned_face_arr = np.asarray(resized, dtype=np.float32) / 255.0

        session = self._ensure_session()
        input_tensor = self.preprocess_aligned_face(aligned_face_arr)
        input_name = session.get_inputs()[0].name
        outputs = session.run(None, {input_name: input_tensor})
        raw_vec = outputs[0][0].astype(np.float32)

        # Strict L2 normalization: v / ||v||_2
        norm_val = float(np.linalg.norm(raw_vec))
        if norm_val > 1e-8:
            norm_vec = raw_vec / norm_val
        else:
            norm_vec = raw_vec

        return [round(float(x), 6) for x in norm_vec.tolist()]

    def embed(self, image_bytes: bytes) -> list[float]:
        """Full pipeline: decode image, detect primary face, align, and generate 512-d embedding."""
        from app.services.face_detection_service import face_detection_service

        det_result = face_detection_service.detect_and_validate(image_bytes)
        if not det_result.is_valid or not det_result.primary_face:
            raise ValueError(det_result.error_message or "Face validation failed.")

        aligned_arr = det_result.primary_face.aligned_crop
        if aligned_arr is None:
            raise ValueError("Face alignment crop was not generated.")

        return self.embed_aligned_face(aligned_arr)


# Global singleton face embedding service
face_embedding_service = FaceEmbeddingService()
