use std::collections::HashSet;
use std::sync::OnceLock;

use rust_stemmers::{Algorithm, Stemmer};
use strsim::jaro_winkler;

#[derive(Debug, Clone)]
pub struct IntentTerms {
    pub exact_terms: Vec<String>,
    pub expanded_terms: Vec<String>,
}

const MIN_FUZZY_SCORE: f64 = 0.88;

const INTENT_ALIASES: &[(&str, &str)] = &[
    ("signin", "auth"),
    ("signon", "auth"),
    ("signout", "logout"),
    ("logon", "login"),
    ("jwt", "auth"),
    ("oauth", "auth"),
    ("oauth2", "auth"),
    ("credential", "auth"),
    ("credentials", "auth"),
    ("cfg", "config"),
    ("env", "config"),
    ("db", "database"),
    ("repo", "repository"),
    ("deps", "dependency"),
    ("perm", "permission"),
    ("perms", "permission"),
    ("acct", "account"),
    ("usr", "user"),
    ("msg", "message"),
];

const INTENT_GROUPS: &[(&str, &[&str])] = &[
    (
        "auth",
        &[
            "auth",
            "authentication",
            "authenticate",
            "authorization",
            "authorize",
            "login",
            "signin",
            "session",
            "token",
            "jwt",
            "oauth",
            "credential",
            "access",
            "identity",
        ],
    ),
    (
        "login",
        &[
            "login",
            "signin",
            "authenticate",
            "auth",
            "session",
            "token",
            "credential",
            "account",
        ],
    ),
    (
        "logout",
        &[
            "logout",
            "signout",
            "revoke",
            "session",
            "token",
            "invalidate",
            "auth",
        ],
    ),
    (
        "permission",
        &[
            "permission",
            "permissions",
            "access",
            "role",
            "roles",
            "rbac",
            "policy",
            "authorize",
            "authz",
        ],
    ),
    (
        "user",
        &[
            "user",
            "users",
            "account",
            "profile",
            "member",
            "identity",
            "auth",
        ],
    ),
    (
        "database",
        &[
            "database",
            "db",
            "sql",
            "query",
            "queries",
            "schema",
            "migration",
            "table",
            "repository",
            "storage",
        ],
    ),
    (
        "config",
        &[
            "config",
            "configuration",
            "settings",
            "env",
            "options",
            "flags",
            "setup",
            "initialize",
        ],
    ),
    (
        "error",
        &[
            "error",
            "errors",
            "exception",
            "failure",
            "panic",
            "retry",
            "recover",
            "fallback",
        ],
    ),
    (
        "cache",
        &[
            "cache",
            "caching",
            "cached",
            "memo",
            "ttl",
            "invalidate",
            "evict",
        ],
    ),
    (
        "request",
        &[
            "request",
            "requests",
            "handler",
            "route",
            "routing",
            "http",
            "api",
            "endpoint",
            "middleware",
        ],
    ),
    (
        "response",
        &[
            "response",
            "responses",
            "reply",
            "result",
            "payload",
            "serialize",
            "json",
        ],
    ),
    (
        "search",
        &[
            "search",
            "query",
            "lookup",
            "find",
            "index",
            "rank",
            "bm25",
            "match",
        ],
    ),
];

pub fn normalize_intent_level(level: u8) -> u8 {
    level.clamp(1, 3)
}

pub fn build_intent_terms(query: &str, level: u8) -> IntentTerms {
    let exact_terms = extract_terms(query);
    if exact_terms.is_empty() {
        return IntentTerms {
            exact_terms,
            expanded_terms: Vec::new(),
        };
    }

    if !is_simple_query(query) {
        return IntentTerms {
            exact_terms,
            expanded_terms: Vec::new(),
        };
    }

    let normalized_level = normalize_intent_level(level);
    let max_expansions = max_expansions_for_level(normalized_level);

    let exact_set: HashSet<String> = exact_terms.iter().cloned().collect();
    let mut expanded_terms = Vec::new();
    let mut seen = HashSet::new();

    for term in &exact_terms {
        let expansions = expand_term(term, normalized_level);
        for candidate in expansions {
            if exact_set.contains(&candidate) {
                continue;
            }
            if seen.insert(candidate.clone()) {
                expanded_terms.push(candidate);
            }
            if expanded_terms.len() >= max_expansions {
                return IntentTerms {
                    exact_terms,
                    expanded_terms,
                };
            }
        }
    }

    IntentTerms {
        exact_terms,
        expanded_terms,
    }
}

pub fn expand_text_query(query: &str, level: u8) -> String {
    let terms = build_intent_terms(query, level);
    if terms.expanded_terms.is_empty() {
        return query.trim().to_string();
    }

    let mut merged = String::new();
    let base = query.trim();
    if !base.is_empty() {
        merged.push_str(base);
    }

    for term in terms.expanded_terms {
        if !merged.is_empty() {
            merged.push(' ');
        }
        merged.push_str(&term);
    }

    merged
}

fn is_simple_query(query: &str) -> bool {
    let trimmed = query.trim();
    if trimmed.is_empty() {
        return false;
    }

    let upper = trimmed.to_ascii_uppercase();
    if upper.contains(" AND ") || upper.contains(" OR ") {
        return false;
    }

    if trimmed.contains('"')
        || trimmed.contains('(')
        || trimmed.contains(')')
        || trimmed.contains('+')
        || trimmed.contains('-')
        || trimmed.contains(':')
    {
        return false;
    }

    extract_terms(trimmed).len() <= 6
}

fn max_expansions_for_level(level: u8) -> usize {
    match level {
        1 => 6,
        2 => 14,
        _ => 24,
    }
}

fn per_group_limit(level: u8) -> usize {
    match level {
        1 => 5,
        2 => 8,
        _ => usize::MAX,
    }
}

fn expand_term(term: &str, level: u8) -> Vec<String> {
    let canonical = canonical_term(term);
    let canonical_stem = stem(&canonical);

    let mut matched: Option<&[&str]> = None;

    for (group_key, group_terms) in INTENT_GROUPS {
        if canonical == *group_key || group_terms.iter().any(|item| *item == canonical) {
            matched = Some(*group_terms);
            break;
        }

        if level >= 2 && jaro_winkler(&canonical, group_key) >= MIN_FUZZY_SCORE {
            matched = Some(*group_terms);
            break;
        }

        if level >= 2 && canonical_stem == stem(group_key) {
            matched = Some(*group_terms);
            break;
        }
    }

    let Some(group_terms) = matched else {
        return Vec::new();
    };

    let mut out = Vec::new();
    let mut seen = HashSet::new();
    let limit = per_group_limit(level);

    for item in group_terms.iter().take(limit) {
        let value = (*item).to_string();
        if seen.insert(value.clone()) {
            out.push(value);
        }
    }

    out
}

fn canonical_term(term: &str) -> String {
    let lower = term.to_ascii_lowercase();
    for (alias, canonical) in INTENT_ALIASES {
        if *alias == lower {
            return (*canonical).to_string();
        }
    }
    lower
}

fn extract_terms(input: &str) -> Vec<String> {
    let mut terms = Vec::new();
    let mut seen = HashSet::new();

    for raw in input
        .split(|ch: char| !ch.is_ascii_alphanumeric() && ch != '_')
        .filter(|chunk| !chunk.is_empty())
    {
        let lower = raw.to_ascii_lowercase();
        if seen.insert(lower.clone()) {
            terms.push(lower);
        }
    }

    terms
}

fn stem(input: &str) -> String {
    stemmer().stem(input).to_string()
}

fn stemmer() -> &'static Stemmer {
    static STEMMER: OnceLock<Stemmer> = OnceLock::new();
    STEMMER.get_or_init(|| Stemmer::create(Algorithm::English))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn expands_auth_query() {
        let expanded = expand_text_query("auth", 2);
        assert!(expanded.contains("authentication"));
        assert!(expanded.contains("login"));
    }

    #[test]
    fn skips_complex_query_expansion() {
        let expanded = expand_text_query("auth AND token", 3);
        assert_eq!(expanded, "auth AND token");
    }

    #[test]
    fn normalizes_level() {
        assert_eq!(normalize_intent_level(0), 1);
        assert_eq!(normalize_intent_level(2), 2);
        assert_eq!(normalize_intent_level(10), 3);
    }
}
