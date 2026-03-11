from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True, slots=True)
class SearchBias:
    """
    Named preset that tunes search parameters for a specific use case.

    Args:
        name: str — Preset identifier.
        vector_mode: str — Which vector space to search: code, desc, or hybrid.
        code_weight: float — Weight for code vector in hybrid mode (0-1).
        desc_weight: float — Weight for description vector in hybrid mode (0-1).
        use_keywords: bool — Enable keyword overlap boosting.
        keyword_weight: float — Weight for keyword score (0-1).
        rerank: bool — Enable ColBERT reranking.
        limit_multiplier: float — Multiply the user's --limit by this factor.
        symbol_kind: Optional[str] — Pre-filter to specific symbol kinds.
        description: str — Human-readable description of the preset.
    """
    name: str
    vector_mode: str
    code_weight: float
    desc_weight: float
    use_keywords: bool
    keyword_weight: float
    rerank: bool
    limit_multiplier: float
    symbol_kind: Optional[str]
    description: str


PRESETS: dict[str, SearchBias] = {
    "precise": SearchBias(
        name="precise",
        vector_mode="code",
        code_weight=1.0,
        desc_weight=0.0,
        use_keywords=True,
        keyword_weight=0.5,
        rerank=False,
        limit_multiplier=1.0,
        symbol_kind=None,
        description="Exact code matching with strong keyword boosting. Best for specific identifiers, API names, function signatures.",
    ),
    "discovery": SearchBias(
        name="discovery",
        vector_mode="hybrid",
        code_weight=0.3,
        desc_weight=0.7,
        use_keywords=False,
        keyword_weight=0.0,
        rerank=True,
        limit_multiplier=2.0,
        symbol_kind=None,
        description="Broad conceptual search favoring descriptions. Best for exploring unfamiliar codebases, finding related functionality.",
    ),
    "implementation": SearchBias(
        name="implementation",
        vector_mode="hybrid",
        code_weight=0.7,
        desc_weight=0.3,
        use_keywords=True,
        keyword_weight=0.3,
        rerank=False,
        limit_multiplier=1.0,
        symbol_kind=None,
        description="Code-heavy hybrid with keyword boosting. Best for finding how something is implemented, tracing logic.",
    ),
    "debug": SearchBias(
        name="debug",
        vector_mode="hybrid",
        code_weight=0.6,
        desc_weight=0.4,
        use_keywords=True,
        keyword_weight=0.4,
        rerank=True,
        limit_multiplier=1.5,
        symbol_kind=None,
        description="Balanced hybrid with reranking and keyword boosting. Best for tracking down bugs, error handling, edge cases.",
    ),
    "planning": SearchBias(
        name="planning",
        vector_mode="desc",
        code_weight=0.0,
        desc_weight=1.0,
        use_keywords=False,
        keyword_weight=0.0,
        rerank=True,
        limit_multiplier=2.0,
        symbol_kind=None,
        description="Pure description search with reranking. Best for architectural overview, understanding module responsibilities.",
    ),
}

BIAS_NAMES: list[str] = sorted(PRESETS.keys())


def get_bias(name: str) -> SearchBias:
    """
    Look up a named search bias preset.

    Args:
        name: str — Preset name (precise, discovery, implementation, debug, planning).

    Returns:
        SearchBias — The preset configuration.

    Raises:
        ValueError — If the preset name is not recognized.
    """
    bias = PRESETS.get(name)
    if bias is None:
        valid = ", ".join(BIAS_NAMES)
        raise ValueError(f"Unknown search bias: {name!r}. Valid options: {valid}")
    return bias


def apply_bias(
    bias: SearchBias,
    limit: int,
    mode: Optional[str] = None,
    use_keywords: Optional[bool] = None,
    keyword_weight: Optional[float] = None,
    rerank: Optional[bool] = None,
) -> dict:
    """
    Merge a bias preset with explicit user overrides.

    Explicit CLI flags always win over preset defaults. Returns a dict
    of resolved search parameters ready to pass to CodeSearcher methods.

    Args:
        bias: SearchBias — The preset to apply.
        limit: int — User-specified result limit.
        mode: Optional[str] — Explicit --mode override (None = use preset).
        use_keywords: Optional[bool] — Explicit --use-keywords override.
        keyword_weight: Optional[float] — Explicit --keyword-weight override.
        rerank: Optional[bool] — Explicit --rerank override.

    Returns:
        dict — Resolved parameters: vector_mode, limit, code_weight, desc_weight,
               use_keywords, keyword_weight, rerank, symbol_kind.
    """
    resolved_limit = max(1, int(limit * bias.limit_multiplier))

    return {
        "vector_mode": mode if mode is not None else bias.vector_mode,
        "limit": resolved_limit,
        "code_weight": bias.code_weight,
        "desc_weight": bias.desc_weight,
        "use_keywords": use_keywords if use_keywords is not None else bias.use_keywords,
        "keyword_weight": keyword_weight if keyword_weight is not None else bias.keyword_weight,
        "rerank": rerank if rerank is not None else bias.rerank,
        "symbol_kind": bias.symbol_kind,
    }
