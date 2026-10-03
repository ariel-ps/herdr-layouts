use serde_json::Value;
use std::{
    env,
    error::Error,
    fs::{self, OpenOptions},
    os::unix::fs::PermissionsExt,
    path::{Path, PathBuf},
    process::Command,
    thread,
    time::{Duration, Instant},
};

type Result<T> = std::result::Result<T, Box<dyn Error>>;

fn herdr(args: &[&str]) -> Result<Value> {
    let executable = env::var_os("HERDR_BIN_PATH")
        .filter(|s| !s.is_empty())
        .unwrap_or_else(|| "herdr".into());
    let output = Command::new(executable).args(args).output()?;
    if !output.status.success() {
        return Err(format!(
            "herdr {}: {}{}",
            args.join(" "),
            output.status,
            String::from_utf8_lossy(&output.stderr)
        )
        .into());
    }
    if output.stdout.iter().all(u8::is_ascii_whitespace) {
        return Ok(Value::Null);
    }
    let response: Value = serde_json::from_slice(&output.stdout)?;
    if let Some(error) = response.get("error") {
        return Err(format!("Herdr API: {error}").into());
    }
    response
        .get("result")
        .cloned()
        .ok_or_else(|| "Herdr response has no result".into())
}

fn string<'a>(value: &'a Value, key: &str) -> Result<&'a str> {
    value
        .get(key)
        .and_then(Value::as_str)
        .ok_or_else(|| format!("Missing or invalid {key}").into())
}

fn executable(path: &Path) -> bool {
    fs::metadata(path).is_ok_and(|m| m.is_file() && m.permissions().mode() & 0o111 != 0)
}

fn shell_quote(path: &Path) -> Result<String> {
    let text = path.to_str().ok_or("Executable path is not UTF-8")?;
    Ok(format!("'{}'", text.replace('\'', "'\"'\"'")))
}

fn label_matches(tab_id: &str, name: &str) -> Result<bool> {
    Ok(herdr(&["tab", "get", tab_id])?["tab"]["label"]
        .as_str()
        .is_some_and(|label| label.eq_ignore_ascii_case(name)))
}

fn run() -> Result<()> {
    let event: Value =
        serde_json::from_str(&env::var("HERDR_PLUGIN_EVENT_JSON").unwrap_or_else(|_| "{}".into()))?;
    let event = event.get("data").unwrap_or(&event);
    let tab = event.get("tab").unwrap_or(event);
    let name = tab["label"].as_str().unwrap_or("").to_ascii_lowercase();
    if name != "code" && name != "board" {
        return Ok(());
    }
    let tab_id = string(tab, "tab_id")?;
    if tab_id.is_empty()
        || !tab_id
            .bytes()
            .all(|b| b.is_ascii_alphanumeric() || b"_:-".contains(&b))
    {
        return Err("Named tab event has no valid tab ID".into());
    }
    let token = format!("herdr-{name}-tab");
    let state = PathBuf::from(
        env::var_os("HERDR_PLUGIN_STATE_DIR")
            .filter(|s| !s.is_empty())
            .ok_or("Missing HERDR_PLUGIN_STATE_DIR")?,
    );
    fs::create_dir_all(&state)?;
    // ponytail: serialize these rare events; per-tab locks if contention matters.
    let lock = OpenOptions::new()
        .create(true)
        .append(true)
        .open(state.join("named-tabs.lock"))?;
    lock.lock()?;
    if !label_matches(tab_id, &name)? {
        return Ok(());
    }
    let response = herdr(&["pane", "list"])?;
    let panes: Vec<_> = response["panes"]
        .as_array()
        .ok_or("Herdr response has no panes")?
        .iter()
        .filter(|p| p["tab_id"].as_str() == Some(tab_id))
        .collect();
    if panes.len() != 1 || panes[0]["tokens"].get(&token).is_some() {
        return Ok(());
    }
    let pane = panes[0];
    if !pane["agent"].is_null() && pane["agent"] != "" && pane["agent"] != false {
        return Ok(());
    }
    let pane_id = string(pane, "pane_id")?;
    let deadline =
        Instant::now() + Duration::from_secs(if event["type"] == "tab_created" { 8 } else { 0 });
    loop {
        let response = herdr(&["pane", "process-info", "--pane", pane_id])?;
        let info = &response["process_info"];
        let idle = info["foreground_processes"]
            .as_array()
            .is_some_and(|processes| {
                processes.len() == 1
                    && info["shell_pid"]
                        .as_u64()
                        .is_some_and(|pid| pid > 0 && processes[0]["pid"].as_u64() == Some(pid))
                    && processes[0]["name"]
                        .as_str()
                        .and_then(|name| Path::new(name).file_name())
                        .and_then(|name| name.to_str())
                        .is_some_and(|name| {
                            matches!(
                                name.trim_start_matches('-'),
                                "bash" | "zsh" | "sh" | "fish" | "dash"
                            )
                        })
            });
        if idle {
            break;
        }
        if Instant::now() >= deadline {
            return Ok(());
        }
        thread::sleep(Duration::from_millis(100));
    }
    if !label_matches(tab_id, &name)? {
        return Ok(());
    }
    let command = if name == "code" {
        let path = env::split_paths(&env::var_os("PATH").unwrap_or_default())
            .map(|dir| dir.join("nvim"))
            .find(|path| executable(path))
            .ok_or("Install Neovim to automatically open code tabs")?;
        format!("{} .", shell_quote(&fs::canonicalize(path)?)?)
    } else {
        let response = herdr(&["plugin", "list", "--json"])?;
        let plugin = response["plugins"]
            .as_array()
            .and_then(|plugins| {
                plugins
                    .iter()
                    .find(|p| p["plugin_id"] == "herdr-board" && p["enabled"] == true)
            })
            .ok_or("Install and enable the herdr-board plugin to open board tabs")?;
        let path = Path::new(string(plugin, "plugin_root")?).join("target/release/board");
        if !executable(&path) {
            return Err(
                "Herdr Board executable is missing; reinstall the herdr-board plugin".into(),
            );
        }
        format!("{} tui", shell_quote(&path)?)
    };
    herdr(&["pane", "run", pane_id, &command])?;
    herdr(&[
        "pane",
        "report-metadata",
        pane_id,
        "--source",
        &token,
        "--token",
        &format!("{token}=started"),
    ])?;
    Ok(())
}

fn main() {
    if let Err(error) = run() {
        eprintln!("herdr-layouts: {error}");
        std::process::exit(1);
    }
}
