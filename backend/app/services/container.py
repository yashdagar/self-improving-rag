from dataclasses import dataclass

from app.core.config import Settings
from app.services.document_processor import DocumentProcessor
from app.services.paper_retrieval import PaperRetriever


@dataclass
class Services:
    paper_retriever: PaperRetriever
    document_processor: DocumentProcessor


def build_services(settings: Settings) -> Services:
    return Services(
        paper_retriever=PaperRetriever(settings),
        document_processor=DocumentProcessor(settings),
    )
