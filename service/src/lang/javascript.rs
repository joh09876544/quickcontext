use tree_sitter::Language;
use crate::lang::LanguageSpec;
use crate::types::SymbolKind;


const QUERY: &str = r#"
(function_declaration
    name: (identifier) @name
    parameters: (formal_parameters) @params
    body: (statement_block) @body) @definition

(class_declaration
    name: (identifier) @name
    body: (class_body) @body) @definition

(method_definition
    name: (property_identifier) @name
    parameters: (formal_parameters) @params
    body: (statement_block) @body) @definition

(arrow_function
    parameters: (formal_parameters) @params
    body: (_) @body) @definition

(variable_declarator
    name: (identifier) @name
    value: (arrow_function
        parameters: (formal_parameters) @params
        body: (_) @body)) @definition

(variable_declarator
    name: (identifier) @name
    value: (function_expression
        parameters: (formal_parameters) @params
        body: (statement_block) @body)) @definition

(export_statement
    (function_declaration
        name: (identifier) @name
        parameters: (formal_parameters) @params
        body: (statement_block) @body)) @definition

(export_statement
    (class_declaration
        name: (identifier) @name
        body: (class_body) @body)) @definition

(import_statement) @definition
"#;


const PATTERN_KINDS: &[SymbolKind] = &[
    SymbolKind::Function,
    SymbolKind::Class,
    SymbolKind::Method,
    SymbolKind::Function,
    SymbolKind::Variable,
    SymbolKind::Variable,
    SymbolKind::Function,
    SymbolKind::Class,
    SymbolKind::Import,
];


pub fn spec() -> LanguageSpec {
    LanguageSpec {
        name: "javascript",
        language: Language::from(tree_sitter_javascript::LANGUAGE),
        extensions: &["js", "mjs", "cjs", "jsx"],
        query: QUERY,
        pattern_kinds: PATTERN_KINDS,
    }
}
