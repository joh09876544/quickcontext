import re
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True, slots=True)
class CompressionStats:
    """
    Metrics from a compression pass.

    original_lines: int — Line count before compression.
    compressed_lines: int — Line count after compression.
    blank_lines_removed: int — Blank lines stripped.
    comment_lines_removed: int — Comment-only lines stripped.
    import_lines_collapsed: int — Import lines collapsed into placeholders.
    boilerplate_lines_removed: int — Getter/setter/trivial body lines removed.
    """
    original_lines: int
    compressed_lines: int
    blank_lines_removed: int
    comment_lines_removed: int
    import_lines_collapsed: int
    boilerplate_lines_removed: int


_COMMENT_PATTERNS: dict[str, re.Pattern] = {
    "python": re.compile(r"^\s*#(?!\s*type:)"),
    "javascript": re.compile(r"^\s*//"),
    "typescript": re.compile(r"^\s*//"),
    "rust": re.compile(r"^\s*//"),
    "go": re.compile(r"^\s*//"),
    "java": re.compile(r"^\s*//"),
    "c": re.compile(r"^\s*//"),
    "cpp": re.compile(r"^\s*//"),
    "c_sharp": re.compile(r"^\s*//"),
    "ruby": re.compile(r"^\s*#"),
    "php": re.compile(r"^\s*(?://|#)"),
    "bash": re.compile(r"^\s*#(?!!)"),
    "swift": re.compile(r"^\s*//"),
    "scala": re.compile(r"^\s*//"),
    "lua": re.compile(r"^\s*--"),
    "elixir": re.compile(r"^\s*#"),
    "hcl": re.compile(r"^\s*#"),
    "sql": re.compile(r"^\s*--"),
    "zig": re.compile(r"^\s*//"),
    "haskell": re.compile(r"^\s*--"),
    "ocaml": re.compile(r"^\s*\(\*.*\*\)\s*$"),
    "r": re.compile(r"^\s*#"),
}

_BLOCK_COMMENT_START: dict[str, str] = {
    "python": '"""',
    "javascript": "/*",
    "typescript": "/*",
    "rust": "/*",
    "go": "/*",
    "java": "/*",
    "c": "/*",
    "cpp": "/*",
    "c_sharp": "/*",
    "php": "/*",
    "css": "/*",
    "swift": "/*",
    "scala": "/*",
    "lua": "--[[",
    "haskell": "{-",
    "ocaml": "(*",
}

_BLOCK_COMMENT_END: dict[str, str] = {
    "python": '"""',
    "javascript": "*/",
    "typescript": "*/",
    "rust": "*/",
    "go": "*/",
    "java": "*/",
    "c": "*/",
    "cpp": "*/",
    "c_sharp": "*/",
    "php": "*/",
    "css": "*/",
    "swift": "*/",
    "scala": "*/",
    "lua": "]]",
    "haskell": "-}",
    "ocaml": "*)",
}

_IMPORT_PATTERNS: dict[str, re.Pattern] = {
    "python": re.compile(r"^\s*(?:from\s+\S+\s+)?import\s+"),
    "javascript": re.compile(r"^\s*import\s+"),
    "typescript": re.compile(r"^\s*import\s+"),
    "rust": re.compile(r"^\s*use\s+"),
    "go": re.compile(r"^\s*import\s+"),
    "java": re.compile(r"^\s*import\s+"),
    "c": re.compile(r"^\s*#\s*include\s+"),
    "cpp": re.compile(r"^\s*#\s*include\s+"),
    "c_sharp": re.compile(r"^\s*using\s+"),
    "php": re.compile(r"^\s*(?:use|require|include)\s+"),
    "ruby": re.compile(r"^\s*require\s+"),
    "swift": re.compile(r"^\s*import\s+"),
    "scala": re.compile(r"^\s*import\s+"),
    "elixir": re.compile(r"^\s*(?:import|alias|use|require)\s+"),
    "hcl": re.compile(r"^\s*source\s*="),
    "sql": re.compile(r"^\s*(?:USE|\\i|\\include)\s+"),
    "protobuf": re.compile(r"^\s*import\s+"),
    "zig": re.compile(r"^\s*const\s+\w+\s*=\s*@import"),
    "haskell": re.compile(r"^\s*import\s+"),
    "ocaml": re.compile(r"^\s*open\s+"),
    "r": re.compile(r"^\s*(?:library|require)\s*\("),
}

_TRIVIAL_BODY = re.compile(
    r"^\s*(?:pass|return\s+self\._\w+|return\s+self\.\w+|\.{3}|raise\s+NotImplementedError)\s*$"
)

_PROPERTY_DECORATOR = re.compile(r"^\s*@(?:property|\w+\.setter)\s*$")


def _strip_blank_lines(lines: list[str]) -> tuple[list[str], int]:
    """
    Collapse consecutive blank lines into at most one.

    lines: list[str] — Source lines.
    Returns: tuple[list[str], int] — (filtered_lines, removed_count).
    """
    out: list[str] = []
    removed = 0
    prev_blank = False

    for line in lines:
        is_blank = line.strip() == ""
        if is_blank:
            if prev_blank:
                removed += 1
                continue
            prev_blank = True
        else:
            prev_blank = False
        out.append(line)

    if out and out[-1].strip() == "":
        out.pop()
        removed += 1

    return out, removed


def _strip_comments(
    lines: list[str],
    language: Optional[str],
    preserve_first_block: bool = True,
) -> tuple[list[str], int]:
    """
    Remove single-line and block comments. Preserves the first block comment
    (assumed to be a docstring) when preserve_first_block is True.

    lines: list[str] — Source lines.
    language: Optional[str] — Programming language for pattern selection.
    preserve_first_block: bool — Keep the first block comment (docstring).
    Returns: tuple[list[str], int] — (filtered_lines, removed_count).
    """
    if not language:
        return lines, 0

    lang = language.lower()
    line_pat = _COMMENT_PATTERNS.get(lang)
    block_start = _BLOCK_COMMENT_START.get(lang)
    block_end = _BLOCK_COMMENT_END.get(lang)

    out: list[str] = []
    removed = 0
    in_block = False
    first_block_seen = False

    for line in lines:
        stripped = line.strip()

        if in_block:
            if block_end and block_end in stripped:
                in_block = False
                if first_block_seen and preserve_first_block:
                    pass
                else:
                    removed += 1
                    continue
            if first_block_seen and preserve_first_block:
                pass
            else:
                removed += 1
                continue

        if block_start and stripped.startswith(block_start):
            if not first_block_seen:
                first_block_seen = True
                if block_end and block_end in stripped[len(block_start):]:
                    out.append(line)
                    continue
                in_block = True
                out.append(line)
                continue
            else:
                if block_end and block_end in stripped[len(block_start):]:
                    removed += 1
                    continue
                in_block = True
                removed += 1
                continue

        if lang == "python" and stripped.startswith(("'''", '"""')):
            marker = stripped[:3]
            if not first_block_seen:
                first_block_seen = True
                if stripped.count(marker) >= 2 and len(stripped) > 3:
                    out.append(line)
                    continue
                in_block = True
                block_end_override = marker
                out.append(line)
                continue
            else:
                if stripped.count(marker) >= 2 and len(stripped) > 3:
                    removed += 1
                    continue
                in_block = True
                removed += 1
                continue

        if line_pat and line_pat.match(line):
            removed += 1
            continue

        out.append(line)

    return out, removed


def _collapse_imports(
    lines: list[str],
    language: Optional[str],
) -> tuple[list[str], int]:
    """
    Collapse contiguous import blocks into a single placeholder line.

    lines: list[str] — Source lines.
    language: Optional[str] — Programming language for import pattern detection.
    Returns: tuple[list[str], int] — (filtered_lines, collapsed_count).
    """
    if not language:
        return lines, 0

    lang = language.lower()
    pat = _IMPORT_PATTERNS.get(lang)
    if not pat:
        return lines, 0

    out: list[str] = []
    collapsed = 0
    import_run: list[str] = []

    def flush_run() -> int:
        """
        Flush accumulated import lines into a placeholder.

        Returns: int — Number of lines collapsed (0 if run was short).
        """
        if len(import_run) <= 2:
            out.extend(import_run)
            return 0
        indent = ""
        for ch in import_run[0]:
            if ch in (" ", "\t"):
                indent += ch
            else:
                break
        out.append(f"{indent}# ... ({len(import_run)} import lines collapsed)")
        saved = len(import_run) - 1
        return saved

    for line in lines:
        stripped = line.strip()
        if pat.match(line) or (import_run and stripped == ""):
            import_run.append(line)
            continue

        if import_run:
            collapsed += flush_run()
            import_run.clear()

        out.append(line)

    if import_run:
        collapsed += flush_run()

    return out, collapsed


def _strip_boilerplate(
    lines: list[str],
    language: Optional[str],
) -> tuple[list[str], int]:
    """
    Replace trivial getter/setter/pass bodies with ellipsis placeholder.

    lines: list[str] — Source lines.
    language: Optional[str] — Programming language.
    Returns: tuple[list[str], int] — (filtered_lines, removed_count).
    """
    if not language or language.lower() != "python":
        return lines, 0

    out: list[str] = []
    removed = 0
    i = 0

    while i < len(lines):
        line = lines[i]

        if _PROPERTY_DECORATOR.match(line) and i + 2 < len(lines):
            def_line = lines[i + 1]
            body_line = lines[i + 2] if i + 2 < len(lines) else ""

            if "def " in def_line and _TRIVIAL_BODY.match(body_line):
                out.append(line)
                out.append(def_line)
                out.append(body_line.split("#")[0].rstrip().replace(
                    body_line.strip(), "..."
                ) if "..." not in body_line else body_line)
                removed += 0
                i += 3
                continue

        out.append(line)
        i += 1

    return out, removed


def compress_source(
    source: str,
    level: str = "medium",
    language: Optional[str] = None,
) -> tuple[str, CompressionStats]:
    """
    Apply language-aware compression to source code.

    source: str — Raw source code text.
    level: str — Compression level: "light", "medium", or "aggressive".
    language: Optional[str] — Programming language name (python, javascript, etc.).
    Returns: tuple[str, CompressionStats] — (compressed_source, stats).
    """
    lines = source.split("\n")
    original_count = len(lines)
    blank_removed = 0
    comment_removed = 0
    import_collapsed = 0
    boilerplate_removed = 0

    lines = [line.rstrip() for line in lines]

    lines, blank_removed = _strip_blank_lines(lines)

    if level in ("medium", "aggressive"):
        lines, comment_removed = _strip_comments(lines, language)
        lines, extra_blanks = _strip_blank_lines(lines)
        blank_removed += extra_blanks

    if level == "aggressive":
        lines, import_collapsed = _collapse_imports(lines, language)
        lines, boilerplate_removed = _strip_boilerplate(lines, language)
        lines, extra_blanks = _strip_blank_lines(lines)
        blank_removed += extra_blanks

    compressed = "\n".join(lines)

    stats = CompressionStats(
        original_lines=original_count,
        compressed_lines=len(lines),
        blank_lines_removed=blank_removed,
        comment_lines_removed=comment_removed,
        import_lines_collapsed=import_collapsed,
        boilerplate_lines_removed=boilerplate_removed,
    )

    return compressed, stats


def compress_grep_line(line: str) -> str:
    """
    Strip trailing whitespace and collapse internal whitespace runs in a grep match line.

    line: str — Raw matched line text.
    Returns: str — Compressed line.
    """
    return re.sub(r"[ \t]+", " ", line.rstrip())
