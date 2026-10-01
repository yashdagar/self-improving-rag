from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models import Paper
from app.schemas.paper import ChunkOut, PaperDetail

router = APIRouter(prefix="/papers", tags=["papers"])


@router.get("/{paper_id:path}", response_model=PaperDetail)
def get_paper(paper_id: str, include_chunks: bool = False, db: Session = Depends(get_db)) -> PaperDetail:
    paper = db.get(Paper, paper_id)
    if paper is None:
        raise HTTPException(status_code=404, detail=f"paper {paper_id} not found")
    detail = PaperDetail.model_validate(
        {**{c.name: getattr(paper, c.name) for c in Paper.__table__.columns}, "chunk_count": len(paper.chunks)}
    )
    if include_chunks:
        detail.chunks = [ChunkOut.model_validate(chunk) for chunk in paper.chunks]
    return detail
