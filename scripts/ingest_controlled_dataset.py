#!/usr/bin/env python3
"""CLI script to ingest a CYBERHUB_CONTROLLED_DATASET folder into PostgreSQL.

Usage:
  python scripts/ingest_controlled_dataset.py --dir CYBERHUB_CONTROLLED_DATASET --org-name "CyberHub Default" [--index-aws]
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys
import uuid
from pathlib import Path

# Add backend directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from sqlalchemy import select
from app.db.session import async_session_factory
from app.models.organization import Organization
from app.services.dataset_ingestion_service import ControlledDatasetIngestionService


async def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest controlled dataset folder into CyberHub.")
    parser.add_argument("--dir", default="CYBERHUB_CONTROLLED_DATASET", help="Path to dataset directory")
    parser.add_argument("--org-name", default=None, help="Organization name to associate with")
    parser.add_argument("--org-id", default=None, help="Organization UUID")
    parser.add_argument("--index-aws", action="store_true", help="Auto-index consented images to AWS Rekognition")
    args = parser.parse_args()

    dataset_path = Path(args.dir)
    if not dataset_path.exists():
        print(f"[ERROR] Directory not found: {dataset_path}")
        sys.exit(1)

    async with async_session_factory() as session:
        # Resolve organization
        org: Organization | None = None
        if args.org_id:
            res = await session.execute(select(Organization).where(Organization.id == uuid.UUID(args.org_id)))
            org = res.scalars().first()
        elif args.org_name:
            res = await session.execute(select(Organization).where(Organization.name == args.org_name))
            org = res.scalars().first()
        else:
            res = await session.execute(select(Organization).limit(1))
            org = res.scalars().first()

        if not org:
            print("[INFO] No existing organization found. Creating default organization...")
            org = Organization(name="CyberHub Default", slug="cyberhub-default")
            session.add(org)
            await session.flush()
            await session.commit()
            print(f"[OK] Created organization: {org.name} ({org.id})")
        else:
            print(f"[OK] Using organization: {org.name} ({org.id})")

        svc = ControlledDatasetIngestionService(session)
        print(f"\nIngesting controlled dataset from: {dataset_path.resolve()}...")
        report = await svc.ingest_dataset_directory(
            dataset_dir=dataset_path,
            organization_id=org.id,
            auto_index_aws=args.index_aws,
        )
        await session.commit()

        print("\n========================================================")
        print("DATASET INGESTION SUMMARY")
        print("========================================================")
        print(f"  Participants Created : {report.participants_created}")
        print(f"  Participants Skipped : {report.participants_skipped}")
        print(f"  Consents Recorded    : {report.consents_recorded}")
        print(f"  Images Ingested      : {report.images_ingested}")
        print(f"  Images Skipped       : {report.images_skipped}")
        print(f"  AWS Faces Indexed    : {report.images_indexed_aws}")
        print(f"  Public Sources Added : {report.sources_ingested}")
        print(f"  Sources Skipped      : {report.sources_skipped}")
        if report.errors:
            print(f"\n  Warnings / Errors ({len(report.errors)}):")
            for err in report.errors:
                print(f"    - {err}")
        print("========================================================\n")


if __name__ == "__main__":
    asyncio.run(main())
