from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models import WeightSnapshot


@dataclass(frozen=True)
class RankingWeights:
    alpha: float
    beta: float
    gamma: float


def latest_snapshot(session: Session) -> WeightSnapshot | None:
    return session.scalars(select(WeightSnapshot).order_by(WeightSnapshot.id.desc()).limit(1)).first()


def current_weights(session: Session, settings: Settings) -> RankingWeights:
    snapshot = latest_snapshot(session)
    if snapshot is None:
        return RankingWeights(settings.alpha_init, settings.beta_init, settings.gamma_init)
    return RankingWeights(snapshot.alpha, snapshot.beta, snapshot.gamma)


def ensure_initial_snapshot(session: Session, settings: Settings) -> None:
    if session.scalar(select(func.count()).select_from(WeightSnapshot)):
        return
    session.add(
        WeightSnapshot(
            alpha=settings.alpha_init,
            beta=settings.beta_init,
            gamma=settings.gamma_init,
            trigger="init",
            note="seeded from settings",
        )
    )
    session.commit()
