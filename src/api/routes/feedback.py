from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.core.logging import get_logger, RequestContextVar
from src.repositories.search_log_repository import apply_feedback

logger = get_logger(__name__)
router = APIRouter()


class FeedbackRequest(BaseModel):
    user_id: int | None = None
    property_id: int
    action: Literal["click", "favorite", "inquiry"]
    search_log_id: int | None = None


@router.post("/feedback")
def feedback(payload: FeedbackRequest) -> dict[str, object]:
    request_id = RequestContextVar.get("request_id", "unknown")
    logger.info(
        "feedback_started",
        extra={
            "request_id": request_id,
            "user_id": payload.user_id or "anonymous",
            "property_id": payload.property_id,
            "action": payload.action,
            "search_log_id": payload.search_log_id,
        },
    )

    try:
        updated_search_log = apply_feedback(
            user_id=payload.user_id,
            property_id=payload.property_id,
            action=payload.action,
            search_log_id=payload.search_log_id,
        )
    except Exception as exc:
        logger.error(
            "feedback_error",
            extra={
                "request_id": request_id,
                "user_id": payload.user_id or "anonymous",
                "property_id": payload.property_id,
                "action": payload.action,
                "error": str(exc),
                "error_type": type(exc).__name__,
            },
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail="Feedback processing failed") from exc

    if payload.search_log_id is not None and not updated_search_log:
        logger.warning(
            "feedback_search_log_not_found",
            extra={
                "request_id": request_id,
                "user_id": payload.user_id or "anonymous",
                "search_log_id": payload.search_log_id,
            },
        )
        raise HTTPException(status_code=404, detail="search_log_id not found")

    logger.info(
        "feedback_completed",
        extra={
            "request_id": request_id,
            "user_id": payload.user_id or "anonymous",
            "property_id": payload.property_id,
            "action": payload.action,
            "search_log_updated": updated_search_log,
        },
    )

    return {
        "status": "ok",
        "property_id": payload.property_id,
        "action": payload.action,
        "search_log_updated": updated_search_log,
    }
