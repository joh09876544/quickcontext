import re
from typing import Optional


STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "has", "he",
    "in", "is", "it", "its", "of", "on", "that", "the", "to", "was", "will", "with",
    "this", "but", "they", "have", "had", "what", "when", "where", "who", "which",
    "why", "how", "can", "could", "should", "would", "may", "might", "must", "shall",
    "do", "does", "did", "doing", "done", "get", "got", "make", "made", "use", "used",
}


def extract_keywords(text: str, min_length: int = 3, max_keywords: Optional[int] = 10) -> list[str]:
    """
    Extract keywords from text using simple tokenization and filtering.

    text: str — Input text to extract keywords from.
    min_length: int — Minimum keyword length (default: 3).
    max_keywords: Optional[int] — Maximum number of keywords to return (default: 10).
    Returns: list[str] — Extracted keywords (lowercase, deduplicated).
    """
    text = text.lower()
    tokens = re.findall(r'\b[a-z_][a-z0-9_]*\b', text)

    keywords = []
    seen = set()

    for token in tokens:
        if len(token) < min_length:
            continue
        if token in STOP_WORDS:
            continue
        if token in seen:
            continue

        keywords.append(token)
        seen.add(token)

        if max_keywords and len(keywords) >= max_keywords:
            break

    return keywords


def keyword_overlap_score(query_keywords: list[str], chunk_keywords: list[str]) -> float:
    """
    Calculate keyword overlap score between query and chunk keywords.

    query_keywords: list[str] — Keywords extracted from search query.
    chunk_keywords: list[str] — Keywords stored in chunk payload.
    Returns: float — Overlap score (0.0 to 1.0).
    """
    if not query_keywords or not chunk_keywords:
        return 0.0

    query_set = set(kw.lower() for kw in query_keywords)
    chunk_set = set(kw.lower() for kw in chunk_keywords)

    overlap = len(query_set & chunk_set)
    max_possible = max(len(query_set), len(chunk_set))

    if max_possible == 0:
        return 0.0

    return overlap / max_possible


def keyword_query_coverage_score(query_keywords: list[str], chunk_keywords: list[str]) -> float:
    """
    Calculate how much of the query vocabulary is covered by candidate keywords.

    query_keywords: list[str] — Keywords extracted from the query.
    chunk_keywords: list[str] — Candidate keywords from metadata or symbols.
    Returns: float — Coverage score (0.0 to 1.0).
    """
    if not query_keywords or not chunk_keywords:
        return 0.0

    query_set = set(kw.lower() for kw in query_keywords)
    chunk_set = set(kw.lower() for kw in chunk_keywords)

    if not query_set:
        return 0.0

    overlap = len(query_set & chunk_set)
    return overlap / len(query_set)
