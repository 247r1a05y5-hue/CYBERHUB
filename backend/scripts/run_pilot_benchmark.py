"""Phase 1 Real Dataset Pilot Benchmark on 100 Real LFW Images.

Runs exact pipeline:
Validation -> Face Detection -> Quality Validation -> Alignment -> Real ArcFace/InsightFace Embedding -> Qdrant Indexing
Measures throughput, failures, execution provider, resource usage, and estimates full dataset time.
"""
from __future__ import annotations

import asyncio
import os
import resource
import time
import uuid
from pathlib import Path
import numpy as np

from app.models.biometrics import FaceValidationStatus
from app.services.face_detection_service import face_detection_service
from app.services.face_embedding_service import face_embedding_service
from app.services.image_validation_service import ImageValidationError, ImageValidationService
from app.services.qdrant_service import qdrant_service


async def run_pilot():
    print("=" * 80)
    print("PHASE 1 — REAL DATASET PILOT BENCHMARK (100 REAL IMAGES)")
    print("=" * 80)

    # 1. Discover first 100 real images deterministically
    lfw_root = Path("data/lfw/identities") if Path("data/lfw/identities").exists() else Path("data/lfw")
    all_images = sorted(list(lfw_root.glob("*/*.jpg")))
    
    if len(all_images) < 100:
        print(f"FATAL: Insufficient images found ({len(all_images)} < 100)")
        return

    pilot_images = all_images[:100]
    print(f"Selected {len(pilot_images)} real LFW images from '{lfw_root}'.")

    # 2. Inspect active model & execution provider
    session = face_embedding_service._ensure_session()
    actual_providers = session.get_providers()
    active_provider = actual_providers[0] if actual_providers else "Unknown"
    model_path = face_embedding_service.model_path
    
    print(f"Model Pack:                 {face_embedding_service.model_pack}")
    print(f"Recognition Model:          {face_embedding_service.model_name}")
    print(f"Embedding Dimension:        {face_embedding_service.embedding_dimension}")
    print(f"Model File Path:            {model_path}")
    print(f"Actual Execution Provider:  {active_provider} (All active: {actual_providers})")
    print("-" * 80)

    # 3. Setup Tenant Context
    tenant_org_id = uuid.uuid4()
    isolated_other_org_id = uuid.uuid4()

    # 4. Metrics Tracking
    total_images_processed = 0
    accepted = 0
    rejected = 0
    zero_face = 0
    multiple_face = 0
    quality_failures = 0
    validation_failures = 0
    embedding_failures = 0
    vectors_indexed = 0

    rejection_reasons = {}
    inference_times = []

    t_start = time.perf_counter()

    for idx, img_path in enumerate(pilot_images, 1):
        total_images_processed += 1
        identity_name = img_path.parent.name.replace("_", " ")
        participant_id = uuid.uuid4()
        image_id = uuid.uuid4()

        try:
            raw_bytes = img_path.read_bytes()
        except Exception as e:
            rejected += 1
            validation_failures += 1
            rejection_reasons[img_path.name] = f"Read error: {e}"
            continue

        # Step 1: Image Validation
        try:
            meta = ImageValidationService.validate_and_sanitize(raw_bytes, filename=img_path.name)
        except ImageValidationError as val_err:
            rejected += 1
            validation_failures += 1
            rejection_reasons[img_path.name] = f"Image validation error: {val_err}"
            continue

        # Step 2 & 3: Face Detection & Quality Validation
        det_t0 = time.perf_counter()
        det = face_detection_service.detect_and_validate(raw_bytes)
        
        if not det.is_valid:
            rejected += 1
            if det.status == FaceValidationStatus.NO_FACE:
                zero_face += 1
                rejection_reasons[img_path.name] = "Zero face detected"
            elif det.status == FaceValidationStatus.MULTIPLE_FACES:
                multiple_face += 1
                rejection_reasons[img_path.name] = f"Multiple faces ({det.face_count}) detected"
            elif det.status == FaceValidationStatus.POOR_QUALITY:
                quality_failures += 1
                rejection_reasons[img_path.name] = f"Quality failure ({det.error_message})"
            else:
                rejection_reasons[img_path.name] = f"Detection rejection: {det.status.value}"
            continue

        # Step 4 & 5: Alignment & Real ArcFace Embedding
        emb_t0 = time.perf_counter()
        try:
            aligned_arr = det.primary_face.aligned_crop if det.primary_face else None
            if aligned_arr is not None:
                embedding_vec = face_embedding_service.embed_aligned_face(aligned_arr)
            else:
                embedding_vec = face_embedding_service.embed(raw_bytes)

            emb_t1 = time.perf_counter()
            inference_times.append(emb_t1 - emb_t0)
        except Exception as emb_err:
            rejected += 1
            embedding_failures += 1
            rejection_reasons[img_path.name] = f"Embedding error: {emb_err}"
            continue

        # Verify vector properties
        emb_arr = np.array(embedding_vec, dtype=np.float32)
        assert len(embedding_vec) == 512, f"Invalid dim: {len(embedding_vec)}"
        assert abs(np.linalg.norm(emb_arr) - 1.0) < 1e-3, f"Non-unit norm: {np.linalg.norm(emb_arr)}"

        # Step 6: Qdrant Indexing
        try:
            await qdrant_service.upsert_face_embedding(
                vector=embedding_vec,
                organization_id=tenant_org_id,
                participant_id=participant_id,
                image_id=image_id,
                model_name=face_embedding_service.model_name,
                model_version=face_embedding_service.model_version,
                metadata={
                    "original_filename": img_path.name,
                    "identity_name": identity_name,
                    "pilot_index": idx,
                },
            )
            vectors_indexed += 1
            accepted += 1
        except Exception as q_err:
            rejected += 1
            rejection_reasons[img_path.name] = f"Qdrant indexing error: {q_err}"

    t_end = time.perf_counter()
    total_elapsed_sec = t_end - t_start

    # Verify Tenant Isolation
    tenant_search = await qdrant_service.search_similar_faces(
        query_vector=embedding_vec,
        organization_id=tenant_org_id,
        limit=5,
        score_threshold=0.1,
    )
    isolated_search = await qdrant_service.search_similar_faces(
        query_vector=embedding_vec,
        organization_id=isolated_other_org_id,
        limit=5,
        score_threshold=0.1,
    )
    tenant_isolation_verified = (len(tenant_search) > 0 and len(isolated_search) == 0)

    # Performance stats
    images_per_second = total_images_processed / total_elapsed_sec if total_elapsed_sec > 0 else 0
    avg_inference_ms = (sum(inference_times) / len(inference_times) * 1000) if inference_times else 0

    # Memory usage
    rusage = resource.getrusage(resource.RUSAGE_SELF)
    max_rss_mb = rusage.ru_maxrss / 1024.0  # Linux ru_maxrss is in KB

    # 13,233 Dataset Estimation
    full_dataset_total_images = 13233
    estimated_seconds = full_dataset_total_images / images_per_second if images_per_second > 0 else 0
    est_hours = int(estimated_seconds // 3600)
    est_minutes = int((estimated_seconds % 3600) // 60)
    est_sec = int(estimated_seconds % 60)
    formatted_est_time = f"{est_hours}h {est_minutes}m {est_sec}s ({estimated_seconds:.1f} seconds)"

    status = "PASS" if accepted > 90 and vectors_indexed == accepted and tenant_isolation_verified else "FAIL"
    short_provider = "CUDA" if "CUDA" in active_provider else "CPU"

    print("\n" + "=" * 80)
    print("PILOT BENCHMARK RESULTS")
    print("=" * 80)
    print(f"Total Images Processed:       {total_images_processed}")
    print(f"Accepted:                     {accepted}")
    print(f"Rejected:                     {rejected}")
    print(f"  - Zero-face:                {zero_face}")
    print(f"  - Multiple-face:            {multiple_face}")
    print(f"  - Quality failures:         {quality_failures}")
    print(f"  - Validation failures:      {validation_failures}")
    print(f"  - Embedding failures:       {embedding_failures}")
    print(f"Vectors Indexed in Qdrant:    {vectors_indexed}")
    print(f"Tenant Isolation Verified:    {tenant_isolation_verified}")
    print(f"Total Elapsed Time:           {total_elapsed_sec:.2f} s")
    print(f"Throughput:                   {images_per_second:.2f} images/sec")
    print(f"Avg Embedding Time/Image:     {avg_inference_ms:.2f} ms")
    print(f"Peak Process RAM (RSS):       {max_rss_mb:.2f} MB")
    print(f"Actual ONNX Provider:         {active_provider}")
    print(f"Estimated Time (13,233 imgs): {formatted_est_time}")
    print("-" * 80)
    if rejection_reasons:
        print("Rejections Encountered:")
        for fname, reason in list(rejection_reasons.items())[:10]:
            print(f"  - {fname}: {reason}")
    print("-" * 80)
    print(f"PILOT_STATUS = {status}")
    print(f"THROUGHPUT = {images_per_second:.2f} images/sec")
    print(f"ESTIMATED_FULL_DATASET_TIME = {formatted_est_time}")
    print(f"ACTUAL_PROVIDER = {short_provider}")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(run_pilot())
