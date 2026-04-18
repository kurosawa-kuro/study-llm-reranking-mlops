from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.infra.repositories.engagement import apply_feedback

router = APIRouter()


class FeedbackRequest(BaseModel):
    user_id: int | None = None
    property_id: int
    action: Literal["click", "favorite", "inquiry"]
    search_log_id: int | None = None


@router.post("/feedback")
def feedback(payload: FeedbackRequest) -> dict[str, object]:
    updated_search_log = apply_feedback(
        user_id=payload.user_id,
        property_id=payload.property_id,
        action=payload.action,
        search_log_id=payload.search_log_id,
    )

    if payload.search_log_id is not None and not updated_search_log:
        raise HTTPException(status_code=404, detail="search_log_id not found")

    return {
        "status": "ok",
        "property_id": payload.property_id,
        "action": payload.action,
        "search_log_updated": updated_search_log,
    }
