"""
retrieve.py
-----------
Retrieval layer for the WGU Unofficial Guide RAG system.

Embeds a query with sentence-transformers/all-MiniLM-L6-v2 (runs fully
locally, no API key required) and returns the top-k most relevant chunks
from ChromaDB along with each chunk's source metadata.

Quickstart
----------
  # One-shot
  from retrieve import retrieve
  results = retrieve("how do I accelerate through WGU courses?")

  # Reuse model + collection across many queries (faster)
  from retrieve import Retriever
  r = Retriever()
  results = r.query("best study strategies for OA exams")

  # CLI smoke-test
  python retrieve.py "how do I finish WGU faster?"
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import chromadb
from sentence_transformers import SentenceTransformer

# ── Defaults ──────────────────────────────────────────────────────────────────

DEFAULT_PERSIST_DIR    = Path("./chromadb_persist")
DEFAULT_COLLECTION     = "wgu_chunks"
DEFAULT_MODEL          = "all-MiniLM-L6-v2"
DEFAULT_TOP_K          = 5


# ── Result dataclass ──────────────────────────────────────────────────────────

@dataclass
class RetrievedChunk:
    """One retrieved chunk with its text and source metadata."""
    rank:        int
    chunk_id:    str
    text:        str
    distance:    float          # lower = more similar (cosine distance)
    source_file: str  = ""
    chunk_index: int  = 0
    source:      str  = ""      # e.g. "Reddit r/WGU", "YouTube"
    title:       str  = ""
    author:      str  = ""
    char_count:  int  = 0
    extra:       dict = field(default_factory=dict)   # any other metadata keys

    def __str__(self) -> str:
        header = (
            f"[{self.rank}] {self.title or self.source_file}"
            f"  (chunk {self.chunk_index})"
            f"  dist={self.distance:.4f}"
        )
        source_line = "  ".join(filter(None, [self.source, self.author]))
        return "\n".join(filter(None, [header, source_line, self.text]))


def _parse_chunk(
    rank: int,
    doc_id: str,
    document: str,
    metadata: dict[str, Any],
    distance: float,
) -> RetrievedChunk:
    """Convert a raw ChromaDB result row into a RetrievedChunk."""
    known = {"chunk_id", "chunk_index", "source_file", "source",
             "title", "author", "char_count"}
    extra = {k: v for k, v in metadata.items() if k not in known}
    return RetrievedChunk(
        rank        = rank,
        chunk_id    = metadata.get("chunk_id", doc_id),
        text        = document,
        distance    = distance,
        source_file = metadata.get("source_file", ""),
        chunk_index = int(metadata.get("chunk_index", 0)),
        source      = metadata.get("source", ""),
        title       = metadata.get("title", ""),
        author      = metadata.get("author", ""),
        char_count  = int(metadata.get("char_count", 0)),
        extra       = extra,
    )


# ── Retriever class ───────────────────────────────────────────────────────────

class Retriever:
    """
    Loads the embedding model and ChromaDB collection once, then serves
    repeated queries efficiently.

    Parameters
    ----------
    persist_dir : Path | str
        Directory where ChromaDB was persisted by embed_chunks_chromadb.py.
    collection_name : str
        Name of the ChromaDB collection to query.
    model_name : str
        Sentence-transformers model identifier.
    """

    def __init__(
        self,
        persist_dir:     Path | str = DEFAULT_PERSIST_DIR,
        collection_name: str        = DEFAULT_COLLECTION,
        model_name:      str        = DEFAULT_MODEL,
    ) -> None:
        self._model = SentenceTransformer(model_name)

        client = chromadb.PersistentClient(path=str(persist_dir))
        self._collection = client.get_collection(name=collection_name)

    def query(
        self,
        query_text: str,
        top_k:      int = DEFAULT_TOP_K,
    ) -> list[RetrievedChunk]:
        """
        Embed *query_text* and return the *top_k* closest chunks.

        Parameters
        ----------
        query_text : str
            Natural-language question or search string.
        top_k : int
            Number of chunks to return (default 5).

        Returns
        -------
        list[RetrievedChunk]
            Ranked from most to least relevant (rank 1 = closest).
        """
        if not query_text.strip():
            raise ValueError("query_text must not be empty")

        query_embedding = self._model.encode(
            query_text, convert_to_numpy=True
        ).tolist()

        results = self._collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            include=["documents", "metadatas", "distances"],
        )

        # results["*"] are lists-of-lists (one inner list per query vector)
        ids       = results["ids"][0]
        documents = results["documents"][0]
        metadatas = results["metadatas"][0]
        distances = results["distances"][0]

        return [
            _parse_chunk(rank + 1, doc_id, doc, meta, dist)
            for rank, (doc_id, doc, meta, dist)
            in enumerate(zip(ids, documents, metadatas, distances))
        ]


# ── Module-level convenience function ────────────────────────────────────────

def retrieve(
    query_text:      str,
    top_k:           int        = DEFAULT_TOP_K,
    persist_dir:     Path | str = DEFAULT_PERSIST_DIR,
    collection_name: str        = DEFAULT_COLLECTION,
    model_name:      str        = DEFAULT_MODEL,
) -> list[RetrievedChunk]:
    """
    One-shot retrieval — loads the model and collection on every call.
    Convenient for scripts; use the ``Retriever`` class for repeated queries.
    """
    return Retriever(
        persist_dir=persist_dir,
        collection_name=collection_name,
        model_name=model_name,
    ).query(query_text, top_k=top_k)


# ── CLI smoke-test ────────────────────────────────────────────────────────────

def _print_results(results: list[RetrievedChunk]) -> None:
    sep = "─" * 72
    print(f"\n{sep}")
    for chunk in results:
        print(chunk)
        print(sep)
    print(f"\n{len(results)} chunk(s) returned.\n")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Retrieve top-k WGU guide chunks for a query."
    )
    parser.add_argument("query", help="Natural-language query string")
    parser.add_argument(
        "--top-k", type=int, default=DEFAULT_TOP_K,
        help=f"Number of results to return (default: {DEFAULT_TOP_K})"
    )
    parser.add_argument(
        "--persist-dir", type=Path, default=DEFAULT_PERSIST_DIR,
        help="ChromaDB persist directory"
    )
    parser.add_argument(
        "--collection", type=str, default=DEFAULT_COLLECTION,
        help="ChromaDB collection name"
    )
    args = parser.parse_args()

    print(f'Query : "{args.query}"')
    print(f"Top-k : {args.top_k}")

    retriever = Retriever(
        persist_dir=args.persist_dir,
        collection_name=args.collection,
    )
    results = retriever.query(args.query, top_k=args.top_k)
    _print_results(results)


if __name__ == "__main__":
    main()
