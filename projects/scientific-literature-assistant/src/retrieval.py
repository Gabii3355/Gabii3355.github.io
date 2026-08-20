from src.embeddings import EmbeddingModel
from src.vector_store import ChromaVectorStore


def retrieve_context(
    question: str,
    embedder: EmbeddingModel,
    store: ChromaVectorStore,
    top_k: int = 5,
) -> list[dict]:
    query_embedding = embedder.encode_query(question)

    return store.query(
        query_embedding=query_embedding,
        top_k=top_k,
    )
