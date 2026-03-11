use tree_sitter::Language;
use crate::lang::LanguageSpec;
use crate::types::SymbolKind;


const QUERY: &str = r#"
(binary_operator
    lhs: (identifier) @name
    operator: "<-"
    rhs: (function_definition) @body) @definition

(binary_operator
    lhs: (identifier) @name
    operator: "<-"
    rhs: (_) @body) @definition

(binary_operator
    lhs: (identifier) @name
    operator: "="
    rhs: (function_definition) @body) @definition

(binary_operator
    lhs: (identifier) @name
    operator: "="
    rhs: (_) @body) @definition
"#;


const PATTERN_KINDS: &[SymbolKind] = &[
    SymbolKind::Function,
    SymbolKind::Variable,
    SymbolKind::Function,
    SymbolKind::Variable,
];


pub fn spec() -> LanguageSpec {
    LanguageSpec {
        name: "r",
        language: Language::from(tree_sitter_r::LANGUAGE),
        extensions: &["r", "R", "Rmd"],
        query: QUERY,
        pattern_kinds: PATTERN_KINDS,
    }
}
