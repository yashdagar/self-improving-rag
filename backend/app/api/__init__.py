from fastapi import APIRouter

from app.api import feedback, improvement, metrics, papers, queries, system

api_router = APIRouter(prefix="/api")
for module in (system, queries, feedback, papers, metrics, improvement):
    api_router.include_router(module.router)
