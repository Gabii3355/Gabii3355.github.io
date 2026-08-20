import os
from functools import lru_cache

import numpy as np
from sentence_transformers import SentenceTransformer


DEFAULT_EMBEDDING_MODEL = (
    "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
)


@lru_cache(maxsize=1)
def _load_model() -> SentenceTransformer:
    model_name = os.getenv(
        "EMBEDDING_MODEL",
        DEFAULT_EMBEDDING_MODEL,
    )

    return SentenceTransformer(
        model_name,
        device="cpu",
    )


class EmbeddingModel:
    def __init__(self):
        self.model = _load_model()

    def encode_documents(self, texts: list[str]) -> np.ndarray:
        return self.model.encode(
            texts,
            batch_size=32,
            show_progress_bar=False,
            convert_to_numpy=True,
            normalize_embeddings=True,
        )

    def encode_query(self, query: str) -> np.ndarray:
        return self.model.encode(
            [query],
            show_progress_bar=False,
            convert_to_numpy=True,
            normalize_embeddings=True,
        )[0]
