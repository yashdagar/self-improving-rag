from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.schemas.feedback import FeedbackOut
from app.schemas.paper import PaperSummary
from app.schemas.weights import Weights


class RetrievedChunkOut(BaseModel):
    rank: int
    chunk_id: str
    paper: PaperSummary
    section: str | None
    page: int | None
    source: str
    text: str
    semantic_score: float
    recency_score: float
    feedback_score: float
    final_score: float
    cited: bool


class CitationOut(BaseModel):
    marker: int
    chunk_id: str
    paper_id: str
    paper_title: str
    claim: str | None


class EvaluationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    retrieval_relevance: float
    groundedness: float
    citation_accuracy: float
    answer_relevance: float
    evidence_coverage: float
    overall: float
    reasoning: dict[str, str]
    evaluator_model: str
    created_at: datetime


class Latency(BaseModel):
    retrieval_ms: float | None
    generation_ms: float | None
    evaluation_ms: float | None
    total_ms: float | None


class QueryDetail(BaseModel):
    id: int
    text: str
    reformulated_text: str | None
    mode: str
    status: str
    answer: str | None
    insufficient_evidence: bool
    error: str | None
    weights: Weights
    latency: Latency
    experiment_run: str | None
    cycle: int | None
    created_at: datetime
    retrieved: list[RetrievedChunkOut]
    citations: list[CitationOut]
    evaluation: EvaluationOut | None
    feedback: list[FeedbackOut]
