use tree_sitter::Language;
use crate::lang::LanguageSpec;
use crate::types::SymbolKind;


const QUERY: &str = r#"
(function_declaration
    name: (identifier) @name
    body: (block) @body) @definition

(test_declaration
    (identifier) @name
    (block) @body) @definition

(test_declaration
    (string) @name
    (block) @body) @definition
"#;


const PATTERN_KINDS: &[SymbolKind] = &[
    SymbolKind::Function,
    SymbolKind::Function,
    SymbolKind::Function,
];


pub fn spec() -> LanguageSpec {
    LanguageSpec {
        name: "zig",
        language: Language::from(tree_sitter_zig::LANGUAGE),
        extensions: &["zig"],
        query: QUERY,
        pattern_kinds: PATTERN_KINDS,
    }
}
