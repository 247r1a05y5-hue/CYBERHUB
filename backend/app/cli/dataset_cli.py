"""CLI Command for Dataset Ingestion (LFW, Directory, ZIP, Controlled).

Usage:
    python -m app.cli.dataset_cli ingest --dir /path/to/lfw --dataset-name "LFW Benchmark"
    python -m app.cli.dataset_cli ingest --zip /path/to/dataset.zip --dataset-name "Participant Set"
"""
from __future__ import annotations

import argparse
import asyncio
import sys
import uuid
from pathlib import Path

from sqlalchemy import select

from app.db.session import async_session_factory
from app.models.organization import Organization
from app.services.dataset_ingestion_service import DatasetIngestionService


async def run_ingest(
    dataset_dir: str | None,
    zip_path: str | None,
    dataset_name: str,
    org_slug: str | None = None,
    gallery_size: int = 3,
    seed: int = 42,
) -> None:
    """Execute dataset ingestion from CLI."""
    async with async_session_factory() as session:
        # Resolve target organization
        if org_slug:
            stmt = select(Organization).where(Organization.slug == org_slug)
        else:
            stmt = select(Organization).limit(1)

        res = await session.execute(stmt)
        org = res.scalar_one_or_none()
        if not org:
            org = Organization(name="Default Organization", slug="default-org")
            session.add(org)
            await session.commit()
            await session.refresh(org)
            print(f"Created default organization: {org.name} ({org.id})")

        print(f"Target Organization: {org.name} ({org.id})")
        print(f"Dataset Name: {dataset_name}")

        ingest_svc = DatasetIngestionService(session)

        if zip_path:
            print(f"Ingesting from ZIP: {zip_path}")
            report = await ingest_svc.ingest_zip_dataset(
                zip_path=zip_path,
                organization_id=org.id,
                dataset_name=dataset_name,
            )
        elif dataset_dir:
            print(f"Ingesting from Directory: {dataset_dir}")
            report = await ingest_svc.ingest_lfw_directory(
                dataset_dir=dataset_dir,
                organization_id=org.id,
                dataset_name=dataset_name,
                gallery_size_per_identity=gallery_size,
                random_seed=seed,
            )
        else:
            print("Error: Either --dir or --zip must be provided.")
            sys.exit(1)

        print("\n" + "=" * 50)
        print("DATASET INGESTION HEALTH REPORT")
        print("=" * 50)
        print(f"Dataset Name:                 {report.dataset_name}")
        print(f"Total Identities:             {report.total_identities}")
        print(f"Total Images Discovered:      {report.total_images}")
        print(f"Images Accepted:              {report.accepted_images}")
        print(f"Images Rejected:              {report.rejected_images}")
        print(f"  - Zero Faces:               {report.zero_face_count}")
        print(f"  - Multiple Faces:           {report.multi_face_count}")
        print(f"  - Quality Rejections:       {report.quality_rejection_count}")
        print(f"  - Corrupted Files:          {report.corrupted_image_count}")
        print(f"  - Duplicate Files:          {report.duplicate_count}")
        print(f"ArcFace Embeddings Generated: {report.embedding_success_count}")
        print(f"Vectors Indexed in Qdrant:    {report.indexed_vectors}")
        print(f"Gallery Images:               {report.gallery_image_count}")
        print(f"Probe Images:                 {report.probe_image_count}")
        print(f"Insufficient Gallery IDs:     {report.identities_with_insufficient_gallery}")
        print("=" * 50)


def main() -> None:
    parser = argparse.ArgumentParser(description="CYBERHUB Dataset Ingestion CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    ingest_parser = subparsers.add_parser("ingest", help="Ingest a dataset directory or ZIP")
    ingest_parser.add_argument("--dir", type=str, default=None, help="Path to dataset directory (LFW format)")
    ingest_parser.add_argument("--zip", type=str, default=None, help="Path to dataset ZIP file")
    ingest_parser.add_argument("--dataset-name", type=str, default="LFW Benchmark", help="Name for the dataset")
    ingest_parser.add_argument("--org-slug", type=str, default=None, help="Organization slug (defaults to first org)")
    ingest_parser.add_argument("--gallery-size", type=int, default=3, help="Gallery images per identity (default: 3)")
    ingest_parser.add_argument("--seed", type=int, default=42, help="Random seed for gallery/probe split")

    args = parser.parse_args()

    if args.command == "ingest":
        asyncio.run(
            run_ingest(
                dataset_dir=args.dir,
                zip_path=args.zip,
                dataset_name=args.dataset_name,
                org_slug=args.org_slug,
                gallery_size=args.gallery_size,
                seed=args.seed,
            )
        )


if __name__ == "__main__":
    main()
