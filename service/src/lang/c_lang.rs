use tree_sitter::Language;
use crate::lang::LanguageSpec;
use crate::types::SymbolKind;


const QUERY: &str = r#"
(function_definition
    declarator: (function_declarator
        declarator: (identifier) @name
        parameters: (parameter_list) @params)
    body: (compound_statement) @body) @definition

(struct_specifier
    name: (type_identifier) @name
    body: (field_declaration_list) @body) @definition

(enum_specifier
    name: (type_identifier) @name
    body: (enumerator_list) @body) @definition

(type_definition
    declarator: (type_identifier) @name) @definition

(declaration
    declarator: (init_declarator
        declarator: (identifier) @name
        value: (_) @body)) @definition

(preproc_include) @definition

(preproc_def
    name: (identifier) @name
    value: (_)? @body) @definition
"#;


const PATTERN_KINDS: &[SymbolKind] = &[
    SymbolKind::Function,
    SymbolKind::Struct,
    SymbolKind::Enum,
    SymbolKind::TypeAlias,
    SymbolKind::Variable,
    SymbolKind::Import,
    SymbolKind::Constant,
];


pub fn spec() -> LanguageSpec {
    LanguageSpec {
        name: "c",
        language: Language::from(tree_sitter_c::LANGUAGE),
        extensions: &["c", "h"],
        query: QUERY,
        pattern_kinds: PATTERN_KINDS,
    }
}
