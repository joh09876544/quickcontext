use tree_sitter::Language;
use crate::lang::LanguageSpec;
use crate::types::SymbolKind;


const QUERY: &str = r#"
(atx_heading
    (atx_h1_marker)
    heading_content: (_) @name) @definition

(atx_heading
    (atx_h2_marker)
    heading_content: (_) @name) @definition

(atx_heading
    (atx_h3_marker)
    heading_content: (_) @name) @definition

(atx_heading
    (atx_h4_marker)
    heading_content: (_) @name) @definition

(atx_heading
    (atx_h5_marker)
    heading_content: (_) @name) @definition

(atx_heading
    (atx_h6_marker)
    heading_content: (_) @name) @definition
"#;


const PATTERN_KINDS: &[SymbolKind] = &[
    SymbolKind::Heading,
    SymbolKind::Heading,
    SymbolKind::Heading,
    SymbolKind::Heading,
    SymbolKind::Heading,
    SymbolKind::Heading,
];


pub fn spec() -> LanguageSpec {
    LanguageSpec {
        name: "markdown",
        language: Language::from(tree_sitter_md::LANGUAGE),
        extensions: &["md", "markdown"],
        query: QUERY,
        pattern_kinds: PATTERN_KINDS,
    }
}
