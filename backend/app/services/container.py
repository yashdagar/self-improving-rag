from dataclasses import dataclass

from app.core.config import Settings
from app.services.paper_retrieval import PaperRetriever


@dataclass
class Services:
    paper_retriever: PaperRetriever


def build_services(settings: Settings) -> Services:
    return Services(paper_retriever=PaperRetriever(settings))
