use tree_sitter::Language;
use crate::lang::LanguageSpec;
use crate::types::SymbolKind;


const QUERY: &str = r#"
(method
    name: (identifier) @name
    parameters: (method_parameters)? @params
    body: (body_statement) @body) @definition

(singleton_method
    name: (identifier) @name
    parameters: (method_parameters)? @params
    body: (body_statement) @body) @definition

(class
    name: [(constant) (scope_resolution)] @name
    body: (body_statement) @body) @definition

(module
    name: [(constant) (scope_resolution)] @name
    body: (body_statement) @body) @definition
"#;


const PATTERN_KINDS: &[SymbolKind] = &[
    SymbolKind::Method,
    SymbolKind::Method,
    SymbolKind::Class,
    SymbolKind::Module,
];


pub fn spec() -> LanguageSpec {
    LanguageSpec {
        name: "ruby",
        language: Language::from(tree_sitter_ruby::LANGUAGE),
        extensions: &["rb", "rake", "gemspec"],
        query: QUERY,
        pattern_kinds: PATTERN_KINDS,
    }
}
