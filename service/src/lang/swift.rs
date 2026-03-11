use tree_sitter::Language;
use crate::lang::LanguageSpec;
use crate::types::SymbolKind;


const QUERY: &str = r#"
(function_declaration
    name: (simple_identifier) @name
    body: (function_body)? @body) @definition

(class_declaration
    name: (_) @name
    body: (_) @body) @definition

(protocol_declaration
    name: (type_identifier) @name
    body: (protocol_body) @body) @definition

(property_declaration
    name: (pattern) @name) @definition

(typealias_declaration
    name: (type_identifier) @name) @definition

(import_declaration) @definition
"#;


const PATTERN_KINDS: &[SymbolKind] = &[
    SymbolKind::Function,
    SymbolKind::Class,
    SymbolKind::Interface,
    SymbolKind::Property,
    SymbolKind::TypeAlias,
    SymbolKind::Import,
];


pub fn spec() -> LanguageSpec {
    LanguageSpec {
        name: "swift",
        language: Language::from(tree_sitter_swift::LANGUAGE),
        extensions: &["swift"],
        query: QUERY,
        pattern_kinds: PATTERN_KINDS,
    }
}
