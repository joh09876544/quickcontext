use tree_sitter::Language;
use crate::lang::LanguageSpec;
use crate::types::SymbolKind;


const QUERY: &str = r#"
(function_item
    name: (identifier) @name
    parameters: (parameters) @params
    return_type: (_)? @return_type
    body: (block) @body) @definition

(struct_item
    name: (type_identifier) @name
    body: (field_declaration_list)? @body) @definition

(enum_item
    name: (type_identifier) @name
    body: (enum_variant_list) @body) @definition

(impl_item
    type: (_) @name
    body: (declaration_list) @body) @definition

(trait_item
    name: (type_identifier) @name
    body: (declaration_list) @body) @definition

(type_item
    name: (type_identifier) @name
    type: (_) @body) @definition

(const_item
    name: (identifier) @name
    type: (_)? @return_type
    value: (_)? @body) @definition

(static_item
    name: (identifier) @name
    type: (_)? @return_type
    value: (_)? @body) @definition

(mod_item
    name: (identifier) @name
    body: (declaration_list)? @body) @definition

(use_declaration
    argument: (_) @name) @definition
"#;


const PATTERN_KINDS: &[SymbolKind] = &[
    SymbolKind::Function,
    SymbolKind::Struct,
    SymbolKind::Enum,
    SymbolKind::Class,
    SymbolKind::Trait,
    SymbolKind::TypeAlias,
    SymbolKind::Constant,
    SymbolKind::Variable,
    SymbolKind::Module,
    SymbolKind::Import,
];


pub fn spec() -> LanguageSpec {
    LanguageSpec {
        name: "rust",
        language: Language::from(tree_sitter_rust::LANGUAGE),
        extensions: &["rs"],
        query: QUERY,
        pattern_kinds: PATTERN_KINDS,
    }
}
