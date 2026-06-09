"""
test_generate.py
----------------
End-to-end grounding test for the WGU Unofficial Guide RAG pipeline.

Tests 3 questions from the evaluation plan in planning.md.
For each query the output includes:

  1. The LLM's answer (must be grounded in retrieved chunks only)
  2. The retrieved chunk excerpts it was based on
  3. A grounding prompt to help you verify: "Could this answer have come
     from anywhere other than the retrieved chunks?"

Run:
  python test_generate.py
"""

from generate import RAGPipeline

# ── Queries from evaluation plan ──────────────────────────────────────────────

TEST_QUERIES = [
    "What study techniques do students most frequently recommend for WGU courses?",
    "What are three strategies to complete your WGU courses faster?",
    "How do WGU courses compare to traditional college courses?",
]

# ── Helpers ───────────────────────────────────────────────────────────────────

SEP  = "═" * 72
SEP2 = "─" * 72

def print_result(result, query_num: int) -> None:
    print(f"\n{SEP}")
    print(f"TEST {query_num}: {result.query}")
    print(SEP)

    print("\n📄 RETRIEVED CONTEXT (what the model was given):")
    print(SEP2)
    for chunk in result.chunks:
        label = f"[{chunk.rank}] {chunk.title or chunk.source_file}  (chunk {chunk.chunk_index}, dist={chunk.distance:.4f})"
        print(label)
        # Print first 300 chars of each chunk as a preview
        preview = chunk.text[:300].replace("\n", " ")
        if len(chunk.text) > 300:
            preview += "…"
        print(f"    {preview}")
    print()

    print("🤖 GENERATED ANSWER:")
    print(SEP2)
    print(result.answer)
    print()

    print("✅ GROUNDING CHECK — verify manually:")
    print(SEP2)
    print("  Could any part of this answer have come from outside the retrieved chunks above?")
    print("  Look for: specific claims, numbers, named resources, or recommendations")
    print("  that don't appear in the chunk previews. If yes → grounding failure.")
    print()


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    print("Initialising RAG pipeline (loads embedding model + ChromaDB)...")
    pipeline = RAGPipeline()
    print("Ready.\n")

    for i, query in enumerate(TEST_QUERIES, start=1):
        result = pipeline.ask(query)
        print_result(result, i)

    print(SEP)
    print("All tests complete.")
    print(SEP)


if __name__ == "__main__":
    main()
