"""Qdrant Vector Database Service for DINOv2 & ArcFace Face Embeddings.

Specifications:
- DINOv2 Collection: cyberhub_image_embeddings (384-d, Cosine)
- ArcFace Face Collection: cyberhub_face_embeddings_512 (512-d, Cosine)
- Multi-tenancy / Isolation: Filter by org_id / organization_id on every query
- Resilient failure handling: Graceful degradation to deterministic in-memory store when Qdrant is unavailable
"""
from __future__ import annotations

import logging
import math
import uuid
from dataclasses import dataclass
from typing import Any

from app.core.config import settings

logger = logging.getLogger(__name__)

IMAGE_COLLECTION_NAME = "cyberhub_image_embeddings"
IMAGE_VECTOR_DIM = 384

FACE_COLLECTION_NAME = "cyberhub_face_embeddings_512"
FACE_VECTOR_DIM = 512


@dataclass(frozen=True)
class VectorSearchResult:
    """Result from vector similarity search."""
    vector_id: str
    score: float
    payload: dict[str, Any]

    @property
    def reference_image_id(self) -> uuid.UUID | str | None:
        val = self.payload.get("reference_image_id") or self.payload.get("ref_image_id") or self.payload.get("image_id")
        if val:
            try:
                return uuid.UUID(str(val))
            except ValueError:
                return val
        return None

    @property
    def participant_id(self) -> str | None:
        return self.payload.get("participant_id") or self.payload.get("identity_id")


class QdrantService:
    """Manages vector collections, upsert, query, and tenant-scoped search."""

    def __init__(self, host: str | None = None, port: int | None = None) -> None:
        self.host = host or getattr(settings, "QDRANT_HOST", "localhost")
        self.port = port or getattr(settings, "QDRANT_PORT", 6333)
        self.image_collection = IMAGE_COLLECTION_NAME
        self.face_collection = FACE_COLLECTION_NAME
        self._client = None
        self._is_connected = False
        self._checked_connection = False
        # In-memory vector store fallback for hermetic offline testing and failure resilience
        self._in_memory_image_store: dict[str, dict[str, Any]] = {}
        self._in_memory_face_store: dict[str, dict[str, Any]] = {}

    def _get_client(self) -> Any:
        """Lazily initialize Qdrant client and collections."""
        if self._checked_connection:
            return self._client

        self._checked_connection = True
        try:
            from qdrant_client import QdrantClient  # type: ignore
            from qdrant_client.http import models as qmodels  # type: ignore

            client = QdrantClient(host=self.host, port=self.port, timeout=0.5)
            collections = [c.name for c in client.get_collections().collections]

            # 1. Ensure Image Collection
            if self.image_collection not in collections:
                client.create_collection(
                    collection_name=self.image_collection,
                    vectors_config=qmodels.VectorParams(
                        size=IMAGE_VECTOR_DIM,
                        distance=qmodels.Distance.COSINE,
                    ),
                )
                logger.info(f"Initialized Qdrant collection '{self.image_collection}' (dim={IMAGE_VECTOR_DIM})")

            # 2. Ensure Face Collection
            if self.face_collection not in collections:
                client.create_collection(
                    collection_name=self.face_collection,
                    vectors_config=qmodels.VectorParams(
                        size=FACE_VECTOR_DIM,
                        distance=qmodels.Distance.COSINE,
                    ),
                )
                logger.info(f"Initialized Qdrant collection '{self.face_collection}' (dim={FACE_VECTOR_DIM})")

            self._client = client
            self._is_connected = True
        except Exception as err:
            logger.warning(f"Qdrant connection unavailable ({err}); operating in resilient in-memory fallback mode.")
            self._client = None
            self._is_connected = False

        return self._client

    @staticmethod
    def _cosine_similarity(v1: list[float], v2: list[float]) -> float:
        """Compute cosine similarity between two float vectors."""
        dot = sum(a * b for a, b in zip(v1, v2))
        norm_a = math.sqrt(sum(a * a for a in v1))
        norm_b = math.sqrt(sum(b * b for b in v2))
        if norm_a == 0.0 or norm_b == 0.0:
            return 0.0
        return dot / (norm_a * norm_b)

    # ── 1. DINOv2 Image Embeddings ───────────────────────────────────────────

    async def upsert_embedding(
        self,
        vector: list[float] | Any,
        investigation_id: str | uuid.UUID,
        org_id: str | uuid.UUID,
        reference_image_id: str | uuid.UUID | None = None,
        ref_image_id: str | uuid.UUID | None = None,
        vector_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """Upsert DINOv2 embedding vector with tenant metadata payload."""
        actual_ref_id = reference_image_id or ref_image_id or vector_id
        actual_vec_id = str(vector_id or actual_ref_id or uuid.uuid4())
        vec_list = vector.vector if hasattr(vector, "vector") else list(vector)

        payload = {
            "investigation_id": str(investigation_id),
            "org_id": str(org_id),
            "organization_id": str(org_id),
            "reference_image_id": str(actual_ref_id) if actual_ref_id else None,
            **(metadata or {}),
        }

        client = self._get_client()
        if client and self._is_connected:
            try:
                from qdrant_client.http import models as qmodels  # type: ignore

                q_id = str(uuid.UUID(actual_vec_id)) if self._is_valid_uuid(actual_vec_id) else str(uuid.uuid4())
                client.upsert(
                    collection_name=self.image_collection,
                    points=[
                        qmodels.PointStruct(
                            id=q_id,
                            vector=vec_list,
                            payload=payload,
                        )
                    ],
                )
                return True
            except Exception as e:
                logger.error(f"Qdrant image upsert error: {e}")

        # Fallback in-memory
        self._in_memory_image_store[actual_vec_id] = {
            "vector": vec_list,
            "payload": payload,
        }
        return True

    async def search_similar(
        self,
        query_vector: list[float] | Any,
        org_id: str | uuid.UUID,
        limit: int = 10,
        score_threshold: float = 0.5,
    ) -> list[VectorSearchResult]:
        """Search DINOv2 visual embeddings with tenant isolation."""
        vec_list = query_vector.vector if hasattr(query_vector, "vector") else list(query_vector)
        str_org_id = str(org_id)

        client = self._get_client()
        if client and self._is_connected:
            try:
                from qdrant_client.http import models as qmodels  # type: ignore

                if hasattr(client, "query_points"):
                    query_res = client.query_points(
                        collection_name=self.image_collection,
                        query=vec_list,
                        query_filter=qmodels.Filter(
                            must=[
                                qmodels.FieldCondition(
                                    key="org_id",
                                    match=qmodels.MatchValue(value=str_org_id),
                                )
                            ]
                        ),
                        limit=limit,
                        score_threshold=score_threshold,
                    )
                    search_res = query_res.points if hasattr(query_res, "points") else query_res
                elif hasattr(client, "search"):
                    search_res = client.search(
                        collection_name=self.image_collection,
                        query_vector=vec_list,
                        query_filter=qmodels.Filter(
                            must=[
                                qmodels.FieldCondition(
                                    key="org_id",
                                    match=qmodels.MatchValue(value=str_org_id),
                                )
                            ]
                        ),
                        limit=limit,
                        score_threshold=score_threshold,
                    )
                else:
                    search_res = []

                return [
                    VectorSearchResult(
                        vector_id=str(r.id),
                        score=float(r.score),
                        payload=dict(r.payload or {}),
                    )
                    for r in search_res
                ]
            except Exception as e:
                logger.error(f"Qdrant search error: {e}")

        # In-memory fallback search
        results = []
        for vid, item in self._in_memory_image_store.items():
            if str(item["payload"].get("org_id")) == str_org_id or str(item["payload"].get("organization_id")) == str_org_id:
                sim = self._cosine_similarity(vec_list, item["vector"])
                if sim >= score_threshold:
                    results.append(VectorSearchResult(vector_id=vid, score=round(sim, 4), payload=item["payload"]))

        results.sort(key=lambda x: x.score, reverse=True)
        return results[:limit]

    # ── 2. ArcFace Face Embeddings (512-d) ───────────────────────────────────

    async def upsert_face_embedding(
        self,
        vector: list[float],
        organization_id: str | uuid.UUID,
        dataset_id: str | uuid.UUID | None = None,
        participant_id: str | uuid.UUID | None = None,
        image_id: str | uuid.UUID | None = None,
        model_name: str = "ArcFace-r100",
        model_version: str = "v1.0",
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Upsert 512-d ArcFace vector with structured participant/identity metadata."""
        vec_list = [float(x) for x in vector]
        vec_id = str(uuid.uuid4())

        payload = {
            "organization_id": str(organization_id),
            "dataset_id": str(dataset_id) if dataset_id else None,
            "participant_id": str(participant_id) if participant_id else None,
            "identity_id": str(participant_id) if participant_id else None,
            "image_id": str(image_id) if image_id else None,
            "model_name": model_name,
            "model_version": model_version,
            **(metadata or {}),
        }

        client = self._get_client()
        if client and self._is_connected:
            try:
                from qdrant_client.http import models as qmodels  # type: ignore

                client.upsert(
                    collection_name=self.face_collection,
                    points=[
                        qmodels.PointStruct(
                            id=vec_id,
                            vector=vec_list,
                            payload=payload,
                        )
                    ],
                )
                return vec_id
            except Exception as e:
                logger.error(f"Qdrant face upsert error: {e}")

        # Fallback in-memory
        self._in_memory_face_store[vec_id] = {
            "vector": vec_list,
            "payload": payload,
        }
        return vec_id

    async def search_similar_faces(
        self,
        query_vector: list[float],
        organization_id: str | uuid.UUID,
        dataset_id: str | uuid.UUID | None = None,
        limit: int = 10,
        score_threshold: float = 0.5,
    ) -> list[VectorSearchResult]:
        """Search similar faces within tenant dataset with strict isolation."""
        vec_list = [float(x) for x in query_vector]
        str_org_id = str(organization_id)

        client = self._get_client()
        if client and self._is_connected:
            try:
                from qdrant_client.http import models as qmodels  # type: ignore

                must_conditions = [
                    qmodels.FieldCondition(
                        key="organization_id",
                        match=qmodels.MatchValue(value=str_org_id),
                    )
                ]
                if dataset_id:
                    must_conditions.append(
                        qmodels.FieldCondition(
                            key="dataset_id",
                            match=qmodels.MatchValue(value=str(dataset_id)),
                        )
                    )

                if hasattr(client, "query_points"):
                    query_res = client.query_points(
                        collection_name=self.face_collection,
                        query=vec_list,
                        query_filter=qmodels.Filter(must=must_conditions),
                        limit=limit,
                        score_threshold=score_threshold,
                    )
                    search_res = query_res.points if hasattr(query_res, "points") else query_res
                elif hasattr(client, "search"):
                    search_res = client.search(
                        collection_name=self.face_collection,
                        query_vector=vec_list,
                        query_filter=qmodels.Filter(must=must_conditions),
                        limit=limit,
                        score_threshold=score_threshold,
                    )
                else:
                    search_res = []

                return [
                    VectorSearchResult(
                        vector_id=str(r.id),
                        score=float(r.score),
                        payload=dict(r.payload or {}),
                    )
                    for r in search_res
                ]
            except Exception as e:
                logger.error(f"Qdrant face search error: {e}")

        # In-memory fallback
        results = []
        for vid, item in self._in_memory_face_store.items():
            p_org = str(item["payload"].get("organization_id"))
            p_ds = str(item["payload"].get("dataset_id")) if item["payload"].get("dataset_id") else None

            if p_org == str_org_id:
                if dataset_id and p_ds != str(dataset_id):
                    continue
                sim = self._cosine_similarity(vec_list, item["vector"])
                if sim >= score_threshold:
                    results.append(VectorSearchResult(vector_id=vid, score=round(sim, 4), payload=item["payload"]))

        results.sort(key=lambda x: x.score, reverse=True)
        return results[:limit]

    @staticmethod
    def _is_valid_uuid(val: str) -> bool:
        try:
            uuid.UUID(str(val))
            return True
        except ValueError:
            return False


# Global singleton Qdrant service
qdrant_service = QdrantService()
