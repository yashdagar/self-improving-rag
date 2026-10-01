from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models import QueryRecord
from app.schemas.feedback import FeedbackOut
from app.schemas.paper import PaperSummary
from app.schemas.query import (
    CitationOut,
    EvaluationOut,
    Latency,
    QueryDetail,
    RetrievedChunkOut,
)
from app.schemas.weights import Weights

router = APIRouter(prefix="/query", tags=["query"])


def build_query_detail(record: QueryRecord) -> QueryDetail:
    cited_ids = {citation.chunk_id for citation in record.citations}
    return QueryDetail(
        id=record.id,
        text=record.text,
        reformulated_text=record.reformulated_text,
        mode=record.mode,
        status=record.status,
        answer=record.answer,
        insufficient_evidence=record.insufficient_evidence,
        error=record.error,
        weights=Weights(alpha=record.alpha, beta=record.beta, gamma=record.gamma),
        latency=Latency(
            retrieval_ms=record.retrieval_ms,
            generation_ms=record.generation_ms,
            evaluation_ms=record.evaluation_ms,
            total_ms=record.total_ms,
        ),
        experiment_run=record.experiment_run,
        cycle=record.cycle,
        created_at=record.created_at,
        retrieved=[
            RetrievedChunkOut(
                rank=item.rank,
                chunk_id=item.chunk_id,
                paper=PaperSummary.model_validate(item.chunk.paper),
                section=item.chunk.section,
                page=item.chunk.page,
                source=item.chunk.source,
                text=item.chunk.text,
                semantic_score=item.semantic_score,
                recency_score=item.recency_score,
                feedback_score=item.feedback_score,
                final_score=item.final_score,
                cited=item.chunk_id in cited_ids,
            )
            for item in record.retrieved
        ],
        citations=[
            CitationOut(
                marker=citation.marker,
                chunk_id=citation.chunk_id,
                paper_id=citation.chunk.paper_id,
                paper_title=citation.chunk.paper.title,
                claim=citation.claim,
            )
            for citation in record.citations
        ],
        evaluation=EvaluationOut.model_validate(record.evaluation) if record.evaluation else None,
        feedback=[FeedbackOut.model_validate(item) for item in record.feedback],
    )


@router.get("/{query_id}", response_model=QueryDetail)
def get_query(query_id: int, db: Session = Depends(get_db)) -> QueryDetail:
    record = db.get(QueryRecord, query_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"query {query_id} not found")
    return build_query_detail(record)
