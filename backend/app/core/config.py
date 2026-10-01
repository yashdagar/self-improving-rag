from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[3]

AI_ML_CATEGORIES = ["cs.AI", "cs.LG", "cs.CL", "cs.CV", "cs.NE", "stat.ML"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Self-Improving RAG for Scientific Research Literature"
    environment: Literal["development", "test", "production"] = "development"
    cors_origins: list[str] = ["http://localhost:5173"]

    data_dir: Path = PROJECT_ROOT / "data"

    arxiv_categories: list[str] = Field(default_factory=lambda: list(AI_ML_CATEGORIES))
    arxiv_max_results: int = Field(20, ge=1, le=100)
    arxiv_recency_days: int | None = Field(1095, ge=1)
    arxiv_request_delay_seconds: float = Field(3.0, ge=0)
    arxiv_api_url: str = "https://export.arxiv.org/api/query"
    arxiv_timeout_seconds: float = Field(30.0, gt=0)
    arxiv_cache_ttl_hours: float = Field(24.0, ge=0)
    arxiv_min_results: int = Field(5, ge=0)
    arxiv_max_keywords: int = Field(5, ge=1, le=10)

    max_pdf_pages: int = Field(30, ge=1)
    chunk_size_chars: int = Field(1200, ge=200)
    chunk_overlap_chars: int = Field(200, ge=0)

    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    retrieval_candidate_pool: int = Field(40, ge=1)
    retrieval_top_k: int = Field(8, ge=1)

    llm_provider: Literal["anthropic", "openai_compatible"] = "anthropic"
    llm_model: str = "claude-sonnet-5"
    llm_api_key: SecretStr | None = None
    llm_base_url: str | None = None
    llm_temperature: float = Field(0.0, ge=0, le=1)
    llm_max_tokens: int = Field(1500, ge=100)

    alpha_init: float = Field(0.70, ge=0, le=1)
    beta_init: float = Field(0.15, ge=0, le=1)
    gamma_init: float = Field(0.15, ge=0, le=1)
    weight_min: float = Field(0.05, ge=0, le=1)
    weight_max: float = Field(0.90, ge=0, le=1)
    weight_learning_rate: float = Field(0.10, gt=0, le=0.5)
    recency_half_life_days: float = Field(365.0, gt=0)

    @model_validator(mode="after")
    def check_consistency(self) -> "Settings":
        if self.chunk_overlap_chars >= self.chunk_size_chars:
            raise ValueError("chunk_overlap_chars must be smaller than chunk_size_chars")
        if self.retrieval_top_k > self.retrieval_candidate_pool:
            raise ValueError("retrieval_top_k cannot exceed retrieval_candidate_pool")
        if not self.weight_min < self.weight_max:
            raise ValueError("weight_min must be smaller than weight_max")
        if not 3 * self.weight_min <= 1 <= 3 * self.weight_max:
            raise ValueError("weight bounds make alpha + beta + gamma = 1 impossible")
        for name in ("alpha_init", "beta_init", "gamma_init"):
            value = getattr(self, name)
            if not self.weight_min <= value <= self.weight_max:
                raise ValueError(f"{name}={value} is outside [{self.weight_min}, {self.weight_max}]")
        if abs(self.alpha_init + self.beta_init + self.gamma_init - 1) > 1e-6:
            raise ValueError("alpha_init + beta_init + gamma_init must sum to 1")
        unknown = set(self.arxiv_categories) - set(AI_ML_CATEGORIES)
        if unknown:
            raise ValueError(f"unsupported arXiv categories: {sorted(unknown)}")
        return self

    @property
    def sqlite_path(self) -> Path:
        return self.data_dir / "rag.db"

    @property
    def database_url(self) -> str:
        return f"sqlite:///{self.sqlite_path}"

    @property
    def chroma_dir(self) -> Path:
        return self.data_dir / "chroma"

    @property
    def pdf_dir(self) -> Path:
        return self.data_dir / "pdfs"

    @property
    def paper_cache_dir(self) -> Path:
        return self.data_dir / "papers"

    def ensure_dirs(self) -> None:
        for path in (self.data_dir, self.chroma_dir, self.pdf_dir, self.paper_cache_dir):
            path.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    return Settings()
