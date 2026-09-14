"""Forensic Investigation Reporting Service.

Generates reproducible, hash-referenced reports directly from stored database state.
Supported Formats:
- PDF (standalone pure-Python compliant PDF artifact)
- JSON (structured machine-readable audit package)
- CSV (tabular findings export)
- TEXT (formal human-readable investigation documentation)

Notice: Reports are hash-referenced with deterministic content hashing across runs.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any


@dataclass
class ReportPayload:
    """Standardized report document structure."""
    investigation_id: str
    case_number: str
    title: str
    generated_at: str
    reference_image_sha256: str
    risk_policy_version: str
    methodology: str
    limitations: str
    risk_assessment: dict[str, Any]
    verified_exposures: list[dict[str, Any]]
    rejected_findings_summary: dict[str, Any]
    uncertain_findings_summary: dict[str, Any]
    exposure_clusters: list[dict[str, Any]]
    evidence_artifacts: list[dict[str, Any]]
    audit_chain: list[dict[str, Any]]


class ExposureReportService:
    """Generates standardized forensic report packages."""

    METHODOLOGY_TEXT = (
        "CyberHub Image Exposure Investigation Methodology (v1.0.0): "
        "Strict image-to-image correlation executing Tier 1 SHA-256 cryptographic verification, "
        "Tier 2 perceptual hash (pHash/dHash) distance analysis, and Tier 3 DINOv2 vision transformer "
        "instance embedding matching against external discovery signals. All findings are gated by "
        "human-in-the-loop analyst verification before admission as verified evidence."
    )

    LIMITATIONS_TEXT = (
        "Investigation Limitations & Boundary Declaration: "
        "1. This report is strictly bounded to the provided reference image and does not perform facial recognition or identity tracking. "
        "2. Public search results depend on external provider indexing and public availability at discovery time. "
        "3. Technical evidence hashes guarantee digital integrity of captured artifacts, not legal admissibility."
    )

    @classmethod
    def compute_deterministic_content_hash(cls, payload: ReportPayload) -> str:
        """
        Compute SHA-256 over canonicalized JSON representation excluding dynamic runtime timestamps.
        Guarantees identical investigation states yield bitwise identical content hashes.
        """
        data = asdict(payload)
        # Exclude dynamic generation timestamp for deterministic hash
        data_for_hashing = {k: v for k, v in data.items() if k != "generated_at"}
        canonical_bytes = json.dumps(data_for_hashing, sort_keys=True, ensure_ascii=False).encode("utf-8")
        return hashlib.sha256(canonical_bytes).hexdigest()

    @classmethod
    def generate_json_report(cls, payload: ReportPayload) -> str:
        """Generate structured JSON report string."""
        data = asdict(payload)
        return json.dumps(data, indent=2, ensure_ascii=False)

    @classmethod
    def generate_csv_report(cls, payload: ReportPayload) -> str:
        """Generate tabular CSV report of all discovered findings."""
        output = io.StringIO()
        writer = csv.writer(output)

        # Header rows
        writer.writerow(["INVESTIGATION ID", payload.investigation_id])
        writer.writerow(["CASE NUMBER", payload.case_number])
        writer.writerow(["REFERENCE HASH", payload.reference_image_sha256])
        writer.writerow(["RISK POLICY", payload.risk_policy_version])
        writer.writerow(["GENERATED AT", payload.generated_at])
        writer.writerow([])

        # Table headers
        writer.writerow([
            "FINDING ID",
            "DOMAIN",
            "PAGE TITLE",
            "PAGE URL",
            "IMAGE URL",
            "SIMILARITY SCORE",
            "VERIFICATION STATUS",
            "SHA-256 ARTIFACT HASH",
        ])

        # Write findings
        for exp in payload.verified_exposures:
            writer.writerow([
                exp.get("id", ""),
                exp.get("domain", ""),
                exp.get("page_title", ""),
                exp.get("page_url", ""),
                exp.get("image_url", ""),
                f"{float(exp.get('similarity_score', 0.0)) * 100:.1f}%",
                "VERIFIED",
                exp.get("evidence_sha256", "N/A"),
            ])

        return output.getvalue()

    @classmethod
    def generate_text_summary_report(cls, payload: ReportPayload) -> str:
        """Generate structured human-readable text report."""
        lines = [
            "=" * 72,
            "CYBERHUB FORENSIC IMAGE EXPOSURE REPORT",
            "=" * 72,
            f"Investigation ID: {payload.investigation_id}",
            f"Case Reference:   {payload.case_number} ({payload.title})",
            f"Reference SHA256: {payload.reference_image_sha256}",
            f"Risk Policy:      {payload.risk_policy_version}",
            f"Timestamp:        {payload.generated_at}",
            "-" * 72,
            "RISK ASSESSMENT",
            f"Overall Tier:     {payload.risk_assessment.get('risk_level', 'UNKNOWN')}",
            f"Explanation:      {payload.risk_assessment.get('explanation', '')}",
            "-" * 72,
            f"VERIFIED EXPOSURES ({len(payload.verified_exposures)})",
        ]

        if not payload.verified_exposures:
            lines.append("No verified exposures identified.")
        else:
            for idx, item in enumerate(payload.verified_exposures, 1):
                lines.append(f"{idx}. [{item.get('domain', 'Domain')}] {item.get('page_title', 'Finding')}")
                lines.append(f"   URL:        {item.get('page_url')}")
                lines.append(f"   Similarity: {float(item.get('similarity_score', 0.0)) * 100:.1f}%")
                if item.get("evidence_sha256"):
                    lines.append(f"   SHA-256:    {item.get('evidence_sha256')}")

        lines.extend([
            "-" * 72,
            "METHODOLOGY",
            cls.METHODOLOGY_TEXT,
            "-" * 72,
            "LIMITATIONS",
            cls.LIMITATIONS_TEXT,
            "=" * 72,
        ])

        return "\n".join(lines)

    @classmethod
    def generate_pdf_report_bytes(cls, payload: ReportPayload) -> bytes:
        """
        Generate pure-Python compliant PDF byte buffer without external binary dependencies.
        Creates a valid PDF-1.4 document structure with standard font and text stream.
        """
        text_content = cls.generate_text_summary_report(payload)
        lines = text_content.split("\n")

        # Construct stream text
        stream_lines = ["BT", "/F1 10 Tf", "50 780 Td", "14 TL"]
        for line in lines[:55]:  # fit on page
            # Escape PDF special characters
            escaped = line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
            # Truncate overly long lines
            if len(escaped) > 85:
                escaped = escaped[:82] + "..."
            stream_lines.append(f"({escaped}) Tj")
            stream_lines.append("T*")
        stream_lines.append("ET")
        stream_data = "\n".join(stream_lines).encode("latin-1", errors="replace")

        objects = []
        # Obj 1: Catalog
        objects.append(b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n")
        # Obj 2: Pages
        objects.append(b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n")
        # Obj 3: Page
        objects.append(b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 842] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>\nendobj\n")
        # Obj 4: Content Stream
        objects.append(f"4 0 obj\n<< /Length {len(stream_data)} >>\nstream\n".encode("latin-1") + stream_data + b"\nendstream\nendobj\n")
        # Obj 5: Font
        objects.append(b"5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n")

        out = io.BytesIO()
        out.write(b"%PDF-1.4\n")
        offsets = []
        for obj in objects:
            offsets.append(out.tell())
            out.write(obj)

        xref_pos = out.tell()
        out.write(b"xref\n0 6\n0000000000 65535 f \n")
        for offset in offsets:
            out.write(f"{offset:010d} 00000 n \n".encode("latin-1"))

        out.write(b"trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n")
        out.write(f"{xref_pos}\n%%EOF\n".encode("latin-1"))

        return out.getvalue()


exposure_report_service = ExposureReportService()
