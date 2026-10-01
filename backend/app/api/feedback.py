from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models import Feedback, QueryRecord
from app.schemas.feedback import FeedbackCreate, FeedbackOut

router = APIRouter(prefix="/feedback", tags=["feedback"])


@router.post("", response_model=FeedbackOut, status_code=status.HTTP_201_CREATED)
def create_feedback(payload: FeedbackCreate, db: Session = Depends(get_db)) -> FeedbackOut:
    record = db.get(QueryRecord, payload.query_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"query {payload.query_id} not found")
    if record.status != "completed":
        raise HTTPException(status_code=409, detail="feedback is only accepted for completed queries")
    if payload.chunk_id is not None and payload.chunk_id not in {r.chunk_id for r in record.retrieved}:
        raise HTTPException(status_code=422, detail=f"chunk {payload.chunk_id} was not retrieved for this query")

    feedback = Feedback(**payload.model_dump())
    db.add(feedback)
    db.commit()
    return FeedbackOut.model_validate(feedback)
