"""Qdrant Vector Database Service for DINOv2 Embeddings.

Specifications:
- Collection name: cyberhub_image_embeddings
- Dimensionality: 384
- Distance metric: Cosine
- Multi-tenancy / Isolation: Filter by org_id on every query
- Resilient failure handling: Graceful degradation to in-memory store when Qdrant is unavailable
"""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from typing import Any

from app.core.config import settings

logger = logging.getLogger(__name__)

COLLECTION_NAME = "cyberhub_image_embeddings"
VECTOR_DIM = 384


@dataclass(frozen=True)
class VectorSearchResult:
    """Result from vector similarity search."""
    vector_id: str
    score: float
    payload: dict[str, Any]

    @property
    def reference_image_id(self) -> uuid.UUID | str | None:
        val = self.payload.get("reference_image_id") or self.payload.get("ref_image_id")
        if val:
            try:
                return uuid.UUID(str(val))
            except ValueError:
                return val
        return None


class QdrantService:
    """Manages vector collection lifecycle, upsert, query, and tenant-scoped deletion."""

    def __init__(self, host: str | None = None, port: int | None = None) -> None:
        self.host = host or getattr(settings, "QDRANT_HOST", "localhost")
        self.port = port or getattr(settings, "QDRANT_PORT", 6333)
        self.collection_name = COLLECTION_NAME
        self._client = None
        self._is_connected = False
        self._checked_connection = False
        # In-memory vector store fallback for hermetic offline testing and failure resilience
        self._in_memory_store: dict[str, dict[str, Any]] = {}

    def _get_client(self) -> Any:
        """Lazily initialize Qdrant client."""
        if self._checked_connection:
            return self._client

        self._checked_connection = True
        try:
            from qdrant_client import QdrantClient  # type: ignore
            client = QdrantClient(host=self.host, port=self.port, timeout=0.5)
            # Fast ping / check collections
            from qdrant_client.http import models as qmodels  # type: ignore
            collections = client.get_collections().collections
            exists = any(c.name == self.collection_name for c in collections)
            if not exists:
                client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=qmodels.VectorParams(
                        size=VECTOR_DIM,
                        distance=qmodels.Distance.COSINE,
                    ),
                )
                logger.info(f"Initialized Qdrant collection '{self.collection_name}' (dim={VECTOR_DIM}, metric=Cosine)")
            self._client = client
            self._is_connected = True
        except Exception as err:
            logger.warning(f"Qdrant connection unavailable ({err}); operating in resilient in-memory fallback mode.")
            self._client = None
            self._is_connected = False

        return self._client

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
            "reference_image_id": str(actual_ref_id) if actual_ref_id else actual_vec_id,
            "ref_image_id": str(actual_ref_id) if actual_ref_id else actual_vec_id,
            **(metadata or {}),
        }

        # Always update in-memory store for fallback consistency
        self._in_memory_store[actual_vec_id] = {
            "vector": vec_list,
            "payload": payload,
        }

        client = self._get_client()
        if client:
            try:
                from qdrant_client.http import models as qmodels  # type: ignore
                try:
                    point_id = str(uuid.UUID(actual_vec_id))
                except ValueError:
                    point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, actual_vec_id))

                client.upsert(
                    collection_name=self.collection_name,
                    points=[
                        qmodels.PointStruct(
                            id=point_id,
                            vector=vec_list,
                            payload=payload,
                        )
                    ],
                )
                return True
            except Exception as err:
                logger.error(f"Failed to upsert to Qdrant ({err}); vector saved in fallback store.")
                return False
        return True

    async def search_similar(
        self,
        query_vector: list[float] | Any,
        org_id: str | uuid.UUID,
        limit: int = 10,
        min_score: float = 0.5,
    ) -> list[VectorSearchResult]:
        """Query similar vectors filtered strictly by organization ID (tenant isolation)."""
        org_id_str = str(org_id)
        vec_list = query_vector.vector if hasattr(query_vector, "vector") else list(query_vector)
        client = self._get_client()

        if client:
            try:
                from qdrant_client.http import models as qmodels  # type: ignore
                filter_condition = qmodels.Filter(
                    must=[
                        qmodels.FieldCondition(
                            key="org_id",
                            match=qmodels.MatchValue(value=org_id_str),
                        )
                    ]
                )
                search_results = client.search(
                    collection_name=self.collection_name,
                    query_vector=vec_list,
                    query_filter=filter_condition,
                    limit=limit,
                    score_threshold=min_score,
                )
                return [
                    VectorSearchResult(
                        vector_id=str(r.id),
                        score=float(r.score),
                        payload=dict(r.payload or {}),
                    )
                    for r in search_results
                ]
            except Exception as err:
                logger.warning(f"Qdrant search failed ({err}); evaluating against in-memory fallback store.")

        # In-memory fallback search
        results: list[VectorSearchResult] = []
        for vid, item in self._in_memory_store.items():
            if item["payload"].get("org_id") == org_id_str:
                stored_vec = item["vector"]
                # Cosine dot product of normalized vectors
                score = sum(a * b for a, b in zip(vec_list, stored_vec))
                if score >= min_score:
                    results.append(
                        VectorSearchResult(
                            vector_id=vid,
                            score=round(float(score), 4),
                            payload=item["payload"],
                        )
                    )

        results.sort(key=lambda r: r.score, reverse=True)
        return results[:limit]

    async def delete_by_id(self, vector_id: str) -> bool:
        """Delete specific vector."""
        if vector_id in self._in_memory_store:
            del self._in_memory_store[vector_id]

        client = self._get_client()
        if client:
            try:
                from qdrant_client.http import models as qmodels  # type: ignore
                try:
                    point_id = str(uuid.UUID(vector_id))
                except ValueError:
                    point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, vector_id))

                client.delete(
                    collection_name=self.collection_name,
                    points_selector=qmodels.PointIdsList(points=[point_id]),
                )
                return True
            except Exception as err:
                logger.error(f"Failed to delete point from Qdrant: {err}")
                return False
        return True

    async def delete_by_investigation(self, investigation_id: str | uuid.UUID, org_id: str | uuid.UUID) -> int:
        """Delete all vectors for an investigation ensuring cross-store consistency."""
        inv_str = str(investigation_id)
        org_str = str(org_id)

        # In-memory cleanup
        to_delete = [
            vid
            for vid, item in self._in_memory_store.items()
            if item["payload"].get("investigation_id") == inv_str and item["payload"].get("org_id") == org_str
        ]
        for vid in to_delete:
            del self._in_memory_store[vid]

        deleted_count = len(to_delete)

        client = self._get_client()
        if client:
            try:
                from qdrant_client.http import models as qmodels  # type: ignore
                client.delete(
                    collection_name=self.collection_name,
                    points_selector=qmodels.FilterSelector(
                        filter=qmodels.Filter(
                            must=[
                                qmodels.FieldCondition(key="investigation_id", match=qmodels.MatchValue(value=inv_str)),
                                qmodels.FieldCondition(key="org_id", match=qmodels.MatchValue(value=org_str)),
                            ]
                        )
                    ),
                )
            except Exception as err:
                logger.error(f"Failed to delete investigation points from Qdrant: {err}")

        return deleted_count


qdrant_service = QdrantService()
