use tree_sitter::Language;
use crate::lang::LanguageSpec;
use crate::types::SymbolKind;


const QUERY: &str = r#"
(function_declaration
    name: (_) @name
    body: (block)? @body) @definition

(variable_declaration
    (assignment_statement
        (variable_list
            name: (_) @name)
        (expression_list
            value: (function_definition)? @body))) @definition
"#;


const PATTERN_KINDS: &[SymbolKind] = &[
    SymbolKind::Function,
    SymbolKind::Variable,
];


pub fn spec() -> LanguageSpec {
    LanguageSpec {
        name: "lua",
        language: Language::from(tree_sitter_lua::LANGUAGE),
        extensions: &["lua"],
        query: QUERY,
        pattern_kinds: PATTERN_KINDS,
    }
}
