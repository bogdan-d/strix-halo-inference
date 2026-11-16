//! Fixed native controls; launchers remain the authority for engine configuration.
use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use std::{
    collections::BTreeMap,
    fs,
    path::{Path, PathBuf},
    process::Stdio,
    sync::{
        atomic::{AtomicU64, AtomicUsize, Ordering},
        Arc, Mutex,
    },
    time::{Duration, Instant},
};
use tauri::{ipc::Channel, Webview};
use tokio::{io::AsyncReadExt, process::Command, sync::oneshot, time::timeout};

const ENGINES: [&str; 3] = ["halogen", "gufo", "strixite"];
const COMPONENTS: [&str; 3] = ["prometheus", "exporter", "probe"];
pub struct Backend {
    pub root: PathBuf,
    busy: Mutex<BTreeMap<String, String>>,
    details: tokio::sync::Mutex<Option<(Instant, Value)>>,
    revision: AtomicU64,
    viewer: Mutex<Option<(u64, oneshot::Sender<()>)>>,
    active_viewers: Arc<AtomicUsize>,
}
impl Backend {
    pub fn new(root: PathBuf) -> Self {
        Self {
            root,
            busy: Mutex::new(BTreeMap::new()),
            details: tokio::sync::Mutex::new(None),
            revision: AtomicU64::new(0),
            viewer: Mutex::new(None),
            active_viewers: Arc::new(AtomicUsize::new(0)),
        }
    }
    pub fn has_viewers(&self) -> bool {
        self.active_viewers.load(Ordering::SeqCst) > 0
    }
    pub fn is_busy(&self) -> bool {
        !self.busy.lock().unwrap().is_empty()
    }
    fn acquire(&self, target: &str, state: &str) -> Result<Busy<'_>, String> {
        let mut busy = self.busy.lock().unwrap();
        if busy.contains_key(target) {
            return Err(format!("{target} already has an operation running"));
        }
        busy.insert(target.into(), state.into());
        Ok(Busy(self, target.into()))
    }
    pub fn stop_logs(&self, id: Option<u64>) {
        let mut viewer = self.viewer.lock().unwrap();
        if viewer
            .as_ref()
            .is_some_and(|(current, _)| id.is_none_or(|id| id == *current))
        {
            if let Some((_, cancel)) = viewer.take() {
                let _ = cancel.send(());
            }
        }
    }
}
struct Busy<'a>(&'a Backend, String);
impl Drop for Busy<'_> {
    fn drop(&mut self) {
        self.0.busy.lock().unwrap().remove(&self.1);
        self.0.revision.fetch_add(1, Ordering::SeqCst);
    }
}
pub fn authorize(view: &Webview) -> Result<(), String> {
    let url = view.url().map_err(|e| e.to_string())?;
    if view.label() == "main"
        && (url.scheme() == "tauri"
            || (url.scheme() == "http" && url.host_str() == Some("tauri.localhost")))
    {
        Ok(())
    } else {
        Err("Only the bundled dashboard may use native controls".into())
    }
}
#[derive(Debug, Serialize)]
pub struct CommandResult {
    status: u16,
    text: String,
}
fn command(root: &Path, program: &str, args: &[&str]) -> Command {
    let mut cmd = Command::new(program);
    cmd.args(args)
        .current_dir(root)
        .process_group(0)
        .stdin(Stdio::null())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .kill_on_drop(true);
    for name in ["WEIGHTS", "GUFO_MODEL", "NPU_MODELS"] {
        cmd.env_remove(name);
    }
    cmd
}
async fn run(mut cmd: Command, seconds: u64) -> Result<CommandResult, String> {
    let child = cmd.spawn().map_err(|e| e.to_string())?;
    let pid = child.id().ok_or("Helper exited before waiting")?;
    let wait = child.wait_with_output();
    tokio::pin!(wait);
    let output = match timeout(Duration::from_secs(seconds), &mut wait).await {
        Ok(result) => result.map_err(|e| e.to_string())?,
        Err(_) => {
            unsafe {
                libc::kill(-(pid as i32), libc::SIGKILL);
            }
            let _ = timeout(Duration::from_secs(5), &mut wait).await;
            return Err(format!(
                "No result after {seconds} seconds. Inspect the engine status before retrying."
            ));
        }
    };
    let mut text = String::from_utf8_lossy(&output.stdout).into_owned();
    text.push_str(&String::from_utf8_lossy(&output.stderr));
    Ok(CommandResult {
        status: if output.status.success() { 200 } else { 409 },
        text,
    })
}
#[derive(Debug, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum Engine {
    Halogen,
    Gufo,
    Strixite,
}
impl Engine {
    fn name(&self) -> &'static str {
        match self {
            Self::Halogen => "halogen",
            Self::Gufo => "gufo",
            Self::Strixite => "strixite",
        }
    }
}
#[derive(Debug, Deserialize)]
#[serde(tag = "kind", rename_all = "snake_case", deny_unknown_fields)]
pub enum Action {
    Start {
        engine: Engine,
        profile: String,
        npu: bool,
    },
    Stop {
        engine: Engine,
    },
    Clear {
        engine: Engine,
    },
    Monitoring {
        start: bool,
    },
}
fn action_args(action: &Action) -> Result<(&str, &str, Vec<String>, bool), String> {
    let (target, state, args, npu) = match action {
        Action::Start {
            engine,
            profile,
            npu,
        } => {
            if profile.is_empty()
                || !profile
                    .bytes()
                    .all(|b| b.is_ascii_alphanumeric() || b == b'-' || b == b'_')
            {
                return Err("Invalid weight profile".into());
            }
            if *npu && !matches!(engine, Engine::Halogen) {
                return Err("Only Halogen supports NPU models".into());
            }
            (
                engine.name(),
                "starting",
                vec!["bin/run.sh", engine.name(), "start", "--weights", profile],
                *npu,
            )
        }
        Action::Stop { engine } => (
            engine.name(),
            "stopping",
            vec!["bin/run.sh", engine.name(), "stop"],
            false,
        ),
        Action::Clear { engine } => (
            engine.name(),
            "clearing",
            vec!["bin/cache.sh", engine.name(), "clear"],
            false,
        ),
        Action::Monitoring { start } => (
            "monitoring",
            if *start { "starting" } else { "stopping" },
            vec!["bin/monitor.sh", if *start { "start" } else { "stop" }],
            false,
        ),
    };
    Ok((
        target,
        state,
        args.into_iter().map(str::to_owned).collect(),
        npu,
    ))
}
fn npu_models() -> String {
    std::env::var("DASHBOARD_NPU_MODELS")
        .unwrap_or_else(|_| "decider-0.8b,embeddinggemma-2,qwen3guard-stream-0.6b".into())
}
async fn weights(root: &Path, engine: &str) -> Result<Value, String> {
    let result = run(
        command(root, "python3", &["-I", "bin/weights.py", engine, "list"]),
        15,
    )
    .await?;
    if result.status != 200 {
        return Err(result.text);
    }
    Ok(Value::Array(
        result
            .text
            .lines()
            .map(|line| {
                let fields: Vec<_> = line.splitn(3, '\t').collect();
                if fields.len() != 3 {
                    return Err("Invalid weights response".into());
                }
                Ok(json!({"id":fields[0],"available":fields[1]=="installed","label":fields[2]}))
            })
            .collect::<Result<_, String>>()?,
    ))
}
#[tauri::command]
pub async fn dashboard_action(
    webview: Webview,
    backend: tauri::State<'_, Backend>,
    action: Action,
) -> Result<CommandResult, String> {
    authorize(&webview)?;
    let (target, state, args, npu) = action_args(&action)?;
    let _busy = backend.acquire(target, state)?;
    if let Action::Start {
        engine, profile, ..
    } = &action
    {
        let entries = weights(&backend.root, engine.name()).await?;
        if !entries
            .as_array()
            .unwrap()
            .iter()
            .any(|entry| entry["id"] == *profile && entry["available"] == true)
        {
            return Err("Unknown or unavailable weight profile; refresh the selection".into());
        }
    }
    let mut cmd = command(
        &backend.root,
        "bash",
        &args.iter().map(String::as_str).collect::<Vec<_>>(),
    );
    if npu {
        cmd.env("NPU_MODELS", npu_models());
    }
    eprintln!("dashboard_action: {action:?}");
    let result = run(cmd, 180).await;
    eprintln!(
        "dashboard_action finished: {}",
        result
            .as_ref()
            .map(|r| r.status.to_string())
            .unwrap_or_else(|e| e.clone())
    );
    result
}
fn disk_bytes(path: &Path) -> std::io::Result<u64> {
    use std::os::unix::fs::MetadataExt;
    let entries = match fs::read_dir(path) {
        Ok(entries) => entries,
        Err(e) if e.kind() == std::io::ErrorKind::NotFound => return Ok(0),
        Err(e) => return Err(e),
    };
    let mut bytes = 0;
    for entry in entries {
        let entry = entry?;
        let meta = match fs::symlink_metadata(entry.path()) {
            Ok(meta) => meta,
            Err(error) if error.kind() == std::io::ErrorKind::NotFound => continue,
            Err(error) => return Err(error),
        };
        bytes += if meta.is_dir() {
            disk_bytes(&entry.path())?
        } else {
            meta.blocks() * 512
        };
    }
    Ok(bytes)
}
async fn details(backend: &Backend) -> Result<Value, String> {
    let mut cache = backend.details.lock().await;
    let revision = backend.revision.load(Ordering::SeqCst);
    if let Some((when, value)) = &*cache {
        if when.elapsed() < Duration::from_secs(30) && value["revision"] == revision {
            return Ok(value.clone());
        }
    }
    let mut entries = json!({});
    for engine in ENGINES {
        entries[engine] = weights(&backend.root, engine).await?;
    }
    let cache_root = std::env::var_os("CACHE_ROOT")
        .filter(|s| !s.is_empty())
        .map(PathBuf::from)
        .unwrap_or_else(|| {
            PathBuf::from(std::env::var_os("HOME").unwrap_or_default())
                .join(".cache/strix-halo-inference")
        });
    let caches = tauri::async_runtime::spawn_blocking(move || -> Result<Value, String> {
        let mut values = json!({});
        for engine in ENGINES {
            values[engine] =
                json!(disk_bytes(&cache_root.join(engine)).map_err(|e| e.to_string())?);
        }
        Ok(values)
    })
    .await
    .map_err(|e| e.to_string())??;
    let value = json!({"weights":entries,"caches":caches,"revision":revision});
    *cache = Some((Instant::now(), value.clone()));
    Ok(value)
}
fn state_from(
    containers: &Value,
    busy: &BTreeMap<String, String>,
    ready: &[bool; 3],
) -> Result<Value, String> {
    let list = containers.as_array().ok_or("Invalid Podman response")?;
    let named = |name: &str| {
        list.iter().find(|c| {
            c["Names"]
                .as_array()
                .is_some_and(|names| names.iter().any(|n| n == name))
        })
    };
    let mut engines = json!({});
    let mut logs = Vec::new();
    for (i, engine) in ENGINES.iter().enumerate() {
        let c = named(&format!("strix-halo-{engine}"));
        let state = busy.get(*engine).map(String::as_str).unwrap_or(match c {
            None => "stopped",
            Some(c) if c["State"] != "running" => "stopping",
            _ if ready[i] => "ready",
            _ => "starting",
        });
        engines[*engine] = json!({"state":state,"since":c.map(|c|c["StartedAt"].clone()).unwrap_or(json!(0)),"weights":c.map(|c|c["Labels"]["io.strix-halo-inference.weights"].as_str().unwrap_or("unknown"))});
        if c.is_some() {
            logs.push(*engine);
        }
    }
    let mut running = 0;
    for component in COMPONENTS {
        if let Some(c) = named(&format!("strix-halo-monitor-{component}")) {
            logs.push(component);
            if c["State"] == "running" {
                running += 1;
            }
        }
    }
    Ok(
        json!({"engines":engines,"logs":logs,"monitoring":busy.get("monitoring").map(String::as_str).unwrap_or(match running {0=>"off",3=>"on",_=>"partial"}),"npu_models":npu_models()}),
    )
}
#[tauri::command]
pub async fn dashboard_state(
    webview: Webview,
    backend: tauri::State<'_, Backend>,
) -> Result<Value, String> {
    authorize(&webview)?;
    let result = run(
        command(
            &backend.root,
            "podman",
            &["ps", "--all", "--format", "json"],
        ),
        10,
    )
    .await?;
    if result.status != 200 {
        return Err(result.text);
    }
    let containers: Value = serde_json::from_str(&result.text).map_err(|e| e.to_string())?;
    let mut ready = [false; 3];
    for (i, url) in [
        "http://127.0.0.1:8731/health",
        "http://127.0.0.1:8080/ready",
        "http://127.0.0.1:5300/health",
    ]
    .iter()
    .enumerate()
    {
        if containers.as_array().is_some_and(|list| {
            list.iter().any(|c| {
                c["State"] == "running"
                    && c["Names"].as_array().is_some_and(|names| {
                        names
                            .iter()
                            .any(|n| n == &format!("strix-halo-{}", ENGINES[i]))
                    })
            })
        }) {
            ready[i] = run(
                command(
                    &backend.root,
                    "curl",
                    &[
                        "--noproxy",
                        "*",
                        "-fsS",
                        "--max-time",
                        "1",
                        "-o",
                        "/dev/null",
                        url,
                    ],
                ),
                2,
            )
            .await
            .is_ok_and(|r| r.status == 200);
        }
    }
    let extra = details(&backend).await?;
    let mut value = state_from(&containers, &backend.busy.lock().unwrap(), &ready)?;
    value["weights"] = extra["weights"].clone();
    value["caches"] = extra["caches"].clone();
    Ok(value)
}
fn log_args(source: &str) -> Result<Vec<&str>, String> {
    if ENGINES.contains(&source) {
        Ok(vec!["bin/run.sh", source, "logs", "--follow"])
    } else if COMPONENTS.contains(&source) {
        Ok(vec!["bin/monitor.sh", source, "logs", "--follow"])
    } else {
        Err("Unknown log source".into())
    }
}
#[derive(Clone, Serialize)]
pub struct LogChunk {
    bytes: Vec<u8>,
    done: bool,
}
#[tauri::command]
pub fn logs_stop(
    webview: Webview,
    backend: tauri::State<'_, Backend>,
    id: u64,
) -> Result<(), String> {
    authorize(&webview)?;
    backend.stop_logs(Some(id));
    Ok(())
}
#[tauri::command]
pub async fn logs_start(
    webview: Webview,
    backend: tauri::State<'_, Backend>,
    source: String,
    id: u64,
    channel: Channel<LogChunk>,
) -> Result<(), String> {
    authorize(&webview)?;
    let args = log_args(&source)?;
    let mut child = command(&backend.root, "bash", &args)
        .spawn()
        .map_err(|e| e.to_string())?;
    let pid = child.id().ok_or("Log viewer exited")?;
    let mut stdout = child.stdout.take().unwrap();
    let mut stderr = child.stderr.take().unwrap();
    let (cancel, mut canceled) = oneshot::channel();
    backend.stop_logs(None);
    *backend.viewer.lock().unwrap() = Some((id, cancel));
    let active = backend.active_viewers.clone();
    active.fetch_add(1, Ordering::SeqCst);
    tauri::async_runtime::spawn(async move {
        let mut out = [0; 8192];
        let mut err = [0; 8192];
        let mut out_end = false;
        let mut err_end = false;
        loop {
            let chunk = tokio::select! {
                _=&mut canceled => break,
                result=stdout.read(&mut out), if !out_end => match result {Ok(0)|Err(_)=>{out_end=true;Vec::new()},Ok(n)=>out[..n].to_vec()},
                result=stderr.read(&mut err), if !err_end => match result {Ok(0)|Err(_)=>{err_end=true;Vec::new()},Ok(n)=>err[..n].to_vec()},
                _=tokio::time::sleep(Duration::from_secs(1)) => Vec::new(),
            };
            if channel
                .send(LogChunk {
                    bytes: chunk,
                    done: out_end && err_end,
                })
                .is_err()
                || out_end && err_end
            {
                break;
            }
        }
        // Only this viewer's group, never an engine or its detached monitor.
        unsafe {
            libc::kill(-(pid as i32), libc::SIGTERM);
        }
        if timeout(Duration::from_secs(2), child.wait()).await.is_err() {
            unsafe {
                libc::kill(-(pid as i32), libc::SIGKILL);
            }
            let _ = child.wait().await;
        }
        active.fetch_sub(1, Ordering::SeqCst);
    });
    Ok(())
}
#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn fixed_actions_and_busy_lifetime() {
        for bad in [
            r#"{"kind":"start","engine":"other","profile":"default","npu":false}"#,
            r#"{"kind":"monitoring","start":true,"command":"sh"}"#,
            r#"{"kind":"pull","engine":"halogen"}"#,
        ] {
            assert!(serde_json::from_str::<Action>(bad).is_err());
        }
        assert!(action_args(&Action::Start {
            engine: Engine::Gufo,
            profile: "../x".into(),
            npu: false
        })
        .is_err());
        assert!(action_args(&Action::Start {
            engine: Engine::Gufo,
            profile: "default".into(),
            npu: true
        })
        .is_err());
        assert_eq!(
            action_args(&Action::Start {
                engine: Engine::Halogen,
                profile: "default".into(),
                npu: true
            })
            .unwrap()
            .2,
            vec!["bin/run.sh", "halogen", "start", "--weights", "default"]
        );
        assert!(log_args("../other").is_err());
        let b = Backend::new(PathBuf::new());
        let guard = b.acquire("halogen", "starting").unwrap();
        assert!(b.is_busy());
        assert!(b.acquire("halogen", "stopping").is_err());
        drop(guard);
        assert!(!b.is_busy());
    }
    #[test]
    fn external_state_and_partial_monitoring() {
        let c = json!([{"Names":["strix-halo-gufo"],"State":"running","StartedAt":42,"Labels":{"io.strix-halo-inference.weights":"iq4-xs"}},{"Names":["strix-halo-monitor-exporter"],"State":"running"}]);
        let state = state_from(&c, &BTreeMap::new(), &[false, true, false]).unwrap();
        assert_eq!(state["engines"]["gufo"]["state"], "ready");
        assert_eq!(state["engines"]["gufo"]["weights"], "iq4-xs");
        assert_eq!(state["monitoring"], "partial");
    }
    #[test]
    fn env_scrub_failure_and_timeout() {
        tauri::async_runtime::block_on(async {
            let mut cmd = command(
                Path::new("."),
                "sh",
                &[
                    "-c",
                    "test -z \"$WEIGHTS$GUFO_MODEL$NPU_MODELS\" && echo refused; exit 1",
                ],
            );
            cmd.env_remove("WEIGHTS");
            let result = run(cmd, 5).await.unwrap();
            assert_eq!(result.status, 409);
            assert!(result.text.contains("refused"));
            let result = run(command(Path::new("."), "sh", &["-c", "sleep 20 & wait"]), 1).await;
            assert!(result.unwrap_err().contains("No result"));
        });
    }
}
