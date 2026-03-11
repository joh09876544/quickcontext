use tree_sitter::Language;
use crate::lang::LanguageSpec;
use crate::types::SymbolKind;


const QUERY: &str = r#"
(create_table
    (object_reference) @name) @definition

(create_function
    (object_reference) @name) @definition

(create_materialized_view
    (object_reference) @name) @definition

(create_index
    (object_reference) @name) @definition
"#;


const PATTERN_KINDS: &[SymbolKind] = &[
    SymbolKind::Class,
    SymbolKind::Function,
    SymbolKind::Class,
    SymbolKind::Property,
];


pub fn spec() -> LanguageSpec {
    LanguageSpec {
        name: "sql",
        language: Language::from(tree_sitter_sequel::LANGUAGE),
        extensions: &["sql"],
        query: QUERY,
        pattern_kinds: PATTERN_KINDS,
    }
}
