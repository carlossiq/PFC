from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/chat", tags=["chat-v2"])


@router.get("/health")
async def health() -> dict[str, str]:
    return {
        "status": "ok",
        "version": "v2",
        "note": "Full v2 chat implementation pending (ResearchService pipeline steps).",
    }
