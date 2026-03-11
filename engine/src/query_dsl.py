from dataclasses import dataclass
from typing import Literal


QueryType = Literal["lex", "vec", "hyde"]


@dataclass(frozen=True, slots=True)
class StructuredSubQuery:
    """
    Typed sub-query used for structured search fusion.

    kind: QueryType — Search intent type (lex, vec, hyde).
    text: str — Query text for this sub-query.
    """

    kind: QueryType
    text: str


def parse_structured_query(query: str) -> list[StructuredSubQuery]:
    """
    Parse a structured query document into typed sub-queries.

    query: str — Raw query string (supports one sub-query per line in kind:text form).
    Returns: list[StructuredSubQuery] — Parsed sub-queries in source order.
    """
    parsed: list[StructuredSubQuery] = []

    for raw_line in query.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        prefix, sep, remainder = line.partition(":")
        if not sep:
            continue

        kind = prefix.strip().lower()
        if kind not in {"lex", "vec", "hyde"}:
            continue

        text = remainder.strip()
        if not text:
            continue

        parsed.append(StructuredSubQuery(kind=kind, text=text))

    return parsed


def looks_like_structured_query(query: str) -> bool:
    """
    Check whether query appears to use structured kind:text syntax.

    query: str — Raw query string.
    Returns: bool — True when at least one valid structured sub-query is found.
    """
    return len(parse_structured_query(query)) > 0
