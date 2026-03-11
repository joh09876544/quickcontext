use std::fs::File;
use std::io::{BufRead, BufReader};
use std::path::Path;
use std::sync::atomic::{AtomicUsize, Ordering};
use std::sync::mpsc;
use std::sync::Arc;
use std::time::Instant;

use ignore::WalkBuilder;

use crate::types::{GrepMatch, GrepResult};

const QUICK_IGNORE_FILENAME: &str = ".quick-ignore";

pub fn grep_path(
    query: &str,
    root: &Path,
    respect_gitignore: bool,
    limit: usize,
    before_context: usize,
    after_context: usize,
) -> Result<GrepResult, String> {
    if query.is_empty() {
        return Err("query cannot be empty".to_string());
    }
    if !root.exists() {
        return Err(format!("path does not exist: {}", root.display()));
    }

    let start = Instant::now();
    let effective_limit = limit.max(1);

    if root.is_file() {
        let mut matches = Vec::new();
        search_file(root, query, effective_limit, before_context, after_context, &mut matches);
        let elapsed_ms = start.elapsed().as_millis();
        return Ok(GrepResult {
            matches,
            searched_files: 1,
            duration_ms: elapsed_ms,
            truncated: false,
        });
    }

    let mut builder = WalkBuilder::new(root);
    builder
        .hidden(true)
        .add_custom_ignore_filename(QUICK_IGNORE_FILENAME)
        .threads(std::thread::available_parallelism().map_or(4, usize::from));

    if !respect_gitignore {
        builder.git_ignore(false).git_global(false).git_exclude(false);
    }

    let (tx, rx) = mpsc::channel::<GrepMatch>();
    let query = Arc::new(query.to_string());
    let match_count = Arc::new(AtomicUsize::new(0));
    let searched_files = Arc::new(AtomicUsize::new(0));

    builder.build_parallel().run(|| {
        let tx = tx.clone();
        let query = Arc::clone(&query);
        let match_count = Arc::clone(&match_count);
        let searched_files = Arc::clone(&searched_files);
        let before_ctx = before_context;
        let after_ctx = after_context;

        Box::new(move |entry| {
            if match_count.load(Ordering::Relaxed) >= effective_limit {
                return ignore::WalkState::Quit;
            }

            let entry = match entry {
                Ok(e) => e,
                Err(_) => return ignore::WalkState::Continue,
            };

            if !entry.file_type().map_or(false, |ft| ft.is_file()) {
                return ignore::WalkState::Continue;
            }

            searched_files.fetch_add(1, Ordering::Relaxed);

            let file_path = entry.path();
            let file = match File::open(file_path) {
                Ok(f) => f,
                Err(_) => return ignore::WalkState::Continue,
            };

            let mut reader = BufReader::new(file);
            let mut line = String::new();
            let mut line_number = 0usize;
            let mut before_lines: Vec<(usize, String)> = Vec::new();
            let mut after_count = 0usize;
            let mut in_after_context = false;
            let mut pending_match: Option<GrepMatch> = None;

            loop {
                if match_count.load(Ordering::Relaxed) >= effective_limit && !in_after_context {
                    return ignore::WalkState::Quit;
                }

                line.clear();
                let read = match reader.read_line(&mut line) {
                    Ok(n) => n,
                    Err(_) => break,
                };
                if read == 0 {
                    break;
                }

                line_number += 1;

                if line.contains('\0') {
                    break;
                }

                let trimmed = line.trim_end_matches(['\r', '\n']).to_string();

                if in_after_context {
                    if after_count > 0 {
                        if let Some(ref mut m) = pending_match {
                            m.context_after.push(trimmed.clone());
                        }
                        after_count -= 1;
                    } else {
                        if let Some(m) = pending_match.take() {
                            let _ = tx.send(m);
                        }
                        in_after_context = false;
                    }

                    if let Some(byte_idx) = line.find(query.as_str()) {
                        if match_count.load(Ordering::Relaxed) < effective_limit {
                            let col_start = line[..byte_idx].chars().count() + 1;
                            let col_end = col_start + query.chars().count() - 1;

                            before_lines = before_lines.iter()
                                .skip(before_lines.len().saturating_sub(before_ctx))
                                .cloned()
                                .collect();

                            if let Some(m) = pending_match.take() {
                                let _ = tx.send(m);
                            }

                            pending_match = Some(GrepMatch {
                                file_path: file_path.to_string_lossy().to_string(),
                                line_number,
                                column_start: col_start,
                                column_end: col_end,
                                line: trimmed.clone(),
                                context_before: before_lines.iter().map(|(_, l)| l.clone()).collect(),
                                context_after: Vec::new(),
                            });

                            let prev = match_count.fetch_add(1, Ordering::Relaxed);
                            if prev >= effective_limit {
                                if let Some(m) = pending_match.take() {
                                    let _ = tx.send(m);
                                }
                                return ignore::WalkState::Quit;
                            }

                            after_count = after_ctx;
                            in_after_context = after_count > 0;
                        }
                    }
                } else {
                    if let Some(byte_idx) = line.find(query.as_str()) {
                        let prev = match_count.fetch_add(1, Ordering::Relaxed);
                        if prev < effective_limit {
                            let col_start = line[..byte_idx].chars().count() + 1;
                            let col_end = col_start + query.chars().count() - 1;

                            before_lines = before_lines.iter()
                                .skip(before_lines.len().saturating_sub(before_ctx))
                                .cloned()
                                .collect();

                            pending_match = Some(GrepMatch {
                                file_path: file_path.to_string_lossy().to_string(),
                                line_number,
                                column_start: col_start,
                                column_end: col_end,
                                line: trimmed.clone(),
                                context_before: before_lines.iter().map(|(_, l)| l.clone()).collect(),
                                context_after: Vec::new(),
                            });

                            after_count = after_ctx;
                            in_after_context = after_count > 0;

                            if after_count == 0 {
                                if let Some(m) = pending_match.take() {
                                    let _ = tx.send(m);
                                }
                            }
                        }
                    }
                }

                before_lines.push((line_number, trimmed));
                if before_lines.len() > before_ctx + 1 {
                    before_lines.remove(0);
                }
            }

            if let Some(m) = pending_match.take() {
                let _ = tx.send(m);
            }

            ignore::WalkState::Continue
        })
    });

    drop(tx);

    let mut matches = Vec::new();
    for m in rx {
        matches.push(m);
    }

    matches.sort_by(|a, b| {
        a.file_path
            .cmp(&b.file_path)
            .then(a.line_number.cmp(&b.line_number))
            .then(a.column_start.cmp(&b.column_start))
    });

    if matches.len() > effective_limit {
        matches.truncate(effective_limit);
    }

    let elapsed_ms = start.elapsed().as_millis();
    Ok(GrepResult {
        matches,
        searched_files: searched_files.load(Ordering::Relaxed),
        duration_ms: elapsed_ms,
        truncated: match_count.load(Ordering::Relaxed) > effective_limit,
    })
}

fn search_file(
    path: &Path,
    query: &str,
    limit: usize,
    before_context: usize,
    after_context: usize,
    out: &mut Vec<GrepMatch>,
) {
    let file = match File::open(path) {
        Ok(f) => f,
        Err(_) => return,
    };

    let mut reader = BufReader::new(file);
    let mut line = String::new();
    let mut line_number = 0usize;
    let mut before_lines: Vec<(usize, String)> = Vec::new();
    let mut after_count = 0usize;
    let mut in_after_context = false;
    let mut pending_match: Option<GrepMatch> = None;

    while out.len() < limit || in_after_context {
        line.clear();
        let read = match reader.read_line(&mut line) {
            Ok(n) => n,
            Err(_) => break,
        };
        if read == 0 {
            break;
        }

        line_number += 1;

        if line.contains('\0') {
            break;
        }

        let trimmed = line.trim_end_matches(['\r', '\n']).to_string();

        if in_after_context {
            if after_count > 0 {
                if let Some(ref mut m) = pending_match {
                    m.context_after.push(trimmed.clone());
                }
                after_count -= 1;
            } else {
                if let Some(m) = pending_match.take() {
                    out.push(m);
                }
                in_after_context = false;
            }

            if out.len() >= limit {
                break;
            }

            if let Some(byte_idx) = line.find(query) {
                let col_start = line[..byte_idx].chars().count() + 1;
                let col_end = col_start + query.chars().count() - 1;

                before_lines = before_lines.iter()
                    .skip(before_lines.len().saturating_sub(before_context))
                    .cloned()
                    .collect();

                if let Some(m) = pending_match.take() {
                    out.push(m);
                }

                pending_match = Some(GrepMatch {
                    file_path: path.to_string_lossy().to_string(),
                    line_number,
                    column_start: col_start,
                    column_end: col_end,
                    line: trimmed.clone(),
                    context_before: before_lines.iter().map(|(_, l)| l.clone()).collect(),
                    context_after: Vec::new(),
                });

                after_count = after_context;
                in_after_context = after_count > 0;

                if after_count == 0 {
                    if let Some(m) = pending_match.take() {
                        out.push(m);
                    }
                }
            }
        } else {
            if let Some(byte_idx) = line.find(query) {
                let col_start = line[..byte_idx].chars().count() + 1;
                let col_end = col_start + query.chars().count() - 1;

                before_lines = before_lines.iter()
                    .skip(before_lines.len().saturating_sub(before_context))
                    .cloned()
                    .collect();

                if let Some(m) = pending_match.take() {
                    out.push(m);
                }

                pending_match = Some(GrepMatch {
                    file_path: path.to_string_lossy().to_string(),
                    line_number,
                    column_start: col_start,
                    column_end: col_end,
                    line: trimmed.clone(),
                    context_before: before_lines.iter().map(|(_, l)| l.clone()).collect(),
                    context_after: Vec::new(),
                });

                after_count = after_context;
                in_after_context = after_count > 0;

                if after_count == 0 {
                    if let Some(m) = pending_match.take() {
                        out.push(m);
                    }
                }
            }
        }

        before_lines.push((line_number, trimmed.clone()));
        if before_lines.len() > before_context + 1 {
            before_lines.remove(0);
        }
    }

    if let Some(m) = pending_match.take() {
        out.push(m);
    }
}
