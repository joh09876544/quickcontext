use tree_sitter::Language;
use crate::lang::LanguageSpec;
use crate::types::SymbolKind;


const QUERY: &str = r#"
(function_definition
    name: (identifier) @name
    parameters: (parameters) @params
    return_type: (_)? @return_type
    body: (block) @body) @definition

(class_definition
    name: (identifier) @name
    body: (block) @body) @definition

(decorated_definition
    (decorator) @decorator
    definition: (function_definition
        name: (identifier) @name
        parameters: (parameters) @params
        return_type: (_)? @return_type
        body: (block) @body)) @definition

(decorated_definition
    (decorator) @decorator
    definition: (class_definition
        name: (identifier) @name
        body: (block) @body)) @definition

(import_statement) @definition

(import_from_statement
    module_name: (dotted_name) @name) @definition

(assignment
    left: (identifier) @name
    right: (_) @body) @definition

(assignment
    left: (identifier) @name
    type: (type) @return_type
    right: (_) @body) @definition
"#;


const PATTERN_KINDS: &[SymbolKind] = &[
    SymbolKind::Function,
    SymbolKind::Class,
    SymbolKind::Function,
    SymbolKind::Class,
    SymbolKind::Import,
    SymbolKind::Import,
    SymbolKind::Variable,
    SymbolKind::Variable,
];


pub fn spec() -> LanguageSpec {
    LanguageSpec {
        name: "python",
        language: Language::from(tree_sitter_python::LANGUAGE),
        extensions: &["py", "pyi"],
        query: QUERY,
        pattern_kinds: PATTERN_KINDS,
    }
}
