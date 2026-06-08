"""
load_documents.py
-----------------
Loads all .txt student knowledge documents from the docs directory and
returns a list of structured Document dicts ready for a RAG pipeline.

Each Document has:
  - text:     raw content of the file
  - source:   human-readable source name (Reddit, YouTube, etc.)
  - url:      original URL (if known)
  - filename: the .txt filename
  - filepath: absolute path to the file
"""

import os
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Source metadata — maps filename fragments → (source label, URL)
# Edit or extend this dict as you add more documents.
# ---------------------------------------------------------------------------
SOURCE_MAP: dict[str, tuple[str, str]] = {
    "reddit_review_of_all_wgu_classes": (
        "Reddit",
        "https://www.reddit.com/r/WGU_CompSci/comments/1k7xbko/review_of_all_wgu_classes_i_took_tips_as_an/",
    ),
    "youtube_survival_tips": (
        "YouTube",
        "https://www.youtube.com/watch?v=yriZNpncMwI",
    ),
    "stunlock_thoughts_on_wgu": (
        "Stunlock",
        "https://stunlock.gg/posts/undergrad/",
    ),
    "infosecinstitute_mba_it_management": (
        "InfoSecInstitute",
        "https://community.infosecinstitute.com/discussion/134945/starting-wgu-mba-it-management-on-mar-1-2019/p2",
    ),
    "reddit_structure_of_typical_course": (
        "Reddit",
        "https://www.reddit.com/r/WGU/comments/y8q6ui/structure_of_a_typical_course/",
    ),
    "degreeforum_tips_for_success": (
        "Degree Forum",
        "https://www.degreeforum.net/mybb/Thread-Tips-for-success-at-WGU-to-finish-in-a-single-term",
    ),
    "reddit_best_study_method": (
        "Reddit",
        "https://www.reddit.com/r/WGU/comments/14pxj4o/what_is_your_best_study_method/",
    ),
    "youtube_finish_as_fast_as_possible": (
        "YouTube",
        "https://www.youtube.com/watch?v=nUhsV0IpXWg",
    ),
    "youtube_study_2x_3x_faster": (
        "YouTube",
        "https://www.youtube.com/watch?v=7kTkSGWExLw",
    ),
    "youtube_how_to_succeed_at_wgu": (
        "YouTube",
        "https://www.youtube.com/watch?v=QPfMchoITKU",
    ),
    "reddit_comprehensive_guide_to_wgu": (
        "Reddit",
        "https://www.reddit.com/r/WGU/comments/1goyuwa/a_comprehensive_guide_to_wgu_my_full_honest/",
    ),
    "reddit_need_all_advice_and_resources": (
        "Reddit",
        "https://www.reddit.com/r/WGU/comments/1pb39gx/need_all_the_advice_and_resources/",
    ),
    "youtube_cybersecurity_degree_review": (
        "YouTube",
        "https://www.youtube.com/watch?v=le91dq4CCnU",
    ),
}

# Source-type fallbacks: if no exact key matches, guess from filename prefix
SOURCE_PREFIX_MAP: dict[str, str] = {
    "reddit_": "Reddit",
    "youtube_": "YouTube",
    "stunlock_": "Stunlock",
    "infosec": "InfoSecInstitute",
    "degreeforum_": "Degree Forum",
}


def _infer_source(stem: str) -> tuple[str, Optional[str]]:
    """Return (source_label, url) for a filename stem, using SOURCE_MAP first."""
    stem_lower = stem.lower()

    # Exact / substring match in SOURCE_MAP
    for key, (label, url) in SOURCE_MAP.items():
        if key in stem_lower:
            return label, url

    # Prefix fallback
    for prefix, label in SOURCE_PREFIX_MAP.items():
        if stem_lower.startswith(prefix):
            return label, None

    return "Unknown", None


def load_documents(docs_dir: str = r"C:\projects\ai201-project1-unofficial-guide-starter\docs") -> list[dict]:
    """
    Load every .txt file in docs_dir and return a list of Document dicts.

    Parameters
    ----------
    docs_dir : str
        Path to the directory containing .txt knowledge files.

    Returns
    -------
    list[dict]
        Each dict has keys: text, source, url, filename, filepath.
    """
    docs_path = Path(docs_dir)
    if not docs_path.exists():
        raise FileNotFoundError(f"Docs directory not found: {docs_dir}")

    txt_files = sorted(docs_path.glob("*.txt"))
    if not txt_files:
        print(f"[WARNING] No .txt files found in {docs_dir}")
        return []

    documents = []
    for filepath in txt_files:
        try:
            text = filepath.read_text(encoding="utf-8", errors="replace").strip()
        except Exception as exc:
            print(f"[ERROR] Could not read {filepath.name}: {exc}")
            continue

        source, url = _infer_source(filepath.stem)

        documents.append(
            {
                "text": text,
                "source": source,
                "url": url,
                "filename": filepath.name,
                "filepath": str(filepath.resolve()),
            }
        )
        print(f"  Loaded [{source:20s}]  {filepath.name}  ({len(text):,} chars)")

    return documents


# ---------------------------------------------------------------------------
# Quick smoke-test — run this file directly to verify loading works
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("Loading documents...\n")
    docs = load_documents()
    print(f"\nTotal documents loaded: {len(docs)}")

    if docs:
        print("\n--- Sample (first document) ---")
        sample = docs[0]
        print(f"  filename : {sample['filename']}")
        print(f"  source   : {sample['source']}")
        print(f"  url      : {sample['url']}")
        print(f"  length   : {len(sample['text']):,} chars")
        print(f"  preview  : {sample['text'][:200]}...")