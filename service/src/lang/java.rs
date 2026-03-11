use tree_sitter::Language;
use crate::lang::LanguageSpec;
use crate::types::SymbolKind;


const QUERY: &str = r#"
(method_declaration
    name: (identifier) @name
    parameters: (formal_parameters) @params
    body: (block) @body) @definition

(constructor_declaration
    name: (identifier) @name
    parameters: (formal_parameters) @params
    body: (constructor_body) @body) @definition

(class_declaration
    name: (identifier) @name
    body: (class_body) @body) @definition

(interface_declaration
    name: (identifier) @name
    body: (interface_body) @body) @definition

(enum_declaration
    name: (identifier) @name
    body: (enum_body) @body) @definition

(field_declaration
    declarator: (variable_declarator
        name: (identifier) @name)) @definition

(import_declaration) @definition
"#;


const PATTERN_KINDS: &[SymbolKind] = &[
    SymbolKind::Method,
    SymbolKind::Constructor,
    SymbolKind::Class,
    SymbolKind::Interface,
    SymbolKind::Enum,
    SymbolKind::Property,
    SymbolKind::Import,
];


pub fn spec() -> LanguageSpec {
    LanguageSpec {
        name: "java",
        language: Language::from(tree_sitter_java::LANGUAGE),
        extensions: &["java"],
        query: QUERY,
        pattern_kinds: PATTERN_KINDS,
    }
}
