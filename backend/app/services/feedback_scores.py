from collections import defaultdict
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Citation, Feedback, QueryRecord, RetrievedChunk

EXPLICIT_CHUNK_WEIGHT = 1.0
EXPLICIT_ANSWER_WEIGHT = 0.5
JUDGED_RELEVANCE_WEIGHT = 0.5
CITATION_SUPPORT_WEIGHT = 0.5


@dataclass
class Signal:
    chunk_id: str
    query_id: int
    value: float
    weight: float


def query_similarity(a: list[float] | None, b: list[float] | None) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    return sum(x * y for x, y in zip(a, b))


def similarity_kernel(similarity: float, threshold: float) -> float:
    if similarity <= threshold:
        return 0.0
    return (similarity - threshold) / (1.0 - threshold)


def collect_signals(session: Session, chunk_ids: list[str], exclude_query_id: int | None) -> list[Signal]:
    if not chunk_ids:
        return []
    signals: list[Signal] = []

    def keep(query_id: int) -> bool:
        return query_id != exclude_query_id

    for feedback in session.scalars(select(Feedback).where(Feedback.chunk_id.in_(chunk_ids))):
        if keep(feedback.query_id):
            signals.append(
                Signal(feedback.chunk_id, feedback.query_id, 1.0 if feedback.rating > 0 else 0.0, EXPLICIT_CHUNK_WEIGHT)
            )

    answer_feedback = session.execute(
        select(Feedback.query_id, Feedback.rating, Citation.chunk_id)
        .join(Citation, Citation.query_id == Feedback.query_id)
        .where(Feedback.chunk_id.is_(None), Citation.chunk_id.in_(chunk_ids))
    )
    for query_id, rating, chunk_id in answer_feedback:
        if keep(query_id):
            signals.append(Signal(chunk_id, query_id, 1.0 if rating > 0 else 0.0, EXPLICIT_ANSWER_WEIGHT))

    judged = session.execute(
        select(RetrievedChunk.query_id, RetrievedChunk.chunk_id, RetrievedChunk.judged_relevance).where(
            RetrievedChunk.chunk_id.in_(chunk_ids), RetrievedChunk.judged_relevance.is_not(None)
        )
    )
    for query_id, chunk_id, relevance in judged:
        if keep(query_id):
            signals.append(Signal(chunk_id, query_id, relevance, JUDGED_RELEVANCE_WEIGHT))

    supported = session.execute(
        select(Citation.query_id, Citation.chunk_id, Citation.supported).where(
            Citation.chunk_id.in_(chunk_ids), Citation.supported.is_not(None)
        )
    )
    for query_id, chunk_id, is_supported in supported:
        if keep(query_id):
            signals.append(Signal(chunk_id, query_id, 1.0 if is_supported else 0.0, CITATION_SUPPORT_WEIGHT))
    return signals


def feedback_scores(
    session: Session,
    chunk_ids: list[str],
    query_vector: list[float] | None,
    prior_strength: float,
    similarity_threshold: float,
    exclude_query_id: int | None = None,
) -> dict[str, float]:
    signals = collect_signals(session, chunk_ids, exclude_query_id)
    query_ids = {s.query_id for s in signals}
    rows = session.execute(select(QueryRecord.id, QueryRecord.embedding).where(QueryRecord.id.in_(query_ids)))
    embeddings = dict(rows.tuples().all())
    kernels = {
        query_id: similarity_kernel(query_similarity(query_vector, embedding), similarity_threshold)
        for query_id, embedding in embeddings.items()
    }

    weighted_sum: dict[str, float] = defaultdict(float)
    total_weight: dict[str, float] = defaultdict(float)
    for signal in signals:
        weight = signal.weight * kernels.get(signal.query_id, 0.0)
        weighted_sum[signal.chunk_id] += weight * signal.value
        total_weight[signal.chunk_id] += weight

    return {
        chunk_id: (prior_strength * 0.5 + weighted_sum[chunk_id]) / (prior_strength + total_weight[chunk_id])
        for chunk_id in chunk_ids
    }
