use tree_sitter::Language;
use crate::lang::LanguageSpec;
use crate::types::SymbolKind;


const QUERY: &str = r#"
(function_definition
    name: (name) @name
    parameters: (formal_parameters) @params
    body: (compound_statement) @body) @definition

(method_declaration
    name: (name) @name
    parameters: (formal_parameters) @params
    body: (compound_statement) @body) @definition

(class_declaration
    name: (name) @name
    body: (declaration_list) @body) @definition

(interface_declaration
    name: (name) @name
    body: (declaration_list) @body) @definition

(trait_declaration
    name: (name) @name
    body: (declaration_list) @body) @definition

(enum_declaration
    name: (name) @name
    body: (enum_declaration_list) @body) @definition

(namespace_definition
    name: (namespace_name) @name
    body: (compound_statement) @body) @definition
"#;


const PATTERN_KINDS: &[SymbolKind] = &[
    SymbolKind::Function,
    SymbolKind::Method,
    SymbolKind::Class,
    SymbolKind::Interface,
    SymbolKind::Trait,
    SymbolKind::Enum,
    SymbolKind::Module,
];


pub fn spec() -> LanguageSpec {
    LanguageSpec {
        name: "php",
        language: Language::from(tree_sitter_php::LANGUAGE_PHP),
        extensions: &["php"],
        query: QUERY,
        pattern_kinds: PATTERN_KINDS,
    }
}
