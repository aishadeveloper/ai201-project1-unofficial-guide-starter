"""
embed_chunks_chromadb.py
------------------------
Load chunk objects from a JSON file, compute embeddings with
sentence-transformers/all-MiniLM-L6-v2, and insert them into a
persistent ChromaDB collection including per-chunk metadata.

Usage:
  python embed_chunks_chromadb.py --chunks-file chunks.json --persist-dir ./chromadb_persist

Defaults assume a local `chunks.json` in the repo root. You can override
paths with the CLI flags.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable, List

import chromadb
from sentence_transformers import SentenceTransformer


def load_chunks(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("chunks JSON must contain a list of chunk objects")
    return data


def batch_iterable(iterable: Iterable, batch_size: int) -> Iterable[List]:
    batch = []
    for item in iterable:
        batch.append(item)
        if len(batch) >= batch_size:
            yield batch
            batch = []
    if batch:
        yield batch


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--chunks-file", type=Path, default=Path("chunks.json"), help="Path to chunks.json")
    parser.add_argument("--collection-name", type=str, default="wgu_chunks", help="ChromaDB collection name")
    parser.add_argument("--persist-dir", type=Path, default=Path("./chromadb_persist"), help="ChromaDB persist directory")
    parser.add_argument("--batch-size", type=int, default=64, help="Batch size for embedding")
    args = parser.parse_args()

    if not args.chunks_file.exists():
        raise FileNotFoundError(f"Chunks file not found: {args.chunks_file}")

    print(f"Loading chunks from: {args.chunks_file}")
    chunks = load_chunks(args.chunks_file)
    print(f"Loaded {len(chunks)} chunks")

    # Load embedding model
    print("Loading sentence-transformers/all-MiniLM-L6-v2 model...")
    model = SentenceTransformer("all-MiniLM-L6-v2")

    # Setup ChromaDB persistent client (chromadb >= 0.4)
    args.persist_dir.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(args.persist_dir))

    collection = client.get_or_create_collection(
        name=args.collection_name,
        metadata={"hnsw:space": "cosine"},
    )
    print(f"Using collection: {args.collection_name} (cosine distance)")

    # Add in batches
    total = 0
    for batch in batch_iterable(chunks, args.batch_size):
        ids = [c.get("chunk_id") or f"chunk_{i}" for i, c in enumerate(batch, start=total)]
        documents = [c.get("text", "") for c in batch]
        # Keep all fields except text as metadata; coerce values to ChromaDB-safe types
        def _safe(v):
            if isinstance(v, (str, int, float, bool)):
                return v
            if v is None:
                return ""
            return str(v)

        metadatas = [{k: _safe(v) for k, v in c.items() if k != "text"} for c in batch]

        # Compute embeddings
        emb = model.encode(documents, show_progress_bar=False, convert_to_numpy=True)

        # Chroma expects python lists for embeddings
        emb_list = emb.tolist()

        collection.add(ids=ids, documents=documents, metadatas=metadatas, embeddings=emb_list)
        total += len(batch)
        print(f"Added {total}/{len(chunks)} chunks")

    print(f"Done. Stored {total} chunks in collection '{args.collection_name}' at {args.persist_dir}")


if __name__ == "__main__":
    main()
