from fastapi import APIRouter

from app.api import arxiv, feedback, improvement, metrics, papers, queries, system

api_router = APIRouter(prefix="/api")
for module in (system, queries, feedback, papers, arxiv, metrics, improvement):
    api_router.include_router(module.router)
