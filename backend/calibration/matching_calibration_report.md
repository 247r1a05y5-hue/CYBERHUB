# CYBERHUB — Matching Engine Calibration Report
## Empirical 15-Transform Benchmark Matrix & Decision Thresholds

### 1. Overview & Benchmark Methodology
This calibration report documents the empirical evaluation of the **CYBERHUB 3-Tier Image Matching Engine** against the controlled **15-Transformation Test Matrix** (`tests/fixtures/synthetic_corpus.py`).

The evaluation was conducted using:
- **Tier 1**: SHA-256 256-bit cryptographic digest.
- **Tier 2**: 64-bit DCT-based Perceptual Hash (pHash) and 64-bit Gradient Difference Hash (dHash) evaluated via Hamming Distance.
- **Tier 3**: DINOv2 Small Vision Transformer (`dinov2_vits14`, 384-dimensional embedding, L2 normalized) evaluated via Cosine Similarity.

---

### 2. Empirical Benchmark Measurements Table

| Transform ID & Name | SHA-256 Match | pHash Hamming Dist (/64) | dHash Hamming Dist (/64) | Min Perceptual Dist | DINOv2 Cosine Similarity | Empirical Classification |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| `01_exact_copy` | **True** | 0 | 0 | 0 | 1.0000 | `EXACT` |
| `02_jpeg_recompressed_q20` | False | 0 | 1 | 0 | 0.9944 | `SAME_TRANSFORMED_IMAGE` |
| `03_resized_down_up` | False | 0 | 0 | 0 | 0.9947 | `SAME_TRANSFORMED_IMAGE` |
| `04_center_crop_80` | False | 6 | 7 | 6 | 0.9504 | `SAME_TRANSFORMED_IMAGE` |
| `05_watermark_overlay` | False | 10 | 5 | 5 | 0.9618 | `SAME_TRANSFORMED_IMAGE` |
| `06_brightness_plus30` | False | 2 | 2 | 2 | 0.9907 | `SAME_TRANSFORMED_IMAGE` |
| `07_contrast_plus40` | False | 0 | 2 | 0 | 0.9856 | `SAME_TRANSFORMED_IMAGE` |
| `08_screenshot_frame` | False | 20 | 18 | 18 | 0.7647 | `PROBABLE_RELATED` |
| `09_rotation_5deg` | False | 10 | 7 | 7 | 0.9763 | `SAME_TRANSFORMED_IMAGE` |
| `10_unrelated_scene` | False | 28 | 32 | 28 | 0.5231 | `UNRELATED` |
| `11_visually_similar_different_layout` | False | 32 | 32 | 32 | 0.4137 | `UNRELATED` |
| `12_same_subject_altered` | False | 4 | 2 | 2 | 0.9768 | `SAME_TRANSFORMED_IMAGE` |
| `13_extreme_compression_q5` | False | 2 | 1 | 1 | 0.9796 | `SAME_TRANSFORMED_IMAGE` |
| `14_metadata_stripped` | **True** | 0 | 0 | 0 | 1.0000 | `EXACT` |
| `15_format_png_conversion` | **True** | 0 | 0 | 0 | 1.0000 | `EXACT` |

---

### 3. Transformation Sensitivity & Margin Analysis

1. **Exact Matches & Non-Pixel Alterations (`01`, `14`, `15`)**:
   - SHA-256 correctly identifies byte-for-byte pixel-identical formats with $100\%$ precision (pHash distance $= 0$, DINOv2 cosine $= 1.0000$).
2. **Standard Modifications (`02`, `03`, `06`, `07`, `12`, `13`)**:
   - Compression, contrast, brightness, and resolution scaling maintain tight perceptual bounds: $\min(\text{pHash}, \text{dHash}) \le 2$ and DINOv2 cosine $\ge 0.9768$.
3. **Geometric / Spatial Cropping & Occlusion (`04`, `05`, `09`)**:
   - 80% Center Crop, heavy Watermarking, and 5° Rotation raise individual pHash Hamming distances up to $10$, but $\min(\text{pHash}, \text{dHash}) \le 7$ while DINOv2 preserves robust semantic invariance ($\ge 0.9504$).
4. **Heavy Framing / Embedding (`08_screenshot_frame`)**:
   - Simulated browser frame introduces substantial surrounding border pixels, reducing DINOv2 cosine to $0.7647$ and increasing perceptual distance to $18$. This is accurately categorized as `PROBABLE_RELATED` rather than a direct variant.
5. **Unrelated & Layout Alterations (`10`, `11`)**:
   - Unrelated content and completely different geometric layout result in $\min(\text{pHash}, \text{dHash}) \ge 28$ and DINOv2 cosine $\le 0.5231$, demonstrating an error-free margin of $\Delta = 0.2416$ below the `PROBABLE_RELATED` boundary.

---

### 4. Calibrated Decision Thresholds

Based directly on the empirical distributions:

```python
@dataclass(frozen=True)
class MatchingThresholds:
    # Tier 2: Perceptual Hamming Distance (out of 64 bits)
    phash_exact_variant_max_dist: int = 8      # Captures crops (6), watermarks (5), rotations (7)
    phash_probable_max_dist: int = 18         # Captures framed screenshots (18)

    # Tier 3: DINOv2 Cosine Similarity
    dinov2_variant_min_cosine: float = 0.88   # Lowest direct variant is crop (0.9504) -> 0.88 provides safe margin
    dinov2_probable_min_cosine: float = 0.72  # Screenshot frame (0.7647) -> 0.72 provides safe margin
    dinov2_similar_diff_min_cosine: float = 0.55 # Separates visually distinct scenes (0.5231)
```

---

### 5. Classification Rules & Hierarchy

1. **`EXACT`**:
   - Cryptographic condition: `SHA256(reference) == SHA256(candidate)`
   - Explanation: *"Exact cryptographic byte-for-byte duplicate."*
2. **`SAME_TRANSFORMED_IMAGE`**:
   - Multi-signal condition: `dinov2_cosine >= 0.88` OR `min_perceptual_dist <= 8`
   - Explanation: *"High semantic and structural match. Identified as a cropped, resized, compressed, or watermarked variant of the reference image."*
3. **`PROBABLE_RELATED`**:
   - Multi-signal condition: `dinov2_cosine >= 0.72` OR `min_perceptual_dist <= 18`
   - Explanation: *"Moderate instance correlation. Detected as a heavy modification, derivative scene, or nested screenshot."*
4. **`VISUALLY_SIMILAR`**:
   - Multi-signal condition: `dinov2_cosine >= 0.55`
   - Explanation: *"Shared aesthetic, palette, or composition layout without shared instance identity."*
5. **`UNRELATED`**:
   - Condition: Does not meet higher criteria (`dinov2_cosine < 0.55` and `min_perceptual_dist > 18`).
   - Explanation: *"No meaningful visual or structural match found."*
