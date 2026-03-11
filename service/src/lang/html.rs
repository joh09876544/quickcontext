use tree_sitter::Language;
use crate::lang::LanguageSpec;
use crate::types::SymbolKind;


const QUERY: &str = r#"
(element
    (start_tag
        (tag_name) @name)) @definition

(script_element
    (start_tag
        (tag_name) @name)) @definition

(style_element
    (start_tag
        (tag_name) @name)) @definition
"#;


const PATTERN_KINDS: &[SymbolKind] = &[
    SymbolKind::HtmlTag,
    SymbolKind::HtmlTag,
    SymbolKind::HtmlTag,
];


pub fn spec() -> LanguageSpec {
    LanguageSpec {
        name: "html",
        language: Language::from(tree_sitter_html::LANGUAGE),
        extensions: &["html", "htm"],
        query: QUERY,
        pattern_kinds: PATTERN_KINDS,
    }
}
