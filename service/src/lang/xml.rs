use tree_sitter::Language;
use crate::lang::LanguageSpec;
use crate::types::SymbolKind;


const QUERY: &str = r#"
(element
    (STag
        (Name) @name)) @definition

(element
    (EmptyElemTag
        (Name) @name)) @definition
"#;


const PATTERN_KINDS: &[SymbolKind] = &[
    SymbolKind::HtmlTag,
    SymbolKind::HtmlTag,
];


pub fn spec() -> LanguageSpec {
    LanguageSpec {
        name: "xml",
        language: Language::from(tree_sitter_xml::LANGUAGE_XML),
        extensions: &["xml", "xsl", "xslt", "xsd", "svg", "plist", "csproj", "fsproj", "vcxproj"],
        query: QUERY,
        pattern_kinds: PATTERN_KINDS,
    }
}
