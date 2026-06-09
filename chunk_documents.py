"""
chunk_documents.py
------------------
Paragraph-aware chunker for the WGU Unofficial Guide RAG system.

Algorithm:
  1. Parse source metadata from each document's header block.
  2. Split body text on blank-line paragraph boundaries.
  3. If a paragraph itself exceeds TARGET_MAX, split it further at sentence
     boundaries (the paragraph is still kept as the primary semantic unit).
  4. Greedily combine atomic units until the chunk reaches 700–900 characters.
  5. Carry a 100–150 character word-boundary overlap into the next chunk.
  6. Attach source metadata to every chunk.

Output: chunks.json — a list of chunk dicts ready for embedding / ingestion.
"""

import argparse
import json
import re
from pathlib import Path

# ── Configuration ──────────────────────────────────────────────────────────────

DOCS_DIR    = Path(r"C:\projects\ai201-project1-unofficial-guide-starter\docs")
OUTPUT      = Path(r"C:\projects\ai201-project1-unofficial-guide-starter\chunks.json")

TARGET_MIN  = 350    # minimum chars per chunk
TARGET_MAX  = 450    # maximum chars per chunk before forcing a split
OVERLAP_MIN = 50     # minimum overlap chars carried forward
OVERLAP_MAX = 75     # maximum overlap chars carried forward


# ── Metadata parsing ──────────────────────────────────────────────────────────

def parse_header(text: str) -> tuple[dict, str]:
    """
    Extract key:value metadata lines before the first '---' separator.
    Returns (metadata_dict, body_text).
    """
    header_keys = {"source", "author", "title", "date", "note", "speaker"}
    metadata: dict = {}
    lines = text.splitlines()
    sep_line = None

    for i, line in enumerate(lines):
        if line.strip() == "---":
            sep_line = i
            break
        m = re.match(r'^([A-Za-z ]+):\s*(.+)$', line)
        if m and m.group(1).strip().lower() in header_keys:
            metadata[m.group(1).strip().lower()] = m.group(2).strip()

    body = "\n".join(lines[sep_line + 1:]).strip() if sep_line is not None else text.strip()
    return metadata, body


# ── Text splitting helpers ────────────────────────────────────────────────────

def split_sentences(text: str) -> list[str]:
    """
    Split *text* into sentences on period/exclamation/question followed by
    whitespace + capital letter, or on a bare newline.
    Returns non-empty sentence strings.
    """
    parts = re.split(r'(?<=[.!?])\s+(?=[A-Z"\'(])|(?<=\n)', text)
    return [p.strip() for p in parts if p.strip()]


def atomic_units(body: str, target_max: int = TARGET_MAX) -> list[str]:
    """
    Return a flat list of text units for chunking:
      - Each paragraph becomes one unit if len <= target_max.
      - Paragraphs longer than target_max are split into sentences first.
    This preserves as much semantic completeness as possible while keeping
    individual units within the size ceiling.
    """
    paragraphs = [p.strip() for p in re.split(r'\n\n+', body) if p.strip()]
    units: list[str] = []

    for para in paragraphs:
        if len(para) <= target_max:
            units.append(para)
        else:
            # Paragraph too long — break into sentences, then re-group
            sentences = split_sentences(para)
            group = ""
            for sent in sentences:
                candidate = (group + " " + sent).strip() if group else sent
                if len(candidate) <= target_max:
                    group = candidate
                else:
                    if group:
                        units.append(group)
                    # If a single sentence exceeds the ceiling, keep it whole
                    group = sent
            if group:
                units.append(group)

    return units


# ── Overlap extraction ────────────────────────────────────────────────────────

def extract_overlap(text: str, overlap_min: int = OVERLAP_MIN, overlap_max: int = OVERLAP_MAX) -> str:
    """
    Return the last overlap_min–overlap_max chars of *text*, snapping to the
    nearest word boundary so the overlap always starts mid-word cleanly.
    """
    if len(text) <= overlap_min:
        return text

    window_start = max(0, len(text) - overlap_max)
    window_end   = len(text) - overlap_min

    if window_end <= window_start:
        return text[-overlap_min:]

    window = text[window_start:window_end]
    space  = window.find(" ")   # first space → longest clean overlap

    if space != -1:
        return text[window_start + space + 1:]

    return text[-overlap_min:]


# ── Core chunker ─────────────────────────────────────────────────────────────

def chunk_body(
    body: str,
    target_min:  int = TARGET_MIN,
    target_max:  int = TARGET_MAX,
    overlap_min: int = OVERLAP_MIN,
    overlap_max: int = OVERLAP_MAX,
) -> list[str]:
    """
    Produce overlapping chunks from *body* text, respecting paragraph / sentence
    boundaries and targeting target_min–target_max characters per chunk.
    """
    units = atomic_units(body, target_max=target_max)
    chunks: list[str] = []
    overlap_text: str = ""
    current_units: list[str] = []

    def assembled() -> str:
        parts = ([overlap_text] if overlap_text else []) + current_units
        return "\n\n".join(parts).strip()

    def assembled_len() -> int:
        return len(assembled())

    for unit in units:
        # Length if we add this unit
        sep       = "\n\n" if (current_units or overlap_text) else ""
        added_len = assembled_len() + len(sep) + len(unit)

        if added_len > target_max and current_units:
            # Adding this unit would breach the ceiling.
            # Always finalise what we have now (even if below target_min —
            # a slightly short chunk is better than a massively oversized one).
            chunk = assembled()
            chunks.append(chunk)
            overlap_text  = extract_overlap(chunk, overlap_min, overlap_max)
            current_units = [unit]
        else:
            # Unit fits — add it.
            current_units.append(unit)
            if assembled_len() >= target_min:
                # ✓ Reached the target window — finalise.
                chunk = assembled()
                chunks.append(chunk)
                overlap_text  = extract_overlap(chunk, overlap_min, overlap_max)
                current_units = []

    # Flush remaining units as the last chunk
    if current_units:
        chunks.append(assembled())

    return chunks


# ── Document processor ────────────────────────────────────────────────────────

def process_file(
    filepath: Path,
    target_min:  int = TARGET_MIN,
    target_max:  int = TARGET_MAX,
    overlap_min: int = OVERLAP_MIN,
    overlap_max: int = OVERLAP_MAX,
) -> list[dict]:
    """Load one .txt file, chunk it, and return a list of chunk dicts."""
    raw = filepath.read_text(encoding="utf-8", errors="replace")
    metadata, body = parse_header(raw)

    if not body:
        print(f"  [SKIP] {filepath.name} — no body text.")
        return []

    raw_chunks = chunk_body(body, target_min, target_max, overlap_min, overlap_max)
    return [
        {
            "chunk_id"    : f"{filepath.stem}_chunk_{idx:03d}",
            "chunk_index" : idx,
            "source_file" : filepath.name,
            "text"        : text,
            "char_count"  : len(text),
            **metadata,
        }
        for idx, text in enumerate(raw_chunks)
    ]


# ── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Chunk WGU guide documents into overlapping text segments."
    )
    parser.add_argument("--target-min",  type=int, default=TARGET_MIN,
                        help=f"Minimum chars per chunk (default: {TARGET_MIN})")
    parser.add_argument("--target-max",  type=int, default=TARGET_MAX,
                        help=f"Maximum chars per chunk (default: {TARGET_MAX})")
    parser.add_argument("--overlap-min", type=int, default=OVERLAP_MIN,
                        help=f"Minimum overlap chars (default: {OVERLAP_MIN})")
    parser.add_argument("--overlap-max", type=int, default=OVERLAP_MAX,
                        help=f"Maximum overlap chars (default: {OVERLAP_MAX})")
    parser.add_argument("--docs-dir",    type=Path, default=DOCS_DIR,
                        help="Directory containing source .txt files")
    parser.add_argument("--output",      type=Path, default=OUTPUT,
                        help="Output path for chunks.json")
    args = parser.parse_args()

    # Override module-level constants with any CLI values so summary stats match
    target_min  = args.target_min
    target_max  = args.target_max
    overlap_min = args.overlap_min
    overlap_max = args.overlap_max

    if not args.docs_dir.exists():
        raise FileNotFoundError(f"Docs directory not found: {args.docs_dir}")

    txt_files = sorted(args.docs_dir.glob("*.txt"))
    if not txt_files:
        print(f"No .txt files found in {args.docs_dir}")
        return

    all_chunks: list[dict] = []

    print(f"Processing {len(txt_files)} documents from {args.docs_dir}")
    print(f"Chunk size: {target_min}–{target_max} chars  |  Overlap: {overlap_min}–{overlap_max} chars\n")
    for filepath in txt_files:
        chunks = process_file(filepath, target_min, target_max, overlap_min, overlap_max)
        all_chunks.extend(chunks)

        sizes = [c["char_count"] for c in chunks]
        avg   = int(sum(sizes) / len(sizes)) if sizes else 0
        in_r  = sum(1 for s in sizes if target_min <= s <= target_max)
        print(
            f"  {filepath.name:<65}"
            f"  {len(chunks):>3} chunks  "
            f"  avg {avg:>4}  "
            f"  [{min(sizes) if sizes else 0}–{max(sizes) if sizes else 0}]  "
            f"  {in_r}/{len(chunks)} in range"
        )

    args.output.write_text(
        json.dumps(all_chunks, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    # ── Summary ──
    all_sizes = [c["char_count"] for c in all_chunks]
    in_range  = sum(1 for s in all_sizes if target_min <= s <= target_max)
    pct       = 100 * in_range / len(all_sizes) if all_sizes else 0

    print(f"\n{'─'*72}")
    print(f"Total chunks      : {len(all_chunks)}")
    print(f"In target range   : {in_range} / {len(all_chunks)}  ({pct:.1f}%)")
    print(f"Avg chunk size    : {int(sum(all_sizes)/len(all_sizes)) if all_sizes else 0} chars")
    print(f"Min / Max         : {min(all_sizes) if all_sizes else 0} / {max(all_sizes) if all_sizes else 0} chars")
    print(f"\nOutput saved to   : {args.output}")


if __name__ == "__main__":
    main()