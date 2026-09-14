"""Ephemeral Temporary Image Public Endpoint.

Serves short-lived temporary image objects to external search engine crawlers (SearchAPI Google Lens)
without exposing private storage credentials or permanent public URLs.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Response, status

from app.services.temporary_image_service import temporary_image_service

router = APIRouter()


@router.get("/{token}", summary="Retrieve Ephemeral Temporary Image")
async def get_temporary_image(token: str) -> Response:
    """
    Fetch raw image bytes for an active, unexpired temporary token.
    Publicly accessible to external search bots with strict no-cache headers.
    """
    res = temporary_image_service.get_temporary_image(token)
    if not res:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Temporary image not found, expired, or access limit reached.",
        )

    image_bytes, content_type = res
    headers = {
        "Content-Type": content_type,
        "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
        "Pragma": "no-cache",
        "X-Content-Type-Options": "nosniff",
    }
    return Response(content=image_bytes, media_type=content_type, headers=headers)
