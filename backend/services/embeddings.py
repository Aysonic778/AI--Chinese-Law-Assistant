from __future__ import annotations

import uuid
from functools import lru_cache

import chromadb
from chromadb.api.models.Collection import Collection
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

from backend.config import settings

COLLECTION_NAME = "law_chunks"


@lru_cache(maxsize=1)
def get_embedding_function() -> SentenceTransformerEmbeddingFunction:
    return SentenceTransformerEmbeddingFunction(
        model_name=settings.embedding_model,
        device=settings.embedding_device,
    )


@lru_cache(maxsize=1)
def get_chroma_client() -> chromadb.PersistentClient:
    return chromadb.PersistentClient(path=settings.chroma_persist_dir)


def get_collection() -> Collection:
    client = get_chroma_client()
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=get_embedding_function(),
        metadata={"hnsw:space": "cosine"},
    )


def make_chroma_id() -> str:
    return str(uuid.uuid4())
