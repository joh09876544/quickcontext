use std::collections::HashMap;
use std::sync::Arc;

use tokio::io::{AsyncBufReadExt, AsyncReadExt, AsyncWriteExt, BufReader};
use tokio::process::{ChildStdin, ChildStdout};
use tokio::sync::{Mutex, oneshot};

use super::jsonrpc::{Id, JsonRpcMessage, JsonRpcNotification, JsonRpcRequest};


pub type PendingMap = Arc<Mutex<HashMap<i64, oneshot::Sender<JsonRpcMessage>>>>;
pub type DiagnosticsMap = Arc<Mutex<HashMap<String, serde_json::Value>>>;


/// Encode a JSON-RPC message with Content-Length header for LSP wire format.
///
/// body: &[u8] — JSON-encoded message bytes.
pub fn encode_message(body: &[u8]) -> Vec<u8> {
    let header = format!("Content-Length: {}\r\n\r\n", body.len());
    let mut out = Vec::with_capacity(header.len() + body.len());
    out.extend_from_slice(header.as_bytes());
    out.extend_from_slice(body);
    out
}


/// Send a JSON-RPC request over the LSP stdin pipe.
///
/// stdin: &Mutex<ChildStdin> — Locked handle to the language server's stdin.
/// req: &JsonRpcRequest — The request to serialize and send.
pub async fn send_request(stdin: &Mutex<ChildStdin>, req: &JsonRpcRequest) -> Result<(), String> {
    let body = serde_json::to_vec(req).map_err(|e| format!("serialize request: {e}"))?;
    send_raw(stdin, &body).await
}


/// Send a JSON-RPC notification over the LSP stdin pipe.
///
/// stdin: &Mutex<ChildStdin> — Locked handle to the language server's stdin.
/// notif: &JsonRpcNotification — The notification to serialize and send.
pub async fn send_notification(
    stdin: &Mutex<ChildStdin>,
    notif: &JsonRpcNotification,
) -> Result<(), String> {
    let body = serde_json::to_vec(notif).map_err(|e| format!("serialize notification: {e}"))?;
    send_raw(stdin, &body).await
}


/// Write a Content-Length framed payload to stdin.
///
/// stdin: &Mutex<ChildStdin> — Locked handle to the language server's stdin.
/// body: &[u8] — JSON-encoded message bytes.
async fn send_raw(stdin: &Mutex<ChildStdin>, body: &[u8]) -> Result<(), String> {
    let frame = encode_message(body);
    let mut lock = stdin.lock().await;
    lock.write_all(&frame).await.map_err(|e| format!("write stdin: {e}"))?;
    lock.flush().await.map_err(|e| format!("flush stdin: {e}"))?;
    Ok(())
}


/// Read a single Content-Length framed message from a buffered reader.
///
/// reader: &mut BufReader<ChildStdout> — Buffered stdout of the language server.
async fn read_message(reader: &mut BufReader<ChildStdout>) -> Result<JsonRpcMessage, String> {
    let mut content_length: Option<usize> = None;
    let mut line = String::new();

    loop {
        line.clear();
        let n = reader.read_line(&mut line).await.map_err(|e| format!("read header: {e}"))?;
        if n == 0 {
            return Err("language server closed stdout".to_string());
        }
        let trimmed = line.trim();
        if trimmed.is_empty() {
            break;
        }
        if let Some(val) = trimmed.strip_prefix("Content-Length:") {
            content_length = Some(
                val.trim().parse::<usize>().map_err(|e| format!("invalid Content-Length: {e}"))?,
            );
        }
    }

    let len = content_length.ok_or_else(|| "missing Content-Length header".to_string())?;
    if len > 32 * 1024 * 1024 {
        return Err(format!("Content-Length too large: {len}"));
    }

    let mut body = vec![0u8; len];
    reader.read_exact(&mut body).await.map_err(|e| format!("read body: {e}"))?;
    serde_json::from_slice(&body).map_err(|e| format!("parse JSON-RPC message: {e}"))
}


/// Background task that reads messages from the language server's stdout.
///
/// Routes responses to waiting callers via the pending map.
/// Stores diagnostics from publishDiagnostics notifications.
///
/// stdout: ChildStdout — The language server's stdout handle (moved in).
/// pending: PendingMap — Shared map of request ID -> oneshot sender.
/// diagnostics: DiagnosticsMap — Shared map of URI -> diagnostics array.
/// server_name: String — Name for log messages.
pub async fn stdout_reader_task(
    stdout: ChildStdout,
    pending: PendingMap,
    diagnostics: DiagnosticsMap,
    server_name: String,
) {
    let mut reader = BufReader::new(stdout);

    loop {
        let msg = match read_message(&mut reader).await {
            Ok(m) => m,
            Err(e) => {
                eprintln!("[lsp:{server_name}] reader stopped: {e}");
                break;
            }
        };

        if msg.is_response() {
            let id = match &msg.id {
                Some(Id::Number(n)) => *n,
                _ => continue,
            };
            let mut map = pending.lock().await;
            if let Some(tx) = map.remove(&id) {
                let _ = tx.send(msg);
            }
        } else if msg.is_notification() {
            let method = msg.method.as_deref().unwrap_or("unknown");
            if method == "textDocument/publishDiagnostics" {
                if let Some(params) = &msg.params {
                    if let Some(uri) = params.get("uri").and_then(|v| v.as_str()) {
                        let mut diag_map = diagnostics.lock().await;
                        diag_map.insert(uri.to_string(), params.clone());
                    }
                }
            }
        }
    }

    let mut map = pending.lock().await;
    map.clear();
}
