import os
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app import __version__
from app.api.deps import get_app_settings, get_db, get_services
from app.core.config import Settings
from app.models import Chunk, Feedback, Paper, QueryRecord, WeightSnapshot
from app.services.container import Services
from app.schemas.system import (
    ComponentStatus,
    LLMConfig,
    RankingConfig,
    RetrievalConfig,
    SystemStatus,
)

router = APIRouter(prefix="/system", tags=["system"])


def _storage_status(settings: Settings) -> ComponentStatus:
    if not settings.data_dir.is_dir():
        return ComponentStatus(status="error", detail=f"{settings.data_dir} does not exist")
    if not os.access(settings.data_dir, os.W_OK):
        return ComponentStatus(status="error", detail=f"{settings.data_dir} is not writable")
    return ComponentStatus(status="ok", detail=str(settings.data_dir))


def _llm_status(settings: Settings) -> ComponentStatus:
    if settings.llm_api_key is None or not settings.llm_api_key.get_secret_value():
        return ComponentStatus(status="not_configured", detail="LLM_API_KEY is not set")
    return ComponentStatus(status="ok", detail=f"{settings.llm_provider}:{settings.llm_model}")


COUNTED_TABLES = {
    "papers": Paper,
    "chunks": Chunk,
    "queries": QueryRecord,
    "feedback": Feedback,
    "weight_snapshots": WeightSnapshot,
}


def _database_status(db: Session, settings: Settings) -> tuple[ComponentStatus, dict[str, int]]:
    try:
        counts = {
            name: db.scalar(select(func.count()).select_from(model)) or 0
            for name, model in COUNTED_TABLES.items()
        }
    except SQLAlchemyError as exc:
        return ComponentStatus(status="error", detail=str(exc)), {}
    return ComponentStatus(status="ok", detail=str(settings.sqlite_path)), counts


def _vector_status(services: Services) -> tuple[ComponentStatus, ComponentStatus, int]:
    loaded = getattr(services.embedder, "loaded", True)
    embeddings = ComponentStatus(
        status="ok",
        detail=f"{services.embedder.model_name} ({'loaded' if loaded else 'loads on first use'})",
    )
    try:
        count = services.vector_store.count()
    except Exception as exc:
        return ComponentStatus(status="error", detail=str(exc)), embeddings, 0
    return ComponentStatus(status="ok", detail=f"{count} chunk vectors"), embeddings, count


@router.get("/status", response_model=SystemStatus)
def system_status(
    settings: Settings = Depends(get_app_settings),
    db: Session = Depends(get_db),
    services: Services = Depends(get_services),
) -> SystemStatus:
    llm = _llm_status(settings)
    database, counts = _database_status(db, settings)
    vector_store, embeddings, vector_count = _vector_status(services)
    counts["vectors"] = vector_count
    return SystemStatus(
        app_name=settings.app_name,
        version=__version__,
        environment=settings.environment,
        server_time=datetime.now(timezone.utc),
        components={
            "storage": _storage_status(settings),
            "database": database,
            "vector_store": vector_store,
            "embeddings": embeddings,
            "llm": llm,
        },
        counts=counts,
        retrieval=RetrievalConfig(
            arxiv_categories=settings.arxiv_categories,
            arxiv_max_results=settings.arxiv_max_results,
            arxiv_recency_days=settings.arxiv_recency_days,
            embedding_model=settings.embedding_model,
            candidate_pool=settings.retrieval_candidate_pool,
            top_k=settings.retrieval_top_k,
        ),
        ranking=RankingConfig(
            alpha_init=settings.alpha_init,
            beta_init=settings.beta_init,
            gamma_init=settings.gamma_init,
            weight_min=settings.weight_min,
            weight_max=settings.weight_max,
            learning_rate=settings.weight_learning_rate,
            recency_half_life_days=settings.recency_half_life_days,
        ),
        llm=LLMConfig(
            provider=settings.llm_provider,
            model=settings.llm_model,
            api_key_configured=llm.status == "ok",
        ),
    )
