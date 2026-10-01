from sqlalchemy.engine import Engine

from app.core.database import Base
from app.models.evaluation import METRIC_FIELDS, Evaluation
from app.models.feedback import Feedback
from app.models.paper import Chunk, Paper
from app.models.query import MODES, Citation, QueryRecord, RetrievedChunk
from app.models.weights import WeightSnapshot

__all__ = [
    "METRIC_FIELDS",
    "MODES",
    "Chunk",
    "Citation",
    "Evaluation",
    "Feedback",
    "Paper",
    "QueryRecord",
    "RetrievedChunk",
    "WeightSnapshot",
    "create_tables",
]


def create_tables(engine: Engine) -> None:
    Base.metadata.create_all(engine)
