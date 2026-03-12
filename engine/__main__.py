import sys


PARSER_ONLY_COMMANDS = {
    "parse",
    "grep",
    "symbol-lookup",
    "find-callers",
    "trace-call-graph",
    "skeleton",
    "import-graph",
    "find-importers",
}


def _find_command(argv: list[str]) -> str | None:
    skip_next = False
    for arg in argv:
        if skip_next:
            skip_next = False
            continue
        if arg == "--config":
            skip_next = True
            continue
        if arg.startswith("-"):
            continue
        return arg
    return None


def main() -> None:
    argv = sys.argv[1:]
    command = _find_command(argv)
    use_lightweight_parser_cli = (
        command in PARSER_ONLY_COMMANDS
        and (not sys.stdout.isatty() or not sys.stderr.isatty())
    )

    if use_lightweight_parser_cli:
        from engine.src.parser_cli import main as parser_main
        raise SystemExit(parser_main(argv))

    from engine.src.cli import main as cli_main
    cli_main()


if __name__ == "__main__":
    main()
