use tree_sitter::Language;
use crate::lang::LanguageSpec;
use crate::types::SymbolKind;


const QUERY: &str = r#"
(function_declaration
    name: (identifier) @name
    parameters: (parameter_list) @params
    result: (_)? @return_type
    body: (block) @body) @definition

(method_declaration
    receiver: (parameter_list) @params
    name: (field_identifier) @name
    result: (_)? @return_type
    body: (block) @body) @definition

(type_declaration
    (type_spec
        name: (type_identifier) @name
        type: (struct_type
            (field_declaration_list) @body))) @definition

(type_declaration
    (type_spec
        name: (type_identifier) @name
        type: (interface_type) @body)) @definition

(type_declaration
    (type_spec
        name: (type_identifier) @name
        type: (_) @body)) @definition

(import_declaration) @definition

(const_declaration
    (const_spec
        name: (identifier) @name
        type: (_)? @return_type
        value: (_)? @body)) @definition

(var_declaration
    (var_spec
        name: (identifier) @name
        type: (_)? @return_type
        value: (_)? @body)) @definition
"#;


const PATTERN_KINDS: &[SymbolKind] = &[
    SymbolKind::Function,
    SymbolKind::Method,
    SymbolKind::Struct,
    SymbolKind::Interface,
    SymbolKind::TypeAlias,
    SymbolKind::Import,
    SymbolKind::Constant,
    SymbolKind::Variable,
];


pub fn spec() -> LanguageSpec {
    LanguageSpec {
        name: "go",
        language: Language::from(tree_sitter_go::LANGUAGE),
        extensions: &["go"],
        query: QUERY,
        pattern_kinds: PATTERN_KINDS,
    }
}
