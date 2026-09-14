"""Synthetic 15-Transform Test Matrix Generator (Slice 13).

Generates a controlled image dataset with 15 distinct transformations
to benchmark and calibrate image matching thresholds for:
- Tier 1: SHA-256
- Tier 2: Perceptual Hashes (pHash, dHash)
- Tier 3: DINOv2 Embeddings (dinov2_vits14)
"""
from __future__ import annotations

import io
import math
from typing import Dict
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter


def create_base_synthetic_image(width: int = 512, height: int = 512) -> Image.Image:
    """Creates a deterministic synthetic test image with rich visual structures."""
    img = Image.new("RGB", (width, height), color=(30, 45, 75))
    draw = ImageDraw.Draw(img)

    # Complex shapes, gradients, and distinct features
    draw.rectangle([(50, 50), (200, 200)], fill=(220, 80, 50), outline=(255, 255, 255), width=3)
    draw.ellipse([(250, 100), (450, 300)], fill=(50, 180, 120), outline=(200, 240, 200), width=4)
    draw.polygon([(100, 400), (250, 320), (400, 450), (150, 480)], fill=(240, 200, 40))

    # Diagonal lines for edge detection
    for i in range(0, width, 40):
        draw.line([(i, 0), (i + 100, height)], fill=(120, 140, 190), width=2)

    # Concentric circles
    for r in range(10, 60, 15):
        draw.ellipse([(256 - r, 256 - r), (256 + r, 256 + r)], outline=(255, 255, 0), width=2)

    return img


def generate_15_transform_corpus() -> Dict[str, Image.Image]:
    """Generates the 15-transform evaluation matrix specified in Slice 13."""
    base = create_base_synthetic_image()
    corpus: Dict[str, Image.Image] = {"00_base": base}

    # 1. Exact copy
    corpus["01_exact_copy"] = base.copy()

    # 2. JPEG recompression (quality 20)
    buf = io.BytesIO()
    base.save(buf, format="JPEG", quality=20)
    buf.seek(0)
    corpus["02_jpeg_recompressed_q20"] = Image.open(buf).convert("RGB")

    # 3. Resize (downscale 50% then upscale)
    w, h = base.size
    small = base.resize((w // 2, h // 2), Image.Resampling.BILINEAR)
    corpus["03_resized_down_up"] = small.resize((w, h), Image.Resampling.BILINEAR)

    # 4. Center crop (80% crop and pad back to original size)
    crop_box = (int(w * 0.1), int(h * 0.1), int(w * 0.9), int(h * 0.9))
    cropped = base.crop(crop_box)
    padded = Image.new("RGB", (w, h), (0, 0, 0))
    padded.paste(cropped, (int(w * 0.1), int(h * 0.1)))
    corpus["04_center_crop_80"] = padded

    # 5. Watermark / text overlay
    watermarked = base.copy()
    draw_wm = ImageDraw.Draw(watermarked)
    draw_wm.rectangle([(50, 420), (350, 470)], fill=(0, 0, 0))
    draw_wm.text((60, 435), "CYBERHUB CONFIDENTIAL EVIDENCE", fill=(255, 255, 255))
    corpus["05_watermark_overlay"] = watermarked

    # 6. Brightness increase (+30%)
    enhancer = ImageEnhance.Brightness(base)
    corpus["06_brightness_plus30"] = enhancer.enhance(1.3)

    # 7. Contrast increase (+40%)
    enhancer_c = ImageEnhance.Contrast(base)
    corpus["07_contrast_plus40"] = enhancer_c.enhance(1.4)

    # 8. Simulated screenshot (surrounded by mock browser window)
    screenshot = Image.new("RGB", (w + 100, h + 100), (230, 230, 235))
    s_draw = ImageDraw.Draw(screenshot)
    s_draw.rectangle([(0, 0), (w + 100, 40)], fill=(200, 200, 210))
    s_draw.ellipse([(15, 12), (27, 24)], fill=(255, 95, 86))
    s_draw.ellipse([(35, 12), (47, 24)], fill=(255, 189, 46))
    s_draw.ellipse([(55, 12), (67, 24)], fill=(39, 201, 63))
    screenshot.paste(base, (50, 60))
    corpus["08_screenshot_frame"] = screenshot.resize((w, h))

    # 9. Mild rotation (5 degrees with bilinear interpolation)
    corpus["09_rotation_5deg"] = base.rotate(5, resample=Image.Resampling.BILINEAR, expand=False)

    # 10. Unrelated image (distinct geometric textures / completely different scene)
    unrelated = Image.new("RGB", (w, h), (180, 220, 250))
    u_draw = ImageDraw.Draw(unrelated)
    for y in range(0, h, 20):
        u_draw.line([(0, y), (w, y)], fill=(80, 100, 140), width=3)
    u_draw.rectangle([(200, 200), (300, 300)], fill=(120, 30, 180))
    corpus["10_unrelated_scene"] = unrelated

    # 11. Visually similar but different (same color theme, completely different objects)
    vis_similar = Image.new("RGB", (w, h), color=(30, 45, 75))
    vs_draw = ImageDraw.Draw(vis_similar)
    vs_draw.rectangle([(300, 50), (450, 200)], fill=(220, 80, 50))
    vs_draw.polygon([(50, 200), (150, 100), (250, 200)], fill=(50, 180, 120))
    corpus["11_visually_similar_different_layout"] = vis_similar

    # 12. Same subject / alternative variant
    alt_variant = base.copy()
    av_draw = ImageDraw.Draw(alt_variant)
    av_draw.rectangle([(50, 50), (200, 200)], fill=(180, 60, 40))  # altered color
    corpus["12_same_subject_altered"] = alt_variant

    # 13. Extreme compression (JPEG quality 5)
    buf_ext = io.BytesIO()
    base.save(buf_ext, format="JPEG", quality=5)
    buf_ext.seek(0)
    corpus["13_extreme_compression_q5"] = Image.open(buf_ext).convert("RGB")

    # 14. Metadata stripped (identical pixels, raw RGB dump)
    corpus["14_metadata_stripped"] = Image.frombytes("RGB", base.size, base.tobytes())

    # 15. Format conversion (PNG format simulation)
    buf_png = io.BytesIO()
    base.save(buf_png, format="PNG")
    buf_png.seek(0)
    corpus["15_format_png_conversion"] = Image.open(buf_png).convert("RGB")

    return corpus


def get_image_bytes(img: Image.Image, format: str = "PNG") -> bytes:
    """Converts PIL image to bytes."""
    buf = io.BytesIO()
    img.save(buf, format=format)
    return buf.getvalue()
