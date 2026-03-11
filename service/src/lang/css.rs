use tree_sitter::Language;
use crate::lang::LanguageSpec;
use crate::types::SymbolKind;


const QUERY: &str = r#"
(rule_set
    (selectors) @name
    (block) @body) @definition

(media_statement
    (keyword_query) @name
    (block) @body) @definition

(keyframes_statement
    (keyframes_name) @name
    (keyframe_block_list) @body) @definition
"#;


const PATTERN_KINDS: &[SymbolKind] = &[
    SymbolKind::CssSelector,
    SymbolKind::CssSelector,
    SymbolKind::CssSelector,
];


pub fn spec() -> LanguageSpec {
    LanguageSpec {
        name: "css",
        language: Language::from(tree_sitter_css::LANGUAGE),
        extensions: &["css"],
        query: QUERY,
        pattern_kinds: PATTERN_KINDS,
    }
}
