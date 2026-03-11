use tree_sitter::Language;
use crate::lang::LanguageSpec;
use crate::types::SymbolKind;


const QUERY: &str = r#"
(value_definition
    (let_binding
        pattern: (_) @name
        body: (_)? @body)) @definition

(type_definition
    (type_binding
        name: (_) @name
        body: (_)? @body)) @definition

(module_definition
    (module_binding
        (module_name) @name
        body: (_)? @body)) @definition

(module_type_definition
    (module_type_name) @name
    body: (_)? @body) @definition

(external
    (value_name) @name) @definition

(exception_definition
    (constructor_declaration) @name) @definition

(open_module
    module: (_) @name) @definition
"#;


const PATTERN_KINDS: &[SymbolKind] = &[
    SymbolKind::Function,
    SymbolKind::TypeAlias,
    SymbolKind::Module,
    SymbolKind::Interface,
    SymbolKind::Function,
    SymbolKind::Class,
    SymbolKind::Import,
];


pub fn spec() -> LanguageSpec {
    LanguageSpec {
        name: "ocaml",
        language: Language::from(tree_sitter_ocaml::LANGUAGE_OCAML),
        extensions: &["ml", "mli"],
        query: QUERY,
        pattern_kinds: PATTERN_KINDS,
    }
}
