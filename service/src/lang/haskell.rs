use tree_sitter::Language;
use crate::lang::LanguageSpec;
use crate::types::SymbolKind;


const QUERY: &str = r#"
(function
    name: (variable) @name) @definition

(signature
    name: (variable) @name) @definition

(data_type
    name: (_) @name) @definition

(class
    name: (_) @name) @definition

(instance
    name: (_) @name) @definition

(import) @definition
"#;


const PATTERN_KINDS: &[SymbolKind] = &[
    SymbolKind::Function,
    SymbolKind::Function,
    SymbolKind::TypeAlias,
    SymbolKind::Class,
    SymbolKind::Class,
    SymbolKind::Import,
];


pub fn spec() -> LanguageSpec {
    LanguageSpec {
        name: "haskell",
        language: Language::from(tree_sitter_haskell::LANGUAGE),
        extensions: &["hs", "lhs"],
        query: QUERY,
        pattern_kinds: PATTERN_KINDS,
    }
}
