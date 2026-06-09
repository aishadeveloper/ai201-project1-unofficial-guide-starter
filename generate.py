"""
generate.py
-----------
Grounded generation layer for the WGU Unofficial Guide RAG system.

Retrieves the top-k most relevant chunks from ChromaDB, then passes them
to Groq's llama-3.3-70b-versatile with a strict grounding prompt that
instructs the model to answer *only* from the provided context and to
attribute its answer to the source documents it drew from.

Quickstart
----------
  # One-shot
  from generate import ask
  result = ask("What study techniques do students recommend for WGU?")
  print(result["answer"])
  print(result["sources"])

  # Reuse the pipeline across many queries (loads model/collection once)
  from generate import RAGPipeline
  pipeline = RAGPipeline()
  result = pipeline.ask("How do WGU courses compare to traditional college?")

  # CLI
  python generate.py "What are three strategies to complete WGU courses faster?"
"""
from __future__ import annotations

import argparse
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from groq import Groq

from retrieve import DEFAULT_COLLECTION, DEFAULT_PERSIST_DIR, DEFAULT_TOP_K, Retriever, RetrievedChunk

# ── Load .env ──────────────────────────────────────────────────────────────────

load_dotenv()

# ── Prompt templates ───────────────────────────────────────────────────────────

SYSTEM_PROMPT = """\
You are a knowledgeable assistant helping students at Western Governors University (WGU).

STRICT GROUNDING RULE: Answer using ONLY the information in the provided context documents.
Do not add outside knowledge, general advice, or anything not explicitly stated in the documents.
If the documents do not contain enough information to fully answer the question, say:
"I don't have enough information on that."

SOURCE CITATION RULE: End every answer with a "Sources:" section that lists — by title — only
the documents you actually drew from. If you drew from multiple documents, list each one.
Format exactly as:
Sources:
- <Title> (<Source>)
- <Title> (<Source>)
"""

def _build_context_block(chunks: list[RetrievedChunk]) -> str:
    """Format retrieved chunks into a numbered context block for the prompt."""
    blocks = []
    for i, chunk in enumerate(chunks, start=1):
        label_parts = [chunk.title or chunk.source_file]
        if chunk.source:
            label_parts.append(chunk.source)
        if chunk.author:
            label_parts.append(f"by {chunk.author}")
        label = " | ".join(label_parts)

        blocks.append(
            f"[DOCUMENT {i}]\n"
            f"Title: {chunk.title or chunk.source_file}\n"
            f"Source: {chunk.source or 'Unknown'}"
            + (f" | Author: {chunk.author}" if chunk.author else "")
            + f"\n---\n{chunk.text}"
        )
    return "\n\n".join(blocks)


def _build_user_message(query: str, chunks: list[RetrievedChunk]) -> str:
    context = _build_context_block(chunks)
    return (
        f"CONTEXT DOCUMENTS:\n\n{context}\n\n"
        f"---\n\n"
        f"QUESTION: {query}\n\n"
        f"Answer using only the context documents above. "
        f"End with a Sources section listing the documents you drew from."
    )


# ── Result dataclass ───────────────────────────────────────────────────────────

@dataclass
class RAGResult:
    """Full result from one RAG pipeline call."""
    query:   str
    answer:  str
    sources: list[str]                        # deduplicated source strings
    chunks:  list[RetrievedChunk] = field(default_factory=list)

    def __str__(self) -> str:
        sep = "─" * 72
        sources_str = "\n".join(f"  • {s}" for s in self.sources)
        retrieved_str = "\n".join(
            f"  [{c.rank}] {c.title or c.source_file}  "
            f"(chunk {c.chunk_index}, dist={c.distance:.4f})"
            for c in self.chunks
        )
        return (
            f"{sep}\n"
            f"Query:  {self.query}\n"
            f"{sep}\n"
            f"{self.answer}\n"
            f"{sep}\n"
            f"Retrieved chunks:\n{retrieved_str}\n"
        )


def _deduplicate_sources(chunks: list[RetrievedChunk]) -> list[str]:
    """Build a deduplicated list of 'Title (Source)' strings from chunks."""
    seen: dict[str, str] = {}
    for c in chunks:
        key = c.title or c.source_file
        if key not in seen:
            label = key
            if c.source:
                label += f" ({c.source})"
            seen[key] = label
    return list(seen.values())


# ── RAGPipeline class ──────────────────────────────────────────────────────────

class RAGPipeline:
    """
    Holds the Retriever and Groq client so both are initialised once and
    reused across multiple queries.

    Parameters
    ----------
    persist_dir : Path | str
        ChromaDB persist directory.
    collection_name : str
        ChromaDB collection name.
    groq_api_key : str | None
        Groq API key. Falls back to the GROQ_API_KEY environment variable.
    model : str
        Groq model identifier.
    top_k : int
        Number of chunks to retrieve per query.
    """

    def __init__(
        self,
        persist_dir:     Path | str  = DEFAULT_PERSIST_DIR,
        collection_name: str         = DEFAULT_COLLECTION,
        groq_api_key:    Optional[str] = None,
        model:           str         = "llama-3.3-70b-versatile",
        top_k:           int         = DEFAULT_TOP_K,
    ) -> None:
        api_key = groq_api_key or os.environ.get("GROQ_API_KEY")
        if not api_key:
            raise EnvironmentError(
                "GROQ_API_KEY not found. Set it in your .env file or pass it directly."
            )

        self._groq   = Groq(api_key=api_key)
        self._model  = model
        self._top_k  = top_k
        self._retriever = Retriever(
            persist_dir=persist_dir,
            collection_name=collection_name,
        )

    def ask(self, query: str, top_k: Optional[int] = None) -> RAGResult:
        """
        Retrieve relevant chunks and generate a grounded answer.

        Parameters
        ----------
        query : str
            Natural-language question from the user.
        top_k : int | None
            Override the pipeline's default top-k for this call.

        Returns
        -------
        RAGResult
            Contains the answer text, deduplicated source list, and raw chunks.
        """
        k = top_k if top_k is not None else self._top_k
        chunks = self._retriever.query(query, top_k=k)

        user_message = _build_user_message(query, chunks)

        completion = self._groq.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": user_message},
            ],
            temperature=0.0,   # deterministic — grounding requires no creativity
        )

        answer = completion.choices[0].message.content.strip()
        sources = _deduplicate_sources(chunks)

        return RAGResult(query=query, answer=answer, sources=sources, chunks=chunks)


# ── Module-level convenience function ─────────────────────────────────────────

def ask(
    query:           str,
    top_k:           int         = DEFAULT_TOP_K,
    persist_dir:     Path | str  = DEFAULT_PERSIST_DIR,
    collection_name: str         = DEFAULT_COLLECTION,
    groq_api_key:    Optional[str] = None,
) -> RAGResult:
    """
    One-shot RAG call. Convenient for scripts; use RAGPipeline for repeated queries.
    """
    return RAGPipeline(
        persist_dir=persist_dir,
        collection_name=collection_name,
        groq_api_key=groq_api_key,
    ).ask(query, top_k=top_k)


# ── CLI ────────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Ask a grounded question against the WGU guide corpus."
    )
    parser.add_argument("query", help="Question to ask")
    parser.add_argument(
        "--top-k", type=int, default=DEFAULT_TOP_K,
        help=f"Number of chunks to retrieve (default: {DEFAULT_TOP_K})"
    )
    parser.add_argument(
        "--persist-dir", type=Path, default=DEFAULT_PERSIST_DIR,
        help="ChromaDB persist directory"
    )
    parser.add_argument(
        "--collection", type=str, default=DEFAULT_COLLECTION,
        help="ChromaDB collection name"
    )
    parser.add_argument(
        "--model", type=str, default="llama-3.3-70b-versatile",
        help="Groq model identifier"
    )
    args = parser.parse_args()

    pipeline = RAGPipeline(
        persist_dir=args.persist_dir,
        collection_name=args.collection,
        model=args.model,
        top_k=args.top_k,
    )

    result = pipeline.ask(args.query)
    print(result)


if __name__ == "__main__":
    main()
