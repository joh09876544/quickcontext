use std::sync::atomic::{AtomicI64, Ordering};

use serde::{Deserialize, Serialize};


static NEXT_ID: AtomicI64 = AtomicI64::new(1);


pub fn next_request_id() -> i64 {
    NEXT_ID.fetch_add(1, Ordering::Relaxed)
}


#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(untagged)]
pub enum Id {
    Number(i64),
    String(String),
}

impl From<i64> for Id {
    fn from(n: i64) -> Self {
        Self::Number(n)
    }
}


#[derive(Debug, Serialize)]
pub struct JsonRpcRequest {
    pub jsonrpc: &'static str,
    pub id: Id,
    pub method: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub params: Option<serde_json::Value>,
}

impl JsonRpcRequest {
    /// Build a new JSON-RPC 2.0 request with auto-incremented ID.
    ///
    /// method: impl Into<String> — LSP method name (e.g. "textDocument/definition").
    /// params: Option<serde_json::Value> — Request parameters, None for parameterless methods.
    pub fn new(method: impl Into<String>, params: Option<serde_json::Value>) -> Self {
        Self {
            jsonrpc: "2.0",
            id: Id::Number(next_request_id()),
            method: method.into(),
            params,
        }
    }
}


#[derive(Debug, Serialize)]
pub struct JsonRpcNotification {
    pub jsonrpc: &'static str,
    pub method: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub params: Option<serde_json::Value>,
}

impl JsonRpcNotification {
    /// Build a new JSON-RPC 2.0 notification (no ID, no response expected).
    ///
    /// method: impl Into<String> — LSP notification method name.
    /// params: Option<serde_json::Value> — Notification parameters.
    pub fn new(method: impl Into<String>, params: Option<serde_json::Value>) -> Self {
        Self {
            jsonrpc: "2.0",
            method: method.into(),
            params,
        }
    }
}


#[derive(Debug, Clone, Deserialize)]
pub struct JsonRpcResponse {
    pub id: Option<Id>,
    pub result: Option<serde_json::Value>,
    pub error: Option<JsonRpcError>,
}

impl JsonRpcResponse {
    /// Extract the numeric ID if present.
    pub fn id_number(&self) -> Option<i64> {
        match &self.id {
            Some(Id::Number(n)) => Some(*n),
            _ => None,
        }
    }
}


#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct JsonRpcError {
    pub code: i64,
    pub message: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub data: Option<serde_json::Value>,
}

impl std::fmt::Display for JsonRpcError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "LSP error {}: {}", self.code, self.message)
    }
}


#[derive(Debug, Deserialize)]
pub struct JsonRpcMessage {
    pub id: Option<Id>,
    pub method: Option<String>,
    pub result: Option<serde_json::Value>,
    pub error: Option<JsonRpcError>,
    pub params: Option<serde_json::Value>,
}

impl JsonRpcMessage {
    /// True if this is a response (has id, no method).
    pub fn is_response(&self) -> bool {
        self.id.is_some() && self.method.is_none()
    }

    /// True if this is a notification from the server (has method, no id).
    pub fn is_notification(&self) -> bool {
        self.method.is_some() && self.id.is_none()
    }

    /// True if this is a server-initiated request (has both id and method).
    pub fn is_request(&self) -> bool {
        self.id.is_some() && self.method.is_some()
    }

    /// Convert to a typed response.
    pub fn into_response(self) -> Option<JsonRpcResponse> {
        if self.is_response() {
            Some(JsonRpcResponse {
                id: self.id,
                result: self.result,
                error: self.error,
            })
        } else {
            None
        }
    }
}
