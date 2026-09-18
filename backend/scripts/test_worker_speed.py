"""High-throughput multiprocessing test for Phase 1 Ingestion pipeline."""
import time
import uuid
from pathlib import Path
from multiprocessing import Pool, cpu_count
import numpy as np

from app.models.biometrics import FaceValidationStatus
from app.services.face_detection_service import FaceDetectionService
from app.services.face_embedding_service import FaceEmbeddingService
from app.services.image_validation_service import ImageValidationError, ImageValidationService

_detector = None
_embedder = None

def init_worker():
    global _detector, _embedder
    _detector = FaceDetectionService()
    _embedder = FaceEmbeddingService()
    _embedder._ensure_session()

def process_image(item):
    idx, img_path_str, partition, identity_name = item
    img_path = Path(img_path_str)
    
    try:
        raw_bytes = img_path.read_bytes()
    except Exception as e:
        return {"status": "corrupted", "filename": img_path.name, "error": str(e)}

    try:
        meta = ImageValidationService.validate_and_sanitize(raw_bytes, filename=img_path.name)
    except ImageValidationError as val_err:
        return {"status": "validation_error", "filename": img_path.name, "error": str(val_err)}

    det = _detector.detect_and_validate(raw_bytes)
    if not det.is_valid:
        if det.status == FaceValidationStatus.NO_FACE:
            return {"status": "zero_face", "filename": img_path.name, "sha256": meta.sha256}
        elif det.status == FaceValidationStatus.MULTIPLE_FACES:
            return {"status": "multi_face", "filename": img_path.name, "sha256": meta.sha256, "count": det.face_count}
        elif det.status == FaceValidationStatus.POOR_QUALITY:
            return {"status": "poor_quality", "filename": img_path.name, "sha256": meta.sha256, "error": det.error_message}
        return {"status": "detection_rejected", "filename": img_path.name, "sha256": meta.sha256}

    aligned_arr = det.primary_face.aligned_crop if det.primary_face else None
    try:
        if aligned_arr is not None:
            emb = _embedder.embed_aligned_face(aligned_arr)
        else:
            emb = _embedder.embed(raw_bytes)
    except Exception as emb_err:
        return {"status": "embedding_error", "filename": img_path.name, "sha256": meta.sha256, "error": str(emb_err)}

    return {
        "status": "accepted",
        "filename": img_path.name,
        "sha256": meta.sha256,
        "phash": meta.phash,
        "dhash": meta.dhash,
        "width": meta.width,
        "height": meta.height,
        "size_bytes": meta.size_bytes,
        "embedding": emb,
        "partition": partition,
        "identity_name": identity_name,
    }

def test_speed():
    lfw_root = Path("data/lfw/identities") if Path("data/lfw/identities").exists() else Path("data/lfw")
    all_images = sorted(list(lfw_root.glob("*/*.jpg")))[:200]
    items = [(i, str(p), "gallery", p.parent.name) for i, p in enumerate(all_images)]

    num_workers = min(8, cpu_count())
    print(f"Testing multiprocessing with {num_workers} workers on 200 images...")
    t0 = time.perf_counter()
    with Pool(num_workers, initializer=init_worker) as pool:
        results = pool.map(process_image, items)
    t1 = time.perf_counter()
    elapsed = t1 - t0
    fps = len(items) / elapsed
    accepted = sum(1 for r in results if r["status"] == "accepted")
    print(f"Processed {len(items)} images in {elapsed:.2f}s ({fps:.2f} imgs/sec). Accepted: {accepted}/{len(items)}")

if __name__ == "__main__":
    test_speed()
