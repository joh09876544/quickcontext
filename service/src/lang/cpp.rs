use tree_sitter::Language;
use crate::lang::LanguageSpec;
use crate::types::SymbolKind;


const QUERY: &str = r#"
(function_definition
    declarator: (function_declarator
        declarator: (_) @name
        parameters: (parameter_list) @params)
    body: (compound_statement) @body) @definition

(class_specifier
    name: (type_identifier) @name
    body: (field_declaration_list) @body) @definition

(struct_specifier
    name: (type_identifier) @name
    body: (field_declaration_list) @body) @definition

(enum_specifier
    name: (type_identifier) @name
    body: (enumerator_list) @body) @definition

(namespace_definition
    name: (namespace_identifier) @name
    body: (declaration_list) @body) @definition

(template_declaration
    (function_definition
        declarator: (function_declarator
            declarator: (_) @name
            parameters: (parameter_list) @params)
        body: (compound_statement) @body)) @definition

(template_declaration
    (class_specifier
        name: (type_identifier) @name
        body: (field_declaration_list) @body)) @definition

(using_declaration) @definition

(preproc_include) @definition
"#;


const PATTERN_KINDS: &[SymbolKind] = &[
    SymbolKind::Function,
    SymbolKind::Class,
    SymbolKind::Struct,
    SymbolKind::Enum,
    SymbolKind::Module,
    SymbolKind::Function,
    SymbolKind::Class,
    SymbolKind::Import,
    SymbolKind::Import,
];


pub fn spec() -> LanguageSpec {
    LanguageSpec {
        name: "cpp",
        language: Language::from(tree_sitter_cpp::LANGUAGE),
        extensions: &["cpp", "cc", "cxx", "hpp", "hxx", "hh"],
        query: QUERY,
        pattern_kinds: PATTERN_KINDS,
    }
}
