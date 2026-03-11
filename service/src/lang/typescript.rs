use tree_sitter::Language;
use crate::lang::LanguageSpec;
use crate::types::SymbolKind;


const QUERY: &str = r#"
(function_declaration
    name: (identifier) @name
    parameters: (formal_parameters) @params
    return_type: (type_annotation)? @return_type
    body: (statement_block) @body) @definition

(class_declaration
    name: (type_identifier) @name
    body: (class_body) @body) @definition

(method_definition
    name: (property_identifier) @name
    parameters: (formal_parameters) @params
    return_type: (type_annotation)? @return_type
    body: (statement_block) @body) @definition

(interface_declaration
    name: (type_identifier) @name
    body: (interface_body) @body) @definition

(type_alias_declaration
    name: (type_identifier) @name
    value: (_) @body) @definition

(enum_declaration
    name: (identifier) @name
    body: (enum_body) @body) @definition

(export_statement
    (function_declaration
        name: (identifier) @name
        parameters: (formal_parameters) @params
        return_type: (type_annotation)? @return_type
        body: (statement_block) @body)) @definition

(export_statement
    (class_declaration
        name: (type_identifier) @name
        body: (class_body) @body)) @definition

(export_statement
    (interface_declaration
        name: (type_identifier) @name
        body: (interface_body) @body)) @definition

(import_statement) @definition
"#;


const PATTERN_KINDS: &[SymbolKind] = &[
    SymbolKind::Function,
    SymbolKind::Class,
    SymbolKind::Method,
    SymbolKind::Interface,
    SymbolKind::TypeAlias,
    SymbolKind::Enum,
    SymbolKind::Function,
    SymbolKind::Class,
    SymbolKind::Interface,
    SymbolKind::Import,
];


pub fn spec() -> LanguageSpec {
    LanguageSpec {
        name: "typescript",
        language: Language::from(tree_sitter_typescript::LANGUAGE_TYPESCRIPT),
        extensions: &["ts", "mts"],
        query: QUERY,
        pattern_kinds: PATTERN_KINDS,
    }
}


pub fn spec_tsx() -> LanguageSpec {
    LanguageSpec {
        name: "tsx",
        language: Language::from(tree_sitter_typescript::LANGUAGE_TSX),
        extensions: &["tsx"],
        query: QUERY,
        pattern_kinds: PATTERN_KINDS,
    }
}
