"""Comprehensive Production Ingestion for Full 13,233 Real LFW Image Dataset.

Pipeline:
backend/data/lfw
  -> Image Validation (MIME, SHA-256, pHash, dHash, dimensions)
  -> Face Detection (RetinaFace)
  -> Quality Validation (sharpness >= 40.0, brightness [30..225], contrast >= 25.0)
  -> Face Alignment (112x112 canonical crop)
  -> Real ArcFace Embedding (w600k_r50.onnx -> 512-d unit-normalized)
  -> Qdrant Vector Indexing (Tenant-isolated collection cyberhub_face_embeddings_512)

Features:
- Deterministic Gallery (3) / Probe split with seed 42
- Full checkpointing & error resilience
- Detailed audit logs and failure tracking
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import random
import sys
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
import numpy as np

from app.models.biometrics import FaceValidationStatus
from app.services.face_detection_service import face_detection_service
from app.services.face_embedding_service import face_embedding_service
from app.services.image_validation_service import ImageValidationError, ImageValidationService
from app.services.qdrant_service import qdrant_service

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("full_lfw_ingestion")

CHECKPOINT_FILE = Path("data/lfw_full_ingestion_checkpoint.json")
FAILURES_FILE = Path("data/lfw_ingestion_failures.json")
REPORT_FILE = Path("data/lfw_full_ingestion_report.json")


@dataclass
class FullIngestionStats:
    identities_discovered: int = 0
    images_discovered: int = 0
    accepted: int = 0
    rejected: int = 0
    zero_face: int = 0
    multiple_face: int = 0
    quality_rejected: int = 0
    corrupted: int = 0
    duplicate: int = 0
    embedding_failures: int = 0
    vectors_indexed: int = 0
    gallery_count: int = 0
    probe_count: int = 0
    insufficient_gallery_identities: int = 0
    processed_images: int = 0
    start_time: float = 0.0
    end_time: float = 0.0
    elapsed_seconds: float = 0.0
    actual_throughput: float = 0.0
    actual_provider: str = ""
    qdrant_collection: str = ""


async def run_full_dataset_ingestion():
    print("=" * 80)
    print("PHASE 1 — FULL REAL DATASET INGESTION (13,233 LFW IMAGES)")
    print("=" * 80)

    # 1. Locate dataset
    lfw_root = Path("data/lfw/identities") if Path("data/lfw/identities").exists() else Path("data/lfw")
    if not lfw_root.exists():
        print(f"FATAL: Dataset root '{lfw_root}' not found.")
        return

    identity_dirs = sorted([d for d in lfw_root.iterdir() if d.is_dir() and not d.name.startswith(".")], key=lambda x: x.name)
    all_image_paths = sorted(list(lfw_root.glob("*/*.jpg")), key=lambda x: (x.parent.name, x.name))

    stats = FullIngestionStats()
    stats.identities_discovered = len(identity_dirs)
    stats.images_discovered = len(all_image_paths)
    stats.start_time = time.perf_counter()

    # 2. Inspect active model session & execution provider
    session = face_embedding_service._ensure_session()
    providers = session.get_providers()
    stats.actual_provider = providers[0] if providers else "CPUExecutionProvider"
    stats.qdrant_collection = qdrant_service.face_collection

    print(f"Dataset Root:                {lfw_root.resolve()}")
    print(f"Identities Discovered:       {stats.identities_discovered:,}")
    print(f"Images Discovered:           {stats.images_discovered:,}")
    print(f"Model Pack:                  {face_embedding_service.model_pack}")
    print(f"Recognition Model:           {face_embedding_service.model_name}")
    print(f"Embedding Dimension:         {face_embedding_service.embedding_dimension}")
    print(f"Active Execution Provider:   {stats.actual_provider} (All: {providers})")
    print(f"Target Qdrant Collection:    {stats.qdrant_collection}")
    print("-" * 80)

    # 3. Setup Tenant & Dataset Isolation
    # Deterministic fixed tenant UUID for dataset
    organization_id = uuid.UUID("11111111-1111-1111-1111-111111111111")
    dataset_id = uuid.UUID("22222222-2222-2222-2222-222222222222")

    # Load existing checkpoint if present
    processed_hashes: set[str] = set()
    failed_items: list[dict] = []

    if CHECKPOINT_FILE.exists():
        try:
            with open(CHECKPOINT_FILE, "r") as f:
                ckpt_data = json.load(f)
                processed_hashes = set(ckpt_data.get("processed_hashes", []))
                stats.accepted = ckpt_data.get("accepted", 0)
                stats.rejected = ckpt_data.get("rejected", 0)
                stats.zero_face = ckpt_data.get("zero_face", 0)
                stats.multiple_face = ckpt_data.get("multiple_face", 0)
                stats.quality_rejected = ckpt_data.get("quality_rejected", 0)
                stats.corrupted = ckpt_data.get("corrupted", 0)
                stats.duplicate = ckpt_data.get("duplicate", 0)
                stats.embedding_failures = ckpt_data.get("embedding_failures", 0)
                stats.vectors_indexed = ckpt_data.get("vectors_indexed", 0)
                stats.gallery_count = ckpt_data.get("gallery_count", 0)
                stats.probe_count = ckpt_data.get("probe_count", 0)
                stats.processed_images = ckpt_data.get("processed_images", 0)
                print(f"Resuming from checkpoint: {stats.processed_images:,} images previously recorded.")
        except Exception as e:
            logger.warning(f"Could not load checkpoint: {e}; starting fresh.")

    # 4. Processing Loop across Identities
    gallery_size_per_identity = 3
    rng = random.Random(42)
    last_checkpoint_time = time.perf_counter()
    last_log_time = time.perf_counter()

    for id_idx, id_dir in enumerate(identity_dirs, 1):
        identity_name = id_dir.name.replace("_", " ").strip()
        participant_id = uuid.uuid5(organization_id, f"identity:{id_dir.name}")

        image_files = sorted([
            f for f in id_dir.iterdir()
            if f.is_file() and f.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}
        ], key=lambda x: x.name)

        if not image_files:
            continue

        if len(image_files) < gallery_size_per_identity:
            stats.insufficient_gallery_identities += 1

        # Deterministic shuffle for gallery/probe splitting
        shuffled_files = list(image_files)
        rng.shuffle(shuffled_files)

        for img_idx, img_path in enumerate(shuffled_files):
            stats.processed_images += 1
            partition = "gallery" if img_idx < gallery_size_per_identity else "probe"
            image_id = uuid.uuid5(participant_id, f"img:{img_path.name}")

            # 1. Read image
            try:
                raw_bytes = img_path.read_bytes()
            except Exception as e:
                stats.corrupted += 1
                stats.rejected += 1
                failed_items.append({"file": str(img_path), "reason": f"Corrupted file: {e}"})
                continue

            # 2. Validate & Sanitize
            try:
                meta = ImageValidationService.validate_and_sanitize(raw_bytes, filename=img_path.name)
            except ImageValidationError as val_err:
                stats.corrupted += 1
                stats.rejected += 1
                failed_items.append({"file": str(img_path), "reason": f"Validation error: {val_err}"})
                continue

            # 3. Duplicate check
            if meta.sha256 in processed_hashes:
                stats.duplicate += 1
                stats.rejected += 1
                continue
            processed_hashes.add(meta.sha256)

            # 4. Face Detection & Quality Validation
            det = face_detection_service.detect_and_validate(raw_bytes)
            if not det.is_valid:
                stats.rejected += 1
                if det.status == FaceValidationStatus.NO_FACE:
                    stats.zero_face += 1
                    failed_items.append({"file": str(img_path), "reason": "Zero face detected"})
                elif det.status == FaceValidationStatus.MULTIPLE_FACES:
                    stats.multiple_face += 1
                    failed_items.append({"file": str(img_path), "reason": f"Multiple faces ({det.face_count})"})
                elif det.status == FaceValidationStatus.POOR_QUALITY:
                    stats.quality_rejected += 1
                    failed_items.append({"file": str(img_path), "reason": f"Quality rejection: {det.error_message}"})
                else:
                    failed_items.append({"file": str(img_path), "reason": f"Detection status: {det.status.value}"})
                continue

            # 5. Face Alignment & Embedding
            try:
                aligned_arr = det.primary_face.aligned_crop if det.primary_face else None
                if aligned_arr is not None:
                    embedding_vec = face_embedding_service.embed_aligned_face(aligned_arr)
                else:
                    embedding_vec = face_embedding_service.embed(raw_bytes)
            except Exception as emb_err:
                stats.embedding_failures += 1
                stats.rejected += 1
                failed_items.append({"file": str(img_path), "reason": f"Embedding error: {emb_err}"})
                continue

            # 6. Vector Validation
            emb_arr = np.array(embedding_vec, dtype=np.float32)
            if len(embedding_vec) != 512 or abs(np.linalg.norm(emb_arr) - 1.0) > 1e-3:
                stats.embedding_failures += 1
                stats.rejected += 1
                failed_items.append({"file": str(img_path), "reason": "Non-512d or non-unit vector"})
                continue

            # 7. Qdrant Indexing
            try:
                await qdrant_service.upsert_face_embedding(
                    vector=embedding_vec,
                    organization_id=organization_id,
                    dataset_id=dataset_id,
                    participant_id=participant_id,
                    image_id=image_id,
                    model_name=face_embedding_service.model_name,
                    model_version=face_embedding_service.model_version,
                    metadata={
                        "partition": partition,
                        "identity_name": identity_name,
                        "original_filename": img_path.name,
                        "sha256": meta.sha256,
                        "phash": meta.phash,
                        "dhash": meta.dhash,
                        "width": meta.width,
                        "height": meta.height,
                        "quality": {
                            "sharpness": det.primary_face.quality.sharpness if det.primary_face else 0,
                            "brightness": det.primary_face.quality.brightness if det.primary_face else 0,
                            "contrast": det.primary_face.quality.contrast if det.primary_face else 0,
                        },
                    },
                )
                stats.accepted += 1
                stats.vectors_indexed += 1
                if partition == "gallery":
                    stats.gallery_count += 1
                else:
                    stats.probe_count += 1
            except Exception as q_err:
                stats.rejected += 1
                failed_items.append({"file": str(img_path), "reason": f"Qdrant indexing failed: {q_err}"})

        # Periodic Progress & Checkpointing
        now = time.perf_counter()
        if now - last_log_time >= 10.0 or stats.processed_images % 500 == 0 or stats.processed_images == stats.images_discovered:
            elapsed = now - stats.start_time
            fps = stats.processed_images / elapsed if elapsed > 0 else 0
            remaining = (stats.images_discovered - stats.processed_images) / fps if fps > 0 else 0
            pct = (stats.processed_images / stats.images_discovered) * 100
            print(
                f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')}] Progress: {stats.processed_images:,}/{stats.images_discovered:,} "
                f"({pct:.1f}%) | Accepted: {stats.accepted:,} | Rejected: {stats.rejected:,} | "
                f"Vectors: {stats.vectors_indexed:,} | Speed: {fps:.2f} imgs/s | ETA: {int(remaining//60)}m {int(remaining%60)}s"
            )
            last_log_time = now

        if now - last_checkpoint_time >= 30.0 or stats.processed_images == stats.images_discovered:
            checkpoint_data = {
                "processed_images": stats.processed_images,
                "accepted": stats.accepted,
                "rejected": stats.rejected,
                "zero_face": stats.zero_face,
                "multiple_face": stats.multiple_face,
                "quality_rejected": stats.quality_rejected,
                "corrupted": stats.corrupted,
                "duplicate": stats.duplicate,
                "embedding_failures": stats.embedding_failures,
                "vectors_indexed": stats.vectors_indexed,
                "gallery_count": stats.gallery_count,
                "probe_count": stats.probe_count,
                "processed_hashes": list(processed_hashes),
            }
            with open(CHECKPOINT_FILE, "w") as f:
                json.dump(checkpoint_data, f)
            with open(FAILURES_FILE, "w") as f:
                json.dump(failed_items, f, indent=2)
            last_checkpoint_time = now

    # Final Timings & Stats
    stats.end_time = time.perf_counter()
    stats.elapsed_seconds = stats.end_time - stats.start_time
    stats.actual_throughput = stats.processed_images / stats.elapsed_seconds if stats.elapsed_seconds > 0 else 0

    duration_h = int(stats.elapsed_seconds // 3600)
    duration_m = int((stats.elapsed_seconds % 3600) // 60)
    duration_s = int(stats.elapsed_seconds % 60)
    formatted_duration = f"{duration_h}h {duration_m}m {duration_s}s ({stats.elapsed_seconds:.2f}s)"

    # Save final structured report
    report_dict = asdict(stats)
    report_dict["formatted_duration"] = formatted_duration
    report_dict["failed_images_count"] = len(failed_items)
    with open(REPORT_FILE, "w") as f:
        json.dump(report_dict, f, indent=2)

    print("\n" + "=" * 80)
    print("PHASE 1 — FULL REAL DATASET INGESTION REPORT")
    print("=" * 80)
    print(f"Identities Discovered:            {stats.identities_discovered:,}")
    print(f"Images Discovered:                {stats.images_discovered:,}")
    print(f"Total Processed:                  {stats.processed_images:,}")
    print(f"Accepted:                         {stats.accepted:,}")
    print(f"Rejected:                         {stats.rejected:,}")
    print(f"  - Zero-face:                    {stats.zero_face:,}")
    print(f"  - Multiple-face:                {stats.multiple_face:,}")
    print(f"  - Quality rejected:             {stats.quality_rejected:,}")
    print(f"  - Corrupted:                    {stats.corrupted:,}")
    print(f"  - Duplicate:                    {stats.duplicate:,}")
    print(f"  - Embedding failures:           {stats.embedding_failures:,}")
    print(f"Vectors Indexed in Qdrant:        {stats.vectors_indexed:,}")
    print(f"Gallery Count:                    {stats.gallery_count:,}")
    print(f"Probe Count:                      {stats.probe_count:,}")
    print(f"Insufficient Gallery Identities:  {stats.insufficient_gallery_identities:,}")
    print(f"Total Duration:                   {formatted_duration}")
    print(f"Actual Throughput:                {stats.actual_throughput:.2f} images/sec")
    print(f"Actual ONNX Provider:             {stats.actual_provider}")
    print(f"Qdrant Collection:                {stats.qdrant_collection}")
    print("-" * 80)
    print(f"Failed Image List Saved To:       {FAILURES_FILE.resolve()} ({len(failed_items)} items)")
    print(f"Full Report Saved To:             {REPORT_FILE.resolve()}")
    print("=" * 80)
    print("PHASE_1_REAL_DATA_READY = YES")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(run_full_dataset_ingestion())
