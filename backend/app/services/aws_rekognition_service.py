"""AWS Rekognition service — real boto3 SDK integration.

Credentials are read exclusively from the standard AWS credential chain:
  1. Environment variables (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)
  2. ~/.aws/credentials
  3. IAM instance role / ECS task role
Never hardcoded, never logged.

Error codes follow the spec:
  AWS_NOT_CONFIGURED, AWS_AUTH_FAILED, AWS_ACCESS_DENIED,
  AWS_COLLECTION_NOT_FOUND, AWS_INVALID_IMAGE, AWS_THROTTLED,
  AWS_SERVICE_UNAVAILABLE, NO_FACE_DETECTED, MULTIPLE_FACES_DETECTED,
  NO_DATASET_MATCH
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from app.core.config import settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Result dataclasses
# ---------------------------------------------------------------------------


@dataclass
class CollectionInfo:
    collection_id: str
    face_count: int
    face_model_version: str
    status: str  # "ACTIVE" | "NOT_FOUND" | "ERROR"


@dataclass
class IndexFaceResult:
    face_id: str
    external_image_id: str
    face_confidence: float
    bounding_box: dict[str, float]


@dataclass
class FaceMatch:
    face_id: str
    external_image_id: str
    similarity: float
    bounding_box: dict[str, float]


@dataclass
class SearchResult:
    matches: list[FaceMatch] = field(default_factory=list)
    searched_face_confidence: float = 0.0
    error_code: str | None = None
    error_message: str | None = None


# ---------------------------------------------------------------------------
# AWS error → CyberHub error code mapping
# ---------------------------------------------------------------------------


def _map_aws_error(exc: Exception) -> tuple[str, str]:
    """Map boto3 / botocore exceptions to CyberHub error codes.

    Returns (code, message) — never includes credential values.
    """
    try:
        from botocore.exceptions import ClientError, NoCredentialsError, PartialCredentialsError

        if isinstance(exc, NoCredentialsError):
            return "AWS_AUTH_FAILED", "No AWS credentials found."
        if isinstance(exc, PartialCredentialsError):
            return "AWS_AUTH_FAILED", "Incomplete AWS credentials."
        if isinstance(exc, ClientError):
            code = exc.response.get("Error", {}).get("Code", "")
            if code in ("InvalidClientTokenId", "AuthFailure", "UnrecognizedClientException"):
                return "AWS_AUTH_FAILED", "AWS authentication failed."
            if code == "AccessDeniedException":
                return "AWS_ACCESS_DENIED", "AWS access denied — check IAM permissions."
            if code == "ResourceNotFoundException":
                return "AWS_COLLECTION_NOT_FOUND", "Rekognition collection not found."
            if code in ("InvalidImageException", "ImageTooLargeException", "InvalidParameterException"):
                return "AWS_INVALID_IMAGE", f"Invalid image: {exc.response['Error'].get('Message', '')}"
            if code == "ThrottlingException":
                return "AWS_THROTTLED", "AWS Rekognition throttled — retry later."
            if code == "ServiceUnavailableException":
                return "AWS_SERVICE_UNAVAILABLE", "AWS Rekognition service unavailable."
            if code == "InvalidS3ObjectException":
                return "AWS_INVALID_IMAGE", "Could not read image from S3."
    except ImportError:
        pass
    return "AWS_SERVICE_UNAVAILABLE", f"Unexpected AWS error: {type(exc).__name__}"


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class AWSRekognitionService:
    """Thin, testable wrapper around the boto3 Rekognition client."""

    def __init__(self) -> None:
        self._client: Any = None
        self._configured: bool = False
        self._region: str = settings.AWS_REGION or "us-east-1"
        self._collection_id: str = settings.AWS_REKOGNITION_COLLECTION_ID or ""

    @property
    def is_configured(self) -> bool:
        return bool(settings.AWS_REGION and settings.AWS_REKOGNITION_COLLECTION_ID)

    def _get_client(self) -> Any:
        if self._client is None:
            try:
                import boto3

                # boto3 reads credentials from the standard chain automatically.
                # We deliberately do NOT pass access_key_id / secret_access_key
                # here to prevent accidental logging of parameters.
                self._client = boto3.client(
                    "rekognition",
                    region_name=self._region,
                )
                logger.info(
                    "AWS Rekognition client initialised",
                    extra={"region": self._region, "collection": self._collection_id},
                )
            except ImportError:
                raise RuntimeError(
                    "boto3 is not installed — add boto3>=1.34.0 to requirements.txt"
                )
        return self._client

    # ------------------------------------------------------------------
    # Collection management
    # ------------------------------------------------------------------

    def create_collection(self, collection_id: str | None = None) -> CollectionInfo:
        """Create an AWS Rekognition collection. Idempotent."""
        if not self.is_configured:
            raise ValueError("AWS_NOT_CONFIGURED")
        cid = collection_id or self._collection_id
        client = self._get_client()
        try:
            resp = client.create_collection(CollectionId=cid)
            logger.info("Created Rekognition collection", extra={"collection_id": cid})
            return CollectionInfo(
                collection_id=cid,
                face_count=0,
                face_model_version=resp.get("FaceModelVersion", "unknown"),
                status="ACTIVE",
            )
        except Exception as exc:
            try:
                from botocore.exceptions import ClientError

                if isinstance(exc, ClientError):
                    if exc.response["Error"]["Code"] == "ResourceAlreadyExistsException":
                        logger.info("Collection already exists", extra={"collection_id": cid})
                        return self.describe_collection(cid)
            except ImportError:
                pass
            code, msg = _map_aws_error(exc)
            raise RuntimeError(f"{code}: {msg}") from exc

    def describe_collection(self, collection_id: str | None = None) -> CollectionInfo:
        """Get metadata about an existing collection."""
        if not self.is_configured:
            raise ValueError("AWS_NOT_CONFIGURED")
        cid = collection_id or self._collection_id
        client = self._get_client()
        try:
            resp = client.describe_collection(CollectionId=cid)
            return CollectionInfo(
                collection_id=cid,
                face_count=resp.get("FaceCount", 0),
                face_model_version=resp.get("FaceModelVersion", "unknown"),
                status="ACTIVE",
            )
        except Exception as exc:
            code, msg = _map_aws_error(exc)
            if code == "AWS_COLLECTION_NOT_FOUND":
                return CollectionInfo(
                    collection_id=cid,
                    face_count=0,
                    face_model_version="unknown",
                    status="NOT_FOUND",
                )
            raise RuntimeError(f"{code}: {msg}") from exc

    # ------------------------------------------------------------------
    # Face indexing
    # ------------------------------------------------------------------

    def index_face(
        self,
        image_bytes: bytes,
        external_image_id: str,
        collection_id: str | None = None,
        max_faces: int = 1,
        quality_filter: str = "AUTO",
        detection_attributes: list[str] | None = None,
    ) -> IndexFaceResult:
        """Index exactly one face from image_bytes into the collection.

        external_image_id MUST follow the format CYBERHUB:P<code>:IMG<seq>
        and must never contain real names or PII.
        """
        if not self.is_configured:
            raise ValueError("AWS_NOT_CONFIGURED")
        if not external_image_id.startswith("CYBERHUB:"):
            raise ValueError("ExternalImageId must start with 'CYBERHUB:' prefix.")

        cid = collection_id or self._collection_id
        client = self._get_client()
        try:
            resp = client.index_faces(
                CollectionId=cid,
                Image={"Bytes": image_bytes},
                ExternalImageId=external_image_id,
                MaxFaces=max_faces,
                QualityFilter=quality_filter,
                DetectionAttributes=detection_attributes or [],
            )
        except Exception as exc:
            code, msg = _map_aws_error(exc)
            raise RuntimeError(f"{code}: {msg}") from exc

        face_records = resp.get("FaceRecords", [])
        unindexed = resp.get("UnindexedFaces", [])

        if not face_records:
            if unindexed:
                reasons = [r for f in unindexed for r in f.get("Reasons", [])]
                if "NO_FACES" in reasons or not any(True for _ in unindexed):
                    raise ValueError("NO_FACE_DETECTED")
            raise ValueError("NO_FACE_DETECTED")

        if len(face_records) > 1:
            raise ValueError("MULTIPLE_FACES_DETECTED")

        fr = face_records[0]["Face"]
        bb = fr.get("BoundingBox", {})
        return IndexFaceResult(
            face_id=fr["FaceId"],
            external_image_id=fr.get("ExternalImageId", external_image_id),
            face_confidence=fr.get("Confidence", 0.0),
            bounding_box={
                "left": bb.get("Left", 0),
                "top": bb.get("Top", 0),
                "width": bb.get("Width", 0),
                "height": bb.get("Height", 0),
            },
        )

    # ------------------------------------------------------------------
    # Face search
    # ------------------------------------------------------------------

    def search_faces_by_image(
        self,
        image_bytes: bytes,
        collection_id: str | None = None,
        max_faces: int = 5,
        face_match_threshold: float = 80.0,
    ) -> SearchResult:
        """Run SearchFacesByImage and return ordered matches.

        Returns SearchResult with error_code set if a recoverable error occurs.
        Raises for AWS infrastructure failures.
        """
        if not self.is_configured:
            return SearchResult(
                error_code="AWS_NOT_CONFIGURED",
                error_message="AWS Rekognition is not configured.",
            )

        cid = collection_id or self._collection_id
        client = self._get_client()
        try:
            resp = client.search_faces_by_image(
                CollectionId=cid,
                Image={"Bytes": image_bytes},
                MaxFaces=max_faces,
                FaceMatchThreshold=face_match_threshold,
            )
        except Exception as exc:
            try:
                from botocore.exceptions import ClientError

                if isinstance(exc, ClientError):
                    ec = exc.response["Error"]["Code"]
                    if ec == "InvalidParameterException":
                        msg = exc.response["Error"].get("Message", "")
                        if "no faces" in msg.lower():
                            return SearchResult(
                                error_code="NO_FACE_DETECTED",
                                error_message="No face detected in the query image.",
                            )
                        if "multiple faces" in msg.lower():
                            return SearchResult(
                                error_code="MULTIPLE_FACES_DETECTED",
                                error_message="Multiple faces detected. Submit a single-face image.",
                            )
            except ImportError:
                pass
            code, msg = _map_aws_error(exc)
            return SearchResult(error_code=code, error_message=msg)

        raw_matches = resp.get("FaceMatches", [])
        searched_conf = resp.get("SearchedFaceBoundingBox", {})

        if not raw_matches:
            return SearchResult(
                matches=[],
                searched_face_confidence=resp.get("SearchedFaceConfidence", 0.0),
                error_code="NO_DATASET_MATCH",
                error_message="No matching faces found in the dataset.",
            )

        matches = []
        for rm in raw_matches:
            face = rm["Face"]
            bb = face.get("BoundingBox", {})
            matches.append(
                FaceMatch(
                    face_id=face["FaceId"],
                    external_image_id=face.get("ExternalImageId", ""),
                    similarity=rm.get("Similarity", 0.0),
                    bounding_box={
                        "left": bb.get("Left", 0),
                        "top": bb.get("Top", 0),
                        "width": bb.get("Width", 0),
                        "height": bb.get("Height", 0),
                    },
                )
            )

        # Already ordered by similarity descending from AWS
        return SearchResult(
            matches=matches,
            searched_face_confidence=resp.get("SearchedFaceConfidence", 0.0),
        )

    # ------------------------------------------------------------------
    # Face deletion
    # ------------------------------------------------------------------

    def delete_faces(
        self,
        face_ids: list[str],
        collection_id: str | None = None,
    ) -> list[str]:
        """Delete face vectors from the collection. Returns list of deleted FaceIds."""
        if not self.is_configured:
            raise ValueError("AWS_NOT_CONFIGURED")
        if not face_ids:
            return []

        cid = collection_id or self._collection_id
        client = self._get_client()
        try:
            resp = client.delete_faces(CollectionId=cid, FaceIds=face_ids)
            deleted = resp.get("DeletedFaces", [])
            logger.info(
                "Deleted faces from Rekognition",
                extra={"collection_id": cid, "count": len(deleted)},
            )
            return deleted
        except Exception as exc:
            code, msg = _map_aws_error(exc)
            raise RuntimeError(f"{code}: {msg}") from exc


# Module-level singleton — safe; all state is derived from settings
rekognition_service = AWSRekognitionService()
