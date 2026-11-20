//! Local Unix socket DLP client. No HTTP, DNS or external API calls.
//! The broker controls de-identification; this crate enforces transport safety.
use serde_json::{json, Value};
use std::error::Error;
use std::fmt;
use std::io::{Read, Write};
use std::net::Shutdown;
use std::os::unix::fs::{FileTypeExt, PermissionsExt};
use std::os::unix::net::UnixStream;
use std::path::Path;
use std::time::Duration;

const MAX_BYTES: usize = 1024 * 1024;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct DlpRejected;

impl fmt::Display for DlpRejected {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "DLP_REJECTED")
    }
}
impl Error for DlpRejected {}

pub fn sanitize_via_socket(socket_path: &Path, payload: &Value) -> Result<Value, DlpRejected> {
    if !socket_path.is_absolute() {
        return Err(DlpRejected);
    }
    let parent = socket_path.parent().ok_or(DlpRejected)?;
    let directory = parent.symlink_metadata().map_err(|_| DlpRejected)?;
    if directory.file_type().is_symlink() || directory.permissions().mode() & 0o077 != 0 {
        return Err(DlpRejected);
    }
    let metadata = socket_path.symlink_metadata().map_err(|_| DlpRejected)?;
    if !metadata.file_type().is_socket() {
        return Err(DlpRejected);
    }
    let request = serde_json::to_vec(&json!({"payload": payload})).map_err(|_| DlpRejected)?;
    if request.len() + 1 > MAX_BYTES {
        return Err(DlpRejected);
    }

    let mut stream = UnixStream::connect(socket_path).map_err(|_| DlpRejected)?;
    stream.set_read_timeout(Some(Duration::from_secs(5))).map_err(|_| DlpRejected)?;
    stream.set_write_timeout(Some(Duration::from_secs(5))).map_err(|_| DlpRejected)?;
    stream.write_all(&request).map_err(|_| DlpRejected)?;
    stream.write_all(b"\n").map_err(|_| DlpRejected)?;
    stream.shutdown(Shutdown::Write).map_err(|_| DlpRejected)?;

    let mut reply = Vec::new();
    stream.take((MAX_BYTES + 1) as u64).read_to_end(&mut reply).map_err(|_| DlpRejected)?;
    if reply.is_empty() || reply.len() > MAX_BYTES || reply.last() != Some(&b'\n') {
        return Err(DlpRejected);
    }
    let value: Value = serde_json::from_slice(&reply[..reply.len() - 1]).map_err(|_| DlpRejected)?;
    if value.get("ok") != Some(&Value::Bool(true)) {
        return Err(DlpRejected);
    }
    value.get("payload").cloned().ok_or(DlpRejected)
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::fs;
    use std::os::unix::net::UnixListener;
    use std::thread;
    use std::time::{SystemTime, UNIX_EPOCH};

    #[test]
    fn rejects_non_socket_paths() {
        let result = sanitize_via_socket(Path::new("/tmp/not-an-actual-dlp.sock"), &json!("secret"));
        assert_eq!(result, Err(DlpRejected));
    }

    #[test]
    fn accepts_sanitized_broker_reply() {
        let nonce = SystemTime::now().duration_since(UNIX_EPOCH).unwrap().as_nanos();
        let root = std::env::temp_dir().join(format!("offline-dlp-test-{}-{nonce}", std::process::id()));
        fs::create_dir(&root).unwrap();
        fs::set_permissions(&root, fs::Permissions::from_mode(0o700)).unwrap();
        let socket = root.join("dlp.sock");
        let listener = UnixListener::bind(&socket).unwrap();
        let handle = thread::spawn(move || {
            let (mut peer, _) = listener.accept().unwrap();
            let mut buf = [0u8; 4096];
            let _ = peer.read(&mut buf).unwrap();
            peer.write_all(b"{\"ok\":true,\"payload\":\"[REDACTED]\"}\n").unwrap();
        });
        let result = sanitize_via_socket(&socket, &json!("synthetic identifier"));
        handle.join().unwrap();
        fs::remove_file(&socket).unwrap();
        fs::remove_dir(&root).unwrap();
        assert_eq!(result, Ok(json!("[REDACTED]")));
    }
}
