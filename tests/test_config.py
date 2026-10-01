import pytest
from pydantic import ValidationError

from app.core.config import Settings


def make(**overrides):
    return Settings(_env_file=None, **overrides)


def test_defaults_are_valid():
    settings = make()
    total = settings.alpha_init + settings.beta_init + settings.gamma_init
    assert total == pytest.approx(1.0)


@pytest.mark.parametrize(
    "overrides",
    [
        {"alpha_init": 0.95, "beta_init": 0.03, "gamma_init": 0.02},
        {"alpha_init": 0.5, "beta_init": 0.3, "gamma_init": 0.3},
        {"weight_min": 0.4},
        {"weight_min": 0.5, "weight_max": 0.4},
        {"chunk_size_chars": 500, "chunk_overlap_chars": 500},
        {"retrieval_top_k": 50, "retrieval_candidate_pool": 10},
        {"arxiv_categories": ["cs.AI", "q-bio.GN"]},
    ],
)
def test_invalid_settings_are_rejected(overrides):
    with pytest.raises(ValidationError):
        make(**overrides)
