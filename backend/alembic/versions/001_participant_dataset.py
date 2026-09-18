"""Add controlled-dataset participant tables for AWS Rekognition pipeline.

Revision ID: 001_participant_dataset
Revises: 
Create Date: 2026-09-17
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "001_participant_dataset"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # â”€â”€ consent_status enum â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    consent_status_enum = sa.Enum(
        "PENDING", "CONSENTED", "REVOKED", "EXPIRED",
        name="consent_status",
    )

    # â”€â”€ image_index_status enum â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    image_index_status_enum = sa.Enum(
        "PENDING", "INDEXED", "FAILED", "DUPLICATE",
        name="image_index_status",
    )

    # â”€â”€ match_status enum â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    match_status_enum = sa.Enum(
        "PENDING_REVIEW", "VERIFIED", "REJECTED", "UNCERTAIN",
        name="match_status",
    )

    # â”€â”€ verification_status enum â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    verification_status_enum = sa.Enum(
        "PENDING_REVIEW", "VERIFIED", "REJECTED", "UNCERTAIN",
        name="verification_status",
    )

    # â”€â”€ participants â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    op.create_table(
        "participants",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("participant_code", sa.String(50), nullable=False),
        sa.Column("display_name", sa.String(255), nullable=False),
        sa.Column("aws_collection_id", sa.String(255), nullable=True),
        sa.Column("consent_status", consent_status_enum, nullable=False, server_default="PENDING"),
        sa.Column("consent_timestamp", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "participant_code", name="uq_participant_org_code"),
    )
    op.create_index("ix_participants_org_id", "participants", ["organization_id"])
    op.create_index("ix_participants_org_code", "participants", ["organization_id", "participant_code"])

    # â”€â”€ participant_images â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    op.create_table(
        "participant_images",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("participant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("phash", sa.String(64), nullable=True),
        sa.Column("dhash", sa.String(64), nullable=True),
        sa.Column("storage_key", sa.String(1024), nullable=False),
        sa.Column("mime_type", sa.String(100), nullable=False),
        sa.Column("file_size_bytes", sa.Integer(), nullable=False),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("aws_face_id", sa.String(255), nullable=True),
        sa.Column("aws_external_image_id", sa.String(255), nullable=True),
        sa.Column("aws_collection_id", sa.String(255), nullable=True),
        sa.Column("aws_indexed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("face_confidence", sa.Float(), nullable=True),
        sa.Column("index_status", image_index_status_enum, nullable=False, server_default="PENDING"),
        sa.Column("index_error", sa.Text(), nullable=True),
        sa.Column("image_sequence", sa.Integer(), nullable=False, server_default="1"),
        sa.ForeignKeyConstraint(["participant_id"], ["participants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "sha256", name="uq_participant_image_org_sha256"),
    )
    op.create_index("ix_participant_images_participant_id", "participant_images", ["participant_id"])
    op.create_index("ix_participant_images_org_id", "participant_images", ["organization_id"])
    op.create_index("ix_participant_images_sha256", "participant_images", ["sha256"])
    op.create_index("ix_participant_images_aws_face_id", "participant_images", ["aws_face_id"])

    # â”€â”€ participant_public_sources â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    op.create_table(
        "participant_public_sources",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("participant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("platform", sa.String(100), nullable=False),
        sa.Column("url", sa.String(2048), nullable=False),
        sa.Column("participant_confirmed", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("added_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["participant_id"], ["participants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("participant_id", "url", name="uq_pps_participant_url"),
    )
    op.create_index("ix_pps_participant_id", "participant_public_sources", ["participant_id"])
    op.create_index("ix_pps_org_id", "participant_public_sources", ["organization_id"])

    # â”€â”€ participant_consents â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    op.create_table(
        "participant_consents",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("participant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("consent_status", consent_status_enum, nullable=False),
        sa.Column("consent_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consent_method", sa.String(100), nullable=False, server_default="ADMIN_ENROLLMENT"),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["participant_id"], ["participants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_participant_consents_participant_id", "participant_consents", ["participant_id"])

    # â”€â”€ dataset_matches â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    op.create_table(
        "dataset_matches",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("case_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("participant_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("requested_by_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("query_image_sha256", sa.String(64), nullable=False),
        sa.Column("query_image_phash", sa.String(64), nullable=True),
        sa.Column("aws_face_id_matched", sa.String(255), nullable=True),
        sa.Column("aws_external_image_id", sa.String(255), nullable=True),
        sa.Column("aws_similarity", sa.Float(), nullable=True),
        sa.Column("aws_collection_id", sa.String(255), nullable=True),
        sa.Column("local_similarity", sa.Float(), nullable=True),
        sa.Column("local_match_method", sa.String(50), nullable=True),
        sa.Column("match_status", match_status_enum, nullable=False, server_default="PENDING_REVIEW"),
        sa.Column("error_code", sa.String(100), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("matched_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["case_id"], ["cases.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["participant_id"], ["participants.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["requested_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_dataset_matches_org_id", "dataset_matches", ["organization_id"])
    op.create_index("ix_dataset_matches_participant_id", "dataset_matches", ["participant_id"])
    op.create_index("ix_dataset_matches_status", "dataset_matches", ["match_status"])

    # â”€â”€ dataset_verifications â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    op.create_table(
        "dataset_verifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("match_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", verification_status_enum, nullable=False, server_default="PENDING_REVIEW"),
        sa.Column("verified_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("verification_note", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["match_id"], ["dataset_matches.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["verified_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_dataset_verifications_match_id", "dataset_verifications", ["match_id"])
    op.create_index("ix_dataset_verifications_org_id", "dataset_verifications", ["organization_id"])


def downgrade() -> None:
    op.drop_table("dataset_verifications")
    op.drop_table("dataset_matches")
    op.drop_table("participant_consents")
    op.drop_table("participant_public_sources")
    op.drop_table("participant_images")
    op.drop_table("participants")

    # Drop enums
    sa.Enum(name="verification_status").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="match_status").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="image_index_status").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="consent_status").drop(op.get_bind(), checkfirst=True)
