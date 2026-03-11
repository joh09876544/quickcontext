use tree_sitter::Language;
use crate::lang::LanguageSpec;
use crate::types::SymbolKind;


const QUERY: &str = r#"
(call
    target: (identifier) @_keyword
    (arguments (alias) @name)
    (do_block) @body
    (#match? @_keyword "^defmodule$")) @definition

(call
    target: (identifier) @_keyword
    (arguments
        (call
            target: (identifier) @name))
    (do_block)? @body
    (#match? @_keyword "^def$")) @definition

(call
    target: (identifier) @_keyword
    (arguments
        (call
            target: (identifier) @name))
    (do_block)? @body
    (#match? @_keyword "^defp$")) @definition

(call
    target: (identifier) @_keyword
    (arguments
        (call
            target: (identifier) @name))
    (do_block)? @body
    (#match? @_keyword "^defmacro$")) @definition

(call
    target: (identifier) @_keyword
    (arguments (alias) @name)
    (do_block) @body
    (#match? @_keyword "^defprotocol$")) @definition

(call
    target: (identifier) @_keyword
    (arguments (alias) @name)
    (do_block) @body
    (#match? @_keyword "^defimpl$")) @definition
"#;


const PATTERN_KINDS: &[SymbolKind] = &[
    SymbolKind::Module,
    SymbolKind::Function,
    SymbolKind::Function,
    SymbolKind::Decorator,
    SymbolKind::Interface,
    SymbolKind::Class,
];


pub fn spec() -> LanguageSpec {
    LanguageSpec {
        name: "elixir",
        language: Language::from(tree_sitter_elixir::LANGUAGE),
        extensions: &["ex", "exs"],
        query: QUERY,
        pattern_kinds: PATTERN_KINDS,
    }
}
