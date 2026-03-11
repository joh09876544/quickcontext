use tree_sitter::Language;
use crate::lang::LanguageSpec;
use crate::types::SymbolKind;


const QUERY: &str = r#"
(block
    (identifier) @name
    (body) @body) @definition

(attribute
    (identifier) @name) @definition
"#;


const PATTERN_KINDS: &[SymbolKind] = &[
    SymbolKind::Module,
    SymbolKind::Property,
];


pub fn spec() -> LanguageSpec {
    LanguageSpec {
        name: "hcl",
        language: Language::from(tree_sitter_hcl::LANGUAGE),
        extensions: &["hcl", "tf", "tfvars"],
        query: QUERY,
        pattern_kinds: PATTERN_KINDS,
    }
}
