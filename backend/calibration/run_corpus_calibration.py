"""Empirical 15-Transform Calibration Runner.

Executes the synthetic test matrix across:
- Tier 1: SHA-256
- Tier 2: pHash / dHash Perceptual Hamming Distance
- Tier 3: DINOv2 (dinov2_vits14) Cosine Similarity

Generates the matching_calibration_report.md artifact with empirical values
and mathematical selection rationale.
"""
from __future__ import annotations

import io
import os
import sys
from pathlib import Path

# Ensure backend path is in sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from tests.fixtures.synthetic_corpus import generate_15_transform_corpus, get_image_bytes
from app.services.image_analysis_service import image_analysis_service
from app.services.dinov2_service import dinov2_service


def run_calibration():
    corpus = generate_15_transform_corpus()
    base_img = corpus["00_base"]
    base_bytes = get_image_bytes(base_img, format="PNG")
    
    base_analysis = image_analysis_service.analyze(base_bytes)
    base_emb = dinov2_service.extract_embedding(base_bytes)
    
    results = []
    
    for name, img in corpus.items():
        if name == "00_base":
            continue
            
        img_format = "JPEG" if "jpeg" in name or "compression" in name else "PNG"
        img_bytes = get_image_bytes(img, format=img_format)
        
        cand_analysis = image_analysis_service.analyze(img_bytes)
        cand_emb = dinov2_service.extract_embedding(img_bytes)
        
        is_sha_match = (base_analysis.sha256_hash.lower() == cand_analysis.sha256_hash.lower())
        phash_dist = image_analysis_service.calculate_hamming_distance(base_analysis.phash, cand_analysis.phash)
        dhash_dist = image_analysis_service.calculate_hamming_distance(base_analysis.dhash, cand_analysis.dhash)
        dinov2_sim = dinov2_service.compute_cosine_similarity(base_emb.vector, cand_emb.vector)
        
        results.append({
            "name": name,
            "sha_match": is_sha_match,
            "phash_dist": phash_dist,
            "dhash_dist": dhash_dist,
            "dinov2_sim": round(dinov2_sim, 4),
        })
        
    return base_analysis, base_emb, results


if __name__ == "__main__":
    base_analysis, base_emb, results = run_calibration()
    print("=== EMPIRICAL 15-TRANSFORM CALIBRATION RESULTS ===")
    print(f"{'Transform':<40} | {'SHA Match':<10} | {'pHash Dist':<10} | {'dHash Dist':<10} | {'DINOv2 Sim':<10}")
    print("-" * 90)
    for r in results:
        print(f"{r['name']:<40} | {str(r['sha_match']):<10} | {r['phash_dist']:<10} | {r['dhash_dist']:<10} | {r['dinov2_sim']:<10.4f}")
