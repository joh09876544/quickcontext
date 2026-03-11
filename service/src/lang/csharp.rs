use tree_sitter::Language;
use crate::lang::LanguageSpec;
use crate::types::SymbolKind;


const QUERY: &str = r#"
(method_declaration
    name: (identifier) @name
    parameters: (parameter_list) @params
    body: (block) @body) @definition

(constructor_declaration
    name: (identifier) @name
    parameters: (parameter_list) @params
    body: (block) @body) @definition

(class_declaration
    name: (identifier) @name
    body: (declaration_list) @body) @definition

(interface_declaration
    name: (identifier) @name
    body: (declaration_list) @body) @definition

(struct_declaration
    name: (identifier) @name
    body: (declaration_list) @body) @definition

(enum_declaration
    name: (identifier) @name
    body: (enum_member_declaration_list) @body) @definition

(namespace_declaration
    name: (identifier) @name
    body: (declaration_list) @body) @definition

(property_declaration
    name: (identifier) @name) @definition

(using_directive) @definition
"#;


const PATTERN_KINDS: &[SymbolKind] = &[
    SymbolKind::Method,
    SymbolKind::Constructor,
    SymbolKind::Class,
    SymbolKind::Interface,
    SymbolKind::Struct,
    SymbolKind::Enum,
    SymbolKind::Module,
    SymbolKind::Property,
    SymbolKind::Import,
];


pub fn spec() -> LanguageSpec {
    LanguageSpec {
        name: "csharp",
        language: Language::from(tree_sitter_c_sharp::LANGUAGE),
        extensions: &["cs"],
        query: QUERY,
        pattern_kinds: PATTERN_KINDS,
    }
}
