from dataclasses import dataclass

from app.core.config import Settings
from app.services.document_processor import DocumentProcessor
from app.services.embeddings import Embedder, SentenceTransformerEmbedder
from app.services.indexer import Indexer
from app.services.paper_retrieval import PaperRetriever
from app.services.vector_store import VectorStore


@dataclass
class Services:
    paper_retriever: PaperRetriever
    document_processor: DocumentProcessor
    embedder: Embedder
    vector_store: VectorStore
    indexer: Indexer


def build_services(settings: Settings, embedder: Embedder | None = None) -> Services:
    embedder = embedder or SentenceTransformerEmbedder(settings)
    vector_store = VectorStore(settings, embedder)
    return Services(
        paper_retriever=PaperRetriever(settings),
        document_processor=DocumentProcessor(settings),
        embedder=embedder,
        vector_store=vector_store,
        indexer=Indexer(vector_store),
    )
