use tree_sitter::Language;
use crate::lang::LanguageSpec;
use crate::types::SymbolKind;


const QUERY: &str = r#"
(function_definition
    name: (identifier) @name
    body: (_)? @body) @definition

(class_definition
    name: (identifier) @name
    body: (template_body)? @body) @definition

(object_definition
    name: (identifier) @name
    body: (template_body)? @body) @definition

(trait_definition
    name: (identifier) @name
    body: (template_body)? @body) @definition

(val_definition
    pattern: (_) @name) @definition

(var_definition
    pattern: (_) @name) @definition

(type_definition
    name: (identifier) @name) @definition

(import_declaration) @definition
"#;


const PATTERN_KINDS: &[SymbolKind] = &[
    SymbolKind::Function,
    SymbolKind::Class,
    SymbolKind::Module,
    SymbolKind::Trait,
    SymbolKind::Constant,
    SymbolKind::Variable,
    SymbolKind::TypeAlias,
    SymbolKind::Import,
];


pub fn spec() -> LanguageSpec {
    LanguageSpec {
        name: "scala",
        language: Language::from(tree_sitter_scala::LANGUAGE),
        extensions: &["scala", "sc"],
        query: QUERY,
        pattern_kinds: PATTERN_KINDS,
    }
}
