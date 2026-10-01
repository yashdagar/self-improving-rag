import os
from datetime import datetime, timezone

from fastapi import APIRouter, Depends

from app import __version__
from app.api.deps import get_app_settings
from app.core.config import Settings
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


@router.get("/status", response_model=SystemStatus)
def system_status(settings: Settings = Depends(get_app_settings)) -> SystemStatus:
    llm = _llm_status(settings)
    return SystemStatus(
        app_name=settings.app_name,
        version=__version__,
        environment=settings.environment,
        server_time=datetime.now(timezone.utc),
        components={"storage": _storage_status(settings), "llm": llm},
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
