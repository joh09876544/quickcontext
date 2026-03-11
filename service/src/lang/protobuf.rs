use tree_sitter::Language;
use crate::lang::LanguageSpec;
use crate::types::SymbolKind;


const QUERY: &str = r#"
(message
    (message_name
        (identifier) @name)
    (message_body) @body) @definition

(service
    (service_name
        (identifier) @name)) @definition

(rpc
    (rpc_name
        (identifier) @name)) @definition

(enum
    (enum_name
        (identifier) @name)
    (enum_body) @body) @definition

(import) @definition
"#;


const PATTERN_KINDS: &[SymbolKind] = &[
    SymbolKind::Struct,
    SymbolKind::Interface,
    SymbolKind::Method,
    SymbolKind::Enum,
    SymbolKind::Import,
];


pub fn spec() -> LanguageSpec {
    LanguageSpec {
        name: "protobuf",
        language: Language::from(tree_sitter_proto::LANGUAGE),
        extensions: &["proto"],
        query: QUERY,
        pattern_kinds: PATTERN_KINDS,
    }
}
