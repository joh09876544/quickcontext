use tree_sitter::Language;
use crate::lang::LanguageSpec;
use crate::types::SymbolKind;


const QUERY: &str = r#"
(function_definition
    name: (word) @name
    body: (compound_statement) @body) @definition

(variable_assignment
    name: (variable_name) @name
    value: (_) @body) @definition
"#;


const PATTERN_KINDS: &[SymbolKind] = &[
    SymbolKind::Function,
    SymbolKind::Variable,
];


pub fn spec() -> LanguageSpec {
    LanguageSpec {
        name: "bash",
        language: Language::from(tree_sitter_bash::LANGUAGE),
        extensions: &["sh", "bash", "zsh"],
        query: QUERY,
        pattern_kinds: PATTERN_KINDS,
    }
}
