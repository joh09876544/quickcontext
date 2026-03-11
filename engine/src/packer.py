from dataclasses import dataclass
from typing import Optional

import tiktoken


_ENCODER: Optional[tiktoken.Encoding] = None


def _get_encoder() -> tiktoken.Encoding:
    """
    Returns: tiktoken.Encoding — Cached cl100k_base encoder instance.
    """
    global _ENCODER
    if _ENCODER is None:
        _ENCODER = tiktoken.get_encoding("cl100k_base")
    return _ENCODER


def count_tokens(text: str) -> int:
    """
    Count tokens using cl100k_base encoding (GPT-4 / Claude compatible).

    text: str — Input text to tokenize.
    Returns: int — Token count.
    """
    return len(_get_encoder().encode(text))


def truncate_source(
    source: str,
    max_tokens: int,
    signature: Optional[str] = None,
) -> tuple[str, bool]:
    """
    Truncate source code to fit within a token budget.

    Preserves the signature line(s) at the top, then fills remaining budget
    with body lines. Appends a truncation marker if cut short.

    source: str — Full source code text.
    max_tokens: int — Maximum tokens allowed for this source block.
    signature: Optional[str] — Function/class signature to always preserve.
    Returns: tuple[str, bool] — (truncated_source, was_truncated).
    """
    if count_tokens(source) <= max_tokens:
        return source, False

    lines = source.split("\n")
    enc = _get_encoder()
    marker = "    # ... (truncated)"
    marker_tokens = len(enc.encode(marker))
    budget = max_tokens - marker_tokens

    if budget <= 0:
        return marker, True

    kept: list[str] = []
    used = 0

    for line in lines:
        line_tokens = len(enc.encode(line + "\n"))
        if used + line_tokens > budget:
            break
        kept.append(line)
        used += line_tokens

    if not kept:
        kept.append(lines[0])

    if len(kept) < len(lines):
        kept.append(marker)
        return "\n".join(kept), True

    return source, False


@dataclass(frozen=True, slots=True)
class PackedResult:
    """
    A search result after token budget packing.

    file_path: str — Source file path.
    symbol_name: str — Symbol name.
    symbol_kind: str — Symbol type.
    line_start: int — Starting line number.
    line_end: int — Ending line number.
    source: str — Source code (possibly truncated).
    description: str — Natural language description.
    score: float — Relevance score.
    signature: Optional[str] — Function/method signature.
    parent: Optional[str] — Parent symbol name.
    language: Optional[str] — Programming language.
    path_context: Optional[str] — Path-derived context string.
    truncated: bool — True if source was truncated to fit budget.
    """
    file_path: str
    symbol_name: str
    symbol_kind: str
    line_start: int
    line_end: int
    source: str
    description: str
    score: float
    signature: Optional[str]
    parent: Optional[str]
    language: Optional[str]
    path_context: Optional[str]
    truncated: bool


@dataclass(frozen=True, slots=True)
class PackedOutput:
    """
    Final packed output with budget accounting.

    results: list[PackedResult] — Packed results that fit within budget.
    total_tokens: int — Total tokens consumed by packed results.
    max_tokens: int — Token budget that was requested.
    results_included: int — Number of results included.
    results_truncated: int — Number of results whose source was truncated.
    results_dropped: int — Number of results that didn't fit at all.
    """
    results: list[PackedResult]
    total_tokens: int
    max_tokens: int
    results_included: int
    results_truncated: int
    results_dropped: int


def _result_to_text(
    file_path: str,
    symbol_name: str,
    symbol_kind: str,
    line_start: int,
    line_end: int,
    source: str,
    description: str,
    signature: Optional[str],
    parent: Optional[str],
    language: Optional[str],
    path_context: Optional[str],
) -> str:
    """
    Render a single result as the text block that gets token-counted.

    Returns: str — Formatted text representation of the result.
    """
    parts = [f"## {symbol_name} ({symbol_kind})"]
    parts.append(f"File: {file_path}:{line_start}-{line_end}")

    if language:
        parts.append(f"Language: {language}")
    if parent:
        parts.append(f"Parent: {parent}")
    if path_context:
        parts.append(f"Context: {path_context}")
    if signature:
        parts.append(f"Signature: {signature}")

    parts.append(f"Description: {description}")
    parts.append(f"```\n{source}\n```")

    return "\n".join(parts)


def pack_search_results(
    results: list,
    max_tokens: int,
    min_source_tokens: int = 64,
    include_source: bool = True,
    compress: Optional[str] = None,
) -> PackedOutput:
    """
    Pack search results into a token budget using greedy allocation.

    Higher-scored results get priority. Each result's source is compressed
    (if requested), then truncated to fit remaining budget. Results that
    can't fit even their metadata are dropped entirely.

    results: list — SearchResult objects (must have score, file_path, symbol_name, etc.).
    max_tokens: int — Total token budget for all results combined.
    min_source_tokens: int — Minimum tokens to allocate per source block. Results that
        would get fewer than this are dropped instead of included with tiny snippets.
    include_source: bool — Include source code in output. When False, only metadata
        and description are packed (much more compact).
    compress: Optional[str] — Compression level before truncation: "light", "medium",
        "aggressive", or None to skip compression.
    Returns: PackedOutput — Packed results with budget accounting.
    """
    sorted_results = sorted(results, key=lambda r: r.score, reverse=True)

    _compressor = None
    if compress:
        from engine.src.compressor import compress_source
        _compressor = compress_source

    packed: list[PackedResult] = []
    total_used = 0
    truncated_count = 0
    dropped_count = 0

    for result in sorted_results:
        meta_text = _result_to_text(
            file_path=result.file_path,
            symbol_name=result.symbol_name,
            symbol_kind=result.symbol_kind,
            line_start=result.line_start,
            line_end=result.line_end,
            source="",
            description=result.description,
            signature=getattr(result, "signature", None),
            parent=getattr(result, "parent", None),
            language=getattr(result, "language", None),
            path_context=getattr(result, "path_context", None),
        )
        meta_tokens = count_tokens(meta_text)

        remaining = max_tokens - total_used

        if meta_tokens > remaining:
            dropped_count += 1
            continue

        if not include_source:
            total_used += meta_tokens
            packed.append(PackedResult(
                file_path=result.file_path,
                symbol_name=result.symbol_name,
                symbol_kind=result.symbol_kind,
                line_start=result.line_start,
                line_end=result.line_end,
                source="",
                description=result.description,
                score=result.score,
                signature=getattr(result, "signature", None),
                parent=getattr(result, "parent", None),
                language=getattr(result, "language", None),
                path_context=getattr(result, "path_context", None),
                truncated=False,
            ))
            continue

        source_budget = remaining - meta_tokens

        if source_budget < min_source_tokens:
            dropped_count += 1
            continue

        source_text = result.source
        if _compressor and source_text:
            source_text, _ = _compressor(
                source_text,
                level=compress,
                language=getattr(result, "language", None),
            )

        truncated_source, was_truncated = truncate_source(
            source=source_text,
            max_tokens=source_budget,
            signature=getattr(result, "signature", None),
        )

        if was_truncated:
            truncated_count += 1

        full_text = _result_to_text(
            file_path=result.file_path,
            symbol_name=result.symbol_name,
            symbol_kind=result.symbol_kind,
            line_start=result.line_start,
            line_end=result.line_end,
            source=truncated_source,
            description=result.description,
            signature=getattr(result, "signature", None),
            parent=getattr(result, "parent", None),
            language=getattr(result, "language", None),
            path_context=getattr(result, "path_context", None),
        )
        result_tokens = count_tokens(full_text)
        total_used += result_tokens

        packed.append(PackedResult(
            file_path=result.file_path,
            symbol_name=result.symbol_name,
            symbol_kind=result.symbol_kind,
            line_start=result.line_start,
            line_end=result.line_end,
            source=truncated_source,
            description=result.description,
            score=result.score,
            signature=getattr(result, "signature", None),
            parent=getattr(result, "parent", None),
            language=getattr(result, "language", None),
            path_context=getattr(result, "path_context", None),
            truncated=was_truncated,
        ))

    return PackedOutput(
        results=packed,
        total_tokens=total_used,
        max_tokens=max_tokens,
        results_included=len(packed),
        results_truncated=truncated_count,
        results_dropped=dropped_count,
    )


def pack_grep_results(
    results: list,
    max_tokens: int,
) -> tuple[list, int, int]:
    """
    Pack grep matches into a token budget.

    results: list — GrepMatch objects (must have file_path, line_number, line).
    max_tokens: int — Total token budget.
    Returns: tuple[list, int, int] — (kept_matches, total_tokens, dropped_count).
    """
    kept = []
    total_used = 0
    dropped = 0

    for match in results:
        line_text = f"{match.file_path}:{match.line_number}: {match.line}"
        tokens = count_tokens(line_text)

        if total_used + tokens > max_tokens:
            dropped += 1
            continue

        kept.append(match)
        total_used += tokens

    return kept, total_used, dropped


def pack_skeleton(
    markdown: str,
    max_tokens: int,
) -> tuple[str, int, bool]:
    """
    Truncate skeleton markdown output to fit a token budget.

    markdown: str — Full skeleton markdown text.
    max_tokens: int — Token budget.
    Returns: tuple[str, int, bool] — (output_text, token_count, was_truncated).
    """
    total = count_tokens(markdown)
    if total <= max_tokens:
        return markdown, total, False

    lines = markdown.split("\n")
    enc = _get_encoder()
    marker = "\n... (skeleton truncated to fit token budget)"
    marker_tokens = len(enc.encode(marker))
    budget = max_tokens - marker_tokens

    kept: list[str] = []
    used = 0

    for line in lines:
        line_tokens = len(enc.encode(line + "\n"))
        if used + line_tokens > budget:
            break
        kept.append(line)
        used += line_tokens

    return "\n".join(kept) + marker, used + marker_tokens, True
