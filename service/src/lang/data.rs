use tree_sitter::Language;
use crate::lang::LanguageSpec;
use crate::types::SymbolKind;


const JSON_QUERY: &str = r#"
(pair
    key: (string) @name
    value: (_) @body) @definition
"#;

const JSON_PATTERN_KINDS: &[SymbolKind] = &[
    SymbolKind::DataKey,
];


const YAML_QUERY: &str = r#"
(block_mapping_pair
    key: (_) @name
    value: (_)? @body) @definition
"#;

const YAML_PATTERN_KINDS: &[SymbolKind] = &[
    SymbolKind::DataKey,
];


const TOML_QUERY: &str = r#"
(table
    (bare_key) @name) @definition

(pair
    (bare_key) @name
    (_) @body) @definition
"#;

const TOML_PATTERN_KINDS: &[SymbolKind] = &[
    SymbolKind::DataKey,
    SymbolKind::DataKey,
];


pub fn spec_json() -> LanguageSpec {
    LanguageSpec {
        name: "json",
        language: Language::from(tree_sitter_json::LANGUAGE),
        extensions: &["json"],
        query: JSON_QUERY,
        pattern_kinds: JSON_PATTERN_KINDS,
    }
}


pub fn spec_yaml() -> LanguageSpec {
    LanguageSpec {
        name: "yaml",
        language: Language::from(tree_sitter_yaml::LANGUAGE),
        extensions: &["yaml", "yml"],
        query: YAML_QUERY,
        pattern_kinds: YAML_PATTERN_KINDS,
    }
}


pub fn spec_toml() -> LanguageSpec {
    LanguageSpec {
        name: "toml",
        language: Language::from(tree_sitter_toml_ng::LANGUAGE),
        extensions: &["toml"],
        query: TOML_QUERY,
        pattern_kinds: TOML_PATTERN_KINDS,
    }
}
