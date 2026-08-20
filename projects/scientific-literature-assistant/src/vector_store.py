from pathlib import Path
import uuid

import chromadb
import numpy as np


class ChromaVectorStore:
    def __init__(
        self,
        persist_directory: str = "vector_store",
        collection_name: str = "scientific_papers",
    ):
        Path(persist_directory).mkdir(
            parents=True,
            exist_ok=True,
        )

        self.client = chromadb.PersistentClient(
            path=persist_directory
        )

        self.collection_name = collection_name

    def rebuild(
        self,
        chunks: list[dict],
        embeddings: np.ndarray,
    ) -> None:
        try:
            self.client.delete_collection(
                name=self.collection_name
            )
        except Exception:
            pass

        collection = self.client.create_collection(
            name=self.collection_name,
            embedding_function=None,
        )

        ids = [
            str(uuid.uuid4())
            for _ in chunks
        ]

        documents = [
            chunk["text"]
            for chunk in chunks
        ]

        metadatas = [
            chunk["metadata"]
            for chunk in chunks
        ]

        collection.add(
            ids=ids,
            documents=documents,
            metadatas=metadatas,
            embeddings=embeddings.tolist(),
        )

    def query(
        self,
        query_embedding: np.ndarray,
        top_k: int = 5,
    ) -> list[dict]:
        collection = self.client.get_collection(
            name=self.collection_name,
            embedding_function=None,
        )

        result = collection.query(
            query_embeddings=[
                query_embedding.tolist()
            ],
            n_results=top_k,
            include=[
                "documents",
                "metadatas",
                "distances",
            ],
        )

        documents = result.get(
            "documents",
            [[]],
        )[0]

        metadatas = result.get(
            "metadatas",
            [[]],
        )[0]

        distances = result.get(
            "distances",
            [[]],
        )[0]

        rows = []

        for document, metadata, distance in zip(
            documents,
            metadatas,
            distances,
        ):
            rows.append(
                {
                    "text": document,
                    "metadata": metadata,
                    "distance": float(distance),
                }
            )

        return rows
